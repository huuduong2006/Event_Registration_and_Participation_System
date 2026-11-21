"""RegistrationService: Luồng 3 – đăng ký tham dự & cấp vé."""
from ..domain import Attendee, Registration, Ticket
from ..errors import Conflict, NotFound, ValidationError

_BY_CODE = {"VALIDATION": ValidationError, "CLOSED": Conflict, "SOLD_OUT": Conflict, "DUPLICATE": Conflict}


class RegistrationService:
    def __init__(self, app):
        self.app = app

    # ---------- xem sự kiện ----------
    def _public_item(self, e, cats) -> dict:
        return {"event": e, "categories": cats, "closed_reason": e.closed_reason(cats)}

    def view_available_events(self) -> list[dict]:
        with self.app.uow() as u:
            return [self._public_item(e, u.categories.list_for_event(e.event_id)) for e in u.events.list_public()]

    def get_public_event(self, ref: str) -> dict:
        with self.app.uow() as u:
            e = u.events.get(ref) or u.events.get_by_url(ref)
            if e is None:
                raise NotFound("Không tìm thấy sự kiện")
            return self._public_item(e, u.categories.list_for_event(e.event_id))

    # ---------- đăng ký ----------
    def submit_registration_form(self, attendee: Attendee, event_ref: str, ticket_type_id: str):
        """Một transaction: đọc số liệu mới nhất → validate → ghi phiếu + vé. Không thể bán quá số lượng."""
        with self.app.uow(write=True) as u:
            event = u.events.get(event_ref) or u.events.get_by_url(event_ref)
            if event is None:
                raise NotFound("Không tìm thấy sự kiện")
            cats = u.categories.list_for_event(event.event_id)
            cat = next((c for c in cats if c.ticket_type_id == ticket_type_id), None)
            reg = Registration.submit_form(event.event_id, attendee.user_id, ticket_type_id, self.app.clock.now())
            already = u.registrations.find(event.event_id, attendee.user_id) is not None
            err = reg.validation_error(event, cat, already, cats)
            if err:
                code, msg = err
                raise _BY_CODE[code](msg, code)
            u.registrations.add(reg)
            ticket = Ticket.issue(reg.registration_id).bind(self.app)
            u.tickets.add(ticket)
        ticket.send_email_with_ticket()                  # sau khi commit; lỗi email không làm mất vé
        return reg, ticket

    def get_registration_history(self, attendee_id: str) -> list[dict]:
        with self.app.uow() as u:
            return u.registrations.history(attendee_id)

    # ---------- danh sách tham dự (Admin) ----------
    def list_attendees(self, event_id, q=None, status=None, ticket_type_id=None, page=1, page_size=20) -> dict:
        page, page_size = max(1, int(page or 1)), min(200, max(1, int(page_size or 20)))
        with self.app.uow() as u:
            if u.events.get(event_id) is None:
                raise NotFound("Không tìm thấy sự kiện")
            rows, total = u.registrations.search(event_id, (q or "").strip() or None, status, ticket_type_id,
                                                 page, page_size)
        return {"items": rows, "total": total, "page": page, "page_size": page_size}
