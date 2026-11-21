"""StaffService: tài khoản nhân viên (chỉ Admin tạo) và phân công StaffAssignment."""
import secrets

from ..domain import EventStaff, Role, StaffAssignment, StaffStatus
from ..domain.validators import format_datetime
from ..errors import Conflict, NotFound, ValidationError


class StaffService:
    def __init__(self, app):
        self.app = app

    def add_staff(self, full_name, email, phone_number, password=None):
        temp = None
        if not password:
            temp = password = secrets.token_urlsafe(9)         # ≥ 8 ký tự
        with self.app.uow(write=True) as u:
            s = self.app.auth.create_staff_user(u, full_name, email, phone_number, password)
        return s, temp

    def set_staff_status(self, staff_id: str, status: StaffStatus) -> EventStaff:
        with self.app.uow(write=True) as u:
            s = u.users.get(staff_id)
            if s is None or s.role != Role.STAFF:
                raise NotFound("Không tìm thấy nhân viên")
            s.staff_status = status
            u.users.update(s)
        return s

    def list_staff(self) -> list[dict]:
        with self.app.uow() as u:
            staff, counts = u.users.list_by_role(Role.STAFF), u.assignments.counts_by_staff()
        return [{"staff": s, "assignments": counts.get(s.user_id, 0)} for s in staff]

    # ---------- phân công ----------
    def assign(self, staff_id, event_id, work_area, shift_start_time=None, shift_end_time=None) -> StaffAssignment:
        a = StaffAssignment.create(staff_id, event_id, work_area, shift_start_time, shift_end_time)
        with self.app.uow(write=True) as u:
            s = u.users.get(staff_id)
            if s is None or s.role != Role.STAFF:
                raise NotFound("Không tìm thấy nhân viên")
            if not s.is_active():
                raise ValidationError("Nhân viên đang bị vô hiệu hoá, hãy kích hoạt lại trước khi phân công")
            if u.events.get(event_id) is None:
                raise NotFound("Không tìm thấy sự kiện")
            if u.assignments.find(staff_id, event_id):
                raise Conflict("Nhân viên đã được phân công cho sự kiện này (hãy sửa phân công hiện có)")
            u.assignments.add(a)
        return a

    def update_assignment(self, assignment_id, work_area=None, shift_start_time=None, shift_end_time=None,
                          change_shift=False) -> StaffAssignment:
        with self.app.uow(write=True) as u:
            a = u.assignments.get(assignment_id)
            if a is None:
                raise NotFound("Không tìm thấy phân công")
            if work_area is not None:
                a.update_work_area(work_area)
            if change_shift:
                a.update_shift_time(shift_start_time, shift_end_time)
            u.assignments.update(a)
        return a

    def unassign(self, assignment_id: str) -> None:
        with self.app.uow(write=True) as u:
            if u.assignments.get(assignment_id) is None:
                raise NotFound("Không tìm thấy phân công")
            u.assignments.delete(assignment_id)

    def list_assignments(self, event_id: str) -> list[dict]:
        with self.app.uow() as u:
            if u.events.get(event_id) is None:
                raise NotFound("Không tìm thấy sự kiện")
            rows = u.assignments.list_for_event(event_id)
        return rows

    def schedule_for(self, staff_id: str) -> list[dict]:
        """Lịch trực của một nhân viên, kèm trạng thái ca tại thời điểm hiện tại."""
        now = self.app.clock.now()
        with self.app.uow() as u:
            rows = u.assignments.list_for_staff(staff_id)
        out = []
        for r in rows:
            a = StaffAssignment(r["assignment_id"], staff_id, r["event_id"], r["work_area"], None, None)
            from ..domain.validators import parse_datetime
            a.shift_start_time, a.shift_end_time = parse_datetime(r["shift_start_time"]), parse_datetime(r["shift_end_time"])
            r["shift_state"] = a.shift_state(now)
            out.append(r)
        return out
