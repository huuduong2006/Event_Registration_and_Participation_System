/**
 * TASK 4.2 - Logic xử lý check-in tại cổng
 *
 * Kết quả trả về luôn có dạng { result, ... } với result thuộc:
 *   SUCCESS      -> xanh : vé hợp lệ, vừa check-in
 *   ALREADY_USED -> đỏ   : vé đã check-in trước đó (nghi vé trùng/copy)
 *   INVALID      -> đỏ   : mã không tồn tại / sai định dạng
 *   WRONG_EVENT  -> vàng : vé hợp lệ nhưng của sự kiện khác
 *
 * Điểm mấu chốt: việc "kiểm tra + cập nhật trạng thái" là MỘT câu UPDATE có điều kiện
 * (atomic). Nếu 2 staff quét cùng 1 vé cùng lúc, chỉ đúng 1 người thắng (changes === 1),
 * người còn lại nhận ALREADY_USED -> không bao giờ check-in 2 lần.
 */
const db = require('./db');

const TOKEN_RE = /^[A-Za-z0-9_-]{16,128}$/;

const stmts = {
  findByToken: db.prepare(`
    SELECT a.id, a.event_id, a.full_name, a.ticket_type, a.email, a.phone,
           a.checkin_status, a.checked_in_at, a.checkin_method, s.full_name AS checked_in_by_name
    FROM attendees a LEFT JOIN staff s ON s.id = a.checked_in_by
    WHERE a.qr_token = ?`),
  findById: db.prepare(`
    SELECT a.id, a.event_id, a.full_name, a.ticket_type, a.email, a.phone,
           a.checkin_status, a.checked_in_at, a.checkin_method, s.full_name AS checked_in_by_name
    FROM attendees a LEFT JOIN staff s ON s.id = a.checked_in_by
    WHERE a.id = ?`),
  markChecked: db.prepare(`
    UPDATE attendees
       SET checkin_status = 'CHECKED_IN', checked_in_at = datetime('now'),
           checked_in_by = @staffId, checkin_method = @method
     WHERE id = @id AND checkin_status = 'NOT_CHECKED_IN'`),
  log: db.prepare(`
    INSERT INTO checkin_logs (event_id, attendee_id, staff_id, method, result, token, note)
    VALUES (@eventId, @attendeeId, @staffId, @method, @result, @token, @note)`),
  stats: db.prepare(`
    SELECT COUNT(*) AS total,
           SUM(CASE WHEN checkin_status = 'CHECKED_IN' THEN 1 ELSE 0 END) AS checked_in
    FROM attendees WHERE event_id = ?`),
  recent: db.prepare(`
    SELECT l.id, l.result, l.method, l.created_at, a.full_name, a.ticket_type
    FROM checkin_logs l LEFT JOIN attendees a ON a.id = l.attendee_id
    WHERE l.event_id = ? ORDER BY l.id DESC LIMIT ?`),
  search: db.prepare(`
    SELECT id, full_name, email, phone, ticket_type, checkin_status, checked_in_at
    FROM attendees
    WHERE event_id = @eventId
      AND (full_name LIKE @q OR email LIKE @q OR phone LIKE @q)
    ORDER BY full_name LIMIT 30`),
};

const publicAttendee = (a) => ({
  id: a.id,
  fullName: a.full_name,
  ticketType: a.ticket_type,
});

const writeLog = (o) => stmts.log.run({ note: null, token: null, attendeeId: null, ...o });

/** Chuẩn hoá nội dung QR: cắt khoảng trắng; nếu là URL thì lấy phần token cuối. */
function extractToken(raw) {
  if (typeof raw !== 'string') return null;
  let t = raw.trim();
  const m = t.match(/[?&]t=([A-Za-z0-9_-]+)/) || t.match(/\/([A-Za-z0-9_-]{16,128})\/?$/);
  if (m) t = m[1];
  return TOKEN_RE.test(t) ? t : null;
}

/** Quét QR tại cổng. */
function scanQr({ rawToken, eventId, staffId }) {
  const token = extractToken(rawToken);
  const base = { eventId, staffId, method: 'QR', token: token || String(rawToken).slice(0, 64) };

  if (!token) {
    writeLog({ ...base, result: 'INVALID' });
    return { result: 'INVALID', message: 'Mã QR không hợp lệ' };
  }

  const run = db.transaction(() => {
    const a = stmts.findByToken.get(token);
    if (!a) {
      writeLog({ ...base, result: 'INVALID' });
      return { result: 'INVALID', message: 'Vé không tồn tại trong hệ thống' };
    }
    if (a.event_id !== eventId) {
      writeLog({ ...base, attendeeId: a.id, result: 'WRONG_EVENT' });
      return { result: 'WRONG_EVENT', message: 'Vé thuộc sự kiện khác', attendee: publicAttendee(a) };
    }
    const upd = stmts.markChecked.run({ id: a.id, staffId, method: 'QR' });
    if (upd.changes === 1) {
      writeLog({ ...base, attendeeId: a.id, result: 'SUCCESS' });
      return { result: 'SUCCESS', message: 'Check-in thành công', attendee: publicAttendee(a) };
    }
    const cur = stmts.findById.get(a.id);
    writeLog({ ...base, attendeeId: a.id, result: 'ALREADY_USED' });
    return {
      result: 'ALREADY_USED',
      message: 'Vé đã được sử dụng – nghi vé trùng/copy!',
      attendee: publicAttendee(a),
      firstCheckin: { at: cur.checked_in_at, by: cur.checked_in_by_name, method: cur.checkin_method },
    };
  });
  return run.immediate();
}

/** Check-in thủ công (quên vé nhưng có giấy tờ tùy thân). Bắt buộc ghi chú giấy tờ đã xem. */
function manualCheckin({ attendeeId, eventId, staffId, note }) {
  const base = { eventId, staffId, method: 'MANUAL', note };
  if (!note || String(note).trim().length < 3) {
    return { result: 'INVALID', message: 'Cần ghi chú giấy tờ đã đối chiếu (VD: CCCD 4 số cuối)' };
  }
  const run = db.transaction(() => {
    const a = stmts.findById.get(attendeeId);
    if (!a) {
      writeLog({ ...base, result: 'INVALID' });
      return { result: 'INVALID', message: 'Không tìm thấy người tham dự' };
    }
    if (a.event_id !== eventId) {
      writeLog({ ...base, attendeeId: a.id, result: 'WRONG_EVENT' });
      return { result: 'WRONG_EVENT', message: 'Người này thuộc sự kiện khác', attendee: publicAttendee(a) };
    }
    const upd = stmts.markChecked.run({ id: a.id, staffId, method: 'MANUAL' });
    if (upd.changes === 1) {
      writeLog({ ...base, attendeeId: a.id, result: 'SUCCESS' });
      return { result: 'SUCCESS', message: 'Check-in thủ công thành công', attendee: publicAttendee(a) };
    }
    const cur = stmts.findById.get(a.id);
    writeLog({ ...base, attendeeId: a.id, result: 'ALREADY_USED' });
    return {
      result: 'ALREADY_USED',
      message: 'Người này đã check-in rồi',
      attendee: publicAttendee(a),
      firstCheckin: { at: cur.checked_in_at, by: cur.checked_in_by_name, method: cur.checkin_method },
    };
  });
  return run.immediate();
}

function searchAttendees(eventId, q) {
  const term = `%${String(q || '').trim().replace(/[%_]/g, '')}%`;
  if (term.length < 4) return []; // tối thiểu 2 ký tự
  return stmts.search.all({ eventId, q: term }).map((r) => ({
    id: r.id,
    fullName: r.full_name,
    email: maskEmail(r.email),
    phone: maskPhone(r.phone),
    ticketType: r.ticket_type,
    checkedIn: r.checkin_status === 'CHECKED_IN',
    checkedInAt: r.checked_in_at,
  }));
}

// Che bớt dữ liệu cá nhân trên màn hình staff (yêu cầu bảo mật dữ liệu)
const maskEmail = (e) => (e ? e.replace(/^(.{2}).*(@.*)$/, '$1***$2') : '');
const maskPhone = (p) => (p && p.length > 4 ? '*'.repeat(p.length - 3) + p.slice(-3) : p || '');

function getStats(eventId) {
  const s = stmts.stats.get(eventId);
  return { total: s.total || 0, checkedIn: s.checked_in || 0, remaining: (s.total || 0) - (s.checked_in || 0) };
}

const getRecent = (eventId, limit = 15) =>
  stmts.recent.all(eventId, limit).map((r) => ({
    id: r.id, result: r.result, method: r.method, at: r.created_at,
    fullName: r.full_name, ticketType: r.ticket_type,
  }));

module.exports = { scanQr, manualCheckin, searchAttendees, getStats, getRecent, extractToken };
