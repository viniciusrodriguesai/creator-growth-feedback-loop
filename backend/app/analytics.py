from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import dataclass

ENGAGEMENT_RATE_DEFINITION = (
    "Engagement rate uses likes plus comments divided by views for posts with "
    "views greater than zero."
)
SHARE_DATA_HANDLING = (
    "Shares are excluded from engagement rate and lift. known_shares sums only "
    "available share counts for eligible posts; missing shares are not treated as zero."
)


@dataclass(frozen=True, slots=True)
class PostAnalyticsInput:
    hook_type: str
    format: str
    creator: str
    views: int
    likes: int
    comments: int
    shares: int | None


@dataclass(frozen=True, slots=True)
class AnalyticsSummaryResult:
    post_count: int
    eligible_post_count: int
    total_views: int
    known_core_engagements: int
    known_shares: int | None
    eligible_posts_with_share_data: int
    eligible_posts_without_share_data: int
    engagement_rate: float | None


@dataclass(frozen=True, slots=True)
class AnalyticsGroupResult:
    value: str
    post_count: int
    eligible_post_count: int
    total_views: int
    known_core_engagements: int
    known_shares: int | None
    eligible_posts_with_share_data: int
    eligible_posts_without_share_data: int
    engagement_rate: float | None
    lift_vs_overall: float | None


@dataclass(frozen=True, slots=True)
class AnalyticsLimitationsResult:
    zero_view_posts_excluded_from_rates: int
    eligible_posts_without_share_data: int
    engagement_rate_definition: str
    share_data_handling: str


@dataclass(frozen=True, slots=True)
class AnalyticsResult:
    overall: AnalyticsSummaryResult
    by_hook_type: tuple[AnalyticsGroupResult, ...]
    by_format: tuple[AnalyticsGroupResult, ...]
    by_creator: tuple[AnalyticsGroupResult, ...]
    limitations: AnalyticsLimitationsResult


def calculate_analytics(posts: Iterable[PostAnalyticsInput]) -> AnalyticsResult:
    post_list = tuple(posts)
    overall = _summarize(post_list)

    return AnalyticsResult(
        overall=overall,
        by_hook_type=_group_posts(post_list, lambda post: post.hook_type, overall),
        by_format=_group_posts(post_list, lambda post: post.format, overall),
        by_creator=_group_posts(post_list, lambda post: post.creator, overall),
        limitations=AnalyticsLimitationsResult(
            zero_view_posts_excluded_from_rates=sum(
                post.views == 0 for post in post_list
            ),
            eligible_posts_without_share_data=(
                overall.eligible_posts_without_share_data
            ),
            engagement_rate_definition=ENGAGEMENT_RATE_DEFINITION,
            share_data_handling=SHARE_DATA_HANDLING,
        ),
    )


def _summarize(posts: tuple[PostAnalyticsInput, ...]) -> AnalyticsSummaryResult:
    eligible_posts = tuple(post for post in posts if post.views > 0)
    total_views = sum(post.views for post in eligible_posts)
    known_core_engagements = sum(
        post.likes + post.comments for post in eligible_posts
    )
    posts_with_share_data = sum(
        post.shares is not None for post in eligible_posts
    )
    known_share_values = tuple(
        post.shares for post in eligible_posts if post.shares is not None
    )

    return AnalyticsSummaryResult(
        post_count=len(posts),
        eligible_post_count=len(eligible_posts),
        total_views=total_views,
        known_core_engagements=known_core_engagements,
        known_shares=(sum(known_share_values) if known_share_values else None),
        eligible_posts_with_share_data=posts_with_share_data,
        eligible_posts_without_share_data=(
            len(eligible_posts) - posts_with_share_data
        ),
        engagement_rate=(
            known_core_engagements / total_views if total_views > 0 else None
        ),
    )


def _group_posts(
    posts: tuple[PostAnalyticsInput, ...],
    value_from_post: Callable[[PostAnalyticsInput], str],
    overall: AnalyticsSummaryResult,
) -> tuple[AnalyticsGroupResult, ...]:
    grouped_posts: dict[str, list[PostAnalyticsInput]] = defaultdict(list)
    for post in posts:
        grouped_posts[value_from_post(post)].append(post)

    groups = []
    for value, group_posts in grouped_posts.items():
        summary = _summarize(tuple(group_posts))
        lift = (
            summary.engagement_rate / overall.engagement_rate
            if summary.engagement_rate is not None
            and overall.engagement_rate is not None
            and overall.engagement_rate > 0
            else None
        )
        groups.append(
            AnalyticsGroupResult(
                value=value,
                post_count=summary.post_count,
                eligible_post_count=summary.eligible_post_count,
                total_views=summary.total_views,
                known_core_engagements=summary.known_core_engagements,
                known_shares=summary.known_shares,
                eligible_posts_with_share_data=(
                    summary.eligible_posts_with_share_data
                ),
                eligible_posts_without_share_data=(
                    summary.eligible_posts_without_share_data
                ),
                engagement_rate=summary.engagement_rate,
                lift_vs_overall=lift,
            )
        )

    return tuple(
        sorted(groups, key=lambda group: (group.value.casefold(), group.value))
    )
