"""Giới hạn tần suất trong bộ nhớ (1 worker). Muốn chạy nhiều worker/server: thay bằng Redis."""
import time
from collections import defaultdict, deque

from ..errors import TooManyRequests


class RateLimiter:
    def __init__(self):
        self._hits: dict[str, deque] = defaultdict(deque)

    def check(self, key: str, limit: int, window_sec: int) -> None:
        now = time.monotonic()
        q = self._hits[key]
        while q and now - q[0] > window_sec:
            q.popleft()
        if len(q) >= limit:
            raise TooManyRequests("Bạn thao tác quá nhanh, vui lòng thử lại sau ít phút")
        q.append(now)

    def reset(self) -> None:
        self._hits.clear()
