from sqlalchemy.orm import Session

from app.models import Post
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
