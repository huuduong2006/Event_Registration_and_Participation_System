"""Dịch lỗi → JSON thống nhất {"error": thông báo, "code": mã}."""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from ..errors import DomainError

log = logging.getLogger("app")


def _json(status: int, message: str, code: str) -> JSONResponse:
    return JSONResponse({"error": message, "code": code}, status_code=status)


def install(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def domain(_: Request, e: DomainError):
        return _json(e.status, e.message, e.code)

    @app.exception_handler(RequestValidationError)
    async def invalid(_: Request, e: RequestValidationError):
        return _json(400, "Dữ liệu gửi lên không hợp lệ", "VALIDATION")

    @app.exception_handler(StarletteHTTPException)
    async def http(_: Request, e: StarletteHTTPException):
        msg = "Không tìm thấy" if e.status_code == 404 else str(e.detail)
        return _json(e.status_code, msg, "NOT_FOUND" if e.status_code == 404 else "ERROR")

    @app.exception_handler(Exception)
    async def unexpected(_: Request, e: Exception):
        log.exception("Lỗi không lường trước")
        return _json(500, "Lỗi hệ thống", "INTERNAL")
