from fastapi import APIRouter, Body, Depends, Request

from ..domain import Attendee, User
from . import serializers as ser
from .deps import bearer, core, current_user, limit

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", dependencies=[Depends(limit("login", "login_rate_max", 900))])
def login(request: Request, body: dict = Body(...)):
    token, user = core(request).auth.login(body.get("email"), body.get("password"), body.get("portal"))
    return {"token": token, "user": ser.user(user)}


@router.post("/register", status_code=201, dependencies=[Depends(limit("signup", "signup_rate_max", 3600))])
def register(request: Request, body: dict = Body(...)):
    """Cổng Attendee: khách tự đăng ký tài khoản (nhân viên KHÔNG đăng ký ở đây)."""
    a = Attendee.register(core(request), body.get("fullName"), body.get("email"), body.get("phoneNumber"),
                          body.get("password"))
    return {"token": a.login(body.get("password")), "user": ser.user(a)}


@router.post("/logout")
def logout(request: Request, user: User = Depends(current_user)):
    user.logout(bearer(request))
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(current_user)):
    return ser.user(user)


@router.patch("/me")
def update_me(body: dict = Body(...), user: User = Depends(current_user)):
    u = user.update_profile(body.get("fullName"), body.get("phoneNumber"), body.get("currentPassword"),
                            body.get("newPassword"))
    return ser.user(u)
