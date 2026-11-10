process.env.DB_PATH = ':memory:';
const test = require('node:test');
const assert = require('node:assert');
const bcrypt = require('bcryptjs');
const db = require('../src/db');
const svc = require('../src/checkinService');
const app = require('../src/server');

db.prepare("INSERT INTO staff (username, full_name, password_hash) VALUES ('s1','Staff 1',?)").run(bcrypt.hashSync('pw', 4));
db.prepare("INSERT INTO staff (username, full_name, password_hash) VALUES ('s2','Staff 2',?)").run(bcrypt.hashSync('pw', 4));
const e1 = db.prepare("INSERT INTO events (name,status) VALUES ('E1','ONGOING')").run().lastInsertRowid;
const e2 = db.prepare("INSERT INTO events (name,status) VALUES ('E2','ONGOING')").run().lastInsertRowid;
const add = (ev, name, tok) => db.prepare(
  'INSERT INTO attendees (event_id,full_name,email,phone,qr_token) VALUES (?,?,?,?,?)')
  .run(ev, name, `${name}@x.com`, '0900000001', tok).lastInsertRowid;
const T1 = 'AAAAAAAAAAAAAAAAAAAAAAAA', T2 = 'BBBBBBBBBBBBBBBBBBBBBBBB', T3 = 'CCCCCCCCCCCCCCCCCCCCCCCC';
const a1 = add(e1, 'Alice', T1); add(e1, 'Bob', T2); add(e2, 'Carol', T3);

test('quét hợp lệ -> SUCCESS, quét lại -> ALREADY_USED kèm thông tin lần đầu', () => {
  const r1 = svc.scanQr({ rawToken: T1, eventId: e1, staffId: 1 });
  assert.equal(r1.result, 'SUCCESS');
  const r2 = svc.scanQr({ rawToken: T1, eventId: e1, staffId: 2 });
  assert.equal(r2.result, 'ALREADY_USED');
  assert.equal(r2.firstCheckin.by, 'Staff 1');
});

test('mã không tồn tại / rác -> INVALID', () => {
  assert.equal(svc.scanQr({ rawToken: 'ZZZZZZZZZZZZZZZZZZZZZZZZ', eventId: e1, staffId: 1 }).result, 'INVALID');
  assert.equal(svc.scanQr({ rawToken: "'; DROP TABLE attendees;--", eventId: e1, staffId: 1 }).result, 'INVALID');
  assert.equal(svc.scanQr({ rawToken: null, eventId: e1, staffId: 1 }).result, 'INVALID');
});

test('vé của sự kiện khác -> WRONG_EVENT và KHÔNG bị check-in', () => {
  assert.equal(svc.scanQr({ rawToken: T3, eventId: e1, staffId: 1 }).result, 'WRONG_EVENT');
  assert.equal(svc.scanQr({ rawToken: T3, eventId: e2, staffId: 1 }).result, 'SUCCESS');
});

test('QR dạng URL vẫn lấy được token', () => {
  assert.equal(svc.extractToken(`https://site.com/ticket?t=${T2}`), T2);
  assert.equal(svc.scanQr({ rawToken: `  ${T2}\n`, eventId: e1, staffId: 1 }).result, 'SUCCESS');
});

test('check-in thủ công: cần ghi chú, không check-in lại người đã vào', () => {
  const b = add(e1, 'Dave', 'DDDDDDDDDDDDDDDDDDDDDDDD');
  assert.equal(svc.manualCheckin({ attendeeId: b, eventId: e1, staffId: 1, note: '' }).result, 'INVALID');
  assert.equal(svc.manualCheckin({ attendeeId: b, eventId: e1, staffId: 1, note: 'CCCD 1234' }).result, 'SUCCESS');
  assert.equal(svc.manualCheckin({ attendeeId: b, eventId: e1, staffId: 2, note: 'CCCD 1234' }).result, 'ALREADY_USED');
  // vé QR của Dave giờ cũng phải bị từ chối (chống dùng lại vé sau khi vào thủ công)
  assert.equal(svc.scanQr({ rawToken: 'DDDDDDDDDDDDDDDDDDDDDDDD', eventId: e1, staffId: 1 }).result, 'ALREADY_USED');
});

test('đồng thời: 50 lượt quét cùng 1 vé -> đúng 1 SUCCESS', () => {
  const tok = 'EEEEEEEEEEEEEEEEEEEEEEEE'; add(e1, 'Eve', tok);
  const results = Array.from({ length: 50 }, (_, i) => svc.scanQr({ rawToken: tok, eventId: e1, staffId: (i % 2) + 1 }).result);
  assert.equal(results.filter((x) => x === 'SUCCESS').length, 1);
  assert.equal(results.filter((x) => x === 'ALREADY_USED').length, 49);
});

test('tìm kiếm che dữ liệu cá nhân', () => {
  const r = svc.searchAttendees(e1, 'Alice');
  assert.equal(r.length, 1);
  assert.match(r[0].email, /\*\*\*/);
  assert.ok(!r[0].phone.includes('0900000'));
});

test('thống kê đúng', () => {
  const s = svc.getStats(e1);
  assert.equal(s.total, s.checkedIn + s.remaining);
  assert.ok(s.checkedIn >= 4);
});

test('HTTP: login + scan end-to-end, phản hồi < 2s, chưa login bị chặn', async () => {
  const server = app.listen(0);
  const base = `http://127.0.0.1:${server.address().port}`;
  try {
    const bad = await fetch(base + '/api/checkin/scan', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
    assert.equal(bad.status, 401);
    const login = await (await fetch(base + '/api/auth/login', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username: 's1', password: 'pw' }) })).json();
    assert.ok(login.token);
    const tok = 'FFFFFFFFFFFFFFFFFFFFFFFF'; add(e1, 'Frank', tok);
    const t0 = performance.now();
    const res = await (await fetch(base + '/api/checkin/scan', {
      method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + login.token },
      body: JSON.stringify({ token: tok, eventId: e1 }) })).json();
    const ms = performance.now() - t0;
    console.log(`   scan latency: ${ms.toFixed(1)} ms`);
    assert.equal(res.result, 'SUCCESS');
    assert.ok(ms < 2000);
    const wrong = await fetch(base + '/api/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username: 's1', password: 'x' }) });
    assert.equal(wrong.status, 401);
  } finally { server.close(); }
});
