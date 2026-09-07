import os
from collections import deque
from collections.abc import Callable, Mapping
from math import ceil
from threading import Lock
from time import monotonic

DEFAULT_DEMO_WRITE_RATE_WINDOW_SECONDS = 3_600


def demo_write_rate_limit_from_environment(
    environment: Mapping[str, str] | None = None,
) -> tuple[int | None, int]:
    source_environment = os.environ if environment is None else environment
    configured_limit = source_environment.get("DEMO_WRITE_RATE_LIMIT", "").strip()
    if not configured_limit:
        return None, DEFAULT_DEMO_WRITE_RATE_WINDOW_SECONDS

    max_requests = _positive_integer(configured_limit, "DEMO_WRITE_RATE_LIMIT")
    configured_window = source_environment.get(
        "DEMO_WRITE_RATE_WINDOW_SECONDS",
        str(DEFAULT_DEMO_WRITE_RATE_WINDOW_SECONDS),
    ).strip()
    window_seconds = _positive_integer(
        configured_window,
        "DEMO_WRITE_RATE_WINDOW_SECONDS",
    )
    return max_requests, window_seconds


def _positive_integer(value: str, variable_name: str) -> int:
    try:
        number = int(value)
    except ValueError:
        raise ValueError(f"{variable_name} must be a positive integer") from None
    if number <= 0:
        raise ValueError(f"{variable_name} must be a positive integer")
    return number


class DemoWriteRateLimiter:
    """Process-local protection against casual abuse of a shared demo."""

    def __init__(
        self,
        max_requests: int,
        window_seconds: int,
        *,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        if max_requests <= 0 or window_seconds <= 0:
            raise ValueError("Rate-limit values must be positive")
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._clock = clock
        self._request_times: deque[float] = deque()
        self._lock = Lock()

    def consume(self) -> int | None:
        """Return retry seconds when blocked, otherwise consume one request."""
        now = self._clock()
        cutoff = now - self._window_seconds

        with self._lock:
            while self._request_times and self._request_times[0] <= cutoff:
                self._request_times.popleft()
            if len(self._request_times) >= self._max_requests:
                retry_after = self._request_times[0] + self._window_seconds - now
                return max(1, ceil(retry_after))
            self._request_times.append(now)
            return None
