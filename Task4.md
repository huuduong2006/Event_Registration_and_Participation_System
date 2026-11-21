# Event Registration and Participation System

## Event Staff – Check-in Module

Phạm vi: **Task 4.1** (giao diện web/mobile cho staff quét QR) và **Task 4.2** (logic xử lý check-in tại cổng).

## 1. Chạy thử trong 3 bước

```bash
npm install
npm run seed     # tạo DB demo + 2 tài khoản staff + 30 người tham dự + ảnh QR ở ./demo-qr/
npm start        # http://localhost:3000
```

Đăng nhập: `staff1` / `staff123`. Mở `demo-qr/ticket-1.png` trên một màn hình khác và đưa camera vào quét.
Chạy test: `npm test` (9 test: logic, quét đồng thời, bảo mật, độ trễ).

> Camera trình duyệt **chỉ hoạt động trên HTTPS** (hoặc `localhost`). Khi test bằng điện thoại thật,
> dùng `ngrok http 3000` / `cloudflared tunnel` hoặc deploy lên host có HTTPS.

## 2. Cấu trúc

```
src/db.js               Schema SQLite (staff, events, attendees, checkin_logs)
src/checkinService.js   TASK 4.2 – toàn bộ logic check-in
src/server.js           REST API + auth JWT + phục vụ file tĩnh
public/index.html|style.css|app.js   TASK 4.1 – giao diện staff (PWA)
public/sw.js, manifest  Cài app lên màn hình chính điện thoại
scripts/seed.js         Dữ liệu demo
test/checkin.test.js    Test tự động
```

## 3. Task 4.2 – Logic check-in (khớp "Process 4" trong SRS)

| Điều kiện | `result` | Màu | Hành động |
|---|---|---|---|
| Mã không tồn tại / sai định dạng | `INVALID` | Đỏ | Ghi log |
| Vé hợp lệ nhưng của event khác | `WRONG_EVENT` | Vàng | Ghi log, **không** check-in |
| Vé hợp lệ, `NOT_CHECKED_IN` | `SUCCESS` | Xanh | Đổi sang `CHECKED_IN`, lưu thời điểm + staff + phương thức |
| Vé đã `CHECKED_IN` | `ALREADY_USED` | Đỏ | Cảnh báo vé trùng/copy, hiển thị lần vào đầu tiên (giờ, staff) |

Điểm quan trọng:
- **Chống check-in đúp khi 2 cổng quét cùng lúc**: bước kiểm tra + cập nhật là một câu
  `UPDATE ... WHERE checkin_status='NOT_CHECKED_IN'` trong transaction `IMMEDIATE`. Test chứng minh 50 lượt
  quét đồng thời → đúng 1 `SUCCESS`.
- **Check-in thủ công** (`POST /api/checkin/manual`): bắt buộc nhập ghi chú giấy tờ đã đối chiếu; sau khi vào
  thủ công thì QR của người đó cũng bị coi là đã dùng.
- **Nhật ký** `checkin_logs` lưu mọi lượt quét (cả thất bại) để đối soát.
- **Hiệu năng** (<2s theo SRS): tra cứu theo cột `qr_token` có UNIQUE index; đo thực tế ~7 ms/lượt quét.
- **Bảo mật**: mật khẩu băm bcrypt; JWT 12h; rate-limit đăng nhập; truy vấn tham số hoá; email/SĐT bị che
  khi staff tìm kiếm (`ab***@x.com`, `*******001`).

### API

| Method | Endpoint | Mô tả |
|---|---|---|
| POST | `/api/auth/login` | `{username,password}` → `{token}` |
| GET | `/api/events` | Sự kiện chưa kết thúc |
| POST | `/api/checkin/scan` | `{eventId, token}` → kết quả + thống kê |
| GET | `/api/checkin/search?eventId=&q=` | Tìm người tham dự (thủ công) |
| POST | `/api/checkin/manual` | `{eventId, attendeeId, note}` |
| GET | `/api/checkin/stats?eventId=` | Đã vào / còn lại / tổng + lịch sử gần đây |

Header: `Authorization: Bearer <token>`.

## 4. Task 4.1 – Giao diện staff

- Mobile-first, nút lớn (≥48px), chạy tốt cả desktop; có thể "Thêm vào màn hình chính" như app.
- Camera quét liên tục (thư viện `html5-qrcode`), ưu tiên camera sau, có đèn flash và đổi camera.
- **Máy quét USB/Bluetooth**: ô "giả lập bàn phím" – máy quét gõ mã rồi Enter là xử lý ngay.
- Kết quả **toàn màn hình**: xanh (tự đóng sau 1.5s cho dòng người đi nhanh), đỏ/vàng (phải bấm xác nhận
  để staff chắc chắn đã thấy), kèm tiếng bíp + rung.
- Chống đọc lặp: cùng một mã trong 4 giây bị bỏ qua; khoá quét khi đang hiển thị kết quả.
- Thống kê trực tiếp (đã vào / còn lại / tổng), tab Lịch sử, tab Thủ công (tìm theo tên/email/SĐT).

## 5. Tích hợp với các phần của nhóm

Module này chỉ **đọc** `events`/`attendees` và **ghi** `checkin_status`, `checked_in_*`. Cần khớp với các bạn làm
phần khác:

1. **Attendee (đăng ký + gửi vé)**: khi lưu đăng ký phải tạo `qr_token` không đoán được, ví dụ
   `crypto.randomBytes(18).toString('base64url')` (xem `scripts/seed.js`), và **mã hoá chính chuỗi đó vào QR**.
   Nếu nhóm bạn mã hoá URL dạng `https://site/ticket?t=<token>` cũng được – `extractToken()` tự bóc token.
2. **Admin**: dùng `checkin_status` để lọc danh sách và vẽ biểu đồ đăng ký vs thực tế; cột
   `checkin_method` cho biết QR hay thủ công.
3. Đang dùng SQLite cho gọn. Nếu nhóm dùng MySQL/PostgreSQL, chỉ cần đổi `src/db.js` và giữ nguyên câu
   `UPDATE ... WHERE checkin_status='NOT_CHECKED_IN'` (kiểm tra `affectedRows === 1`).
4. Production: đặt `JWT_SECRET` (bắt buộc), chạy sau HTTPS, đổi mật khẩu staff mặc định.

## 6. Kịch bản demo/bảo vệ gợi ý

1. Đăng nhập staff → chọn sự kiện → quét QR hợp lệ → **xanh**, số "Đã check-in" tăng.
2. Quét lại cùng QR → **đỏ**, hiện giờ và người check-in lần đầu.
3. Nhập `abc` vào ô máy quét → **đỏ – không hợp lệ**.
4. Tab Thủ công → tìm tên → nhập "CCCD 1234" → check-in; QR của người đó giờ bị từ chối.
5. Chạy `npm test` để cho thấy test quét đồng thời và độ trễ.