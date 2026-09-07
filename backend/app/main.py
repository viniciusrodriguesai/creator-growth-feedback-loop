from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics import PostAnalyticsInput, calculate_analytics
from app.analytics_schemas import AnalyticsResponse
from app.database import DEFAULT_DATABASE_URL, create_database_engine, get_session
from app.integrations.youtube import (
    InvalidYouTubeUrlError,
    MalformedYouTubeResponseError,
    MissingYouTubeApiKeyError,
    YouTubeAccessDeniedError,
    YouTubeIntegrationError,
    YouTubeMetricsUnavailableError,
    YouTubeQuotaExceededError,
    YouTubeRequestTimeoutError,
    YouTubeUpstreamUnavailableError,
    YouTubeVideoData,
    YouTubeVideoNotFoundError,
    fetch_public_youtube_video,
    parse_youtube_video_url,
)
from app.models import Base, Post
from app.posts import persist_post
from app.recommendation_schemas import RecommendationResponse
from app.recommendations import recommend_next_experiment
from app.schemas import PostCreate, PostResponse, YouTubeImportCreate
from app.youtube_imports import (
    YouTubeVideoAlreadyImportedError,
    is_youtube_video_imported,
    persist_youtube_import,
)

YouTubeVideoFetcher = Callable[[str], YouTubeVideoData]

YOUTUBE_IMPORT_ERROR_STATUS = {
    InvalidYouTubeUrlError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    YouTubeMetricsUnavailableError: status.HTTP_422_UNPROCESSABLE_CONTENT,
    YouTubeVideoNotFoundError: status.HTTP_404_NOT_FOUND,
    YouTubeVideoAlreadyImportedError: status.HTTP_409_CONFLICT,
    YouTubeAccessDeniedError: status.HTTP_502_BAD_GATEWAY,
    MalformedYouTubeResponseError: status.HTTP_502_BAD_GATEWAY,
    YouTubeUpstreamUnavailableError: status.HTTP_502_BAD_GATEWAY,
    MissingYouTubeApiKeyError: status.HTTP_503_SERVICE_UNAVAILABLE,
    YouTubeQuotaExceededError: status.HTTP_503_SERVICE_UNAVAILABLE,
    YouTubeRequestTimeoutError: status.HTTP_504_GATEWAY_TIMEOUT,
}


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


def _youtube_import_http_error(
    error: YouTubeIntegrationError | YouTubeVideoAlreadyImportedError,
) -> HTTPException:
    return HTTPException(
        status_code=YOUTUBE_IMPORT_ERROR_STATUS[type(error)],
        detail={"code": error.code, "message": str(error)},
    )


def create_app(
    database_url: str = DEFAULT_DATABASE_URL,
    *,
    youtube_video_fetcher: YouTubeVideoFetcher = fetch_public_youtube_video,
) -> FastAPI:
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

    @application.post(
        "/imports/youtube",
        response_model=PostResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def import_youtube_video(
        import_data: YouTubeImportCreate,
        session: Annotated[Session, Depends(get_session)],
    ) -> Post:
        try:
            reference = parse_youtube_video_url(import_data.url)
            if is_youtube_video_imported(session, reference.video_id):
                raise YouTubeVideoAlreadyImportedError
            video = youtube_video_fetcher(reference.video_id)
            return persist_youtube_import(
                session,
                video,
                hook_type=import_data.hook_type,
                format=import_data.format,
            )
        except (
            YouTubeIntegrationError,
            YouTubeVideoAlreadyImportedError,
        ) as error:
            raise _youtube_import_http_error(error) from None

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
