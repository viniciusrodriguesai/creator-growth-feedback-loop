from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator[datetime]):
    impl = DateTime
    cache_ok = True

    def process_bind_param(
        self,
        value: datetime | None,
        dialect: Dialect,
    ) -> datetime | None:
        if value is None:
            return None
        if value.utcoffset() is None:
            raise ValueError("published_at must be timezone-aware")
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def process_result_value(
        self,
        value: datetime | None,
        dialect: Dialect,
    ) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc)


class Base(DeclarativeBase):
    pass


class Post(Base):
    __tablename__ = "posts"
    __table_args__ = (
        CheckConstraint("views >= 0", name="ck_posts_views_non_negative"),
        CheckConstraint("likes >= 0", name="ck_posts_likes_non_negative"),
        CheckConstraint("comments >= 0", name="ck_posts_comments_non_negative"),
        CheckConstraint("shares >= 0", name="ck_posts_shares_non_negative"),
        CheckConstraint(
            "duration_seconds IS NULL OR duration_seconds >= 0",
            name="ck_posts_duration_non_negative",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    hook_type: Mapped[str] = mapped_column(String, nullable=False)
    format: Mapped[str] = mapped_column(String, nullable=False)
    creator: Mapped[str] = mapped_column(String, nullable=False)
    views: Mapped[int] = mapped_column(nullable=False)
    likes: Mapped[int] = mapped_column(nullable=False)
    comments: Mapped[int] = mapped_column(nullable=False)
    shares: Mapped[int | None] = mapped_column(nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(nullable=True)
    published_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)


class YouTubeImport(Base):
    __tablename__ = "youtube_imports"

    video_id: Mapped[str] = mapped_column(String(11), primary_key=True)
    post_id: Mapped[int] = mapped_column(
        ForeignKey("posts.id"),
        nullable=False,
        unique=True,
    )
