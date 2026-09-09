from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models import Post, YouTubeImport
from app.schemas import PostCreate


def add_post(session: Session, post_data: PostCreate) -> Post:
    post = Post(**post_data.model_dump())
    session.add(post)
    return post


def persist_post(session: Session, post_data: PostCreate) -> Post:
    post = add_post(session, post_data)
    session.commit()
    session.refresh(post)
    return post


def delete_post(session: Session, post_id: int) -> bool:
    post = session.get(Post, post_id)
    if post is None:
        return False

    try:
        session.execute(
            delete(YouTubeImport).where(YouTubeImport.post_id == post_id)
        )
        session.delete(post)
        session.commit()
    except Exception:
        session.rollback()
        raise

    return True
