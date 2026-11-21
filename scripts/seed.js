// Tạo dữ liệu demo: 1 sự kiện, 2 staff, 30 người tham dự + ảnh QR để test quét.
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const bcrypt = require('bcryptjs');
const QRCode = require('qrcode');
const db = require('../src/db');

const newToken = () => crypto.randomBytes(18).toString('base64url'); // 24 ký tự, không đoán được

db.exec('DELETE FROM checkin_logs; DELETE FROM attendees; DELETE FROM events; DELETE FROM staff;');

const addStaff = db.prepare('INSERT INTO staff (username, full_name, password_hash, role) VALUES (?,?,?,?)');
addStaff.run('staff1', 'Nguyễn Văn Staff', bcrypt.hashSync('staff123', 10), 'STAFF');
addStaff.run('staff2', 'Trần Thị Cổng B', bcrypt.hashSync('staff123', 10), 'STAFF');

const ev = db.prepare(`INSERT INTO events (name, location, start_time, end_time, status)
  VALUES ('Tech Conference 2026','Hội trường A, TP.HCM','2026-11-10 08:00','2026-11-10 17:00','ONGOING')`).run();
db.prepare(`INSERT INTO events (name, status) VALUES ('Sự kiện khác (test sai event)','ONGOING')`).run();

const names = ['An','Bình','Châu','Dũng','Giang','Hà','Hạnh','Khoa','Lan','Minh','Nam','Oanh','Phúc','Quân','Sơn'];
const ins = db.prepare(`INSERT INTO attendees (event_id, full_name, email, phone, ticket_type, qr_token)
  VALUES (?,?,?,?,?,?)`);
const outDir = path.join(__dirname, '..', 'demo-qr');
fs.mkdirSync(outDir, { recursive: true });

(async () => {
  for (let i = 0; i < 30; i++) {
    const n = `${['Nguyễn','Trần','Lê','Phạm'][i % 4]} ${names[i % names.length]} ${i + 1}`;
    const t = newToken();
    ins.run(ev.lastInsertRowid, n, `user${i + 1}@example.com`, `09000000${String(i).padStart(2, '0')}`,
      i % 5 === 0 ? 'VIP' : 'Standard', t);
    if (i < 6) await QRCode.toFile(path.join(outDir, `ticket-${i + 1}.png`), t, { width: 360, margin: 2 });
  }
  console.log('Seed xong. Đăng nhập: staff1 / staff123');
  console.log('Ảnh QR demo (6 vé đầu) nằm ở ./demo-qr/ – mở lên màn hình khác để quét thử.');
})();
