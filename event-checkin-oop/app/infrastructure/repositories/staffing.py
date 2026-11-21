from ...domain import StaffAssignment
from ...domain.validators import format_datetime, parse_datetime
from ..database import ts
from .base import Repository


class AssignmentRepository(Repository):
    def _entity(self, r):
        return None if r is None else StaffAssignment(
            r["assignment_id"], r["staff_id"], r["event_id"], r["work_area"],
            parse_datetime(r["shift_start_time"]), parse_datetime(r["shift_end_time"]))

    def add(self, a: StaffAssignment) -> StaffAssignment:
        self.conn.execute("INSERT INTO staff_assignments(assignment_id,staff_id,event_id,work_area,shift_start_time,"
                          "shift_end_time) VALUES(?,?,?,?,?,?)",
                          (a.assignment_id, a.staff_id, a.event_id, a.work_area,
                           format_datetime(a.shift_start_time), format_datetime(a.shift_end_time)))
        return a

    def update(self, a: StaffAssignment) -> StaffAssignment:
        self.conn.execute("UPDATE staff_assignments SET work_area=?, shift_start_time=?, shift_end_time=?"
                          " WHERE assignment_id=?",
                          (a.work_area, format_datetime(a.shift_start_time), format_datetime(a.shift_end_time),
                           a.assignment_id))
        return a

    def delete(self, assignment_id: str) -> None:
        self.conn.execute("DELETE FROM staff_assignments WHERE assignment_id=?", (assignment_id,))

    def get(self, assignment_id: str):
        return self._entity(self._one("SELECT * FROM staff_assignments WHERE assignment_id=?", (assignment_id,)))

    def find(self, staff_id: str, event_id: str):
        return self._entity(self._one("SELECT * FROM staff_assignments WHERE staff_id=? AND event_id=?",
                                      (staff_id, event_id)))

    def list_for_event(self, event_id: str) -> list[dict]:
        return [dict(r) for r in self._all(
            "SELECT a.*, u.full_name, u.email, u.phone_number, u.staff_status FROM staff_assignments a"
            " JOIN users u ON u.user_id=a.staff_id WHERE a.event_id=? ORDER BY a.work_area, u.full_name", (event_id,))]

    def list_for_staff(self, staff_id: str) -> list[dict]:
        return [dict(r) for r in self._all(
            "SELECT a.*, e.event_name, e.start_time, e.end_time, e.location, e.status, e.unique_url"
            " FROM staff_assignments a JOIN events e ON e.event_id=a.event_id WHERE a.staff_id=?"
            " ORDER BY e.start_time IS NULL, e.start_time DESC", (staff_id,))]

    def counts_by_staff(self) -> dict[str, int]:
        return {r["staff_id"]: r["c"] for r in self._all(
            "SELECT staff_id, COUNT(*) c FROM staff_assignments GROUP BY staff_id")}


class CheckInLogRepository(Repository):
    def add(self, *, event_id, ticket_id, registration_id, staff_id, outcome: str, method: str, note, at) -> None:
        self.conn.execute(
            "INSERT INTO check_in_logs(event_id,ticket_id,registration_id,staff_id,outcome,method,note,created_at)"
            " VALUES(?,?,?,?,?,?,?,?)", (event_id, ticket_id, registration_id, staff_id, outcome, method, note, ts(at)))

    def recent(self, event_id: str, limit: int = 15) -> list[dict]:
        return [dict(r) for r in self._all(
            "SELECT l.log_id, l.outcome, l.method, l.note, l.created_at, l.registration_id, s.full_name AS staff_name,"
            " u.full_name AS attendee_name FROM check_in_logs l LEFT JOIN users s ON s.user_id=l.staff_id"
            " LEFT JOIN registrations r ON r.registration_id=l.registration_id"
            " LEFT JOIN users u ON u.user_id=r.attendee_id WHERE l.event_id=? ORDER BY l.log_id DESC LIMIT ?",
            (event_id, limit))]

    def outcome_counts(self, event_id: str) -> dict[str, int]:
        return {r["outcome"]: r["c"] for r in self._all(
            "SELECT outcome, COUNT(*) c FROM check_in_logs WHERE event_id=? GROUP BY outcome", (event_id,))}


class RevokedTokenRepository(Repository):
    def revoke(self, jti: str, expires_at: int) -> None:
        self.conn.execute("INSERT OR IGNORE INTO revoked_tokens(jti,expires_at) VALUES(?,?)", (jti, expires_at))

    def is_revoked(self, jti: str) -> bool:
        return self._one("SELECT 1 FROM revoked_tokens WHERE jti=?", (jti,)) is not None

    def purge(self, now_epoch: int) -> None:
        self.conn.execute("DELETE FROM revoked_tokens WHERE expires_at < ?", (now_epoch,))
