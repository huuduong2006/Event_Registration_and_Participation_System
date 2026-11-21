"""CheckInResult – kết quả trả về của CheckInService."""
from dataclasses import dataclass, field

from .enums import CheckInOutcome

_SIGNAL = {
    CheckInOutcome.VALID: "GREEN",          # XANH
    CheckInOutcome.ALREADY_USED: "RED",     # ĐỎ – cảnh báo gian lận/vé sao chép
    CheckInOutcome.INVALID: "RED",          # ĐỎ – từ chối qua cổng
    CheckInOutcome.WRONG_EVENT: "YELLOW",   # VÀNG
}


@dataclass(frozen=True)
class CheckInResult:
    outcome: CheckInOutcome
    message: str
    attendee_name: str | None = None
    ticket_type: str | None = None
    registration_id: str | None = None
    work_area: str | None = None
    first_check_in: dict | None = None       # {at, by, method} – khi ALREADY_USED
    extra: dict = field(default_factory=dict)

    @property
    def signal(self) -> str:
        return _SIGNAL[self.outcome]

    @property
    def is_valid(self) -> bool:
        return self.outcome == CheckInOutcome.VALID

    def to_dict(self) -> dict:
        d = {"result": self.outcome.value, "signal": self.signal, "message": self.message}
        if self.attendee_name:
            d["attendee"] = {"fullName": self.attendee_name, "ticketType": self.ticket_type,
                             "registrationId": self.registration_id}
        if self.work_area:
            d["workArea"] = self.work_area
        if self.first_check_in:
            d["firstCheckin"] = self.first_check_in
        return {**d, **self.extra}
