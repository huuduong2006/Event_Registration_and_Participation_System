# Hệ thống Quản lý Sự kiện & Check-in (OOP – Python/FastAPI – Docker)

Xây dựng lại từ đầu theo tài liệu *Phân tích Thiết kế Hệ thống Quản lý Sự kiện & Check-in – OOP & Business Flows*.
Mỗi lớp trong tài liệu là **một file/lớp trong code**; mỗi luồng nghiệp vụ là **một service**.

## Chạy nhanh
```bash
# Docker (khuyến nghị) – xem DEPLOY.md để lên web thật
cp .env.example .env        # điền JWT_SECRET, ADMIN_EMAIL, ADMIN_PASSWORD
docker compose up -d --build        # → http://localhost:8000
docker compose exec -e APP_ENV=development app python seed.py   # (tuỳ chọn) dữ liệu demo

# Không dùng Docker
pip install -r requirements-dev.txt
ADMIN_EMAIL=admin@demo.vn ADMIN_PASSWORD=Admin12345 uvicorn app.main:app --reload
python -m pytest            # 31 test
```
Ba cổng: khách `/` · quản trị `/admin/` · nhân viên soát vé `/staff/` (cổng nội bộ tự chuyển đúng giao diện theo vai trò).

## Kiến trúc phân tầng
```
app/
  domain/            ← CÁC LỚP TRONG PDF (thuần nghiệp vụ, không biết DB/HTTP)
    user.py            User (abstract) → Administrator | EventStaff | Attendee
    event.py  ticket_category.py  registration.py  ticket.py  staff_assignment.py  check_in_result.py
    enums.py  validators.py  qr.py  base.py
  services/          ← LUỒNG NGHIỆP VỤ (mỗi service = một nhóm use-case)
    auth_service  event_service  staff_service  registration_service  ticket_service
    check_in_service (Luồng 4)  report_exporter (ReportExporter)
  infrastructure/    ← kỹ thuật: database.py (schema+SQLite), unit_of_work.py, repositories/, security.py, mailer.py, rate_limit.py
  api/               ← HTTP: routers (auth, public, admin, staff), deps.py (phân quyền), serializers.py, errors.py
  application.py     ← Composition Root: dựng và nối mọi thành phần
  main.py            ← create_app()
public/              ← portal (khách) · account · admin · staff (PWA soát vé) · assets · vendor
tests/               ← domain, 4 luồng nghiệp vụ, API/phân quyền
```
**Phân quyền nằm trong cấu trúc lớp:** chỉ `Administrator` có `create_event()`, chỉ `EventStaff` có `scan_qr_code()`, chỉ `Attendee` có `submit_registration_form()`.
Router chỉ khai báo `Depends(admin_user)` / `staff_user` / `attendee_user` → nạp đúng lớp theo token rồi gọi phương thức; gọi nhầm vai trò là `403`.

## Bảng đối chiếu PDF ↔ code (camelCase → snake_case)
| PDF | Code |
|---|---|
| `User(userId, fullName, email, phoneNumber, password, role)` | `domain/user.py: User` · `password_hash` (bcrypt) · `login()`, `logout()`, `update_profile()` |
| `Administrator.createEvent / editEvent / updateEventStatus` | `create_event / edit_event / update_event_status` (+ `delete_event`) |
| `configureTicketCategory` | `configure_ticket_category` (+ `remove_ticket_category`) |
| `assignStaffSchedule`, `viewAttendeeList`, `ReportExporter` | `assign_staff_schedule`, `view_attendee_list`, `report_exporter()` → `generate_report / export_excel / export_csv` |
| `EventStaff(staffStatus)` `viewAssignedSchedule / scanQRCode / manualCheckIn` | `view_assigned_schedule / scan_qr_code / manual_check_in` |
| `Attendee.viewAvailableEvents / submitRegistrationForm` | `view_available_events / submit_registration_form` (+ `get_registration_history`) |
| `Event.create / edit / updateStatus / getAvailableCapacity` | `Event.create / edit / update_status / get_available_capacity` |
| `TicketCategory.updatePricing / checkAvailability` | `update_pricing / check_availability` |
| `Registration.submitForm / validateRegistration` | `submit_form / validate_registration` (+ `validation_error` trả mã lỗi) |
| `Ticket.generateQRCode / sendEmailWithTicket` | `generate_qr_code / send_email_with_ticket` |
| `StaffAssignment.updateWorkArea / updateShiftTime / isWithinShift` | `update_work_area / update_shift_time / is_within_shift` |
| `CheckInService.processQRCodeScan / processManualCheckIn` → `CheckInResult` | `services/check_in_service.py` → `domain/check_in_result.py` |

## Phần BỔ SUNG ngoài PDF (đã đánh dấu để bạn quyết định giữ/bỏ)
- Kết quả `WRONG_EVENT` (vàng) khi quét vé của sự kiện khác; `check_in_logs` ghi **mọi** lần quét (kể cả bị từ chối).
- Check-in thủ công bắt buộc ghi **giấy tờ đã đối chiếu** (`check_in_note`); vé lưu `checked_in_at/by/method`, `email_status` (PENDING/SENT/FAILED, Admin gửi lại được).
- `Event.description`, `registered_count`/`sold_count` (tính từ phiếu đăng ký, không lưu trùng).
- `shiftStartTime/EndTime` **không bắt buộc** (trống = cả sự kiện). Ngoài ca → từ chối `OUTSIDE_SHIFT`.
- Gỡ nhân viên = chuyển `INACTIVE` (giữ lịch sử đối soát); token cũ bị chặn ngay.
- Admin chọn nhân viên từ danh sách khi phân công (thay vì gõ ID + họ tên) – an toàn hơn, tránh nhập sai.

## Quyết định thiết kế cần bạn xác nhận
1. **Khách chưa đăng nhập** vẫn đăng ký được (tạo hồ sơ khách theo email, chưa có mật khẩu). Hồ sơ này **không thể "nhận" lại** bằng cách đăng ký tài khoản cùng email (tránh chiếm vé của người khác khi chưa xác thực email). Nếu email đã có tài khoản → yêu cầu đăng nhập.
2. Trạng thái sự kiện cho phép chuyển tự do giữa UPCOMING/ONGOING/COMPLETED (Admin sửa nhầm được). Sự kiện COMPLETED đóng đăng ký và đóng check-in.
3. Sự kiện đã có người đăng ký thì **không xoá được** (chuyển Completed); hạng vé đã bán không xoá được.
4. Mỗi khách **1 vé / sự kiện**.

## Mở rộng (ví dụ)
- **Thêm hạng người dùng** (vd. `Sponsor`): thêm giá trị vào `Role`, lớp con của `User`, ánh xạ ở `UserRepository`, `deps.py`.
- **Thêm trường cho Event**: `domain/event.py` + cột trong `database.py` + `repositories/events.py` + `serializers.py`.
- **Đổi DB sang PostgreSQL**: chỉ viết lại `database.py` + `repositories/` (domain, service giữ nguyên).
- **Đổi cách gửi mail/SMS**: sửa `infrastructure/mailer.py`.
- **Thêm luật check-in** (vd. chỉ cho vào đúng khu theo hạng vé): sửa `CheckInService._process`.

## Giới hạn đã biết
- SQLite + rate-limit trong bộ nhớ ⇒ chạy **1 worker/1 instance** (đủ cho sự kiện vài nghìn người). Quy mô lớn hơn: PostgreSQL + Redis.
- Email gửi đồng bộ khi đăng ký (SMTP chậm làm chậm phản hồi); lỗi email không làm mất vé.
- Chưa có quên mật khẩu qua email, chưa xác thực email khách.
- Camera quét QR cần HTTPS hoặc `localhost`.
