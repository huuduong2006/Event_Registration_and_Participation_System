"""Băm mật khẩu (bcrypt) và token phiên (JWT có jti để thu hồi khi đăng xuất)."""
import os
import time
import uuid

import bcrypt
import jwt

from ..errors import Unauthorized


class PasswordHasher:
    def __init__(self, rounds: int | None = None):
        self.rounds = rounds or int(os.environ.get("BCRYPT_ROUNDS") or 12)

    @property
    def dummy(self) -> str:
        """Hash giả để đăng nhập email không tồn tại tốn thời gian như email có thật."""
        if not hasattr(self, "_dummy"):
            self._dummy = self.hash("dummy-password")
        return self._dummy

    def hash(self, password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt(self.rounds)).decode()

    def verify(self, password: str, hashed: str) -> bool:
        try:
            return bcrypt.checkpw(str(password).encode()[:72], hashed.encode())
        except ValueError:
            return False


class TokenService:
    ALG = "HS256"

    def __init__(self, secret: str, ttl_hours: int):
        self.secret, self.ttl = secret, ttl_hours * 3600

    def issue(self, user_id: str, role: str) -> str:
        now = int(time.time())
        return jwt.encode({"sub": user_id, "role": role, "jti": uuid.uuid4().hex, "iat": now, "exp": now + self.ttl},
                          self.secret, algorithm=self.ALG)

    def decode(self, token: str) -> dict:
        try:
            return jwt.decode(token, self.secret, algorithms=[self.ALG])
        except jwt.ExpiredSignatureError:
            raise Unauthorized("Phiên đăng nhập đã hết hạn, vui lòng đăng nhập lại")
        except jwt.PyJWTError:
            raise Unauthorized("Phiên đăng nhập không hợp lệ")
