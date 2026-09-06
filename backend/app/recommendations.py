from dataclasses import dataclass
from typing import Literal

from app.analytics import AnalyticsGroupResult, AnalyticsResult

MIN_ELIGIBLE_POST_COUNT = 2
CandidateDimension = Literal["hook_type", "format", "creator"]


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
