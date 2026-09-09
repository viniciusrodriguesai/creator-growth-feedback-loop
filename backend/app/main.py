import os
from collections.abc import AsyncIterator, Callable, Mapping, Sequence
from contextlib import asynccontextmanager
from typing import Annotated
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.analytics import PostAnalyticsInput, calculate_analytics
from app.analytics_schemas import AnalyticsResponse
from app.database import (
    DEFAULT_DATABASE_URL,
    create_database_engine,
    database_url_from_environment,
    get_session,
)
from app.demo_rate_limit import (
    DEFAULT_DEMO_WRITE_RATE_WINDOW_SECONDS,
    DemoWriteRateLimiter,
    demo_write_rate_limit_from_environment,
)
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
from app.posts import delete_post, persist_post
from app.recommendation_schemas import RecommendationResponse
from app.recommendations import recommend_next_experiment
from app.schemas import PostCreate, PostResponse, YouTubeImportCreate
from app.youtube_imports import (
    YouTubeVideoAlreadyImportedError,
    is_youtube_video_imported,
    persist_youtube_import,
)

YouTubeVideoFetcher = Callable[[str], YouTubeVideoData]
SUPPORTED_APP_ENVIRONMENTS = frozenset({"development", "production"})
PRODUCTION_REQUIRED_VARIABLES = (
    "DATABASE_URL",
    "FRONTEND_ORIGINS",
    "YOUTUBE_API_KEY",
)

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
DEMO_WRITE_RATE_LIMIT_DETAIL = {
    "code": "demo_write_rate_limited",
    "message": "This demo has reached its write limit. Please try again later.",
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


def frontend_origins_from_environment(
    environment: Mapping[str, str] | None = None,
) -> tuple[str, ...]:
    source_environment = os.environ if environment is None else environment
    configured_origins = source_environment.get("FRONTEND_ORIGINS", "")
    origins: list[str] = []

    for configured_origin in configured_origins.split(","):
        origin = configured_origin.strip().rstrip("/")
        if not origin:
            continue
        parsed = urlsplit(origin)
        if (
            origin == "*"
            or parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or parsed.path
            or parsed.query
            or parsed.fragment
            or parsed.username is not None
            or parsed.password is not None
        ):
            raise ValueError(
                "FRONTEND_ORIGINS must contain exact HTTP(S) origins without paths"
            )
        if origin not in origins:
            origins.append(origin)

    return tuple(origins)


def app_environment_from_environment(
    environment: Mapping[str, str] | None = None,
) -> str:
    source_environment = os.environ if environment is None else environment
    app_environment = source_environment.get("APP_ENV", "development").strip()
    app_environment = app_environment or "development"
    if app_environment not in SUPPORTED_APP_ENVIRONMENTS:
        raise ValueError("APP_ENV must be 'development' or 'production'")
    return app_environment


def validate_production_environment(environment: Mapping[str, str]) -> None:
    if app_environment_from_environment(environment) != "production":
        return

    missing_variables = [
        variable_name
        for variable_name in PRODUCTION_REQUIRED_VARIABLES
        if not environment.get(variable_name, "").strip()
    ]
    if missing_variables:
        raise ValueError(
            "Missing required production configuration: "
            + ", ".join(missing_variables)
        )


def enforce_demo_write_rate_limit(request: Request) -> None:
    limiter: DemoWriteRateLimiter | None = (
        request.app.state.demo_write_rate_limiter
    )
    if limiter is None:
        return
    retry_after = limiter.consume()
    if retry_after is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=DEMO_WRITE_RATE_LIMIT_DETAIL,
            headers={"Retry-After": str(retry_after)},
        )


def create_app(
    database_url: str = DEFAULT_DATABASE_URL,
    *,
    youtube_video_fetcher: YouTubeVideoFetcher = fetch_public_youtube_video,
    frontend_origins: Sequence[str] = (),
    demo_write_rate_limit: int | None = None,
    demo_write_rate_window_seconds: int = (
        DEFAULT_DEMO_WRITE_RATE_WINDOW_SECONDS
    ),
) -> FastAPI:
    application = FastAPI(lifespan=lifespan)
    application.state.database_engine = create_database_engine(database_url)
    application.state.demo_write_rate_limiter = (
        DemoWriteRateLimiter(
            demo_write_rate_limit,
            demo_write_rate_window_seconds,
        )
        if demo_write_rate_limit is not None
        else None
    )
    if frontend_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=list(frontend_origins),
            allow_methods=["GET", "POST", "DELETE"],
            allow_headers=["Accept", "Content-Type"],
        )

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/ready")
    def ready() -> dict[str, str]:
        try:
            with application.state.database_engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except SQLAlchemyError:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "database_unavailable",
                    "message": "The database is unavailable.",
                },
            ) from None
        return {"status": "ready"}

    @application.post(
        "/posts",
        response_model=PostResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[Depends(enforce_demo_write_rate_limit)],
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
        dependencies=[Depends(enforce_demo_write_rate_limit)],
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

    @application.delete(
        "/posts/{post_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        dependencies=[Depends(enforce_demo_write_rate_limit)],
    )
    def remove_post(
        post_id: int,
        session: Annotated[Session, Depends(get_session)],
    ) -> Response:
        if not delete_post(session, post_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "post_not_found",
                    "message": "The requested post was not found.",
                },
            )
        return Response(status_code=status.HTTP_204_NO_CONTENT)

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


def create_runtime_app(
    environment: Mapping[str, str] | None = None,
) -> FastAPI:
    source_environment = os.environ if environment is None else environment
    validate_production_environment(source_environment)
    demo_write_rate_limit, demo_write_rate_window_seconds = (
        demo_write_rate_limit_from_environment(source_environment)
    )
    return create_app(
        database_url=database_url_from_environment(source_environment),
        frontend_origins=frontend_origins_from_environment(source_environment),
        demo_write_rate_limit=demo_write_rate_limit,
        demo_write_rate_window_seconds=demo_write_rate_window_seconds,
    )


app = create_runtime_app()
