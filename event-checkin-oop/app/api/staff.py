"""EventStaff (Luồng 4). Mọi route yêu cầu lớp EventStaff."""
from fastapi import APIRouter, Body, Depends

from ..domain import EventStaff
from . import serializers as ser
from .deps import staff_user

router = APIRouter(prefix="/api/staff", tags=["staff"])


@router.get("/schedule")
def schedule(me: EventStaff = Depends(staff_user)):
    return [ser.assignment_row(r) for r in me.view_assigned_schedule()]


@router.post("/check-in/scan")
def scan(body: dict = Body(...), me: EventStaff = Depends(staff_user)):
    return me.scan_qr_code(body.get("qrCodeData"), body.get("eventId")).to_dict()


@router.post("/check-in/manual")
def manual(body: dict = Body(...), me: EventStaff = Depends(staff_user)):
    return me.manual_check_in(body.get("registrationId"), body.get("note"), body.get("eventId")).to_dict()


@router.get("/events/{event_id}/attendees")
def search(event_id: str, q: str = "", me: EventStaff = Depends(staff_user)):
    return [ser.attendee_row(r) for r in me.search_attendees(event_id, q)]


@router.get("/events/{event_id}/stats")
def stats(event_id: str, me: EventStaff = Depends(staff_user)):
    s = me.check_in_stats(event_id)
    return {"event": ser.event(s["event"]), "workArea": s["assignment"].work_area, "shiftState": s["shift_state"],
            "registered": s["registered"], "checkedIn": s["checked_in"], "remaining": s["remaining"],
            "byOutcome": s["by_outcome"],
            "recent": [{"outcome": r["outcome"], "method": r["method"], "at": r["created_at"],
                        "attendeeName": r["attendee_name"], "staffName": r["staff_name"],
                        "registrationId": r["registration_id"]} for r in s["recent"]]}
