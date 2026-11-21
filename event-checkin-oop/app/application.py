"""Application – container dựng và nối mọi thành phần (Composition Root).

Đổi cách lưu trữ / gửi mail / đồng hồ: chỉ sửa ở đây. Các lớp domain được `bind(app)` để gọi service.
"""
import logging

from .clock import Clock
from .config import Settings
from .infrastructure.database import Database
from .infrastructure.mailer import Mailer
from .infrastructure.rate_limit import RateLimiter
from .infrastructure.security import PasswordHasher, TokenService
from .infrastructure.unit_of_work import UnitOfWork
from .services import (AuthService, CheckInService, EventService, RegistrationService, ReportExporter, StaffService,
                       TicketService)

log = logging.getLogger("app")


class Application:
    def __init__(self, settings: Settings | None = None, clock: Clock | None = None):
        self.settings = settings or Settings.from_env()
        self.clock = clock or Clock(self.settings.tz_offset_hours)
        self.db = Database(self.settings.db_path)
        self.db.init_schema()
        self.hasher = PasswordHasher()
        self.tokens = TokenService(self.settings.jwt_secret, self.settings.token_ttl_hours)
        self.mailer = Mailer(self.settings)
        self.limiter = RateLimiter()
        self.auth = AuthService(self)
        self.events = EventService(self)
        self.staff = StaffService(self)
        self.registrations = RegistrationService(self)
        self.tickets = TicketService(self)
        self._reports = ReportExporter(self)

    def uow(self, write: bool = False) -> UnitOfWork:
        return UnitOfWork(self.db, self, write)

    def check_in_service(self, staff_id: str) -> CheckInService:
        return CheckInService(self, staff_id)

    def report_exporter(self) -> ReportExporter:
        return self._reports

    def bootstrap_admin(self) -> None:
        """Data Seeding (Luồng 1): tạo Administrator đầu tiên từ ADMIN_EMAIL/ADMIN_PASSWORD nếu chưa có."""
        s = self.settings
        if not (s.bootstrap_admin_email and s.bootstrap_admin_password):
            return
        with self.uow() as u:
            exists = u.users.get_by_email(s.bootstrap_admin_email.strip().lower())
        if exists is None:
            self.auth.create_admin(s.bootstrap_admin_name, s.bootstrap_admin_email, s.bootstrap_admin_password)
            log.info("Đã tạo tài khoản Administrator: %s", s.bootstrap_admin_email)
