"""EventService: sự kiện & hạng vé (chức năng của Administrator)."""
from ..domain import Event, EventStatus, TicketCategory
from ..domain.validators import format_datetime
from ..errors import Conflict, NotFound
from ..infrastructure.database import ts


class EventService:
    def __init__(self, app):
        self.app = app

    def create_event(self, event_name, max_capacity, start_time=None, end_time=None, location=None,
                     description=None, status=EventStatus.UPCOMING, **_) -> Event:
        e = Event.create(event_name, max_capacity, start_time, end_time, location, description, status)
        e.created_at = ts(self.app.clock.now())
        with self.app.uow(write=True) as u:
            u.events.add(e)
        return e

    def get_event(self, event_id: str) -> Event:
        with self.app.uow() as u:
            e = u.events.get(event_id)
        if e is None:
            raise NotFound("Không tìm thấy sự kiện")
        return e

    def get_event_by_ref(self, ref: str) -> Event:
        """Tìm theo event_id hoặc unique_url."""
        with self.app.uow() as u:
            e = u.events.get(ref) or u.events.get_by_url(ref)
        if e is None:
            raise NotFound("Không tìm thấy sự kiện")
        return e

    def edit_event(self, event_id: str, **data) -> Event:
        with self.app.uow(write=True) as u:
            e = u.events.get(event_id)
            if e is None:
                raise NotFound("Không tìm thấy sự kiện")
            cur = dict(event_name=e.event_name, max_capacity=e.max_capacity, start_time=format_datetime(e.start_time),
                       end_time=format_datetime(e.end_time), location=e.location, description=e.description)
            cur.update({k: v for k, v in data.items() if k in cur})
            e.edit(**cur)
            if "status" in data and data["status"] is not None:
                e.update_status(data["status"])
            u.events.update(e)
        return e

    def update_event_status(self, event_id: str, status) -> Event:
        with self.app.uow(write=True) as u:
            e = u.events.get(event_id)
            if e is None:
                raise NotFound("Không tìm thấy sự kiện")
            e.update_status(status)
            u.events.update(e)
        return e

    def delete_event(self, event_id: str) -> None:
        with self.app.uow(write=True) as u:
            e = u.events.get(event_id)
            if e is None:
                raise NotFound("Không tìm thấy sự kiện")
            if e.registered_count > 0:
                raise Conflict(f"Sự kiện đã có {e.registered_count} người đăng ký nên không thể xoá. "
                               "Hãy chuyển sang trạng thái Completed.")
            u.events.delete(event_id)

    def list_events_with_stats(self) -> list[dict]:
        with self.app.uow() as u:
            events, checked = u.events.list_all(), u.events.checked_in_counts()
        return [{"event": e, "checked_in": checked.get(e.event_id, 0)} for e in events]

    # ---------- hạng vé ----------
    def list_categories(self, event_id: str) -> list[TicketCategory]:
        with self.app.uow() as u:
            if u.events.get(event_id) is None:
                raise NotFound("Không tìm thấy sự kiện")
            return u.categories.list_for_event(event_id)

    def configure_ticket_category(self, event_id, type_name, price, quantity_limit, ticket_type_id=None):
        with self.app.uow(write=True) as u:
            if u.events.get(event_id) is None:
                raise NotFound("Không tìm thấy sự kiện")
            if ticket_type_id:
                c = u.categories.get(ticket_type_id)
                if c is None or c.event_id != event_id:
                    raise NotFound("Không tìm thấy loại vé")
                c.update_details(type_name, price, quantity_limit)
                return u.categories.update(c)
            return u.categories.add(TicketCategory.create(event_id, type_name, price, quantity_limit))

    def remove_ticket_category(self, ticket_type_id: str) -> str:
        with self.app.uow(write=True) as u:
            c = u.categories.get(ticket_type_id)
            if c is None:
                raise NotFound("Không tìm thấy loại vé")
            if c.sold_count > 0:
                raise Conflict(f"Đã bán {c.sold_count} vé loại này nên không thể xoá")
            u.categories.delete(ticket_type_id)
            return c.event_id
