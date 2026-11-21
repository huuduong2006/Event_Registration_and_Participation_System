"""Registration (Phiếu đăng ký).

Gắn `attendee_id` (FK → Attendee) thay vì lưu lặp họ tên/email/SĐT ở mỗi phiếu: dữ liệu cá nhân chỉ nằm ở
một nơi và có thể truy vết toàn bộ lịch sử tham gia của từng khách hàng.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

from ..ids import REGISTRATION, new_id
from .event import Event
from .ticket_category import TicketCategory


@dataclass
class Registration:
    registration_id: str                 
    event_id: str                        
    attendee_id: str                     
    ticket_type_id: str                  
    registration_date: datetime

    @classmethod
    def submit_form(cls, event_id: str, attendee_id: str, ticket_type_id: str, now: datetime) -> "Registration":
        """Tiếp nhận dữ liệu form đăng ký và lập phiếu (chưa lưu; phải qua validate_registration)."""
        return cls(new_id(REGISTRATION), event_id, attendee_id, ticket_type_id, now.replace(microsecond=0))

    def validation_error(self, event: Event, category: TicketCategory | None, already_registered: bool = False,
                         categories: Sequence[TicketCategory] | None = None) -> tuple[str, str] | None:
        """Trả về (mã, thông báo) nếu KHÔNG hợp lệ; None nếu hợp lệ.
        `event` và `category` phải mang số liệu đã bán mới nhất (đọc trong cùng transaction với việc ghi)."""
        if event.status.value == "COMPLETED":
            return "CLOSED", "Sự kiện đã kết thúc."
        if event.get_available_capacity() <= 0:
            return "CLOSED", "Sự kiện đã đủ số lượng đăng ký. Cổng đăng ký đã đóng."
        if categories is not None and not categories:
            return "CLOSED", "Sự kiện chưa mở bán vé."
        if category is None or category.event_id != event.event_id or category.ticket_type_id != self.ticket_type_id:
            return "VALIDATION", "Vui lòng chọn loại vé hợp lệ"
        if not category.check_availability():
            return "SOLD_OUT", f"Vé {category.type_name} đã hết. Vui lòng chọn loại vé khác."
        if already_registered:
            return "DUPLICATE", "Bạn đã đăng ký sự kiện này rồi. Hãy xem vé trong mục “Vé của tôi”."
        return None

    def validate_registration(self, event: Event, category: TicketCategory | None,
                              already_registered: bool = False) -> bool:
        """Kiểm tra tính hợp lệ và giới hạn sức chứa."""
        return self.validation_error(event, category, already_registered) is None
