from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.integrations.youtube import (
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
)
from app.main import create_app
from app.models import Post, YouTubeImport

VIDEO_ID = "dQw4w9WgXcQ"
VIDEO_URL = f"https://www.youtube.com/watch?v={VIDEO_ID}"
SHORT_VIDEO_URL = f"https://youtu.be/{VIDEO_ID}?si=normalized"
VideoFetcher = Callable[[str], YouTubeVideoData]


def import_payload(**overrides: Any) -> dict[str, Any]:
    payload = {
        "url": VIDEO_URL,
        "hook_type": "pain_point",
        "format": "short",
    }
    payload.update(overrides)
    return payload


def video_data(video_id: str = VIDEO_ID) -> YouTubeVideoData:
    return YouTubeVideoData(
        video_id=video_id,
        platform="youtube",
        title="A public video",
        creator="Creator Channel",
        views=12_000,
        likes=850,
        comments=42,
        shares=None,
        duration_seconds=73,
        published_at=datetime(2026, 8, 20, 14, 30, tzinfo=timezone.utc),
    )


@contextmanager
def youtube_client(
    tmp_path: Path,
    fetcher: VideoFetcher,
) -> Iterator[TestClient]:
    database_path = tmp_path / "youtube-endpoint.db"
    application = create_app(
        f"sqlite:///{database_path.as_posix()}",
        youtube_video_fetcher=fetcher,
    )
    with TestClient(application) as client:
        yield client


def database_counts(client: TestClient) -> tuple[int, int]:
    with Session(client.app.state.database_engine) as session:
        post_count = session.scalar(select(func.count()).select_from(Post))
        import_count = session.scalar(
            select(func.count()).select_from(YouTubeImport)
        )
    assert post_count is not None
    assert import_count is not None
    return post_count, import_count


def test_import_youtube_video_returns_post_response_and_persists_once(
    tmp_path: Path,
) -> None:
    requested_ids: list[str] = []

    def fetcher(video_id: str) -> YouTubeVideoData:
        requested_ids.append(video_id)
        return video_data(video_id)

    with youtube_client(tmp_path, fetcher) as client:
        response = client.post("/imports/youtube", json=import_payload())

        assert response.status_code == 201
        assert response.json() == {
            "id": 1,
            "platform": "youtube",
            "title": "A public video",
            "hook_type": "pain_point",
            "format": "short",
            "creator": "Creator Channel",
            "views": 12_000,
            "likes": 850,
            "comments": 42,
            "shares": None,
            "duration_seconds": 73,
            "published_at": "2026-08-20T14:30:00Z",
        }
        assert requested_ids == [VIDEO_ID]
        assert database_counts(client) == (1, 1)


def test_import_youtube_video_normalizes_url_before_fetch(tmp_path: Path) -> None:
    requested_ids: list[str] = []

    def fetcher(video_id: str) -> YouTubeVideoData:
        requested_ids.append(video_id)
        return video_data(video_id)

    with youtube_client(tmp_path, fetcher) as client:
        response = client.post(
            "/imports/youtube",
            json=import_payload(url=SHORT_VIDEO_URL),
        )

    assert response.status_code == 201
    assert requested_ids == [VIDEO_ID]


def test_duplicate_pre_check_skips_fetch_and_creates_no_post(
    tmp_path: Path,
) -> None:
    fetch_calls = 0

    def fetcher(video_id: str) -> YouTubeVideoData:
        nonlocal fetch_calls
        fetch_calls += 1
        if fetch_calls > 1:
            raise AssertionError("duplicate pre-check called the fetcher")
        return video_data(video_id)

    with youtube_client(tmp_path, fetcher) as client:
        first_response = client.post("/imports/youtube", json=import_payload())
        duplicate_response = client.post(
            "/imports/youtube",
            json=import_payload(),
        )

        assert first_response.status_code == 201
        assert duplicate_response.status_code == 409
        assert duplicate_response.json() == {
            "detail": {
                "code": "youtube_video_already_imported",
                "message": "This YouTube video has already been imported.",
            }
        }
        assert fetch_calls == 1
        assert database_counts(client) == (1, 1)


def test_database_duplicate_is_still_mapped_to_conflict(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fetcher(video_id: str) -> YouTubeVideoData:
        return video_data(video_id)

    with youtube_client(tmp_path, fetcher) as client:
        first_response = client.post("/imports/youtube", json=import_payload())
        monkeypatch.setattr(
            "app.main.is_youtube_video_imported",
            lambda session, video_id: False,
        )
        monkeypatch.setattr(
            "app.youtube_imports.is_youtube_video_imported",
            lambda session, video_id: False,
        )

        duplicate_response = client.post(
            "/imports/youtube",
            json=import_payload(),
        )

        assert first_response.status_code == 201
        assert duplicate_response.status_code == 409
        assert duplicate_response.json()["detail"]["code"] == (
            "youtube_video_already_imported"
        )
        assert "UNIQUE" not in duplicate_response.text
        assert "INSERT" not in duplicate_response.text
        assert database_counts(client) == (1, 1)


def test_invalid_youtube_url_returns_validation_error_without_fetch(
    tmp_path: Path,
) -> None:
    def fetcher(video_id: str) -> YouTubeVideoData:
        raise AssertionError("invalid URL called the fetcher")

    with youtube_client(tmp_path, fetcher) as client:
        response = client.post(
            "/imports/youtube",
            json=import_payload(url="https://example.com/video"),
        )

    assert response.status_code == 422
    assert response.json() == {
        "detail": {
            "code": "invalid_youtube_url",
            "message": "Provide a supported public YouTube video URL.",
        }
    }


def test_import_request_body_is_validated(tmp_path: Path) -> None:
    def fetcher(video_id: str) -> YouTubeVideoData:
        raise AssertionError("invalid request called the fetcher")

    invalid_payload = import_payload(hook_type="   ")
    with youtube_client(tmp_path, fetcher) as client:
        response = client.post("/imports/youtube", json=invalid_payload)

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("error_type", "expected_status", "expected_code"),
    [
        (MissingYouTubeApiKeyError, 503, "youtube_not_configured"),
        (YouTubeVideoNotFoundError, 404, "youtube_video_not_found"),
        (YouTubeMetricsUnavailableError, 422, "youtube_metrics_unavailable"),
        (YouTubeAccessDeniedError, 502, "youtube_access_denied"),
        (MalformedYouTubeResponseError, 502, "youtube_invalid_response"),
        (
            YouTubeUpstreamUnavailableError,
            502,
            "youtube_upstream_unavailable",
        ),
        (YouTubeQuotaExceededError, 503, "youtube_quota_exceeded"),
        (YouTubeRequestTimeoutError, 504, "youtube_timeout"),
    ],
)
def test_youtube_integration_errors_have_stable_http_responses(
    tmp_path: Path,
    error_type: type[YouTubeIntegrationError],
    expected_status: int,
    expected_code: str,
) -> None:
    def fetcher(video_id: str) -> YouTubeVideoData:
        raise error_type

    with youtube_client(tmp_path, fetcher) as client:
        response = client.post("/imports/youtube", json=import_payload())

    assert response.status_code == expected_status
    assert response.json() == {
        "detail": {
            "code": expected_code,
            "message": str(error_type()),
        }
    }
    assert "API_KEY" not in response.text
    assert "Traceback" not in response.text
