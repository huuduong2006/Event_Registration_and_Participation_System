"""Gửi email. Có SMTP_HOST → gửi thật; không có → ghi file .eml vào thư mục outbox (chế độ DEV)."""
import os
import smtplib
import ssl
import time
from email.message import EmailMessage

from ..config import Settings


class Mailer:
    def __init__(self, settings: Settings):
        self.s = settings

    def send(self, to: str, subject: str, text: str, html: str | None = None,
             attachments: list[tuple[str, bytes, str, str | None]] = ()) -> None:
        """attachments: (tên file, bytes, mime 'image/png', content-id hoặc None). Lỗi → ném Exception để gọi nơi ghi trạng thái FAILED."""
        msg = EmailMessage()
        msg["From"], msg["To"], msg["Subject"] = self.s.mail_from, to, subject
        msg.set_content(text)
        if html:
            msg.add_alternative(html, subtype="html")
        for name, data, mime, cid in attachments:
            maintype, subtype = mime.split("/")
            part = msg.get_payload()[-1] if html else msg
            part.add_attachment(data, maintype=maintype, subtype=subtype, filename=name, cid=f"<{cid}>" if cid else None)
        if not self.s.smtp_host:
            os.makedirs(self.s.outbox_dir, exist_ok=True)
            fn = os.path.join(self.s.outbox_dir, f"{int(time.time() * 1000)}-{to.replace('@', '_at_')}.eml")
            with open(fn, "wb") as f:
                f.write(bytes(msg))
            return
        if self.s.smtp_secure:
            smtp = smtplib.SMTP_SSL(self.s.smtp_host, self.s.smtp_port, timeout=20, context=ssl.create_default_context())
        else:
            smtp = smtplib.SMTP(self.s.smtp_host, self.s.smtp_port, timeout=20)
        with smtp:
            if not self.s.smtp_secure:
                try:
                    smtp.starttls(context=ssl.create_default_context())
                except smtplib.SMTPNotSupportedError:
                    pass
            if self.s.smtp_user:
                smtp.login(self.s.smtp_user, self.s.smtp_pass)
            smtp.send_message(msg)
