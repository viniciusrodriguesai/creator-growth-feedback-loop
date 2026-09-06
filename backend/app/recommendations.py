from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal, cast

from app.analytics import (
    AnalyticsGroupResult,
    AnalyticsResult,
    PostAnalyticsInput,
    calculate_analytics,
)

MIN_ELIGIBLE_POST_COUNT = 2
CandidateDimension = Literal["hook_type", "format", "creator"]
RecommendationDimension = Literal["hook_type", "format"]
RecommendationStatus = Literal["recommendation_available", "insufficient_data"]

RANKING_BASIS = (
    "Candidates are ranked by rate_difference, then eligible sample, views, "
    "dimension priority, and lexical value."
)
BASE_LIMITATIONS = (
    "The minimum eligible-post count is a product heuristic, not statistical "
    "significance.",
    "The result is observational and shows association, not causation.",
    "Shares are excluded from the primary comparison because share data may be "
    "unavailable.",
)
DIMENSION_PRIORITY: dict[CandidateDimension, int] = {
    "hook_type": 0,
    "format": 1,
    "creator": 2,
}


@dataclass(frozen=True, slots=True)
class CandidateEvaluation:
    dimension: CandidateDimension
    value: str
    eligible_post_count: int
    total_views: int
    known_core_engagements: int
    engagement_rate: float
    comparison_eligible_post_count: int
    comparison_total_views: int
    comparison_known_core_engagements: int
    comparison_engagement_rate: float
    contrast_vs_rest: float | None
    rate_difference: float


@dataclass(frozen=True, slots=True)
class CreatorEvidenceResult:
    value: str
    eligible_post_count: int
    total_views: int
    engagement_rate: float
    comparison_engagement_rate: float
    contrast_vs_rest: float | None
    rate_difference: float


@dataclass(frozen=True, slots=True)
class RecommendationEvidenceResult:
    summary: str
    minimum_eligible_post_count: int
    overall_eligible_post_count: int
    actionable_candidates_evaluated: int
    creator_candidates_evaluated: int
    candidate_known_core_engagements: int | None
    comparison_eligible_post_count: int | None
    comparison_total_views: int | None
    comparison_known_core_engagements: int | None
    ranking_basis: str
    strongest_creator: CreatorEvidenceResult | None


@dataclass(frozen=True, slots=True)
class RecommendationResult:
    status: RecommendationStatus
    dimension: RecommendationDimension | None
    value: str | None
    candidate_engagement_rate: float | None
    comparison_engagement_rate: float | None
    contrast_vs_rest: float | None
    rate_difference: float | None
    eligible_post_count: int | None
    total_views: int | None
    evidence: RecommendationEvidenceResult
    action: str
    limitations: tuple[str, ...]


def evaluate_candidates(
    analytics: AnalyticsResult,
    minimum_eligible_post_count: int = MIN_ELIGIBLE_POST_COUNT,
) -> tuple[CandidateEvaluation, ...]:
    if minimum_eligible_post_count < 1:
        raise ValueError("minimum_eligible_post_count must be at least 1")

    dimensions: tuple[
        tuple[CandidateDimension, tuple[AnalyticsGroupResult, ...]], ...
    ] = (
        ("hook_type", analytics.by_hook_type),
        ("format", analytics.by_format),
        ("creator", analytics.by_creator),
    )
    candidates = []

    for dimension, groups in dimensions:
        for group in groups:
            candidate = _evaluate_group(
                dimension,
                group,
                analytics,
                minimum_eligible_post_count,
            )
            if candidate is not None:
                candidates.append(candidate)

    return tuple(candidates)


def recommend_next_experiment(
    posts: Iterable[PostAnalyticsInput],
    minimum_eligible_post_count: int = MIN_ELIGIBLE_POST_COUNT,
) -> RecommendationResult:
    post_list = tuple(posts)
    analytics = calculate_analytics(post_list)
    candidates = evaluate_candidates(analytics, minimum_eligible_post_count)
    actionable_candidates = tuple(
        candidate for candidate in candidates if candidate.dimension != "creator"
    )
    creator_candidates = tuple(
        candidate for candidate in candidates if candidate.dimension == "creator"
    )
    strongest_creator = _select_best_candidate(creator_candidates)
    selected = _select_best_candidate(
        tuple(
            candidate
            for candidate in actionable_candidates
            if candidate.rate_difference > 0
        )
    )

    if selected is None:
        return _insufficient_result(
            analytics,
            actionable_candidates,
            creator_candidates,
            strongest_creator,
            minimum_eligible_post_count,
        )

    limitations = BASE_LIMITATIONS + _confounding_limitations(selected, post_list)
    return RecommendationResult(
        status="recommendation_available",
        dimension=cast(RecommendationDimension, selected.dimension),
        value=selected.value,
        candidate_engagement_rate=selected.engagement_rate,
        comparison_engagement_rate=selected.comparison_engagement_rate,
        contrast_vs_rest=selected.contrast_vs_rest,
        rate_difference=selected.rate_difference,
        eligible_post_count=selected.eligible_post_count,
        total_views=selected.total_views,
        evidence=RecommendationEvidenceResult(
            summary=(
                f"The '{selected.value}' {selected.dimension} was associated with "
                "higher observed core engagement than the rest of eligible posts."
            ),
            minimum_eligible_post_count=minimum_eligible_post_count,
            overall_eligible_post_count=analytics.overall.eligible_post_count,
            actionable_candidates_evaluated=len(actionable_candidates),
            creator_candidates_evaluated=len(creator_candidates),
            candidate_known_core_engagements=selected.known_core_engagements,
            comparison_eligible_post_count=(
                selected.comparison_eligible_post_count
            ),
            comparison_total_views=selected.comparison_total_views,
            comparison_known_core_engagements=(
                selected.comparison_known_core_engagements
            ),
            ranking_basis=RANKING_BASIS,
            strongest_creator=_creator_evidence(strongest_creator),
        ),
        action=_action_for(selected),
        limitations=limitations,
    )


def _evaluate_group(
    dimension: CandidateDimension,
    group: AnalyticsGroupResult,
    analytics: AnalyticsResult,
    minimum_eligible_post_count: int,
) -> CandidateEvaluation | None:
    if (
        group.eligible_post_count < minimum_eligible_post_count
        or group.engagement_rate is None
    ):
        return None

    comparison_eligible_post_count = (
        analytics.overall.eligible_post_count - group.eligible_post_count
    )
    comparison_total_views = analytics.overall.total_views - group.total_views
    if comparison_eligible_post_count < 1 or comparison_total_views <= 0:
        return None

    comparison_known_core_engagements = (
        analytics.overall.known_core_engagements - group.known_core_engagements
    )
    comparison_engagement_rate = (
        comparison_known_core_engagements / comparison_total_views
    )
    contrast_vs_rest = (
        group.engagement_rate / comparison_engagement_rate
        if comparison_engagement_rate > 0
        else None
    )

    return CandidateEvaluation(
        dimension=dimension,
        value=group.value,
        eligible_post_count=group.eligible_post_count,
        total_views=group.total_views,
        known_core_engagements=group.known_core_engagements,
        engagement_rate=group.engagement_rate,
        comparison_eligible_post_count=comparison_eligible_post_count,
        comparison_total_views=comparison_total_views,
        comparison_known_core_engagements=comparison_known_core_engagements,
        comparison_engagement_rate=comparison_engagement_rate,
        contrast_vs_rest=contrast_vs_rest,
        rate_difference=group.engagement_rate - comparison_engagement_rate,
    )


def _select_best_candidate(
    candidates: tuple[CandidateEvaluation, ...],
) -> CandidateEvaluation | None:
    if not candidates:
        return None

    return min(
        candidates,
        key=lambda candidate: (
            -candidate.rate_difference,
            -candidate.eligible_post_count,
            -candidate.total_views,
            DIMENSION_PRIORITY[candidate.dimension],
            candidate.value.casefold(),
            candidate.value,
        ),
    )


def _creator_evidence(
    candidate: CandidateEvaluation | None,
) -> CreatorEvidenceResult | None:
    if candidate is None:
        return None

    return CreatorEvidenceResult(
        value=candidate.value,
        eligible_post_count=candidate.eligible_post_count,
        total_views=candidate.total_views,
        engagement_rate=candidate.engagement_rate,
        comparison_engagement_rate=candidate.comparison_engagement_rate,
        contrast_vs_rest=candidate.contrast_vs_rest,
        rate_difference=candidate.rate_difference,
    )


def _insufficient_result(
    analytics: AnalyticsResult,
    actionable_candidates: tuple[CandidateEvaluation, ...],
    creator_candidates: tuple[CandidateEvaluation, ...],
    strongest_creator: CandidateEvaluation | None,
    minimum_eligible_post_count: int,
) -> RecommendationResult:
    if analytics.overall.eligible_post_count == 0:
        summary = "No posts with views greater than zero are available."
    elif not actionable_candidates:
        summary = (
            "No actionable group met the minimum eligible-post count with a valid "
            "comparison population."
        )
    else:
        summary = (
            "No actionable group showed higher observed core engagement than its "
            "comparison population."
        )

    return RecommendationResult(
        status="insufficient_data",
        dimension=None,
        value=None,
        candidate_engagement_rate=None,
        comparison_engagement_rate=None,
        contrast_vs_rest=None,
        rate_difference=None,
        eligible_post_count=None,
        total_views=None,
        evidence=RecommendationEvidenceResult(
            summary=summary,
            minimum_eligible_post_count=minimum_eligible_post_count,
            overall_eligible_post_count=analytics.overall.eligible_post_count,
            actionable_candidates_evaluated=len(actionable_candidates),
            creator_candidates_evaluated=len(creator_candidates),
            candidate_known_core_engagements=None,
            comparison_eligible_post_count=None,
            comparison_total_views=None,
            comparison_known_core_engagements=None,
            ranking_basis=RANKING_BASIS,
            strongest_creator=_creator_evidence(strongest_creator),
        ),
        action=(
            "Collect more eligible posts across at least two hook types or formats "
            "before selecting an experiment."
        ),
        limitations=BASE_LIMITATIONS,
    )


def _action_for(candidate: CandidateEvaluation) -> str:
    if candidate.dimension == "hook_type":
        return (
            f"Test new hook variations within the '{candidate.value}' hook_type "
            "while keeping format as consistent as possible."
        )
    return (
        f"Test the '{candidate.value}' format while keeping hook_type as consistent "
        "as possible."
    )


def _confounding_limitations(
    selected: CandidateEvaluation,
    posts: tuple[PostAnalyticsInput, ...],
) -> tuple[str, ...]:
    selected_posts = tuple(
        post
        for post in posts
        if post.views > 0 and getattr(post, selected.dimension) == selected.value
    )
    limitations = []

    if len({post.creator for post in selected_posts}) == 1:
        limitations.append(
            f"The selected {selected.dimension} appears with only one creator among "
            "eligible posts, so creator may be confounded with the observed result."
        )

    control_dimension = "format" if selected.dimension == "hook_type" else "hook_type"
    if len({getattr(post, control_dimension) for post in selected_posts}) == 1:
        limitations.append(
            f"The selected {selected.dimension} appears with only one "
            f"{control_dimension} among eligible posts, so {control_dimension} may "
            "be confounded with the observed result."
        )

    return tuple(limitations)
