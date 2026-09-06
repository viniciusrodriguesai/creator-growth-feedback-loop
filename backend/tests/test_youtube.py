import pytest

from app.integrations.youtube import (
    InvalidYouTubeDurationError,
    InvalidYouTubeUrlError,
    parse_youtube_duration,
    parse_youtube_video_url,
)

VIDEO_ID = "dQw4w9WgXcQ"


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
