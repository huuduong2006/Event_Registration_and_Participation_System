const Database = require('better-sqlite3');
const path = require('path');

const DB_PATH = process.env.DB_PATH || path.join(__dirname, '..', 'data.sqlite');
const db = new Database(DB_PATH);
db.pragma('journal_mode = WAL');
db.pragma('foreign_keys = ON');

db.exec(`
CREATE TABLE IF NOT EXISTS staff (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  username      TEXT NOT NULL UNIQUE,
  full_name     TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  role          TEXT NOT NULL DEFAULT 'STAFF'   -- STAFF | ADMIN
);

CREATE TABLE IF NOT EXISTS events (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  name       TEXT NOT NULL,
  location   TEXT,
  start_time TEXT,
  end_time   TEXT,
  status     TEXT NOT NULL DEFAULT 'UPCOMING'   -- UPCOMING | ONGOING | COMPLETED
);

-- Bảng attendee/ticket (phần Attendee Module sẽ ghi vào đây; Staff chỉ đọc + cập nhật check-in)
CREATE TABLE IF NOT EXISTS attendees (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id        INTEGER NOT NULL REFERENCES events(id),
  full_name       TEXT NOT NULL,
  email           TEXT NOT NULL,
  phone           TEXT,
  ticket_type     TEXT NOT NULL DEFAULT 'Standard',
  qr_token        TEXT NOT NULL UNIQUE,         -- chuỗi định danh duy nhất mã hoá trong QR
  checkin_status  TEXT NOT NULL DEFAULT 'NOT_CHECKED_IN', -- NOT_CHECKED_IN | CHECKED_IN
  checked_in_at   TEXT,
  checked_in_by   INTEGER REFERENCES staff(id),
  checkin_method  TEXT,                         -- QR | MANUAL
  created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_att_event  ON attendees(event_id);
CREATE INDEX IF NOT EXISTS idx_att_status ON attendees(event_id, checkin_status);

-- Nhật ký mọi lần quét / check-in (kể cả thất bại) để đối soát & chống gian lận
CREATE TABLE IF NOT EXISTS checkin_logs (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id    INTEGER,
  attendee_id INTEGER,
  staff_id    INTEGER,
  method      TEXT NOT NULL,                    -- QR | MANUAL
  result      TEXT NOT NULL,                    -- SUCCESS | ALREADY_USED | INVALID | WRONG_EVENT
  token       TEXT,
  note        TEXT,
  created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_log_event ON checkin_logs(event_id, id DESC);
`);

module.exports = db;
