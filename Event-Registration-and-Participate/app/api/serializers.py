"""Đối tượng domain → JSON (camelCase,)."""
import base64

from ..domain import Event, TicketCategory, User
from ..domain.user import EventStaff
from ..domain.validators import format_datetime


def user(u: User) -> dict:
    d = {"userId": u.user_id, "fullName": u.full_name, "email": u.email, "phoneNumber": u.phone_number,
         "role": u.role.value, "createdAt": u.created_at}
    if isinstance(u, EventStaff):
        d["staffStatus"] = u.staff_status.value
    return d


def category(c: TicketCategory, event: Event | None = None) -> dict:
    return {"ticketTypeId": c.ticket_type_id, "eventId": c.event_id, "typeName": c.type_name, "price": c.price,
            "quantityLimit": c.quantity_limit, "soldCount": c.sold_count,
            "remaining": event.remaining_for(c) if event else c.remaining}


def event(e: Event, categories=None, checked_in: int | None = None, closed_reason=False) -> dict:
    d = {"eventId": e.event_id, "eventName": e.event_name, "startTime": format_datetime(e.start_time),
         "endTime": format_datetime(e.end_time), "location": e.location, "maxCapacity": e.max_capacity,
         "status": e.status.value, "uniqueUrl": e.unique_url, "description": e.description,
         "registeredCount": e.registered_count, "availableCapacity": e.get_available_capacity()}
    if categories is not None:
        d["ticketCategories"] = [category(c, e) for c in categories]
    if checked_in is not None:
        d["checkedInCount"] = checked_in
    if closed_reason is not False:
        d["closedReason"] = closed_reason
    return d


def public_event(item: dict) -> dict:
    return event(item["event"], item["categories"], closed_reason=item["closed_reason"])


def attendee_row(r: dict) -> dict:
    return {"registrationId": r["registration_id"], "ticketId": r["ticket_id"], "attendeeId": r["attendee_id"],
            "fullName": r["full_name"], "email": r["email"], "phoneNumber": r["phone_number"],
            "ticketTypeId": r["ticket_type_id"], "ticketType": r["type_name"], "price": r["price"],
            "registrationDate": r["registration_date"], "checkInStatus": r["check_in_status"],
            "checkedInAt": r["checked_in_at"], "checkInMethod": r["check_in_method"],
            "checkInNote": r["check_in_note"], "checkedInBy": r["checked_in_by_name"],
            "emailStatus": r["email_status"]}


def assignment_row(r: dict) -> dict:
    d = {"assignmentId": r["assignment_id"], "staffId": r["staff_id"], "eventId": r["event_id"],
         "workArea": r["work_area"], "shiftStartTime": r["shift_start_time"], "shiftEndTime": r["shift_end_time"]}
    for k_src, k in (("full_name", "fullName"), ("email", "email"), ("phone_number", "phoneNumber"),
                     ("staff_status", "staffStatus"), ("event_name", "eventName"), ("start_time", "startTime"),
                     ("end_time", "endTime"), ("location", "location"), ("status", "status"),
                     ("unique_url", "uniqueUrl"), ("shift_state", "shiftState")):
        if k_src in r:
            d[k] = r[k_src]
    return d


def history_row(r: dict) -> dict:
    return {"registrationId": r["registration_id"], "registrationDate": r["registration_date"],
            "eventId": r["event_id"], "eventName": r["event_name"], "startTime": r["start_time"],
            "location": r["location"], "eventStatus": r["status"], "uniqueUrl": r["unique_url"],
            "ticketType": r["type_name"], "price": r["price"], "ticketId": r["ticket_id"],
            "checkInStatus": r["check_in_status"], "checkedInAt": r["checked_in_at"],
            "emailStatus": r["email_status"]}


def ticket_view(v: dict, with_png: bool = False) -> dict:
    t, reg, ev, cat = v["ticket"], v["registration"], v["event"], v["category"]
    d = {"registrationId": reg.registration_id, "registrationDate": reg.registration_date.strftime("%Y-%m-%dT%H:%M:%S"),
         "ticketId": t.ticket_id, "qrCodeData": t.qr_code_data, "checkInStatus": t.check_in_status.value,
         "checkedInAt": t.checked_in_at, "emailStatus": t.email_status.value,
         "event": event(ev), "ticketType": cat.type_name, "price": cat.price}
    if with_png:
        d["qrImage"] = "data:image/png;base64," + base64.b64encode(t.generate_qr_code()).decode()
    return d
