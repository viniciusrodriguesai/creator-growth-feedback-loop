from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import DEFAULT_DATABASE_URL, create_database_engine, get_session
from app.models import Base, Post
from app.schemas import PostCreate, PostResponse


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    Base.metadata.create_all(application.state.database_engine)
    yield
    application.state.database_engine.dispose()


def create_app(database_url: str = DEFAULT_DATABASE_URL) -> FastAPI:
    application = FastAPI(lifespan=lifespan)
    application.state.database_engine = create_database_engine(database_url)

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.post(
        "/posts",
        response_model=PostResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_post(
        post_data: PostCreate,
        session: Annotated[Session, Depends(get_session)],
    ) -> Post:
        post = Post(**post_data.model_dump())
        session.add(post)
        session.commit()
        session.refresh(post)
        return post

    @application.get("/posts", response_model=list[PostResponse])
    def list_posts(
        session: Annotated[Session, Depends(get_session)],
    ) -> list[Post]:
        return list(session.scalars(select(Post).order_by(Post.id)))

    return application


app = create_app()
