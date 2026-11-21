"""Dữ liệu DEMO (chỉ để thử, KHÔNG chạy trên máy chủ thật): 1 admin, 2 staff, 2 sự kiện, 12 khách.
   python seed.py        → in ra tài khoản demo và 3 mã QR mẫu.
"""
import os
import sys
from datetime import timedelta

from app.application import Application
from app.config import Settings
from app.domain import Attendee

if os.environ.get("APP_ENV") == "production":
    sys.exit("seed.py bị chặn khi APP_ENV=production (tạo mật khẩu mặc định yếu). Dùng ADMIN_EMAIL/ADMIN_PASSWORD hoặc create_admin.py.")

app = Application(Settings.from_env())
with app.uow() as u:
    if u.users.get_by_email("admin@demo.vn"):
        sys.exit("Dữ liệu demo đã có (admin@demo.vn). Xoá file DB nếu muốn tạo lại.")
admin = app.auth.create_admin("Quản trị viên Demo", "admin@demo.vn", "admin12345")
admin = app.auth.authenticate(admin.login("admin12345"))
now = app.clock.now().replace(minute=0, second=0, microsecond=0)
f = lambda d: d.strftime("%Y-%m-%dT%H:%M")

e1 = admin.create_event(event_name="Hội nghị Công nghệ 2026", max_capacity=40, start_time=f(now - timedelta(hours=1)),
                        end_time=f(now + timedelta(hours=7)), location="Trung tâm Hội nghị, Hà Nội",
                        description="Một ngày với các chủ đề AI, Cloud và An toàn thông tin.")
admin.update_event_status(e1.event_id, "ONGOING")
vip = admin.configure_ticket_category(e1.event_id, "VIP", 500000, 10)
std = admin.configure_ticket_category(e1.event_id, "Standard", 100000, 30)
e2 = admin.create_event(event_name="Workshop Python cho người mới", max_capacity=20,
                        start_time=f(now + timedelta(days=7)), end_time=f(now + timedelta(days=7, hours=4)), location="TP.HCM")
free = admin.configure_ticket_category(e2.event_id, "Miễn phí", 0, 20)

staff_accounts = []
for i, (name, area) in enumerate([("Nguyễn Văn Soát", "Cổng A"), ("Trần Thị Cổng", "Khu VIP")], 1):
    s, _ = admin.add_staff(name, f"staff{i}@demo.vn", f"090000000{i}", "staff12345")
    admin.assign_staff_schedule(s.user_id, e1.event_id, area, f(now - timedelta(hours=1)), f(now + timedelta(hours=7)))
    staff_accounts.append((s.email, area))

tickets = []
for i in range(1, 13):
    a = Attendee.guest(app, f"Khách Demo {i:02d}", f"khach{i:02d}@demo.vn", f"09110000{i:02d}")
    reg, t = a.submit_registration_form(e1.event_id, (vip if i <= 4 else std).ticket_type_id)
    tickets.append(t)
app.auth.register_attendee("Người Dùng Demo", "user@demo.vn", "0912345678", "user12345")

print("== TÀI KHOẢN DEMO ==")
print("Admin     : admin@demo.vn / admin12345        → /admin/")
for em, area in staff_accounts:
    print(f"Staff     : {em} / staff12345 ({area})  → /staff/")
print("Khách     : user@demo.vn / user12345          → /")
print(f"Sự kiện   : /e/{e1.unique_url}   |   /e/{e2.unique_url}")
print("Mã QR mẫu (dán vào ô 'Máy quét / nhập mã vé' của Staff):")
for t in tickets[:3]:
    print("   ", t.qr_code_data)
