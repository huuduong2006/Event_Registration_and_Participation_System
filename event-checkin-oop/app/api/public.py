"""Cổng công khai + Attendee (Luồng 1 & 3)."""
from fastapi import APIRouter, Body, Depends, Request, Response

from ..domain import Attendee
from . import serializers as ser
from .deps import attendee_user, core, limit

router = APIRouter(prefix="/api", tags=["public"])


@router.get("/public/events", dependencies=[Depends(limit("read", "read_rate_max", 60))])
def public_events(request: Request):
    return [ser.public_event(i) for i in core(request).registrations.view_available_events()]


@router.get("/public/events/{ref}", dependencies=[Depends(limit("read", "read_rate_max", 60))])
def public_event(ref: str, request: Request):
    return ser.public_event(core(request).registrations.get_public_event(ref))


def _registered(reg, ticket, app):
    v = app.tickets.view_ticket(reg.registration_id, reg.attendee_id)
    return ser.ticket_view(v, with_png=True)


@router.post("/public/events/{ref}/register", status_code=201,
             dependencies=[Depends(limit("register", "register_rate_max", 600))])
def guest_register(ref: str, request: Request, body: dict = Body(...)):
    """Khách CHƯA đăng nhập đăng ký tham dự (hồ sơ khách theo email)."""
    app = core(request)
    guest = Attendee.guest(app, body.get("fullName"), body.get("email"), body.get("phoneNumber"))
    reg, ticket = guest.submit_registration_form(ref, body.get("ticketTypeId"))
    return _registered(reg, ticket, app)


@router.post("/attendee/events/{ref}/register", status_code=201,
             dependencies=[Depends(limit("register", "register_rate_max", 600))])
def attendee_register(ref: str, request: Request, body: dict = Body(...), me: Attendee = Depends(attendee_user)):
    reg, ticket = me.submit_registration_form(ref, body.get("ticketTypeId"))
    return _registered(reg, ticket, core(request))


@router.get("/attendee/registrations")
def history(me: Attendee = Depends(attendee_user)):
    return [ser.history_row(r) for r in me.get_registration_history()]


@router.get("/attendee/registrations/{registration_id}/ticket")
def my_ticket(registration_id: str, request: Request, me: Attendee = Depends(attendee_user)):
    return ser.ticket_view(core(request).tickets.view_ticket(registration_id, me.user_id), with_png=True)


@router.get("/attendee/registrations/{registration_id}/qr.png")
def my_qr(registration_id: str, request: Request, me: Attendee = Depends(attendee_user)):
    return Response(core(request).tickets.qr_png(registration_id, me.user_id), media_type="image/png",
                    headers={"Cache-Control": "no-store"})
