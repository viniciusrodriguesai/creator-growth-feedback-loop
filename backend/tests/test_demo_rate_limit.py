from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.demo_rate_limit import (
    DEFAULT_DEMO_WRITE_RATE_WINDOW_SECONDS,
    DemoWriteRateLimiter,
    demo_write_rate_limit_from_environment,
)
from app.integrations.youtube import YouTubeVideoData
from app.main import create_app


def post_payload() -> dict[str, object]:
    return {
        "platform": "youtube",
        "title": "A demo post",
        "hook_type": "pain_point",
        "format": "short",
        "creator": "Demo Creator",
        "views": 100,
        "likes": 10,
        "comments": 2,
        "shares": None,
        "duration_seconds": 30,
        "published_at": "2026-09-05T12:30:00Z",
    }


def test_demo_write_rate_limit_is_disabled_when_unconfigured() -> None:
    assert demo_write_rate_limit_from_environment({}) == (
        None,
        DEFAULT_DEMO_WRITE_RATE_WINDOW_SECONDS,
    )


def test_demo_write_rate_limit_reads_positive_environment_values() -> None:
    assert demo_write_rate_limit_from_environment(
        {
            "DEMO_WRITE_RATE_LIMIT": "10",
            "DEMO_WRITE_RATE_WINDOW_SECONDS": "3600",
        }
    ) == (10, 3600)


@pytest.mark.parametrize(
    ("variable_name", "value"),
    [
        ("DEMO_WRITE_RATE_LIMIT", "0"),
        ("DEMO_WRITE_RATE_LIMIT", "many"),
        ("DEMO_WRITE_RATE_WINDOW_SECONDS", "-1"),
    ],
)
def test_demo_write_rate_limit_rejects_invalid_configuration(
    variable_name: str,
    value: str,
) -> None:
    environment = {
        "DEMO_WRITE_RATE_LIMIT": "10",
        "DEMO_WRITE_RATE_WINDOW_SECONDS": "3600",
        variable_name: value,
    }

    with pytest.raises(ValueError, match=f"{variable_name} must be"):
        demo_write_rate_limit_from_environment(environment)


def test_limiter_allows_writes_again_after_its_window() -> None:
    current_time = 0.0
    limiter = DemoWriteRateLimiter(1, 60, clock=lambda: current_time)

    assert limiter.consume() is None
    assert limiter.consume() == 60
    current_time = 60.0
    assert limiter.consume() is None


def test_limit_is_shared_by_public_write_endpoints_only(tmp_path: Path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'limited.db').as_posix()}"
    fetch_calls = 0

    def unexpected_fetch(video_id: str) -> YouTubeVideoData:
        nonlocal fetch_calls
        fetch_calls += 1
        raise AssertionError(f"Rate-limited request fetched {video_id}")

    application = create_app(
        database_url,
        youtube_video_fetcher=unexpected_fetch,
        demo_write_rate_limit=1,
        demo_write_rate_window_seconds=3_600,
    )

    with TestClient(application) as client:
        create_response = client.post("/posts", json=post_payload())
        limited_response = client.post(
            "/imports/youtube",
            json={
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "hook_type": "pain_point",
                "format": "short",
            },
        )
        read_responses = [
            client.get("/health"),
            client.get("/posts"),
            client.get("/analytics"),
            client.get("/recommendations"),
        ]

    assert create_response.status_code == 201
    assert limited_response.status_code == 429
    assert limited_response.json() == {
        "detail": {
            "code": "demo_write_rate_limited",
            "message": (
                "This demo has reached its write limit. Please try again later."
            ),
        }
    }
    assert limited_response.headers["retry-after"] == "3600"
    assert fetch_calls == 0
    assert all(response.status_code == 200 for response in read_responses)
