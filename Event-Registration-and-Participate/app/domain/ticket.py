"""Ticket (Vé điện tử)."""
from dataclasses import dataclass

from ..ids import TICKET, new_id, new_secret_token
from .base import Bindable
from .enums import CheckInStatus, EmailStatus
from .qr import render_qr_png


@dataclass
class Ticket(Bindable):
    ticket_id: str                       
    registration_id: str                 
    qr_code_data: str                   
    check_in_status: CheckInStatus = CheckInStatus.NOT_CHECKED_IN
    # ---- Thuộc tính để truy vết  ----
    checked_in_at: str | None = None
    checked_in_by: str | None = None     # user_id của staff
    check_in_method: str | None = None   # QR | MANUAL
    email_status: EmailStatus = EmailStatus.PENDING

    @classmethod
    def issue(cls, registration_id: str) -> "Ticket":
        """Cấp vé cho một phiếu đăng ký: sinh mã định danh độc nhất (Luồng 3 – bước 4)."""
        t = cls(new_id(TICKET), registration_id, qr_code_data="")
        t.generate_qr_code()
        return t

    def generate_qr_code(self) -> bytes:
        """Sinh mã QR độc nhất: tạo `qr_code_data` nếu chưa có, trả về ảnh PNG của mã đó."""
        if not self.qr_code_data:
            self.qr_code_data = new_secret_token()
        return render_qr_png(self.qr_code_data)

    def send_email_with_ticket(self) -> EmailStatus:
        """Gửi vé (ảnh QR) qua email cho khách; trạng thái gửi được lưu lại để Admin gửi lại nếu lỗi."""
        return self.app.tickets.send_email(self)

    @property
    def is_checked_in(self) -> bool:
        return self.check_in_status == CheckInStatus.CHECKED_IN
