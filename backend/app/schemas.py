from enum import StrEnum
from typing import Annotated

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints

NonEmptyString = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]
NonNegativeInteger = Annotated[int, Field(ge=0)]


class Platform(StrEnum):
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"


class PostCreate(BaseModel):
    platform: Platform
    title: NonEmptyString
    hook_type: NonEmptyString
    format: NonEmptyString
    creator: NonEmptyString
    views: NonNegativeInteger
    likes: NonNegativeInteger
    comments: NonNegativeInteger
    shares: NonNegativeInteger | None = None
    duration_seconds: NonNegativeInteger | None = None
    published_at: AwareDatetime


class PostResponse(PostCreate):
    model_config = ConfigDict(from_attributes=True)

    id: Annotated[int, Field(gt=0)]
