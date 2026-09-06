from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx2
import pytest

from app.integrations.youtube import (
    InvalidYouTubeDurationError,
    InvalidYouTubeUrlError,
    MalformedYouTubeResponseError,
    MissingYouTubeApiKeyError,
    YOUTUBE_API_PARTS,
    YOUTUBE_REQUEST_TIMEOUT_SECONDS,
    YOUTUBE_VIDEOS_ENDPOINT,
    YouTubeAccessDeniedError,
    YouTubeMetricsUnavailableError,
    YouTubeQuotaExceededError,
    YouTubeRequestTimeoutError,
    YouTubeUpstreamUnavailableError,
    YouTubeVideoNotFoundError,
    fetch_public_youtube_video,
    parse_youtube_duration,
    parse_youtube_video_url,
)

VIDEO_ID = "dQw4w9WgXcQ"


@dataclass
class FakeResponse:
    status_code: int
    payload: object
    raises_on_json: bool = False

    def json(self) -> object:
        if self.raises_on_json:
            raise ValueError("raw upstream response")
        return self.payload


def youtube_payload(**overrides: Any) -> dict[str, Any]:
    item = {
        "id": VIDEO_ID,
        "snippet": {
            "title": "A public video",
            "channelTitle": "Creator Channel",
            "publishedAt": "2026-08-20T14:30:00Z",
        },
        "statistics": {
            "viewCount": "12000",
            "likeCount": "850",
            "commentCount": "42",
        },
        "contentDetails": {"duration": "PT1M13S"},
    }
    item.update(overrides)
    return {"items": [item]}


@pytest.mark.parametrize(
    "url",
    [
        f"https://www.youtube.com/watch?v={VIDEO_ID}",
        f"https://youtube.com/watch?v={VIDEO_ID}&feature=share",
        f"https://m.youtube.com/watch?v={VIDEO_ID}",
        f"https://youtu.be/{VIDEO_ID}",
        f"https://youtu.be/{VIDEO_ID}?si=example",
        f"https://www.youtube.com/shorts/{VIDEO_ID}",
        f"https://www.youtube.com/embed/{VIDEO_ID}",
        f"https://www.youtube.com/live/{VIDEO_ID}",
    ],
)
def test_parse_youtube_video_url_accepts_supported_shapes(url: str) -> None:
    assert parse_youtube_video_url(url).video_id == VIDEO_ID


@pytest.mark.parametrize(
    "url",
    [
        "",
        f"http://www.youtube.com/watch?v={VIDEO_ID}",
        f"https://youtube.com.example.com/watch?v={VIDEO_ID}",
        f"https://www.youtube.com@evil.example/watch?v={VIDEO_ID}",
        f"https://www.youtube.com:443/watch?v={VIDEO_ID}",
        "https://www.youtube.com/watch",
        "https://www.youtube.com/watch?v=",
        f"https://www.youtube.com/watch?v={VIDEO_ID}&v=abcdefghijk",
        "https://www.youtube.com/watch?v=too-short",
        "https://www.youtube.com/watch?v=invalid!id1",
        f"https://youtu.be/{VIDEO_ID}/extra",
        f"https://www.youtube.com/channel/{VIDEO_ID}",
        f"https://evil.example/watch?v={VIDEO_ID}",
    ],
)
def test_parse_youtube_video_url_rejects_unsupported_or_unsafe_urls(
    url: str,
) -> None:
    with pytest.raises(InvalidYouTubeUrlError):
        parse_youtube_video_url(url)


@pytest.mark.parametrize(
    ("duration", "expected_seconds"),
    [
        ("PT0S", 0),
        ("PT45S", 45),
        ("PT2M", 120),
        ("PT2M5S", 125),
        ("PT1H", 3_600),
        ("PT1H2M3S", 3_723),
        ("P1DT2H3M4S", 93_784),
    ],
)
def test_parse_youtube_duration_converts_to_seconds(
    duration: str,
    expected_seconds: int,
) -> None:
    assert parse_youtube_duration(duration) == expected_seconds


@pytest.mark.parametrize(
    "duration",
    ["", "P", "PT", "1M", "PT-1S", "PT1.5S", "PT1M2H"],
)
def test_parse_youtube_duration_rejects_malformed_values(duration: str) -> None:
    with pytest.raises(InvalidYouTubeDurationError):
        parse_youtube_duration(duration)


def test_fetch_public_youtube_video_maps_required_fields() -> None:
    captured_request: dict[str, Any] = {}

    def transport(
        url: str,
        *,
        params: Mapping[str, str],
        timeout: float,
    ) -> FakeResponse:
        captured_request.update(url=url, params=params, timeout=timeout)
        return FakeResponse(200, youtube_payload())

    video = fetch_public_youtube_video(
        VIDEO_ID,
        transport=transport,
        environment={"YOUTUBE_API_KEY": "test-key"},
    )

    assert captured_request == {
        "url": YOUTUBE_VIDEOS_ENDPOINT,
        "params": {
            "part": YOUTUBE_API_PARTS,
            "id": VIDEO_ID,
            "key": "test-key",
        },
        "timeout": YOUTUBE_REQUEST_TIMEOUT_SECONDS,
    }
    assert video.video_id == VIDEO_ID
    assert video.platform == "youtube"
    assert video.title == "A public video"
    assert video.creator == "Creator Channel"
    assert video.views == 12_000
    assert video.likes == 850
    assert video.comments == 42
    assert video.shares is None
    assert video.duration_seconds == 73
    assert video.published_at == datetime(
        2026,
        8,
        20,
        14,
        30,
        tzinfo=timezone.utc,
    )


def test_fetch_public_youtube_video_reads_api_key_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received_key: str | None = None

    def transport(
        url: str,
        *,
        params: Mapping[str, str],
        timeout: float,
    ) -> FakeResponse:
        nonlocal received_key
        received_key = params["key"]
        return FakeResponse(200, youtube_payload())

    monkeypatch.setenv("YOUTUBE_API_KEY", "environment-test-key")

    fetch_public_youtube_video(VIDEO_ID, transport=transport)

    assert received_key == "environment-test-key"


def test_fetch_public_youtube_video_requires_api_key() -> None:
    transport_called = False

    def transport(
        url: str,
        *,
        params: Mapping[str, str],
        timeout: float,
    ) -> FakeResponse:
        nonlocal transport_called
        transport_called = True
        return FakeResponse(200, youtube_payload())

    with pytest.raises(MissingYouTubeApiKeyError) as error:
        fetch_public_youtube_video(
            VIDEO_ID,
            transport=transport,
            environment={},
        )

    assert not transport_called
    assert error.value.code == "youtube_not_configured"
    assert str(error.value) == "YouTube import is not configured."


def test_fetch_public_youtube_video_handles_missing_video() -> None:
    def transport(
        url: str,
        *,
        params: Mapping[str, str],
        timeout: float,
    ) -> FakeResponse:
        return FakeResponse(200, {"items": []})

    with pytest.raises(YouTubeVideoNotFoundError):
        fetch_public_youtube_video(
            VIDEO_ID,
            transport=transport,
            environment={"YOUTUBE_API_KEY": "test-key"},
        )


@pytest.mark.parametrize("reason", ["quotaExceeded", "dailyLimitExceeded"])
def test_fetch_public_youtube_video_handles_quota_errors(reason: str) -> None:
    def transport(
        url: str,
        *,
        params: Mapping[str, str],
        timeout: float,
    ) -> FakeResponse:
        return FakeResponse(
            403,
            {
                "error": {
                    "errors": [
                        {"reason": reason, "message": "raw Google message"}
                    ]
                }
            },
        )

    with pytest.raises(YouTubeQuotaExceededError) as error:
        fetch_public_youtube_video(
            VIDEO_ID,
            transport=transport,
            environment={"YOUTUBE_API_KEY": "test-key"},
        )

    assert str(error.value) == "The YouTube API quota is currently exhausted."
    assert "raw Google message" not in str(error.value)


@pytest.mark.parametrize("status_code", [400, 401, 403])
def test_fetch_public_youtube_video_handles_access_denied(
    status_code: int,
) -> None:
    def transport(
        url: str,
        *,
        params: Mapping[str, str],
        timeout: float,
    ) -> FakeResponse:
        return FakeResponse(
            status_code,
            {"error": {"errors": [{"reason": "forbidden"}]}},
        )

    with pytest.raises(YouTubeAccessDeniedError) as error:
        fetch_public_youtube_video(
            VIDEO_ID,
            transport=transport,
            environment={"YOUTUBE_API_KEY": "test-key"},
        )

    assert error.value.code == "youtube_access_denied"


def test_fetch_public_youtube_video_handles_timeout_without_leaking_request() -> None:
    def transport(
        url: str,
        *,
        params: Mapping[str, str],
        timeout: float,
    ) -> FakeResponse:
        request = httpx2.Request(
            "GET",
            f"{url}?id={VIDEO_ID}&key=do-not-expose",
        )
        raise httpx2.ReadTimeout("raw timeout details", request=request)

    with pytest.raises(YouTubeRequestTimeoutError) as error:
        fetch_public_youtube_video(
            VIDEO_ID,
            transport=transport,
            environment={"YOUTUBE_API_KEY": "test-key"},
        )

    assert str(error.value) == "YouTube did not respond before the request timed out."
    assert "do-not-expose" not in str(error.value)
    assert error.value.__cause__ is None


def test_fetch_public_youtube_video_handles_network_failure() -> None:
    def transport(
        url: str,
        *,
        params: Mapping[str, str],
        timeout: float,
    ) -> FakeResponse:
        request = httpx2.Request("GET", url)
        raise httpx2.ConnectError("raw network details", request=request)

    with pytest.raises(YouTubeUpstreamUnavailableError) as error:
        fetch_public_youtube_video(
            VIDEO_ID,
            transport=transport,
            environment={"YOUTUBE_API_KEY": "test-key"},
        )

    assert str(error.value) == "YouTube is temporarily unavailable."
    assert "raw network details" not in str(error.value)
    assert error.value.__cause__ is None


def test_fetch_public_youtube_video_handles_upstream_failure() -> None:
    def transport(
        url: str,
        *,
        params: Mapping[str, str],
        timeout: float,
    ) -> FakeResponse:
        return FakeResponse(503, {"raw": "upstream body"})

    with pytest.raises(YouTubeUpstreamUnavailableError):
        fetch_public_youtube_video(
            VIDEO_ID,
            transport=transport,
            environment={"YOUTUBE_API_KEY": "test-key"},
        )


@pytest.mark.parametrize("missing_field", ["likeCount", "commentCount"])
def test_fetch_public_youtube_video_rejects_unavailable_core_metrics(
    missing_field: str,
) -> None:
    payload = youtube_payload()
    del payload["items"][0]["statistics"][missing_field]

    def transport(
        url: str,
        *,
        params: Mapping[str, str],
        timeout: float,
    ) -> FakeResponse:
        return FakeResponse(200, payload)

    with pytest.raises(YouTubeMetricsUnavailableError):
        fetch_public_youtube_video(
            VIDEO_ID,
            transport=transport,
            environment={"YOUTUBE_API_KEY": "test-key"},
        )


def test_fetch_public_youtube_video_preserves_known_zero_metrics() -> None:
    payload = youtube_payload()
    payload["items"][0]["statistics"]["likeCount"] = "0"
    payload["items"][0]["statistics"]["commentCount"] = "0"

    def transport(
        url: str,
        *,
        params: Mapping[str, str],
        timeout: float,
    ) -> FakeResponse:
        return FakeResponse(200, payload)

    video = fetch_public_youtube_video(
        VIDEO_ID,
        transport=transport,
        environment={"YOUTUBE_API_KEY": "test-key"},
    )

    assert video.likes == 0
    assert video.comments == 0


def test_fetch_public_youtube_video_requires_valid_view_count() -> None:
    payload = youtube_payload()
    payload["items"][0]["statistics"]["viewCount"] = "not-a-count"

    def transport(
        url: str,
        *,
        params: Mapping[str, str],
        timeout: float,
    ) -> FakeResponse:
        return FakeResponse(200, payload)

    with pytest.raises(MalformedYouTubeResponseError):
        fetch_public_youtube_video(
            VIDEO_ID,
            transport=transport,
            environment={"YOUTUBE_API_KEY": "test-key"},
        )


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {},
        {"items": "not-a-list"},
        {"items": [{"id": "different01"}]},
    ],
)
def test_fetch_public_youtube_video_rejects_malformed_payloads(
    payload: object,
) -> None:
    def transport(
        url: str,
        *,
        params: Mapping[str, str],
        timeout: float,
    ) -> FakeResponse:
        return FakeResponse(200, payload)

    with pytest.raises(MalformedYouTubeResponseError):
        fetch_public_youtube_video(
            VIDEO_ID,
            transport=transport,
            environment={"YOUTUBE_API_KEY": "test-key"},
        )


def test_fetch_public_youtube_video_rejects_invalid_duration() -> None:
    payload = youtube_payload(contentDetails={"duration": "not-a-duration"})

    def transport(
        url: str,
        *,
        params: Mapping[str, str],
        timeout: float,
    ) -> FakeResponse:
        return FakeResponse(200, payload)

    with pytest.raises(MalformedYouTubeResponseError):
        fetch_public_youtube_video(
            VIDEO_ID,
            transport=transport,
            environment={"YOUTUBE_API_KEY": "test-key"},
        )


def test_fetch_public_youtube_video_rejects_timezone_naive_publication() -> None:
    payload = youtube_payload()
    payload["items"][0]["snippet"]["publishedAt"] = "2026-08-20T14:30:00"

    def transport(
        url: str,
        *,
        params: Mapping[str, str],
        timeout: float,
    ) -> FakeResponse:
        return FakeResponse(200, payload)

    with pytest.raises(MalformedYouTubeResponseError):
        fetch_public_youtube_video(
            VIDEO_ID,
            transport=transport,
            environment={"YOUTUBE_API_KEY": "test-key"},
        )


def test_fetch_public_youtube_video_rejects_invalid_json() -> None:
    def transport(
        url: str,
        *,
        params: Mapping[str, str],
        timeout: float,
    ) -> FakeResponse:
        return FakeResponse(200, None, raises_on_json=True)

    with pytest.raises(MalformedYouTubeResponseError) as error:
        fetch_public_youtube_video(
            VIDEO_ID,
            transport=transport,
            environment={"YOUTUBE_API_KEY": "test-key"},
        )

    assert "raw upstream response" not in str(error.value)
