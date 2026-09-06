from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat

NonNegativeInteger = Annotated[int, Field(ge=0)]
NonNegativeFiniteFloat = Annotated[FiniteFloat, Field(ge=0)]

RecommendationStatus = Literal[
    "recommendation_available",
    "insufficient_data",
]
RecommendationDimension = Literal["hook_type", "format"]


class CreatorEvidence(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    value: str
    eligible_post_count: NonNegativeInteger
    total_views: NonNegativeInteger
    engagement_rate: NonNegativeFiniteFloat
    comparison_engagement_rate: NonNegativeFiniteFloat
    contrast_vs_rest: NonNegativeFiniteFloat | None
    rate_difference: FiniteFloat


class RecommendationEvidence(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    summary: str
    minimum_eligible_post_count: Annotated[int, Field(gt=0)]
    overall_eligible_post_count: NonNegativeInteger
    actionable_candidates_evaluated: NonNegativeInteger
    creator_candidates_evaluated: NonNegativeInteger
    candidate_known_core_engagements: NonNegativeInteger | None
    comparison_eligible_post_count: NonNegativeInteger | None
    comparison_total_views: NonNegativeInteger | None
    comparison_known_core_engagements: NonNegativeInteger | None
    ranking_basis: str
    strongest_creator: CreatorEvidence | None


class RecommendationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: RecommendationStatus
    dimension: RecommendationDimension | None
    value: str | None
    candidate_engagement_rate: NonNegativeFiniteFloat | None
    comparison_engagement_rate: NonNegativeFiniteFloat | None
    contrast_vs_rest: NonNegativeFiniteFloat | None
    rate_difference: FiniteFloat | None
    eligible_post_count: NonNegativeInteger | None
    total_views: NonNegativeInteger | None
    evidence: RecommendationEvidence
    action: str
    limitations: list[str]
