"""Event (Sự kiện)."""
import secrets
from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

from ..errors import ValidationError
from ..ids import EVENT, new_id
from .enums import EventStatus, parse_enum
from .ticket_category import TicketCategory
from .validators import clean_int, clean_name, parse_datetime, slugify


@dataclass
class Event:
    event_id: str                        # PK
    event_name: str
    start_time: datetime | None
    end_time: datetime | None
    location: str | None
    max_capacity: int
    status: EventStatus
    unique_url: str                      # đường dẫn truyền thông: /e/<unique_url>
    description: str | None = None       # (bổ sung) mô tả hiển thị ở trang chi tiết
    created_at: str | None = None
    registered_count: int = 0            # (dẫn xuất) số phiếu đăng ký hiện có – repository nạp kèm

    # ---------- khởi tạo / chỉnh sửa ----------
    @staticmethod
    def _validated(event_name, max_capacity, start_time, end_time, location, description) -> dict:
        start, end = parse_datetime(start_time, "Thời gian bắt đầu"), parse_datetime(end_time, "Thời gian kết thúc")
        if start and end and end < start:
            raise ValidationError("Thời gian kết thúc phải sau thời gian bắt đầu")
        return {
            "event_name": clean_name(event_name, "Tên sự kiện", 3, 150),
            "max_capacity": clean_int(max_capacity, "Sức chứa tối đa", 1, 1_000_000),
            "start_time": start, "end_time": end,
            "location": (str(location).strip() or None) if location is not None else None,
            "description": (str(description).strip() or None) if description is not None else None,
        }

    @classmethod
    def create(cls, event_name, max_capacity, start_time=None, end_time=None, location=None, description=None,
               status: EventStatus = EventStatus.UPCOMING) -> "Event":
        """Tạo sự kiện mới và PHÁT HÀNH uniqueUrl (Luồng 2 – bước 2)."""
        v = cls._validated(event_name, max_capacity, start_time, end_time, location, description)
        return cls(event_id=new_id(EVENT), status=status,
                   unique_url=f"{slugify(v['event_name'])}-{secrets.token_hex(3)}", **v)

    def edit(self, event_name, max_capacity, start_time=None, end_time=None, location=None, description=None) -> None:
        v = self._validated(event_name, max_capacity, start_time, end_time, location, description)
        if v["max_capacity"] < self.registered_count:
            raise ValidationError(f"Đã có {self.registered_count} người đăng ký, sức chứa không thể nhỏ hơn con số này",
                                  "CONFLICT")
        for k, val in v.items():
            setattr(self, k, val)

    def update_status(self, new_status) -> None:
        """Upcoming → Ongoing → Completed (Admin cập nhật theo tiến trình thực tế)."""
        self.status = parse_enum(EventStatus, new_status, "Trạng thái") if not isinstance(new_status, EventStatus) else new_status

    # ---------- nghiệp vụ ----------
    def get_available_capacity(self) -> int:
        """Số chỗ còn trống so với sức chứa tối đa."""
        return max(0, self.max_capacity - self.registered_count)

    def remaining_for(self, category: TicketCategory) -> int:
        """Số vé còn bán được của một hạng vé: bị chặn bởi cả hạng vé lẫn sức chứa chung của sự kiện."""
        return max(0, min(category.remaining, self.get_available_capacity()))

    def closed_reason(self, categories: Sequence[TicketCategory] = ()) -> str | None:
        """Lý do cổng đăng ký đang ĐÓNG (None = đang mở). Luồng 3 – bước 3: đủ sức chứa thì tự đóng."""
        if self.status == EventStatus.COMPLETED:
            return "Sự kiện đã kết thúc."
        if self.get_available_capacity() <= 0:
            return "Sự kiện đã đủ số lượng đăng ký. Cổng đăng ký đã đóng."
        if not categories:
            return "Sự kiện chưa mở bán vé."
        if not any(self.remaining_for(c) > 0 for c in categories):
            return "Tất cả loại vé đã hết. Cổng đăng ký đã đóng."
        return None

    def is_registration_open(self, categories: Sequence[TicketCategory] = ()) -> bool:
        return self.closed_reason(categories) is None
