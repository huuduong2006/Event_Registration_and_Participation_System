"""Tạo hoặc đặt lại mật khẩu Administrator.
   python create_admin.py admin@example.com "Quản trị viên"      (hỏi mật khẩu, không hiện khi gõ)
   Docker: docker compose exec app python create_admin.py admin@example.com "Quản trị viên"
"""
import getpass
import os
import sys

from app.application import Application
from app.config import Settings
from app.domain import Role
from app.domain.validators import clean_email, clean_password


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    email = clean_email(sys.argv[1])
    name = sys.argv[2] if len(sys.argv) > 2 else "Quản trị viên"
    pw = os.environ.get("ADMIN_PASSWORD") or getpass.getpass("Mật khẩu (>= 10 ký tự): ")
    if len(pw) < 10:
        print("Mật khẩu quá ngắn (cần >= 10 ký tự).")
        return 1
    clean_password(pw)
    app = Application(Settings.from_env())
    with app.uow() as u:
        existing = u.users.get_by_email(email)
    if existing is None:
        app.auth.create_admin(name, email, pw)
        print(f"Đã tạo Administrator {email}")
    elif existing.role == Role.ADMIN:
        with app.uow(write=True) as u:
            existing.password_hash = app.hasher.hash(pw)
            u.users.update(existing)
        print(f"Đã đặt lại mật khẩu cho {email}")
    else:
        print("Email này đang thuộc tài khoản không phải Administrator.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
