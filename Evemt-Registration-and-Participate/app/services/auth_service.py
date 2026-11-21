"""AuthService: đăng ký Attendee, đăng nhập (2 cổng), phiên, hồ sơ cá nhân."""
import time

from ..domain import Administrator, Attendee, EventStaff, Role, User
from ..domain.validators import clean_email, clean_name, clean_password, clean_phone
from ..errors import Conflict, Forbidden, NotFound, Unauthorized, ValidationError
from ..ids import USER, new_id
from ..infrastructure.database import ts


class AuthService:
    def __init__(self, app):
        self.app = app

    # ---------- tạo người dùng ----------
    def build_user(self, cls, full_name, email, phone_number, password=None, **kw) -> User:
        return cls(new_id(USER), clean_name(full_name), clean_email(email),
                   clean_phone(phone_number) if phone_number else None,
                   self.app.hasher.hash(clean_password(password)) if password else None,
                   ts(self.app.clock.now()), **kw).bind(self.app)

    def register_attendee(self, full_name, email, phone_number, password) -> Attendee:
        user = self.build_user(Attendee, full_name, email, clean_phone(phone_number), password)
        if not password:
            raise ValidationError("Vui lòng nhập mật khẩu")
        with self.app.uow(write=True) as u:
            u.users.add(user)                       # UNIQUE(email) → Conflict EMAIL_EXISTS
        return user

    def find_or_create_guest(self, full_name, email, phone_number) -> Attendee:
        name, mail, phone = clean_name(full_name), clean_email(email), clean_phone(phone_number)
        with self.app.uow(write=True) as u:
            ex = u.users.get_by_email(mail)
            if ex is not None:
                if ex.role != Role.ATTENDEE:
                    raise Conflict("Email này không dùng được để đăng ký tham dự", "EMAIL_EXISTS")
                if ex.password_hash:
                    raise Conflict("Email này đã có tài khoản. Vui lòng đăng nhập để đăng ký.", "LOGIN_REQUIRED")
                return ex
            g = self.build_user(Attendee, name, mail, phone)
            u.users.add(g)
            return g

    def create_staff_user(self, uow, full_name, email, phone_number, password) -> EventStaff:
        s = self.build_user(EventStaff, full_name, email, clean_phone(phone_number), password)
        uow.users.add(s)
        return s

    def create_admin(self, full_name, email, password) -> Administrator:
        a = self.build_user(Administrator, full_name, email, None, password)
        with self.app.uow(write=True) as u:
            u.users.add(a)
        return a

    # ---------- đăng nhập / phiên ----------
    def login(self, email, password, portal: str | None = None) -> tuple[str, User]:
        """portal: 'attendee' (cổng khách) | 'internal' (cổng Admin/Staff) | None (không ràng buộc)."""
        try:
            mail = clean_email(email)
        except ValidationError:
            raise Unauthorized("Sai email hoặc mật khẩu")
        with self.app.uow() as u:
            user = u.users.get_by_email(mail)
        if user is None:
            self.app.hasher.verify(password or "", self.app.hasher.dummy)       # giữ thời gian phản hồi đồng đều
            raise Unauthorized("Sai email hoặc mật khẩu")
        if portal == "attendee" and user.role != Role.ATTENDEE or portal == "internal" and user.role == Role.ATTENDEE:
            self.app.hasher.verify(password or "", user.password_hash or self.app.hasher.dummy)
            raise Unauthorized("Sai email hoặc mật khẩu")
        return user.login(password or ""), user

    def issue_token(self, user: User) -> str:
        return self.app.tokens.issue(user.user_id, user.role.value)

    def revoke_token(self, token: str) -> None:
        try:
            claims = self.app.tokens.decode(token)
        except Unauthorized:
            return
        with self.app.uow(write=True) as u:
            u.revoked.revoke(claims["jti"], claims["exp"])
            u.revoked.purge(int(time.time()))

    def authenticate(self, token: str) -> User:
        """Token → đối tượng User ĐÚNG LỚP (Administrator/EventStaff/Attendee). Kiểm tra thu hồi + trạng thái."""
        claims = self.app.tokens.decode(token)
        with self.app.uow() as u:
            if u.revoked.is_revoked(claims["jti"]):
                raise Unauthorized("Phiên đăng nhập đã kết thúc, vui lòng đăng nhập lại")
            user = u.users.get(claims["sub"])
        if user is None or user.role.value != claims["role"]:
            raise Unauthorized("Phiên đăng nhập không hợp lệ")
        if not user.is_active():
            raise Forbidden("Tài khoản đã bị vô hiệu hoá", "ACCOUNT_INACTIVE")
        return user

    # ---------- hồ sơ ----------
    def update_profile(self, user: User, full_name, phone_number, current_password, new_password) -> User:
        with self.app.uow(write=True) as u:
            cur = u.users.get(user.user_id)
            if cur is None:
                raise NotFound("Không tìm thấy tài khoản")
            if full_name is not None:
                cur.full_name = clean_name(full_name)
            if phone_number is not None:
                cur.phone_number = clean_phone(phone_number) if str(phone_number).strip() else None
            if new_password:
                if not cur.password_hash or not self.app.hasher.verify(current_password or "", cur.password_hash):
                    raise ValidationError("Mật khẩu hiện tại không đúng")
                cur.password_hash = self.app.hasher.hash(clean_password(new_password))
            u.users.update(cur)
        user.full_name, user.phone_number, user.password_hash = cur.full_name, cur.phone_number, cur.password_hash
        return cur
