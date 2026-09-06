from typing import ClassVar

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.integrations.youtube import YouTubeVideoData
from app.models import Post, YouTubeImport
from app.posts import add_post
from app.schemas import Platform, PostCreate


class YouTubeVideoAlreadyImportedError(Exception):
    code: ClassVar[str] = "youtube_video_already_imported"
    safe_message: ClassVar[str] = "This YouTube video has already been imported."

    def __init__(self) -> None:
        super().__init__(self.safe_message)


def is_youtube_video_imported(session: Session, video_id: str) -> bool:
    return _youtube_import_exists(session, video_id)


def _youtube_import_exists(session: Session, video_id: str) -> bool:
    statement = select(YouTubeImport.video_id).where(
        YouTubeImport.video_id == video_id
    )
    return session.scalar(statement) is not None


def persist_youtube_import(
    session: Session,
    video: YouTubeVideoData,
    *,
    hook_type: str,
    format: str,
) -> Post:
    if is_youtube_video_imported(session, video.video_id):
        raise YouTubeVideoAlreadyImportedError

    post_data = PostCreate(
        platform=Platform.YOUTUBE,
        title=video.title,
        creator=video.creator,
        views=video.views,
        likes=video.likes,
        comments=video.comments,
        shares=None,
        duration_seconds=video.duration_seconds,
        published_at=video.published_at,
        hook_type=hook_type,
        format=format,
    )
    post = add_post(session, post_data)

    try:
        session.flush()
        session.add(YouTubeImport(video_id=video.video_id, post_id=post.id))
        session.commit()
    except IntegrityError:
        session.rollback()
        if _youtube_import_exists(session, video.video_id):
            raise YouTubeVideoAlreadyImportedError from None
        raise

    session.refresh(post)
    return post
