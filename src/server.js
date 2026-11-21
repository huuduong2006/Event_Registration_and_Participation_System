const express = require('express');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const path = require('path');
const db = require('./db');
const svc = require('./checkinService');

const JWT_SECRET = process.env.JWT_SECRET || 'dev-only-change-me';
if (process.env.NODE_ENV === 'production' && JWT_SECRET === 'dev-only-change-me') {
  throw new Error('Phải đặt biến môi trường JWT_SECRET khi chạy production');
}

const app = express();
app.use(helmet({ contentSecurityPolicy: false })); // camera cần inline script/blob; siết lại nếu cần
app.use(express.json({ limit: '10kb' }));
app.use(express.static(path.join(__dirname, '..', 'public')));
app.use('/vendor/html5-qrcode', express.static(path.join(__dirname, '..', 'node_modules', 'html5-qrcode')));

// ---- Auth ----
const loginLimiter = rateLimit({ windowMs: 15 * 60 * 1000, max: 30 });
app.post('/api/auth/login', loginLimiter, (req, res) => {
  const { username, password } = req.body || {};
  const u = db.prepare('SELECT * FROM staff WHERE username = ?').get(String(username || ''));
  if (!u || !bcrypt.compareSync(String(password || ''), u.password_hash)) {
    return res.status(401).json({ error: 'Sai tên đăng nhập hoặc mật khẩu' });
  }
  const token = jwt.sign({ sub: u.id, name: u.full_name, role: u.role }, JWT_SECRET, { expiresIn: '12h' });
  res.json({ token, staff: { id: u.id, fullName: u.full_name, role: u.role } });
});

function auth(req, res, next) {
  const h = req.headers.authorization || '';
  try {
    const p = jwt.verify(h.replace(/^Bearer /, ''), JWT_SECRET);
    req.staff = { id: p.sub, name: p.name, role: p.role };
    next();
  } catch {
    res.status(401).json({ error: 'Phiên đăng nhập hết hạn' });
  }
}

const eventId = (req) => Number.parseInt(req.query.eventId ?? req.body?.eventId, 10);
const needEvent = (req, res, next) => {
  if (!Number.isInteger(eventId(req))) return res.status(400).json({ error: 'Thiếu eventId' });
  next();
};

// ---- Staff API ----
app.get('/api/events', auth, (req, res) => {
  res.json(db.prepare(`SELECT id, name, location, start_time AS startTime, status
                       FROM events WHERE status != 'COMPLETED' ORDER BY start_time IS NULL, start_time, id`).all());
});

// Quét QR
app.post('/api/checkin/scan', auth, needEvent, (req, res) => {
  const out = svc.scanQr({ rawToken: req.body.token, eventId: eventId(req), staffId: req.staff.id });
  res.json({ ...out, stats: svc.getStats(eventId(req)) });
});

// Tìm người tham dự (quên vé)
app.get('/api/checkin/search', auth, needEvent, (req, res) => {
  res.json(svc.searchAttendees(eventId(req), req.query.q));
});

// Check-in thủ công
app.post('/api/checkin/manual', auth, needEvent, (req, res) => {
  const out = svc.manualCheckin({
    attendeeId: Number.parseInt(req.body.attendeeId, 10),
    eventId: eventId(req), staffId: req.staff.id, note: req.body.note,
  });
  res.json({ ...out, stats: svc.getStats(eventId(req)) });
});

app.get('/api/checkin/stats', auth, needEvent, (req, res) => {
  res.json({ ...svc.getStats(eventId(req)), recent: svc.getRecent(eventId(req)) });
});

app.use((err, _req, res, _next) => {
  console.error(err);
  res.status(500).json({ error: 'Lỗi hệ thống' });
});

module.exports = app;

if (require.main === module) {
  const port = process.env.PORT || 3000;
  app.listen(port, () => console.log(`Check-in app: http://localhost:${port}`));
}
