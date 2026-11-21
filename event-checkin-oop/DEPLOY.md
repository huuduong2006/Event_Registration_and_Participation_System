# Hướng dẫn triển khai bằng Docker

Có hai cách chạy: **A. thử trên máy bạn** (HTTP, không cần tên miền) và **B. lên web thật** trên VPS (HTTPS tự động).
Camera quét QR chỉ hoạt động trên HTTPS hoặc `localhost`, nên khi dùng thật bắt buộc phải theo cách B (hoặc nền tảng đã có HTTPS).

Các file liên quan: `Dockerfile`, `docker-compose.yml`, `Caddyfile`, `.env.example`, `create_admin.py`, `seed.py`.

---

## A. Thử trên máy bạn

Cài **Docker Desktop** (Windows/macOS) hoặc Docker Engine (Linux), rồi:

```bash
cp .env.example .env                 # Windows PowerShell: Copy-Item .env.example .env
```
Mở `.env`, điền `JWT_SECRET` (chuỗi ngẫu nhiên ≥ 32 ký tự; tạo bằng `python3 -c "import secrets;print(secrets.token_urlsafe(48))"`). Giữ `BASE_URL=http://localhost:8000`.

```bash
docker compose up -d --build         # build và chạy nền
```
Mở http://localhost:8000. Muốn có dữ liệu demo (admin@demo.vn/admin12345, staff1@demo.vn/staff12345, 12 khách):

```bash
docker compose exec -e APP_ENV=development app python seed.py
# lệnh trên in ra 3 mã QR mẫu: dán vào ô "Máy quét / nhập mã vé" ở trang /staff/ để thử check-in
```
> `seed.py` **xoá toàn bộ dữ liệu** và tạo mật khẩu mặc định, nên mặc định bị chặn trong container (APP_ENV=production). Chỉ dùng để demo, **không** chạy trên máy chủ thật.

Dừng: `docker compose down` (dữ liệu vẫn còn trong volume). Xoá cả dữ liệu: `docker compose down -v`.

---

## B. Lên web thật (VPS + HTTPS)

### B1. Chuẩn bị
1. **VPS** Linux (Ubuntu 22.04/24.04, 1 vCPU / 1 GB RAM là đủ cho sự kiện vài trăm–vài nghìn người).
2. **Tên miền** (hoặc tên miền phụ, ví dụ `sukien.example.com`): tạo bản ghi **A** trỏ về IP của VPS. Đợi vài phút cho DNS cập nhật.
3. Mở cổng **80 và 443** (và 22 cho SSH). Với Ubuntu: `sudo ufw allow 22,80,443/tcp && sudo ufw enable`.
4. Cài Docker trên VPS (xem https://docs.docker.com/engine/install/ubuntu/). Cách nhanh: `curl -fsSL https://get.docker.com | sudo sh`.

### B2. Đưa code lên và cấu hình
```bash
# từ máy bạn (hoặc dùng git clone nếu code nằm trên GitHub)
scp event-checkin-oop.zip user@IP_VPS:~/ && ssh user@IP_VPS
unzip event-checkin-oop.zip && cd event-checkin-oop

cp .env.example .env && nano .env
```
Trong `.env` điền tối thiểu:
```
JWT_SECRET=<chuỗi ngẫu nhiên ≥ 32 ký tự>
BASE_URL=https://sukien.example.com
DOMAIN=sukien.example.com
ADMIN_EMAIL=ban@example.com
ADMIN_PASSWORD=<mật khẩu ≥ 10 ký tự>
```
(Muốn gửi email thật thì điền thêm `SMTP_*`; Gmail cần *App Password*. Bỏ trống thì email chỉ được ghi vào thư mục outbox.)

### B3. Chạy
```bash
docker compose --profile https up -d --build
docker compose ps                    # app phải ở trạng thái "healthy"
docker compose logs -f caddy         # lần đầu sẽ thấy Caddy xin chứng chỉ HTTPS
```
Sau ~1 phút mở `https://sukien.example.com`.

### B4. Administrator đầu tiên
Khi khởi động, nếu `ADMIN_EMAIL` + `ADMIN_PASSWORD` có trong `.env` và email chưa tồn tại, hệ thống **tự tạo** Administrator (Data Seeding).
Đăng nhập tại `https://<tên-miền>/admin/`, sau đó **xoá `ADMIN_PASSWORD` khỏi `.env`** rồi `docker compose up -d --force-recreate`.
Có thể tạo/đặt lại mật khẩu admin bất cứ lúc nào:
```bash
docker compose exec app python create_admin.py admin@example.com "Quản trị viên"
```
Quy trình vận hành: Admin tạo sự kiện + hạng vé → tạo **tài khoản nhân viên** (mục “Nhân viên”; nhân viên *không* tự đăng ký) → **phân công** nhân viên vào sự kiện (khu vực + ca) → nhân viên đăng nhập `https://<tên-miền>/staff/` để check-in. Khách tham dự dùng `https://<tên-miền>/`.

---

## Vận hành

| Việc | Lệnh |
|---|---|
| Xem log | `docker compose logs -f app` |
| Khởi động lại | `docker compose restart app` |
| Cập nhật code mới | thay code rồi `docker compose --profile https up -d --build` (dữ liệu giữ nguyên) |
| Xem email vé (khi chưa cấu hình SMTP) | `docker compose exec app ls /data/outbox` |
| Kiểm tra sống/chết | `curl https://<tên-miền>/api/health` → `{"ok":true}` |

### Sao lưu dữ liệu (nên làm trước và ngay sau sự kiện)
```bash
docker compose exec app python -c "import sqlite3;s=sqlite3.connect('/data/data.sqlite');d=sqlite3.connect('/data/backup.sqlite');s.backup(d);d.close()"
docker compose cp app:/data/backup.sqlite ./backup-$(date +%F).sqlite
```
(dùng API sao lưu của SQLite nên an toàn kể cả khi ứng dụng đang chạy).

### Khôi phục
```bash
docker compose stop app
docker compose run --rm --no-deps -v "$PWD":/backup:ro app \
  python -c "import shutil;shutil.copy('/backup/backup-2026-11-20.sqlite','/data/data.sqlite')"
docker compose start app
```

---

## Dùng nền tảng PaaS (Render, Railway, Fly.io…)

Các nền tảng này build trực tiếp từ `Dockerfile` và tự cấp HTTPS (không cần Caddy). Cần:
- Cổng của ứng dụng: **8000**.
- Biến môi trường: `JWT_SECRET`, `BASE_URL` (địa chỉ nền tảng cấp hoặc tên miền riêng), và `SMTP_*` nếu gửi email.
- **Gắn ổ đĩa lưu trữ (persistent disk/volume) vào `/data`**. Nếu không, file SQLite sẽ mất mỗi lần khởi động lại. Gói miễn phí không có ổ đĩa thường không phù hợp.
- Chỉ chạy **1 instance**, không bật tự động mở rộng (SQLite và bộ đếm giới hạn đăng nhập nằm trong một tiến trình).
- Tạo admin bằng shell của nền tảng: `python create_admin.py admin "Quản trị viên"` (hoặc đặt tạm `ADMIN_PASSWORD` trong môi trường lúc chạy lệnh).

---

## Lỗi thường gặp

| Hiện tượng | Nguyên nhân / cách xử lý |
|---|---|
| `env file .env not found` | Chưa tạo `.env` (`cp .env.example .env`). |
| Ứng dụng thoát ngay, log báo `JWT_SECRET chưa đặt hoặc quá ngắn` | `JWT_SECRET` trong `.env` đang trống hoặc < 32 ký tự. Điền chuỗi ngẫu nhiên, rồi `docker compose up -d --force-recreate`. Xem log: `docker compose logs app --tail 30`. |
| Đăng nhập báo `Lỗi hệ thống` (bản cũ) | Cũng do `JWT_SECRET` trống (bản cũ không báo lỗi khi khởi động). Điền `JWT_SECRET` rồi `docker compose up -d --force-recreate`. |
| Caddy không lấy được chứng chỉ | DNS chưa trỏ về VPS, hoặc cổng 80/443 bị chặn (tường lửa của VPS/nhà cung cấp). Xem `docker compose logs caddy`. |
| Trang mở được nhưng camera không bật | Đang truy cập bằng HTTP hoặc IP. Dùng `https://<tên-miền>` và cấp quyền camera. |
| Báo `429 Quá nhiều yêu cầu` | Chạm giới hạn đăng nhập/đăng ký theo IP; đợi vài phút hoặc tăng `LOGIN_RATE_MAX` / `REG_RATE_MAX` trong `.env`. |
| Link trong email trỏ về `localhost` | `BASE_URL` trong `.env` chưa đặt đúng địa chỉ công khai. |
| `permission denied` ghi `/data` | Volume cũ do root tạo: `docker compose down -v` (mất dữ liệu cũ) hoặc `docker compose run --rm --user root app chown -R app /data`. |

## Danh sách kiểm tra trước ngày sự kiện

- [ ] `JWT_SECRET` ngẫu nhiên, dài; không dùng lại ở nơi khác; file `.env` không đưa lên Git.
- [ ] Đã tạo admin (ADMIN_EMAIL/ADMIN_PASSWORD hoặc `create_admin.py`), đã xoá `ADMIN_PASSWORD` khỏi `.env`; **không** chạy `seed.py`; không còn tài khoản demo.
- [ ] Truy cập bằng HTTPS, thử quét QR bằng điện thoại thật ngay tại hiện trường mạng (Wi-Fi/4G).
- [ ] Đã thử gửi email thật tới một hộp thư bên ngoài (kiểm tra cả thư mục Spam).
- [ ] Đã sao lưu dữ liệu, và biết cách khôi phục.
- [ ] Admin đã tạo tài khoản nhân viên và phân công đúng sự kiện, khu vực, ca trực (nhân viên ngoài ca sẽ bị từ chối).
