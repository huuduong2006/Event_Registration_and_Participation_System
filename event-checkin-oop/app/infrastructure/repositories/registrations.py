from ...domain import CheckInStatus, EmailStatus, Registration, Ticket
from ..database import from_ts, ts
from .base import Repository

_ATT_SQL = """
SELECT r.registration_id, r.registration_date, r.event_id, r.ticket_type_id,
       u.user_id AS attendee_id, u.full_name, u.email, u.phone_number,
       c.type_name, c.price,
       t.ticket_id, t.check_in_status, t.checked_in_at, t.check_in_method, t.check_in_note, t.email_status,
       s.full_name AS checked_in_by_name
FROM registrations r
JOIN users u ON u.user_id = r.attendee_id
JOIN ticket_categories c ON c.ticket_type_id = r.ticket_type_id
JOIN tickets t ON t.registration_id = r.registration_id
LEFT JOIN users s ON s.user_id = t.checked_in_by
"""


class RegistrationRepository(Repository):
    def _entity(self, r):
        return None if r is None else Registration(r["registration_id"], r["event_id"], r["attendee_id"],
                                                   r["ticket_type_id"], from_ts(r["registration_date"]))

    def add(self, g: Registration) -> Registration:
        self.conn.execute("INSERT INTO registrations(registration_id,event_id,attendee_id,ticket_type_id,"
                          "registration_date) VALUES(?,?,?,?,?)",
                          (g.registration_id, g.event_id, g.attendee_id, g.ticket_type_id, ts(g.registration_date)))
        return g

    def get(self, registration_id: str):
        return self._entity(self._one("SELECT * FROM registrations WHERE registration_id=?", (registration_id,)))

    def find(self, event_id: str, attendee_id: str):
        return self._entity(self._one("SELECT * FROM registrations WHERE event_id=? AND attendee_id=?",
                                      (event_id, attendee_id)))

    def history(self, attendee_id: str) -> list[dict]:
        rows = self._all(
            "SELECT r.registration_id, r.registration_date, e.event_id, e.event_name, e.start_time, e.location,"
            " e.status, e.unique_url, c.type_name, c.price, t.ticket_id, t.check_in_status, t.checked_in_at,"
            " t.email_status FROM registrations r JOIN events e ON e.event_id=r.event_id"
            " JOIN ticket_categories c ON c.ticket_type_id=r.ticket_type_id"
            " JOIN tickets t ON t.registration_id=r.registration_id WHERE r.attendee_id=?"
            " ORDER BY r.registration_date DESC", (attendee_id,))
        return [dict(r) for r in rows]

    def attendee_row(self, registration_id: str) -> dict | None:
        r = self._one(_ATT_SQL + " WHERE r.registration_id=?", (registration_id,))
        return dict(r) if r else None

    def search(self, event_id: str, q: str | None = None, status: str | None = None,
               ticket_type_id: str | None = None, page: int | None = None, page_size: int = 20):
        where, args = ["r.event_id=?"], [event_id]
        if q:
            like = f"%{q.lower()}%"
            where.append("(LOWER(u.full_name) LIKE ? OR LOWER(u.email) LIKE ? OR u.phone_number LIKE ?"
                         " OR LOWER(r.registration_id) LIKE ?)")
            args += [like, like, f"%{q}%", like]
        if status in ("CHECKED_IN", "NOT_CHECKED_IN"):
            where.append("t.check_in_status=?"); args.append(status)
        if ticket_type_id:
            where.append("r.ticket_type_id=?"); args.append(ticket_type_id)
        w = " WHERE " + " AND ".join(where)
        total = self._one("SELECT COUNT(*) c FROM registrations r JOIN users u ON u.user_id=r.attendee_id"
                          " JOIN tickets t ON t.registration_id=r.registration_id" + w, args)["c"]
        sql = _ATT_SQL + w + " ORDER BY r.registration_date DESC, r.registration_id"
        if page:
            sql += " LIMIT ? OFFSET ?"
            args += [page_size, (page - 1) * page_size]
        return [dict(r) for r in self._all(sql, args)], total

    def count_for_event(self, event_id: str) -> int:
        return self._one("SELECT COUNT(*) c FROM registrations WHERE event_id=?", (event_id,))["c"]


class TicketRepository(Repository):
    def _entity(self, r) -> Ticket | None:
        if r is None:
            return None
        return self._bind(Ticket(r["ticket_id"], r["registration_id"], r["qr_code_data"],
                                 CheckInStatus(r["check_in_status"]), r["checked_in_at"], r["checked_in_by"],
                                 r["check_in_method"], EmailStatus(r["email_status"])))

    def add(self, t: Ticket) -> Ticket:
        self.conn.execute("INSERT INTO tickets(ticket_id,registration_id,qr_code_data,check_in_status,email_status)"
                          " VALUES(?,?,?,?,?)",
                          (t.ticket_id, t.registration_id, t.qr_code_data, t.check_in_status.value, t.email_status.value))
        return t

    def get(self, ticket_id: str):
        return self._entity(self._one("SELECT * FROM tickets WHERE ticket_id=?", (ticket_id,)))

    def get_by_registration(self, registration_id: str):
        return self._entity(self._one("SELECT * FROM tickets WHERE registration_id=?", (registration_id,)))

    def get_by_qr(self, qr_code_data: str):
        return self._entity(self._one("SELECT * FROM tickets WHERE qr_code_data=?", (qr_code_data,)))

    def set_email_status(self, ticket_id: str, status: EmailStatus) -> None:
        self.conn.execute("UPDATE tickets SET email_status=? WHERE ticket_id=?", (status.value, ticket_id))

    def mark_checked_in(self, ticket_id: str, at, by: str, method: str, note: str | None = None) -> bool:
        """Cập nhật CÓ ĐIỀU KIỆN: chỉ thành công khi vé chưa check-in → an toàn tuyệt đối với quét đồng thời."""
        cur = self.conn.execute(
            "UPDATE tickets SET check_in_status='CHECKED_IN', checked_in_at=?, checked_in_by=?, check_in_method=?,"
            " check_in_note=? WHERE ticket_id=? AND check_in_status='NOT_CHECKED_IN'",
            (ts(at), by, method, note, ticket_id))
        return cur.rowcount == 1
