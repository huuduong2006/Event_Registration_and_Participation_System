"""ReportExporter: số liệu báo cáo, biểu đồ, xuất Excel/CSV (Luồng 2 – bước 5)."""
import csv
import io
from collections import Counter

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from ..errors import NotFound

HEADERS = ["Mã đăng ký", "Họ tên", "Email", "Số điện thoại", "Loại vé", "Giá (VND)", "Ngày đăng ký",
           "Trạng thái check-in", "Giờ check-in", "Hình thức", "Nhân viên check-in", "Ghi chú", "Email vé"]


class ReportExporter:
    def __init__(self, app):
        self.app = app

    def _load(self, event_id):
        with self.app.uow() as u:
            e = u.events.get(event_id)
            if e is None:
                raise NotFound("Không tìm thấy sự kiện")
            cats = u.categories.list_for_event(event_id)
            rows, _ = u.registrations.search(event_id)
        return e, cats, rows

    def generate_report(self, event_id: str) -> dict:
        e, cats, rows = self._load(event_id)
        checked = [r for r in rows if r["check_in_status"] == "CHECKED_IN"]
        by_type = [{"name": c.type_name, "price": c.price, "quantity": c.quantity_limit, "sold": c.sold_count,
                    "checked_in": sum(1 for r in checked if r["ticket_type_id"] == c.ticket_type_id)} for c in cats]
        hours = Counter(r["checked_in_at"][:13].replace("T", " ") + "h" for r in checked if r["checked_in_at"])
        days = Counter(r["registration_date"][:10] for r in rows)
        by_staff = Counter(r["checked_in_by_name"] or "—" for r in checked)
        n = len(rows)
        return {"event": e, "registered": n, "checked_in": len(checked), "not_checked_in": n - len(checked),
                "attendance_rate": round(len(checked) / n * 100, 1) if n else 0.0,
                "capacity": e.max_capacity, "fill_rate": round(n / e.max_capacity * 100, 1),
                "revenue": sum(r["price"] for r in rows),
                "by_ticket_type": by_type,
                "checkin_by_hour": [{"label": k, "count": v} for k, v in sorted(hours.items())],
                "registrations_by_day": [{"label": k, "count": v} for k, v in sorted(days.items())],
                "by_staff": [{"name": k, "count": v} for k, v in by_staff.most_common()]}

    @staticmethod
    def _row(r):
        return [r["registration_id"], r["full_name"], r["email"], r["phone_number"] or "", r["type_name"], r["price"],
                (r["registration_date"] or "").replace("T", " "),
                "Đã check-in" if r["check_in_status"] == "CHECKED_IN" else "Chưa check-in",
                (r["checked_in_at"] or "").replace("T", " "), r["check_in_method"] or "",
                r["checked_in_by_name"] or "", r["check_in_note"] or "", r["email_status"]]

    def export_csv(self, event_id: str) -> bytes:
        _, _, rows = self._load(event_id)
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(HEADERS)
        for r in rows:
            w.writerow([_safe(x) for x in self._row(r)])
        return b"\xef\xbb\xbf" + buf.getvalue().encode()        # BOM để Excel đọc đúng tiếng Việt

    def export_excel(self, event_id: str) -> bytes:
        rep = self.generate_report(event_id)
        _, _, rows = self._load(event_id)
        wb = Workbook()
        ws = wb.active
        ws.title = "Tổng quan"
        e = rep["event"]
        info = [("Sự kiện", e.event_name), ("Địa điểm", e.location or ""), ("Sức chứa", rep["capacity"]),
                ("Đã đăng ký", rep["registered"]), ("Đã check-in", rep["checked_in"]),
                ("Tỉ lệ có mặt (%)", rep["attendance_rate"]), ("Doanh thu đăng ký (VND)", rep["revenue"])]
        for i, (k, v) in enumerate(info, 1):
            ws.cell(i, 1, k).font = Font(bold=True)
            ws.cell(i, 2, _safe(v))
        r0 = len(info) + 2
        for j, h in enumerate(["Loại vé", "Giá", "Số lượng", "Đã bán", "Đã check-in"], 1):
            c = ws.cell(r0, j, h)
            c.font, c.fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="2F5597")
        for i, t in enumerate(rep["by_ticket_type"], r0 + 1):
            for j, v in enumerate([t["name"], t["price"], t["quantity"], t["sold"], t["checked_in"]], 1):
                ws.cell(i, j, _safe(v))
        ws.column_dimensions["A"].width, ws.column_dimensions["B"].width = 26, 34
        ws2 = wb.create_sheet("Danh sách tham dự")
        for j, h in enumerate(HEADERS, 1):
            c = ws2.cell(1, j, h)
            c.font, c.fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="2F5597")
            c.alignment = Alignment(horizontal="center")
            ws2.column_dimensions[get_column_letter(j)].width = 22
        for i, r in enumerate(rows, 2):
            for j, v in enumerate(self._row(r), 1):
                ws2.cell(i, j, _safe(v))
        ws2.freeze_panes = "A2"
        out = io.BytesIO()
        wb.save(out)
        return out.getvalue()


def _safe(v):
    """Chống CSV/Excel injection: ô văn bản bắt đầu bằng = + - @ bị Excel hiểu là công thức."""
    return "'" + v if isinstance(v, str) and v[:1] in ("=", "+", "-", "@") else v
