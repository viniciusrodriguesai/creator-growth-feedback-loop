import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

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


class YouTubeIntegrationError(Exception):
    """Base error for safe, expected YouTube integration failures."""


class InvalidYouTubeUrlError(YouTubeIntegrationError):
    """Raised when a URL is not a supported YouTube video reference."""


class InvalidYouTubeDurationError(YouTubeIntegrationError):
    """Raised when a YouTube duration cannot be converted to seconds."""


@dataclass(frozen=True, slots=True)
class YouTubeVideoReference:
    video_id: str


def parse_youtube_video_url(url: str) -> YouTubeVideoReference:
    candidate = url.strip()
    try:
        parsed = urlparse(candidate)
        hostname = parsed.hostname.lower() if parsed.hostname else None
        port = parsed.port
    except ValueError as error:
        raise InvalidYouTubeUrlError("Invalid YouTube video URL.") from error

    if (
        parsed.scheme != "https"
        or hostname is None
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
    ):
        raise InvalidYouTubeUrlError("Invalid YouTube video URL.")

    if hostname == YOUTUBE_SHORT_HOST:
        video_id = _video_id_from_short_url(parsed.path)
    elif hostname in YOUTUBE_HOSTS:
        video_id = _video_id_from_youtube_url(parsed.path, parsed.query)
    else:
        raise InvalidYouTubeUrlError("Invalid YouTube video URL.")

    if not VIDEO_ID_PATTERN.fullmatch(video_id):
        raise InvalidYouTubeUrlError("Invalid YouTube video URL.")

    return YouTubeVideoReference(video_id=video_id)


def parse_youtube_duration(duration: str) -> int:
    match = DURATION_PATTERN.fullmatch(duration)
    if match is None or all(value is None for value in match.groupdict().values()):
        raise InvalidYouTubeDurationError("Invalid YouTube video duration.")

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


def _video_id_from_short_url(path: str) -> str:
    segments = [segment for segment in path.split("/") if segment]
    if len(segments) != 1:
        raise InvalidYouTubeUrlError("Invalid YouTube video URL.")
    return segments[0]


def _video_id_from_youtube_url(path: str, query: str) -> str:
    normalized_path = path.rstrip("/") or "/"
    if normalized_path == "/watch":
        video_ids = parse_qs(query, keep_blank_values=True).get("v", [])
        if len(video_ids) != 1:
            raise InvalidYouTubeUrlError("Invalid YouTube video URL.")
        return video_ids[0]

    segments = [segment for segment in path.split("/") if segment]
    if len(segments) == 2 and segments[0] in {"shorts", "embed", "live"}:
        return segments[1]

    raise InvalidYouTubeUrlError("Invalid YouTube video URL.")
