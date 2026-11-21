"""UnitOfWork: một transaction + bộ repository dùng chung kết nối đó."""
from .repositories import (AssignmentRepository, CategoryRepository, CheckInLogRepository, EventRepository,
                           RegistrationRepository, RevokedTokenRepository, TicketRepository, UserRepository)


class UnitOfWork:
    def __init__(self, db, app=None, write: bool = False):
        self._db, self._app, self._write = db, app, write
        self.conn = None

    def __enter__(self) -> "UnitOfWork":
        self.conn = self._db.connect()
        if self._write:
            self.conn.execute("BEGIN IMMEDIATE")
        c, a = self.conn, self._app
        self.users = UserRepository(c, a)
        self.events = EventRepository(c, a)
        self.categories = CategoryRepository(c, a)
        self.registrations = RegistrationRepository(c, a)
        self.tickets = TicketRepository(c, a)
        self.assignments = AssignmentRepository(c, a)
        self.logs = CheckInLogRepository(c, a)
        self.revoked = RevokedTokenRepository(c, a)
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        try:
            if self._write:
                self.conn.execute("ROLLBACK" if exc_type else "COMMIT")
        finally:
            self.conn.close()
        return False
