FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000 \
    APP_ENV=production \
    DB_PATH=/data/data.sqlite \
    OUTBOX_DIR=/data/outbox

WORKDIR /app

# Cài thư viện trước để Docker cache layer (chỉ build lại khi requirements.txt đổi)
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
COPY public ./public
COPY seed.py create_admin.py ./

# Chạy bằng user thường (không phải root); /data là nơi lưu SQLite + outbox (gắn volume)
RUN useradd --system --uid 10001 --no-create-home app \
    && mkdir -p /data \
    && chown -R app:app /data
USER app
VOLUME ["/data"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4).status == 200 else 1)"

# CHỈ 1 worker: SQLite + bộ đếm rate-limit nằm trong bộ nhớ của tiến trình.
# --proxy-headers: lấy IP thật của người dùng từ Caddy/nginx phía trước (dùng cho giới hạn số lần đăng nhập/đăng ký).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers"]
