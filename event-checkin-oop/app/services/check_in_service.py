"""CheckInService – xử lý logic check-in tại cổng (Luồng 4).

Quy tắc: đối chiếu StaffAssignment (ca & khu vực) → tra vé → cập nhật trạng thái.
Toàn bộ chạy trong MỘT transaction ghi; việc đánh dấu check-in là UPDATE có điều kiện nên 2 thiết bị quét
cùng lúc một vé thì chỉ một bên VALID, bên kia nhận ALREADY_USED.
Mọi lần quét có kết quả đều được ghi check_in_logs (kể cả bị từ chối) để đối soát gian lận.
"""
from ..domain import CheckInMethod, CheckInOutcome, CheckInResult, EventStatus, Role
from ..domain.staff_assignment import ENDED, NOT_STARTED
from ..errors import Conflict, Forbidden, NotFound, ValidationError


class CheckInService:
    def __init__(self, app, staff_id: str):
        self.app, self.staff_id = app, staff_id

    # ---------- kiểm tra quyền theo phân công ----------
    def _staff(self, u):
        s = u.users.get(self.staff_id)
        if s is None or s.role != Role.STAFF or not s.is_active():
            raise Forbidden("Tài khoản nhân viên không hợp lệ hoặc đã bị vô hiệu hoá", "ACCOUNT_INACTIVE")
        return s

    def _assignment(self, u, event_id: str, need_shift: bool):
        a = u.assignments.find(self.staff_id, event_id)
        if a is None:
            raise Forbidden("Bạn chưa được phân công cho sự kiện này", "NOT_ASSIGNED")
        if need_shift:
            state = a.shift_state(self.app.clock.now())
            if state == NOT_STARTED:
                raise Forbidden(f"Chưa đến ca trực của bạn ({a.shift_start_time:%H:%M %d/%m}).", "OUTSIDE_SHIFT")
            if state == ENDED:
                raise Forbidden(f"Ca trực của bạn đã kết thúc ({a.shift_end_time:%H:%M %d/%m}).", "OUTSIDE_SHIFT")
        return a

    # ---------- check-in ----------
    def process_qr_code_scan(self, qr_code_data: str, event_id: str | None = None) -> CheckInResult:
        qr = str(qr_code_data or "").strip()
        if not qr or len(qr) > 200:
            raise ValidationError("Dữ liệu QR trống hoặc không hợp lệ")
        return self._process(CheckInMethod.QR, qr=qr, event_id=event_id)

    def process_manual_check_in(self, registration_id: str, note: str, event_id: str | None = None) -> CheckInResult:
        note = str(note or "").strip()
        if len(note) < 3:
            raise ValidationError("Vui lòng ghi giấy tờ đã đối chiếu (VD: SĐT)")
        return self._process(CheckInMethod.MANUAL, registration_id=str(registration_id or "").strip(), note=note[:200],
                             event_id=event_id)

    def _process(self, method, qr=None, registration_id=None, note=None, event_id=None) -> CheckInResult:
        with self.app.uow(write=True) as u:
            staff = self._staff(u)
            if event_id:                                   # sự kiện nhân viên đang làm việc trên màn hình
                if u.events.get(event_id) is None:
                    raise NotFound("Không tìm thấy sự kiện")
                self._assignment(u, event_id, need_shift=True)
            ticket = u.tickets.get_by_qr(qr) if qr else None
            reg = u.registrations.get(registration_id) if registration_id else (
                u.registrations.get(ticket.registration_id) if ticket else None)
            if reg and not ticket:
                ticket = u.tickets.get_by_registration(reg.registration_id)
            now = self.app.clock.now()

            def log(outcome, tk=None, rg=None, ev=None):
                u.logs.add(event_id=ev or event_id, ticket_id=tk.ticket_id if tk else None,
                           registration_id=rg.registration_id if rg else None, staff_id=self.staff_id,
                           outcome=outcome.value, method=method.value, note=note, at=now)

            if ticket is None or reg is None:              # mã không tồn tại
                log(CheckInOutcome.INVALID)
                return CheckInResult(CheckInOutcome.INVALID, "Mã vé không hợp lệ – không có trong hệ thống. TỪ CHỐI.")

            target_event = u.events.get(reg.event_id)
            attendee = u.users.get(reg.attendee_id)
            cat = u.categories.get(reg.ticket_type_id)
            base = dict(attendee_name=attendee.full_name, ticket_type=cat.type_name, registration_id=reg.registration_id)

            if event_id and reg.event_id != event_id:      # vé của sự kiện khác
                log(CheckInOutcome.WRONG_EVENT, ticket, reg, ev=event_id)
                return CheckInResult(CheckInOutcome.WRONG_EVENT,
                                     f"Vé thuộc sự kiện khác: “{target_event.event_name}”.", **base)
            if not event_id:                               # không chọn sự kiện → Kiểm tra nhân viên có được phân công cho sự kiện của vé hay không
                self._assignment(u, reg.event_id, need_shift=True)
            if target_event.status == EventStatus.COMPLETED:
                raise Conflict("Sự kiện đã kết thúc, không thể check-in.", "EVENT_CLOSED")

            area = u.assignments.find(self.staff_id, reg.event_id).work_area
            if u.tickets.mark_checked_in(ticket.ticket_id, now, self.staff_id, method.value, note):
                log(CheckInOutcome.VALID, ticket, reg, ev=reg.event_id)
                return CheckInResult(CheckInOutcome.VALID, "Hợp lệ – mời vào.", work_area=area, **base)
            prev = u.tickets.get(ticket.ticket_id)
            by = u.users.get(prev.checked_in_by)
            log(CheckInOutcome.ALREADY_USED, ticket, reg, ev=reg.event_id)
            return CheckInResult(
                CheckInOutcome.ALREADY_USED, "Vé ĐÃ ĐƯỢC SỬ DỤNG – nghi vé sao chép. TỪ CHỐI và báo giám sát.",
                work_area=area, first_check_in={"at": prev.checked_in_at, "by": by.full_name if by else None,
                                                "method": prev.check_in_method}, **base)

    # ---------- hỗ trợ màn hình check-in ----------
    def search_attendees(self, event_id: str, query: str) -> list[dict]:
        q = str(query or "").strip()
        if len(q) < 2:
            return []
        with self.app.uow() as u:
            self._staff(u)
            self._assignment(u, event_id, need_shift=False)
            rows, _ = u.registrations.search(event_id, q, page=1, page_size=20)
        return rows

    def get_stats(self, event_id: str) -> dict:
        with self.app.uow() as u:
            self._staff(u)
            a = self._assignment(u, event_id, need_shift=False)
            e = u.events.get(event_id)
            registered, checked = e.registered_count, u.events.checked_in_count(event_id)
            recent, outcomes = u.logs.recent(event_id, 15), u.logs.outcome_counts(event_id)
        return {"event": e, "assignment": a, "registered": registered, "checked_in": checked,
                "remaining": registered - checked, "recent": recent, "by_outcome": outcomes,
                "shift_state": a.shift_state(self.app.clock.now())}
