from ...domain import Event, EventStatus, TicketCategory
from ...errors import Conflict
from ..database import from_ts
from ..database import ts as _ts
from ...domain.validators import format_datetime, parse_datetime
from .base import Repository

_EVENT_SQL = ("SELECT e.*, (SELECT COUNT(*) FROM registrations r WHERE r.event_id=e.event_id) AS registered_count"
              " FROM events e")
_CAT_SQL = ("SELECT c.*, (SELECT COUNT(*) FROM registrations r WHERE r.ticket_type_id=c.ticket_type_id) AS sold_count"
            " FROM ticket_categories c")


class EventRepository(Repository):
    def _entity(self, r) -> Event | None:
        if r is None:
            return None
        return Event(event_id=r["event_id"], event_name=r["event_name"], start_time=parse_datetime(r["start_time"]),
                     end_time=parse_datetime(r["end_time"]), location=r["location"], max_capacity=r["max_capacity"],
                     status=EventStatus(r["status"]), unique_url=r["unique_url"], description=r["description"],
                     created_at=r["created_at"], registered_count=r["registered_count"])

    def add(self, e: Event) -> Event:
        self.conn.execute(
            "INSERT INTO events(event_id,event_name,start_time,end_time,location,max_capacity,status,unique_url,"
            "description,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (e.event_id, e.event_name, format_datetime(e.start_time), format_datetime(e.end_time), e.location,
             e.max_capacity, e.status.value, e.unique_url, e.description, e.created_at))
        return e

    def update(self, e: Event) -> Event:
        self.conn.execute(
            "UPDATE events SET event_name=?,start_time=?,end_time=?,location=?,max_capacity=?,status=?,description=?"
            " WHERE event_id=?",
            (e.event_name, format_datetime(e.start_time), format_datetime(e.end_time), e.location, e.max_capacity,
             e.status.value, e.description, e.event_id))
        return e

    def delete(self, event_id: str) -> None:
        self.conn.execute("DELETE FROM events WHERE event_id=?", (event_id,))

    def get(self, event_id: str) -> Event | None:
        return self._entity(self._one(_EVENT_SQL + " WHERE e.event_id=?", (event_id,)))

    def get_by_url(self, unique_url: str) -> Event | None:
        return self._entity(self._one(_EVENT_SQL + " WHERE e.unique_url=?", (unique_url,)))

    def list_all(self) -> list[Event]:
        return [self._entity(r) for r in self._all(_EVENT_SQL + " ORDER BY e.start_time IS NULL, e.start_time DESC, e.created_at DESC")]

    def list_public(self) -> list[Event]:
        """Sự kiện chưa kết thúc (hiển thị ở cổng Attendee)."""
        return [self._entity(r) for r in self._all(
            _EVENT_SQL + " WHERE e.status<>'COMPLETED' ORDER BY e.start_time IS NULL, e.start_time ASC")]

    def checked_in_count(self, event_id: str) -> int:
        return self._one(
            "SELECT COUNT(*) c FROM tickets t JOIN registrations r ON r.registration_id=t.registration_id"
            " WHERE r.event_id=? AND t.check_in_status='CHECKED_IN'", (event_id,))["c"]

    def checked_in_counts(self) -> dict[str, int]:
        return {r["event_id"]: r["c"] for r in self._all(
            "SELECT r.event_id, COUNT(*) c FROM tickets t JOIN registrations r ON r.registration_id=t.registration_id"
            " WHERE t.check_in_status='CHECKED_IN' GROUP BY r.event_id")}


class CategoryRepository(Repository):
    def _entity(self, r) -> TicketCategory | None:
        if r is None:
            return None
        return TicketCategory(r["ticket_type_id"], r["event_id"], r["type_name"], r["price"], r["quantity_limit"],
                              r["sold_count"])

    def add(self, c: TicketCategory) -> TicketCategory:
        try:
            self.conn.execute("INSERT INTO ticket_categories(ticket_type_id,event_id,type_name,price,quantity_limit)"
                              " VALUES(?,?,?,?,?)", (c.ticket_type_id, c.event_id, c.type_name, c.price, c.quantity_limit))
        except Exception as e:
            if "UNIQUE" in str(e):
                raise Conflict(f"Sự kiện đã có loại vé tên “{c.type_name}”")
            raise
        return c

    def update(self, c: TicketCategory) -> TicketCategory:
        try:
            self.conn.execute("UPDATE ticket_categories SET type_name=?,price=?,quantity_limit=? WHERE ticket_type_id=?",
                              (c.type_name, c.price, c.quantity_limit, c.ticket_type_id))
        except Exception as e:
            if "UNIQUE" in str(e):
                raise Conflict(f"Sự kiện đã có loại vé tên “{c.type_name}”")
            raise
        return c

    def delete(self, ticket_type_id: str) -> None:
        self.conn.execute("DELETE FROM ticket_categories WHERE ticket_type_id=?", (ticket_type_id,))

    def get(self, ticket_type_id: str) -> TicketCategory | None:
        return self._entity(self._one(_CAT_SQL + " WHERE c.ticket_type_id=?", (ticket_type_id,)))

    def list_for_event(self, event_id: str) -> list[TicketCategory]:
        return [self._entity(r) for r in self._all(_CAT_SQL + " WHERE c.event_id=? ORDER BY c.price DESC, c.type_name",
                                                   (event_id,))]
