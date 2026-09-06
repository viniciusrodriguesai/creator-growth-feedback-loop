from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics import PostAnalyticsInput, calculate_analytics
from app.analytics_schemas import AnalyticsResponse
from app.database import DEFAULT_DATABASE_URL, create_database_engine, get_session
from app.models import Base, Post
from app.posts import persist_post
from app.recommendation_schemas import RecommendationResponse
from app.recommendations import recommend_next_experiment
from app.schemas import PostCreate, PostResponse


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    Base.metadata.create_all(application.state.database_engine)
    yield
    application.state.database_engine.dispose()


def _to_analytics_input(post: Post) -> PostAnalyticsInput:
    return PostAnalyticsInput(
        hook_type=post.hook_type,
        format=post.format,
        creator=post.creator,
        views=post.views,
        likes=post.likes,
        comments=post.comments,
        shares=post.shares,
    )


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
        return persist_post(session, post_data)

    @application.get("/posts", response_model=list[PostResponse])
    def list_posts(
        session: Annotated[Session, Depends(get_session)],
    ) -> list[Post]:
        return list(session.scalars(select(Post).order_by(Post.id)))

    @application.get("/analytics", response_model=AnalyticsResponse)
    def get_analytics(
        session: Annotated[Session, Depends(get_session)],
    ) -> AnalyticsResponse:
        posts = session.scalars(select(Post).order_by(Post.id)).all()
        result = calculate_analytics(map(_to_analytics_input, posts))
        return AnalyticsResponse.model_validate(result)

    @application.get("/recommendations", response_model=RecommendationResponse)
    def get_recommendation(
        session: Annotated[Session, Depends(get_session)],
    ) -> RecommendationResponse:
        posts = session.scalars(select(Post).order_by(Post.id)).all()
        result = recommend_next_experiment(map(_to_analytics_input, posts))
        return RecommendationResponse.model_validate(result)

    return application


app = create_app()
