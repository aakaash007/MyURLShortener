from collections import defaultdict, deque
from threading import Lock
from time import monotonic


class SlidingWindowRateLimiter:
    """Limit repeated actions per client within a rolling time window."""

    def __init__(self, limit: int, window_seconds: int) -> None:
        """Configure the allowed request count and rolling window length."""
        self.limit = limit
        self.window_seconds = window_seconds
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, client_key: str) -> tuple[bool, int]:
        """Record an allowed request or return how long a blocked client must wait."""
        now = monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            timestamps = self._requests[client_key]
            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()
            if len(timestamps) >= self.limit:
                retry_after = max(1, int(self.window_seconds - (now - timestamps[0])) + 1)
                return False, retry_after
            timestamps.append(now)
            return True, 0

