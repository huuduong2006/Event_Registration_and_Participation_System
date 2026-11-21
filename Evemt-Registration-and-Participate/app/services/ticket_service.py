"""TicketService: gửi/gửi lại email vé, xem vé của khách."""
import html

from ..domain import EmailStatus, Ticket
from ..errors import Forbidden, NotFound


class TicketService:
    def __init__(self, app):
        self.app = app

    def _context(self, u, ticket: Ticket):
        reg = u.registrations.get(ticket.registration_id)
        event = u.events.get(reg.event_id)
        cat = u.categories.get(reg.ticket_type_id)
        att = u.users.get(reg.attendee_id)
        return reg, event, cat, att

    def send_email(self, ticket: Ticket) -> EmailStatus:
        """Gửi vé (QR nhúng + đính kèm). Không bao giờ ném lỗi: kết quả lưu vào email_status."""
        try:
            with self.app.uow() as u:
                reg, event, cat, att = self._context(u, ticket)
            png = ticket.generate_qr_code()
            when = event.start_time.strftime("%H:%M %d/%m/%Y") if event.start_time else "Sẽ thông báo sau"
            link = f"{self.app.settings.base_url}/account/ticket.html?id={reg.registration_id}"
            text = (f"Xin chào {att.full_name},\n\nBạn đã đăng ký thành công “{event.event_name}”.\n"
                    f"Loại vé: {cat.type_name}\nThời gian: {when}\nĐịa điểm: {event.location or '—'}\n"
                    f"Mã đăng ký: {reg.registration_id}\n\nXuất trình mã QR đính kèm tại cổng. Xem vé: {link}\n")
            body = (f"<p>Xin chào <b>{html.escape(att.full_name)}</b>,</p><p>Bạn đã đăng ký thành công "
                    f"<b>{html.escape(event.event_name)}</b>.</p><ul><li>Loại vé: {html.escape(cat.type_name)}</li>"
                    f"<li>Thời gian: {when}</li><li>Địa điểm: {html.escape(event.location or '—')}</li>"
                    f"<li>Mã đăng ký: {reg.registration_id}</li></ul>"
                    f'<p><img src="cid:qr" width="220" alt="QR"></p><p><a href="{link}">Xem vé trực tuyến</a></p>')
            self.app.mailer.send(att.email, f"Vé tham dự: {event.event_name}", text, body,
                                 [("ticket-qr.png", png, "image/png", "qr")])
            status = EmailStatus.SENT
        except Exception:
            status = EmailStatus.FAILED
        with self.app.uow(write=True) as u:
            u.tickets.set_email_status(ticket.ticket_id, status)
        ticket.email_status = status
        return status

    def resend_email(self, ticket_id: str) -> EmailStatus:
        with self.app.uow() as u:
            t = u.tickets.get(ticket_id)
        if t is None:
            raise NotFound("Không tìm thấy vé")
        return self.send_email(t)

    def view_ticket(self, registration_id: str, attendee_id: str) -> dict:
        """Chi tiết vé – chỉ chủ vé xem được."""
        with self.app.uow() as u:
            reg = u.registrations.get(registration_id)
            if reg is None:
                raise NotFound("Không tìm thấy vé")
            if reg.attendee_id != attendee_id:
                raise Forbidden("Bạn không có quyền xem vé này")
            t = u.tickets.get_by_registration(registration_id)
            return {"registration": reg, "ticket": t, "event": u.events.get(reg.event_id),
                    "category": u.categories.get(reg.ticket_type_id)}

    def qr_png(self, registration_id: str, attendee_id: str) -> bytes:
        return self.view_ticket(registration_id, attendee_id)["ticket"].generate_qr_code()
