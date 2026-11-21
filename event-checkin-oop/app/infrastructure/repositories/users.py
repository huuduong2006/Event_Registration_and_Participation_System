from ...domain import Administrator, Attendee, EventStaff, Role, StaffStatus, User
from ...errors import Conflict
from .base import Repository

_CLASSES = {Role.ADMIN: Administrator, Role.STAFF: EventStaff, Role.ATTENDEE: Attendee}


class UserRepository(Repository):
    def _entity(self, r) -> User | None:
        if r is None:
            return None
        role = Role(r["role"])
        kw = dict(user_id=r["user_id"], full_name=r["full_name"], email=r["email"], phone_number=r["phone_number"],
                  password_hash=r["password_hash"], created_at=r["created_at"])
        if role == Role.STAFF:
            kw["staff_status"] = StaffStatus(r["staff_status"] or "ACTIVE")
        return self._bind(_CLASSES[role](**kw))

    def add(self, u: User) -> User:
        try:
            self.conn.execute(
                "INSERT INTO users(user_id,role,full_name,email,phone_number,password_hash,staff_status,created_at)"
                " VALUES(?,?,?,?,?,?,?,?)",
                (u.user_id, u.role.value, u.full_name, u.email, u.phone_number, u.password_hash,
                 u.staff_status.value if isinstance(u, EventStaff) else None, u.created_at))
        except Exception as e:                                   # UNIQUE(email)
            if "UNIQUE" in str(e):
                raise Conflict("Email này đã được sử dụng", "EMAIL_EXISTS")
            raise
        return u

    def update(self, u: User) -> User:
        self.conn.execute(
            "UPDATE users SET full_name=?, phone_number=?, password_hash=?, staff_status=? WHERE user_id=?",
            (u.full_name, u.phone_number, u.password_hash,
             u.staff_status.value if isinstance(u, EventStaff) else None, u.user_id))
        return u

    def get(self, user_id: str) -> User | None:
        return self._entity(self._one("SELECT * FROM users WHERE user_id=?", (user_id,)))

    def get_by_email(self, email: str) -> User | None:
        return self._entity(self._one("SELECT * FROM users WHERE email=?", (email,)))

    def list_by_role(self, role: Role) -> list[User]:
        return [self._entity(r) for r in self._all(
            "SELECT * FROM users WHERE role=? ORDER BY created_at DESC, user_id", (role.value,))]

    def count_by_role(self, role: Role) -> int:
        return self._one("SELECT COUNT(*) c FROM users WHERE role=?", (role.value,))["c"]
