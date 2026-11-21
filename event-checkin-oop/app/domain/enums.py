"""Các kiểu Enum trong tài liệu thiết kế."""
from enum import Enum


class Role(str, Enum):                 # User.role
    ADMIN = "ADMIN"
    STAFF = "STAFF"
    ATTENDEE = "ATTENDEE"


class StaffStatus(str, Enum):          # EventStaff.staffStatus
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class EventStatus(str, Enum):          # Event.status
    UPCOMING = "UPCOMING"
    ONGOING = "ONGOING"
    COMPLETED = "COMPLETED"


class CheckInStatus(str, Enum):        # Ticket.checkInStatus
    NOT_CHECKED_IN = "NOT_CHECKED_IN"
    CHECKED_IN = "CHECKED_IN"


# ---- Method bổ sung để kiểm tra các enum ----
class CheckInOutcome(str, Enum):       # kết quả của CheckInService
    VALID = "VALID"                    # XANH – hợp lệ, vừa check-in
    ALREADY_USED = "ALREADY_USED"      # ĐỎ   – vé đã dùng (nghi vé sao chép)
    INVALID = "INVALID"                # ĐỎ   – mã không tồn tại
    WRONG_EVENT = "WRONG_EVENT"        # VÀNG – vé hợp lệ nhưng của sự kiện khác


class CheckInMethod(str, Enum):
    QR = "QR"
    MANUAL = "MANUAL"


class EmailStatus(str, Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


def parse_enum(enum_cls, value, field: str):
    """Chuyển chuỗi thành Enum; sai giá trị -> ValidationError có thông báo tiếng Việt."""
    from ..errors import ValidationError
    try:
        return enum_cls(value)
    except ValueError:
        allowed = ", ".join(e.value for e in enum_cls)
        raise ValidationError(f"{field} không hợp lệ (chỉ nhận: {allowed})")
