"""Dependency: nạp người dùng đúng LỚP theo token. Router khai báo lớp được phép → phân quyền theo cấu trúc OOP."""
from fastapi import Depends, Request

from ..domain import Administrator, Attendee, EventStaff, User
from ..errors import Forbidden, Unauthorized


def core(request: Request):
    return request.app.state.core


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "?"


def bearer(request: Request) -> str:
    h = request.headers.get("authorization", "")
    if not h.lower().startswith("bearer ") or not h[7:].strip():
        raise Unauthorized("Vui lòng đăng nhập")
    return h[7:].strip()


def current_user(request: Request) -> User:
    return core(request).auth.authenticate(bearer(request))


def _require(*classes):
    def dep(user: User = Depends(current_user)):
        if not isinstance(user, classes):
            raise Forbidden("Bạn không có quyền thực hiện thao tác này")
        return user
    return dep


admin_user = _require(Administrator)
staff_user = _require(EventStaff)
attendee_user = _require(Attendee)


def limit(kind: str, maximum_attr: str, window: int):
    """Giới hạn tần suất theo IP."""
    def dep(request: Request):
        c = core(request)
        c.limiter.check(f"{kind}:{client_ip(request)}", getattr(c.settings, maximum_attr), window)
    return dep
