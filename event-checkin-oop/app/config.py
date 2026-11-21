"""Cấu hình đọc từ biến môi trường (file .env khi chạy Docker)."""
import os
from dataclasses import dataclass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEV_SECRET = "dev-only-change-me-please-use-a-32-byte-secret"


def env_int(name: str, default: int) -> int:
    """Biến rỗng/sai định dạng -> dùng mặc định (không làm sập ứng dụng)."""
    try:
        return int(os.environ.get(name) or default)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    db_path: str
    jwt_secret: str
    production: bool
    base_url: str
    outbox_dir: str
    tz_offset_hours: int            # múi giờ của sự kiện (VN = +7); dùng cho ca trực & giờ check-in
    token_ttl_hours: int
    # email
    smtp_host: str | None
    smtp_port: int
    smtp_secure: bool
    smtp_user: str | None
    smtp_pass: str
    mail_from: str
    # Data Seeding (Luồng 1): tài khoản Administrator tạo sẵn khi khởi động nếu chưa có
    bootstrap_admin_email: str | None
    bootstrap_admin_password: str | None
    bootstrap_admin_name: str
    # giới hạn tần suất (theo IP)
    login_rate_max: int             # / 15 phút
    signup_rate_max: int            # / 1 giờ (đăng ký tài khoản Attendee)
    register_rate_max: int          # / 10 phút (đăng ký tham dự)
    read_rate_max: int              # / 1 phút (trang công khai)

    @classmethod
    def from_env(cls) -> "Settings":
        # `or`: biến có mặt nhưng RỖNG (vd. JWT_SECRET= trong .env) được coi như chưa đặt
        e = os.environ.get
        return cls(
            db_path=e("DB_PATH") or os.path.join(ROOT, "data.sqlite"),
            jwt_secret=e("JWT_SECRET") or _DEV_SECRET,
            production=e("APP_ENV") == "production",
            base_url=(e("BASE_URL") or f"http://localhost:{e('PORT') or 8000}").rstrip("/"),
            outbox_dir=e("OUTBOX_DIR") or os.path.join(ROOT, "outbox"),
            tz_offset_hours=env_int("TZ_OFFSET_HOURS", 7),
            token_ttl_hours=env_int("TOKEN_TTL_HOURS", 12),
            smtp_host=e("SMTP_HOST") or None,
            smtp_port=env_int("SMTP_PORT", 587),
            smtp_secure=e("SMTP_SECURE") == "true",
            smtp_user=e("SMTP_USER") or None,
            smtp_pass=e("SMTP_PASS") or "",
            mail_from=e("MAIL_FROM") or "Event <no-reply@example.com>",
            bootstrap_admin_email=e("ADMIN_EMAIL") or None,
            bootstrap_admin_password=e("ADMIN_PASSWORD") or None,
            bootstrap_admin_name=e("ADMIN_NAME") or "Quản trị viên",
            login_rate_max=env_int("LOGIN_RATE_MAX", 30),
            signup_rate_max=env_int("SIGNUP_RATE_MAX", 20),
            register_rate_max=env_int("REG_RATE_MAX", 20),
            read_rate_max=env_int("READ_RATE_MAX", 120),
        )

    def validate(self) -> None:
        if self.production and (self.jwt_secret == _DEV_SECRET or len(self.jwt_secret) < 32):
            raise RuntimeError(
                "JWT_SECRET chưa đặt hoặc quá ngắn (cần >= 32 ký tự) khi chạy production.\n"
                "  -> Mở file .env, điền JWT_SECRET=<chuỗi ngẫu nhiên dài>, rồi chạy lại.\n"
                '  -> Tạo chuỗi:  python -c "import secrets;print(secrets.token_urlsafe(48))"')
