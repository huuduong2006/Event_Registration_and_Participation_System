"""Đồng hồ hệ thống. Mọi thời điểm trong ứng dụng (ca trực, giờ check-in, ngày đăng ký) là GIỜ ĐỊA PHƯƠNG
của sự kiện, không kèm múi giờ (naive) – cùng dạng với giá trị Admin nhập ở ô datetime-local.

Tách thành lớp riêng để test có thể thay bằng đồng hồ cố định (app.clock = FixedClock(...))."""
from datetime import datetime, timedelta, timezone


class Clock:
    def __init__(self, offset_hours: int = 7):
        self._offset = timedelta(hours=offset_hours)

    def now(self) -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None) + self._offset


class FixedClock(Clock):
    """Dùng trong test: thời gian đứng yên, có thể tua bằng advance()."""

    def __init__(self, at: datetime):
        super().__init__(0)
        self._at = at

    def now(self) -> datetime:
        return self._at

    def advance(self, **kwargs) -> None:
        self._at += timedelta(**kwargs)
