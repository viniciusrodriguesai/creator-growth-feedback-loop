from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat

NonNegativeInteger = Annotated[int, Field(ge=0)]
NonNegativeFiniteFloat = Annotated[FiniteFloat, Field(ge=0)]


class AnalyticsSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    post_count: NonNegativeInteger
    eligible_post_count: NonNegativeInteger
    total_views: NonNegativeInteger
    known_core_engagements: NonNegativeInteger
    known_shares: NonNegativeInteger | None
    eligible_posts_with_share_data: NonNegativeInteger
    eligible_posts_without_share_data: NonNegativeInteger
    engagement_rate: NonNegativeFiniteFloat | None


class AnalyticsGroup(AnalyticsSummary):
    value: str
    lift_vs_overall: NonNegativeFiniteFloat | None


class AnalyticsLimitations(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    zero_view_posts_excluded_from_rates: NonNegativeInteger
    eligible_posts_without_share_data: NonNegativeInteger
    engagement_rate_definition: str
    share_data_handling: str


class AnalyticsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    overall: AnalyticsSummary
    by_hook_type: list[AnalyticsGroup]
    by_format: list[AnalyticsGroup]
    by_creator: list[AnalyticsGroup]
    limitations: AnalyticsLimitations
