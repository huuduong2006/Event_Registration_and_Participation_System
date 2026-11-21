"""Database + UnitOfWork (SQLite).

* Mỗi "đơn vị công việc" (UnitOfWork) mở 1 kết nối riêng. Ghi dùng `BEGIN IMMEDIATE` để khoá ghi ngay từ đầu:
  đọc-số-liệu → kiểm tra → ghi diễn ra trong CÙNG một transaction nên không thể bán quá số lượng hay check-in đúp.
"""
import sqlite3
from datetime import datetime

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  user_id       TEXT PRIMARY KEY,
  role          TEXT NOT NULL CHECK (role IN ('ADMIN','STAFF','ATTENDEE')),
  full_name     TEXT NOT NULL,
  email         TEXT NOT NULL UNIQUE,
  phone_number  TEXT,
  password_hash TEXT,                              -- NULL = hồ sơ khách (chưa có tài khoản đăng nhập)
  staff_status  TEXT CHECK (staff_status IN ('ACTIVE','INACTIVE')),   -- chỉ dùng cho STAFF
  created_at    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
  event_id     TEXT PRIMARY KEY,
  event_name   TEXT NOT NULL,
  start_time   TEXT,
  end_time     TEXT,
  location     TEXT,
  max_capacity INTEGER NOT NULL CHECK (max_capacity > 0),
  status       TEXT NOT NULL CHECK (status IN ('UPCOMING','ONGOING','COMPLETED')),
  unique_url   TEXT NOT NULL UNIQUE,
  description  TEXT,
  created_at   TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ticket_categories (
  ticket_type_id TEXT PRIMARY KEY,
  event_id       TEXT NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
  type_name      TEXT NOT NULL,
  price          REAL NOT NULL CHECK (price >= 0),
  quantity_limit INTEGER NOT NULL CHECK (quantity_limit > 0),
  UNIQUE (event_id, type_name COLLATE NOCASE)
);
CREATE TABLE IF NOT EXISTS registrations (
  registration_id   TEXT PRIMARY KEY,
  event_id          TEXT NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
  attendee_id       TEXT NOT NULL REFERENCES users(user_id),
  ticket_type_id    TEXT NOT NULL REFERENCES ticket_categories(ticket_type_id) ON DELETE CASCADE,
  registration_date TEXT NOT NULL,
  UNIQUE (event_id, attendee_id)                   -- mỗi khách 1 vé / sự kiện
);
CREATE TABLE IF NOT EXISTS tickets (
  ticket_id        TEXT PRIMARY KEY,
  registration_id  TEXT NOT NULL UNIQUE REFERENCES registrations(registration_id) ON DELETE CASCADE,
  qr_code_data     TEXT NOT NULL UNIQUE,
  check_in_status  TEXT NOT NULL DEFAULT 'NOT_CHECKED_IN' CHECK (check_in_status IN ('NOT_CHECKED_IN','CHECKED_IN')),
  checked_in_at    TEXT,
  checked_in_by    TEXT REFERENCES users(user_id),
  check_in_method  TEXT,
  check_in_note    TEXT,
  email_status     TEXT NOT NULL DEFAULT 'PENDING'
);
CREATE TABLE IF NOT EXISTS staff_assignments (
  assignment_id    TEXT PRIMARY KEY,
  staff_id         TEXT NOT NULL REFERENCES users(user_id),
  event_id         TEXT NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
  work_area        TEXT NOT NULL,
  shift_start_time TEXT,
  shift_end_time   TEXT,
  UNIQUE (staff_id, event_id)
);
CREATE TABLE IF NOT EXISTS check_in_logs (          -- nhật ký MỌI lần quét (kể cả bị từ chối) để đối soát
  log_id          INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id        TEXT,
  ticket_id       TEXT,
  registration_id TEXT,
  staff_id        TEXT,
  outcome         TEXT NOT NULL,
  method          TEXT NOT NULL,
  note            TEXT,
  created_at      TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS revoked_tokens (jti TEXT PRIMARY KEY, expires_at INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS ix_reg_event   ON registrations(event_id);
CREATE INDEX IF NOT EXISTS ix_reg_att     ON registrations(attendee_id);
CREATE INDEX IF NOT EXISTS ix_reg_type    ON registrations(ticket_type_id);
CREATE INDEX IF NOT EXISTS ix_assign_st   ON staff_assignments(staff_id);
CREATE INDEX IF NOT EXISTS ix_log_event   ON check_in_logs(event_id, created_at);
"""

TS = "%Y-%m-%dT%H:%M:%S"


def ts(dt: datetime) -> str:
    return dt.strftime(TS)


def from_ts(s: str | None) -> datetime | None:
    return datetime.strptime(s[:19], TS if len(s) >= 19 else "%Y-%m-%dT%H:%M") if s else None


class Database:
    def __init__(self, path: str):
        self.path = path

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=15, isolation_level=None)   # autocommit; BEGIN thủ công
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 15000")
        return conn

    def init_schema(self) -> None:
        conn = self.connect()
        try:
            if self.path != ":memory:":
                conn.execute("PRAGMA journal_mode = WAL")
            conn.executescript(SCHEMA)
        finally:
            conn.close()
