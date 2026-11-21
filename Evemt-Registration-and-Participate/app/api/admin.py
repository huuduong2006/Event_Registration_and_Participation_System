"""Administrator (Luồng 2). Mọi route yêu cầu lớp Administrator."""
from urllib.parse import quote

from fastapi import APIRouter, Body, Depends, Query, Request, Response

from ..domain import Administrator
from . import serializers as ser
from .deps import admin_user, core

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(admin_user)])


# ---------- sự kiện ----------
@router.get("/events")
def list_events(me: Administrator = Depends(admin_user)):
    return [ser.event(i["event"], checked_in=i["checked_in"]) for i in me.list_events()]


@router.post("/events", status_code=201)
def create_event(body: dict = Body(...), me: Administrator = Depends(admin_user)):
    return ser.event(me.create_event(
        event_name=body.get("eventName"), max_capacity=body.get("maxCapacity"), start_time=body.get("startTime"),
        end_time=body.get("endTime"), location=body.get("location"), description=body.get("description")))


@router.get("/events/{event_id}")
def get_event(event_id: str, me: Administrator = Depends(admin_user)):
    return ser.event(me.get_event(event_id), me.list_ticket_categories(event_id))


@router.put("/events/{event_id}")
def edit_event(event_id: str, body: dict = Body(...), me: Administrator = Depends(admin_user)):
    m = {"eventName": "event_name", "maxCapacity": "max_capacity", "startTime": "start_time", "endTime": "end_time",
         "location": "location", "description": "description"}
    return ser.event(me.edit_event(event_id, **{v: body[k] for k, v in m.items() if k in body}))


@router.patch("/events/{event_id}/status")
def set_status(event_id: str, body: dict = Body(...), me: Administrator = Depends(admin_user)):
    return ser.event(me.update_event_status(event_id, body.get("status")))


@router.delete("/events/{event_id}")
def delete_event(event_id: str, me: Administrator = Depends(admin_user)):
    me.delete_event(event_id)
    return {"ok": True}


# ---------- hạng vé ----------
@router.post("/events/{event_id}/categories", status_code=201)
def add_category(event_id: str, body: dict = Body(...), me: Administrator = Depends(admin_user)):
    return ser.category(me.configure_ticket_category(event_id, body.get("typeName"), body.get("price"),
                                                     body.get("quantityLimit")))


@router.put("/events/{event_id}/categories/{ticket_type_id}")
def edit_category(event_id: str, ticket_type_id: str, body: dict = Body(...), me: Administrator = Depends(admin_user)):
    return ser.category(me.configure_ticket_category(event_id, body.get("typeName"), body.get("price"),
                                                     body.get("quantityLimit"), ticket_type_id))


@router.delete("/categories/{ticket_type_id}")
def delete_category(ticket_type_id: str, me: Administrator = Depends(admin_user)):
    me.remove_ticket_category(ticket_type_id)
    return {"ok": True}


# ---------- nhân sự ----------
@router.get("/staff")
def list_staff(me: Administrator = Depends(admin_user)):
    return [{**ser.user(i["staff"]), "assignmentCount": i["assignments"]} for i in me.list_staff()]


@router.post("/staff", status_code=201)
def add_staff(body: dict = Body(...), me: Administrator = Depends(admin_user)):
    s, temp = me.add_staff(body.get("fullName"), body.get("email"), body.get("phoneNumber"), body.get("password"))
    return {**ser.user(s), "temporaryPassword": temp}


@router.patch("/staff/{staff_id}")
def set_staff_status(staff_id: str, body: dict = Body(...), me: Administrator = Depends(admin_user)):
    active = str(body.get("staffStatus", "")).upper() == "ACTIVE"
    return ser.user(me.reactivate_staff(staff_id) if active else me.remove_staff(staff_id))


# ---------- phân công ----------
@router.get("/events/{event_id}/assignments")
def list_assignments(event_id: str, me: Administrator = Depends(admin_user)):
    return [ser.assignment_row(r) for r in me.list_staff_assignments(event_id)]


@router.post("/events/{event_id}/assignments", status_code=201)
def assign(event_id: str, body: dict = Body(...), me: Administrator = Depends(admin_user)):
    a = me.assign_staff_schedule(body.get("staffId"), event_id, body.get("workArea"), body.get("shiftStartTime"),
                                 body.get("shiftEndTime"))
    return ser.assignment_row({"assignment_id": a.assignment_id, "staff_id": a.staff_id, "event_id": a.event_id,
                               "work_area": a.work_area,
                               "shift_start_time": a.shift_start_time and a.shift_start_time.strftime("%Y-%m-%dT%H:%M"),
                               "shift_end_time": a.shift_end_time and a.shift_end_time.strftime("%Y-%m-%dT%H:%M")})


@router.patch("/assignments/{assignment_id}")
def update_assignment(assignment_id: str, body: dict = Body(...), me: Administrator = Depends(admin_user)):
    a = me.update_staff_assignment(assignment_id, body.get("workArea"), body.get("shiftStartTime"),
                                   body.get("shiftEndTime"), change_shift=("shiftStartTime" in body or "shiftEndTime" in body))
    return {"assignmentId": a.assignment_id, "workArea": a.work_area}


@router.delete("/assignments/{assignment_id}")
def unassign(assignment_id: str, me: Administrator = Depends(admin_user)):
    me.unassign_staff(assignment_id)
    return {"ok": True}


# ---------- báo cáo ----------
@router.get("/events/{event_id}/attendees")
def attendees(event_id: str, q: str | None = None, status: str | None = None, ticketTypeId: str | None = None,
              page: int = Query(1, ge=1), pageSize: int = Query(20, ge=1, le=200),
              me: Administrator = Depends(admin_user)):
    r = me.view_attendee_list(event_id, q, status, ticketTypeId, page, pageSize)
    return {"items": [ser.attendee_row(x) for x in r["items"]], "total": r["total"], "page": r["page"],
            "pageSize": r["page_size"]}


@router.get("/events/{event_id}/report")
def report(event_id: str, me: Administrator = Depends(admin_user)):
    r = me.report_exporter().generate_report(event_id)
    e = r.pop("event")
    out = {"event": ser.event(e)}
    out.update({_camel(k): v for k, v in r.items()})
    out["byTicketType"] = [{_camel(k): v for k, v in t.items()} for t in r["by_ticket_type"]]
    return out


@router.get("/events/{event_id}/export.{fmt}")
def export(event_id: str, fmt: str, me: Administrator = Depends(admin_user)):
    ex = me.report_exporter()
    ev = me.get_event(event_id)
    name = quote(f"{ev.unique_url}.{'xlsx' if fmt == 'xlsx' else 'csv'}")
    if fmt == "xlsx":
        data, mt = ex.export_excel(event_id), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        data, mt = ex.export_csv(event_id), "text/csv; charset=utf-8"
    return Response(data, media_type=mt, headers={"Content-Disposition": f"attachment; filename*=UTF-8''{name}"})


@router.post("/tickets/{ticket_id}/resend-email")
def resend(ticket_id: str, me: Administrator = Depends(admin_user)):
    return {"emailStatus": me.resend_ticket_email(ticket_id).value}


def _camel(s: str) -> str:
    h, *t = s.split("_")
    return h + "".join(x.title() for x in t)
