"""Kiểm tra & chuẩn hoá dữ liệu đầu vào."""
import re
import unicodedata
from datetime import datetime

from ..errors import ValidationError

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$")
PHONE_RE = re.compile(r"^(\+?84|0)\d{8,10}$")          # số di động/cố định Việt Nam
DT_FORMAT = "%Y-%m-%dT%H:%M"


def clean_name(value, field: str = "Họ tên", lo: int = 2, hi: int = 100) -> str:
    v = re.sub(r"\s+", " ", str(value if value is not None else "").strip())
    if not lo <= len(v) <= hi:
        raise ValidationError(f"{field} phải từ {lo} đến {hi} ký tự")
    return v


def clean_email(value) -> str:
    v = str(value if value is not None else "").strip().lower()
    if not EMAIL_RE.match(v) or len(v) > 254:
        raise ValidationError("Email không hợp lệ")
    return v


def clean_phone(value) -> str:
    v = re.sub(r"[\s.\-]", "", str(value if value is not None else ""))
    if not PHONE_RE.match(v):
        raise ValidationError("Số điện thoại không hợp lệ (VD: 0901234567)")
    return v


def clean_password(value, minimum: int = 8) -> str:
    v = str(value if value is not None else "")
    if len(v) < minimum or len(v.encode()) > 72:      # bcrypt chỉ nhận tối đa 72 byte
        raise ValidationError(f"Mật khẩu phải từ {minimum} đến 72 ký tự")
    return v


def clean_int(value, field: str, lo: int | None = None, hi: int | None = None) -> int:
    if isinstance(value, bool):
        raise ValidationError(f"{field} phải là số nguyên")
    try:
        f = float(str(value).strip())
    except (TypeError, ValueError):
        raise ValidationError(f"{field} phải là số nguyên")
    if f != int(f):
        raise ValidationError(f"{field} phải là số nguyên")
    n = int(f)
    if (lo is not None and n < lo) or (hi is not None and n > hi):
        rng = f"≥ {lo}" if hi is None else f"từ {lo} đến {hi}"
        raise ValidationError(f"{field} phải {rng}")
    return n


def clean_money(value, field: str = "Giá vé") -> float:
    try:
        f = float(str(value).strip())
    except (TypeError, ValueError):
        raise ValidationError(f"{field} phải là một số ≥ 0 (VND)")
    if f < 0 or f != f or f == float("inf"):
        raise ValidationError(f"{field} phải là một số ≥ 0 (VND)")
    return f


def parse_datetime(value, field: str = "Thời gian") -> datetime | None:
    """Nhận 'YYYY-MM-DDTHH:MM[:SS]' (ô datetime-local) hoặc có dấu cách; rỗng -> None."""
    if value is None or str(value).strip() == "":
        return None
    if isinstance(value, datetime):
        return value.replace(second=0, microsecond=0)
    s = str(value).strip().replace(" ", "T")
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    raise ValidationError(f"{field} không hợp lệ")


def format_datetime(dt: datetime | None) -> str | None:
    return dt.strftime(DT_FORMAT) if dt else None


def slugify(text: str) -> str:
    s = unicodedata.normalize("NFD", str(text))
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).replace("đ", "d").replace("Đ", "D").lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:50] or "event"
