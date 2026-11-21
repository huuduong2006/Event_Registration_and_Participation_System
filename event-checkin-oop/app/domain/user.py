"""Nhóm phân quyền người dùng (User Hierarchy):  User (abstract) ← Administrator | EventStaff | Attendee.

Phân quyền thể hiện NGAY TRONG CẤU TRÚC LỚP: chỉ `Administrator` mới có createEvent(); chỉ `EventStaff` mới có
scanQRCode(); chỉ `Attendee` mới có submitRegistrationForm(). API chỉ cần nạp đúng loại đối tượng theo
`role` rồi gọi phương thức – không thể "quên" kiểm tra quyền ở từng endpoint.
"""
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from ..errors import Forbidden, Unauthorized
from .base import Bindable
from .enums import Role, StaffStatus

if TYPE_CHECKING:
    from .check_in_result import CheckInResult
    from .event import Event
    from .registration import Registration
    from .staff_assignment import StaffAssignment
    from .ticket import Ticket
    from .ticket_category import TicketCategory


class User(Bindable, ABC):
    """Lớp trừu tượng gốc: tập trung dữ liệu định danh và cơ chế xác thực, tránh trùng lặp giữa các vai trò."""

    def __init__(self, user_id: str, full_name: str, email: str, phone_number: str | None = None,
                 password_hash: str | None = None, created_at: str | None = None):
        self.user_id = user_id
        self.full_name = full_name
        self.email = email
        self.phone_number = phone_number
        self.password_hash = password_hash        
        self.created_at = created_at

    @property
    @abstractmethod
    def role(self) -> Role:
        """Vai trò – lớp con khai báo bằng thuộc tính lớp (role = Role.ADMIN ...)."""

    def is_active(self) -> bool:
        return True

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.user_id} {self.email}>"

    # ---------- phương thức chung ----------
    def login(self, password: str) -> str:
        """Xác thực đăng nhập. Thành công trả về token phiên."""
        if not self.password_hash or not self.app.hasher.verify(password, self.password_hash):
            raise Unauthorized("Sai email hoặc mật khẩu")
        if not self.is_active():                  # kiểm tra SAU mật khẩu để không lộ trạng thái tài khoản
            raise Forbidden("Tài khoản đã bị vô hiệu hoá. Vui lòng liên hệ Administrator.", "ACCOUNT_INACTIVE")
        return self.app.auth.issue_token(self)

    def logout(self, token: str) -> None:
        """Đăng xuất khỏi phiên: thu hồi token."""
        self.app.auth.revoke_token(token)

    def update_profile(self, full_name=None, phone_number=None, current_password=None, new_password=None) -> "User":
        """Cập nhật thông tin cá nhân (đổi mật khẩu cần nhập mật khẩu hiện tại)."""
        return self.app.auth.update_profile(self, full_name, phone_number, current_password, new_password)


class Administrator(User):
    """Quản lý toàn bộ hệ thống: sự kiện, hạng vé, nhân sự, phân công và báo cáo."""

    role = Role.ADMIN

    # ----- Sự kiện  -----
    def create_event(self, **data) -> "Event":
        return self.app.events.create_event(**data)

    def edit_event(self, event_id: str, **data) -> "Event":
        return self.app.events.edit_event(event_id, **data)

    def delete_event(self, event_id: str) -> None:
        self.app.events.delete_event(event_id)

    def update_event_status(self, event_id: str, status) -> "Event":
        """Upcoming → Ongoing → Completed."""
        return self.app.events.update_event_status(event_id, status)

    def list_events(self) -> list[dict]:
        return self.app.events.list_events_with_stats()

    def get_event(self, event_id: str) -> "Event":
        return self.app.events.get_event(event_id)

    # ----- Hạng vé -----
    def configure_ticket_category(self, event_id: str, type_name, price, quantity_limit,
                                  ticket_type_id: str | None = None) -> "TicketCategory":
        """Cấu hình VIP/Standard: tạo mới (hoặc sửa nếu truyền ticket_type_id) tên hạng, giá, số lượng."""
        return self.app.events.configure_ticket_category(event_id, type_name, price, quantity_limit, ticket_type_id)

    def remove_ticket_category(self, ticket_type_id: str) -> str:
        """Xoá hạng vé (chỉ khi chưa bán). Trả về event_id để giao diện tải lại danh sách."""
        return self.app.events.remove_ticket_category(ticket_type_id)

    def list_ticket_categories(self, event_id: str) -> list["TicketCategory"]:
        return self.app.events.list_categories(event_id)

    # ----- Nhân sự & phân công -----
    def add_staff(self, full_name, email, phone_number, password=None) -> tuple["EventStaff", str | None]:
        """Tạo tài khoản nhân viên (nhân viên KHÔNG tự đăng ký). Trả về (staff, mật khẩu tạm nếu hệ thống tự sinh)."""
        return self.app.staff.add_staff(full_name, email, phone_number, password)

    def remove_staff(self, staff_id: str) -> "EventStaff":
        """Gỡ nhân viên: chuyển sang INACTIVE (giữ lại lịch sử check-in để đối soát)."""
        return self.app.staff.set_staff_status(staff_id, StaffStatus.INACTIVE)

    def reactivate_staff(self, staff_id: str) -> "EventStaff":
        return self.app.staff.set_staff_status(staff_id, StaffStatus.ACTIVE)

    def list_staff(self) -> list[dict]:
        return self.app.staff.list_staff()

    def assign_staff_schedule(self, staff_id: str, event_id: str, work_area, shift_start_time=None,
                              shift_end_time=None) -> "StaffAssignment":
        """Phân công ca và khu vực: tạo StaffAssignment gán nhân viên vào sự kiện."""
        return self.app.staff.assign(staff_id, event_id, work_area, shift_start_time, shift_end_time)

    def update_staff_assignment(self, assignment_id: str, work_area=None, shift_start_time=None,
                                shift_end_time=None, change_shift: bool = False) -> "StaffAssignment":
        """Điều chuyển khu vực (update_work_area) và/hoặc đổi ca (update_shift_time) bất cứ lúc nào."""
        return self.app.staff.update_assignment(assignment_id, work_area, shift_start_time, shift_end_time, change_shift)

    def unassign_staff(self, assignment_id: str) -> None:
        self.app.staff.unassign(assignment_id)

    def list_staff_assignments(self, event_id: str) -> list[dict]:
        return self.app.staff.list_assignments(event_id)

    # ----- Báo cáo & thống kê -----
    def view_attendee_list(self, event_id: str, q=None, status=None, ticket_type_id=None, page=1, page_size=20) -> dict:
        """Danh sách tham dự, lọc theo trạng thái check-in / hạng vé / từ khoá."""
        return self.app.registrations.list_attendees(event_id, q, status, ticket_type_id, page, page_size)

    def resend_ticket_email(self, ticket_id: str):
        return self.app.tickets.resend_email(ticket_id)

    def report_exporter(self):
        """ReportExporter: xuất Excel/CSV và dữ liệu biểu đồ."""
        return self.app.report_exporter()


class EventStaff(User):
    """Nhân sự soát vé tại cổng. Chỉ thao tác được trong ca/khu vực đã được phân công (StaffAssignment)."""

    role = Role.STAFF

    def __init__(self, *args, staff_status: StaffStatus = StaffStatus.ACTIVE, **kwargs):
        super().__init__(*args, **kwargs)
        self.staff_status = staff_status

    def is_active(self) -> bool:
        return self.staff_status == StaffStatus.ACTIVE

    def view_assigned_schedule(self) -> list[dict]:
        """Xem ca và khu vực trực của mình."""
        return self.app.staff.schedule_for(self.user_id)

    def scan_qr_code(self, qr_code_data: str, event_id: str | None = None) -> "CheckInResult":
        """Quét mã QR bằng thiết bị (camera/máy quét). Đối chiếu StaffAssignment rồi xử lý check-in."""
        return self.app.check_in_service(self.user_id).process_qr_code_scan(qr_code_data, event_id)

    def manual_check_in(self, registration_id: str, note: str, event_id: str | None = None) -> "CheckInResult":
        """Điểm danh thủ công khi khách quên vé nhưng xuất trình giấy tờ hợp lệ (note = giấy tờ đã đối chiếu)."""
        return self.app.check_in_service(self.user_id).process_manual_check_in(registration_id, note, event_id)

    # ---- hỗ trợ màn hình check-in (bổ sung) ----
    def search_attendees(self, event_id: str, query: str) -> list[dict]:
        return self.app.check_in_service(self.user_id).search_attendees(event_id, query)

    def check_in_stats(self, event_id: str) -> dict:
        return self.app.check_in_service(self.user_id).get_stats(event_id)


class Attendee(User):
    """Khách tham dự: xem sự kiện, đăng ký lấy vé, xem lịch sử vé của mình."""

    role = Role.ATTENDEE

    @classmethod
    def register(cls, app, full_name, email, phone_number, password) -> "Attendee":
        """Tự đăng ký tài khoản khách hàng (Cổng Attendee – Luồng 1)."""
        return app.auth.register_attendee(full_name, email, phone_number, password)

    @classmethod
    def guest(cls, app, full_name, email, phone_number) -> "Attendee":
        """Khách chưa đăng nhập vẫn đăng ký được: tạo (hoặc dùng lại) hồ sơ khách theo email, chưa có mật khẩu."""
        return app.auth.find_or_create_guest(full_name, email, phone_number)

    @property
    def has_account(self) -> bool:
        return bool(self.password_hash)

    def view_available_events(self) -> list[dict]:
        """Danh sách sự kiện đang mở."""
        return self.app.registrations.view_available_events()

    def submit_registration_form(self, event_ref: str, ticket_type_id: str) -> tuple["Registration", "Ticket"]:
        """Gửi form đăng ký nhận vé. attendeeId được gắn tự động từ chính đối tượng này (Luồng 3 – bước 2).
        `event_ref` là event_id hoặc unique_url."""
        return self.app.registrations.submit_registration_form(self, event_ref, ticket_type_id)

    def get_registration_history(self) -> list[dict]:
        """Xem lịch sử vé đã đặt."""
        return self.app.registrations.get_registration_history(self.user_id)
