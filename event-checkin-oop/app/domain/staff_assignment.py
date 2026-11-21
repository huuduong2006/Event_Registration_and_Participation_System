"""StaffAssignment (Phân công trực) – lớp trung gian EventStaff ↔ Event.

Không gắn cứng khu vực và thời gian trực vào EventStaff: một nhân viên có thể được điều phối linh hoạt qua
nhiều sự kiện, nhiều cổng và nhiều khung giờ khác nhau.
"""
from dataclasses import dataclass
from datetime import datetime

from ..errors import ValidationError
from ..ids import ASSIGNMENT, new_id
from .validators import clean_name, parse_datetime

ON_SHIFT, NOT_STARTED, ENDED = "ON_SHIFT", "NOT_STARTED", "ENDED"


@dataclass
class StaffAssignment:
    assignment_id: str                   
    staff_id: str                        
    event_id: str                       
    work_area: str                       
    shift_start_time: datetime | None    # None = không giới hạn đầu ca
    shift_end_time: datetime | None      # None = không giới hạn cuối ca

    @staticmethod
    def _shift(start, end) -> tuple[datetime | None, datetime | None]:
        s, e = parse_datetime(start, "Giờ bắt đầu ca"), parse_datetime(end, "Giờ kết thúc ca")
        if s and e and e <= s:
            raise ValidationError("Giờ kết thúc ca phải sau giờ bắt đầu ca")
        return s, e

    @classmethod
    def create(cls, staff_id: str, event_id: str, work_area, shift_start_time=None, shift_end_time=None):
        s, e = cls._shift(shift_start_time, shift_end_time)
        return cls(new_id(ASSIGNMENT), staff_id, event_id, clean_name(work_area, "Khu vực làm việc", 1, 60), s, e)

    def update_work_area(self, new_area) -> None:
        """Điều chuyển khu vực."""
        self.work_area = clean_name(new_area, "Khu vực làm việc", 1, 60)

    def update_shift_time(self, start, end) -> None:
        """Đổi giờ làm việc."""
        self.shift_start_time, self.shift_end_time = self._shift(start, end)

    def shift_state(self, current_time: datetime) -> str:
        if self.shift_start_time and current_time < self.shift_start_time:
            return NOT_STARTED
        if self.shift_end_time and current_time > self.shift_end_time:
            return ENDED
        return ON_SHIFT

    def is_within_shift(self, current_time: datetime) -> bool:
        """Xác thực ca trực hợp lệ tại thời điểm hiện tại."""
        return self.shift_state(current_time) == ON_SHIFT
