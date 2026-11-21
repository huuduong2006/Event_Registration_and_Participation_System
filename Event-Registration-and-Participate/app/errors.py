"""Lỗi nghiệp vụ.

Tầng domain/services chỉ ném các lỗi này; tầng API (api/errors.py) dịch chúng thành HTTP + JSON
{"error": <thông báo>, "code": <mã>} nên frontend luôn nhận cùng một định dạng.
"""


class DomainError(Exception):
    status = 400
    default_code = "ERROR"

    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        self.message = message
        self.code = code or self.default_code


class ValidationError(DomainError):
    status, default_code = 400, "VALIDATION"


class Unauthorized(DomainError):
    status, default_code = 401, "UNAUTHORIZED"


class Forbidden(DomainError):
    status, default_code = 403, "FORBIDDEN"


class NotFound(DomainError):
    status, default_code = 404, "NOT_FOUND"


class Conflict(DomainError):
    status, default_code = 409, "CONFLICT"


class TooManyRequests(DomainError):
    status, default_code = 429, "RATE_LIMIT"
