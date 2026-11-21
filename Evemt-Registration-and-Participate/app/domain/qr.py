"""Vẽ mã QR thành ảnh PNG."""
import io


def render_qr_png(data: str, box_size: int = 10, border: int = 2) -> bytes:
    import qrcode
    from qrcode.constants import ERROR_CORRECT_M

    img = qrcode.make(data, box_size=box_size, border=border, error_correction=ERROR_CORRECT_M)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
