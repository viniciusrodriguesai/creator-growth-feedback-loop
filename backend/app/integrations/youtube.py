import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, ClassVar, Literal, Protocol
from urllib.parse import parse_qs, urlparse

import httpx2

YOUTUBE_HOSTS = frozenset(
    {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
    }
)
YOUTUBE_SHORT_HOST = "youtu.be"
VIDEO_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{11}$")
DURATION_PATTERN = re.compile(
    r"^P(?:(?P<days>\d+)D)?T"
    r"(?:(?P<hours>\d+)H)?"
    r"(?:(?P<minutes>\d+)M)?"
    r"(?:(?P<seconds>\d+)S)?$"
)
YOUTUBE_VIDEOS_ENDPOINT = "https://www.googleapis.com/youtube/v3/videos"
YOUTUBE_API_PARTS = "snippet,statistics,contentDetails"
YOUTUBE_REQUEST_TIMEOUT_SECONDS = 5.0
QUOTA_ERROR_REASONS = frozenset(
    {
        "dailyLimitExceeded",
        "dailyLimitExceededUnreg",
        "quotaExceeded",
        "rateLimitExceeded",
        "userRateLimitExceeded",
    }
)


class YouTubeIntegrationError(Exception):
    """Base error for safe, expected YouTube integration failures."""

    code: ClassVar[str] = "youtube_integration_error"
    safe_message: ClassVar[str] = "The YouTube integration could not complete."

    def __init__(self) -> None:
        super().__init__(self.safe_message)


class InvalidYouTubeUrlError(YouTubeIntegrationError):
    """Raised when a URL is not a supported YouTube video reference."""

    code = "invalid_youtube_url"
    safe_message = "Provide a supported public YouTube video URL."


class InvalidYouTubeDurationError(YouTubeIntegrationError):
    """Raised when a YouTube duration cannot be converted to seconds."""

    code = "youtube_invalid_duration"
    safe_message = "The YouTube video duration is invalid."


class MissingYouTubeApiKeyError(YouTubeIntegrationError):
    code = "youtube_not_configured"
    safe_message = "YouTube import is not configured."


class YouTubeVideoNotFoundError(YouTubeIntegrationError):
    code = "youtube_video_not_found"
    safe_message = "The requested YouTube video was not found."


class YouTubeQuotaExceededError(YouTubeIntegrationError):
    code = "youtube_quota_exceeded"
    safe_message = "The YouTube API quota is currently exhausted."


class YouTubeAccessDeniedError(YouTubeIntegrationError):
    code = "youtube_access_denied"
    safe_message = "YouTube rejected the configured API credentials."


class YouTubeRequestTimeoutError(YouTubeIntegrationError):
    code = "youtube_timeout"
    safe_message = "YouTube did not respond before the request timed out."


class YouTubeUpstreamUnavailableError(YouTubeIntegrationError):
    code = "youtube_upstream_unavailable"
    safe_message = "YouTube is temporarily unavailable."


class MalformedYouTubeResponseError(YouTubeIntegrationError):
    code = "youtube_invalid_response"
    safe_message = "YouTube returned an invalid response."


class YouTubeMetricsUnavailableError(YouTubeIntegrationError):
    code = "youtube_metrics_unavailable"
    safe_message = "This video does not expose the metrics required for import."


class YouTubeHttpResponse(Protocol):
    status_code: int

    def json(self) -> object: ...


class YouTubeTransport(Protocol):
    def __call__(
        self,
        url: str,
        *,
        params: Mapping[str, str],
        timeout: float,
    ) -> YouTubeHttpResponse: ...


@dataclass(frozen=True, slots=True)
class YouTubeVideoReference:
    video_id: str


@dataclass(frozen=True, slots=True)
class YouTubeVideoData:
    video_id: str
    platform: Literal["youtube"]
    title: str
    creator: str
    views: int
    likes: int
    comments: int
    shares: None
    duration_seconds: int
    published_at: datetime


def parse_youtube_video_url(url: str) -> YouTubeVideoReference:
    candidate = url.strip()
    try:
        parsed = urlparse(candidate)
        hostname = parsed.hostname.lower() if parsed.hostname else None
        port = parsed.port
    except ValueError:
        raise InvalidYouTubeUrlError from None

    if (
        parsed.scheme != "https"
        or hostname is None
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
    ):
        raise InvalidYouTubeUrlError

    if hostname == YOUTUBE_SHORT_HOST:
        video_id = _video_id_from_short_url(parsed.path)
    elif hostname in YOUTUBE_HOSTS:
        video_id = _video_id_from_youtube_url(parsed.path, parsed.query)
    else:
        raise InvalidYouTubeUrlError

    if not VIDEO_ID_PATTERN.fullmatch(video_id):
        raise InvalidYouTubeUrlError

    return YouTubeVideoReference(video_id=video_id)


def parse_youtube_duration(duration: str) -> int:
    match = DURATION_PATTERN.fullmatch(duration)
    if match is None or all(value is None for value in match.groupdict().values()):
        raise InvalidYouTubeDurationError

    values = {
        name: int(value) if value is not None else 0
        for name, value in match.groupdict().items()
    }
    return (
        values["days"] * 86_400
        + values["hours"] * 3_600
        + values["minutes"] * 60
        + values["seconds"]
    )


def fetch_public_youtube_video(
    video_id: str,
    *,
    transport: YouTubeTransport | None = None,
    environment: Mapping[str, str] | None = None,
    timeout_seconds: float = YOUTUBE_REQUEST_TIMEOUT_SECONDS,
) -> YouTubeVideoData:
    source_environment = os.environ if environment is None else environment
    api_key = source_environment.get("YOUTUBE_API_KEY", "").strip()
    if not api_key:
        raise MissingYouTubeApiKeyError

    request = transport or httpx2.get
    try:
        response = request(
            YOUTUBE_VIDEOS_ENDPOINT,
            params={
                "part": YOUTUBE_API_PARTS,
                "id": video_id,
                "key": api_key,
            },
            timeout=timeout_seconds,
        )
    except httpx2.TimeoutException:
        raise YouTubeRequestTimeoutError from None
    except httpx2.RequestError:
        raise YouTubeUpstreamUnavailableError from None

    payload = _response_payload(response)
    if response.status_code != 200:
        _raise_for_upstream_error(response.status_code, payload)

    return _video_data_from_payload(video_id, payload)


def _video_id_from_short_url(path: str) -> str:
    segments = [segment for segment in path.split("/") if segment]
    if len(segments) != 1:
        raise InvalidYouTubeUrlError
    return segments[0]


def _video_id_from_youtube_url(path: str, query: str) -> str:
    normalized_path = path.rstrip("/") or "/"
    if normalized_path == "/watch":
        video_ids = parse_qs(query, keep_blank_values=True).get("v", [])
        if len(video_ids) != 1:
            raise InvalidYouTubeUrlError
        return video_ids[0]

    segments = [segment for segment in path.split("/") if segment]
    if len(segments) == 2 and segments[0] in {"shorts", "embed", "live"}:
        return segments[1]

    raise InvalidYouTubeUrlError


def _response_payload(response: YouTubeHttpResponse) -> object:
    try:
        return response.json()
    except (TypeError, ValueError):
        if response.status_code == 200:
            raise MalformedYouTubeResponseError from None
        return None


def _raise_for_upstream_error(status_code: int, payload: object) -> None:
    reason = _upstream_error_reason(payload)
    if reason in QUOTA_ERROR_REASONS:
        raise YouTubeQuotaExceededError
    if status_code == 404 or reason == "videoNotFound":
        raise YouTubeVideoNotFoundError
    if status_code in {400, 401, 403}:
        raise YouTubeAccessDeniedError
    raise YouTubeUpstreamUnavailableError


def _upstream_error_reason(payload: object) -> str | None:
    if not isinstance(payload, dict):
        return None
    error = payload.get("error")
    if not isinstance(error, dict):
        return None
    errors = error.get("errors")
    if not isinstance(errors, list):
        return None
    for item in errors:
        if isinstance(item, dict) and isinstance(item.get("reason"), str):
            return item["reason"]
    return None


def _video_data_from_payload(video_id: str, payload: object) -> YouTubeVideoData:
    item = _single_video_item(payload)
    snippet = _required_mapping(item, "snippet")
    statistics = _required_mapping(item, "statistics")
    content_details = _required_mapping(item, "contentDetails")

    response_video_id = _required_string(item, "id")
    if response_video_id != video_id:
        raise MalformedYouTubeResponseError

    likes = _optional_count(statistics, "likeCount")
    comments = _optional_count(statistics, "commentCount")
    if likes is None or comments is None:
        raise YouTubeMetricsUnavailableError

    try:
        duration_seconds = parse_youtube_duration(
            _required_string(content_details, "duration")
        )
    except InvalidYouTubeDurationError:
        raise MalformedYouTubeResponseError from None

    return YouTubeVideoData(
        video_id=video_id,
        platform="youtube",
        title=_required_string(snippet, "title"),
        creator=_required_string(snippet, "channelTitle"),
        views=_required_count(statistics, "viewCount"),
        likes=likes,
        comments=comments,
        shares=None,
        duration_seconds=duration_seconds,
        published_at=_published_at(snippet),
    )


def _single_video_item(payload: object) -> Mapping[str, Any]:
    if not isinstance(payload, dict):
        raise MalformedYouTubeResponseError
    items = payload.get("items")
    if not isinstance(items, list):
        raise MalformedYouTubeResponseError
    if not items:
        raise YouTubeVideoNotFoundError
    if len(items) != 1 or not isinstance(items[0], dict):
        raise MalformedYouTubeResponseError
    return items[0]


def _required_mapping(
    source: Mapping[str, Any],
    field: str,
) -> Mapping[str, Any]:
    value = source.get(field)
    if not isinstance(value, dict):
        raise MalformedYouTubeResponseError
    return value


def _required_string(source: Mapping[str, Any], field: str) -> str:
    value = source.get(field)
    if not isinstance(value, str) or not value.strip():
        raise MalformedYouTubeResponseError
    return value


def _required_count(source: Mapping[str, Any], field: str) -> int:
    value = _optional_count(source, field)
    if value is None:
        raise MalformedYouTubeResponseError
    return value


def _optional_count(source: Mapping[str, Any], field: str) -> int | None:
    value = source.get(field)
    if value is None:
        return None
    if not isinstance(value, str) or not value.isascii() or not value.isdigit():
        raise MalformedYouTubeResponseError
    return int(value)


def _published_at(snippet: Mapping[str, Any]) -> datetime:
    value = _required_string(snippet, "publishedAt")
    normalized = f"{value[:-1]}+00:00" if value.endswith("Z") else value
    try:
        published_at = datetime.fromisoformat(normalized)
    except ValueError:
        raise MalformedYouTubeResponseError from None
    if published_at.utcoffset() is None:
        raise MalformedYouTubeResponseError
    return published_at
