"""Sinh mã định danh dạng chuỗi (String) cho các lớp: 'EV-7QX03B2K', 'RG-...', 'TK-...'.

Bảng chữ cái Crockford base32 (bỏ I, L, O, U) để không nhầm 0/O, 1/I khi đọc mã cho người khác.
"""
import secrets

_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

# Tiền tố theo lớp – nhìn mã là biết thuộc đối tượng nào
USER, EVENT, CATEGORY, REGISTRATION, TICKET, ASSIGNMENT, REPORT = "US", "EV", "TC", "RG", "TK", "SA", "RP"


def new_id(prefix: str, length: int = 8) -> str:
    return f"{prefix}-" + "".join(secrets.choice(_ALPHABET) for _ in range(length))


def new_secret_token(nbytes: int = 18) -> str:
    """Chuỗi bí mật không đoán được (24 ký tự URL-safe) – dùng làm Ticket.qr_code_data."""
    return secrets.token_urlsafe(nbytes)
