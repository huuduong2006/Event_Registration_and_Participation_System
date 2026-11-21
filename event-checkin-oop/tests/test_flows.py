"""Kiểm thử theo 4 luồng nghiệp vụ trong tài liệu thiết kế."""
import threading
from datetime import datetime

import pytest

from app.domain import Attendee, CheckInOutcome
from app.errors import Conflict, Forbidden, Unauthorized, ValidationError
from .conftest import guest


# ---- Luồng 1: tài khoản ----
def test_two_portals_and_roles(core, admin, staff):
    core.auth.register_attendee("Khách A", "a@x.com", "0911222333", "Matkhau123")
    assert core.auth.login("a@x.com", "Matkhau123", "attendee")[1].role.value == "ATTENDEE"
    with pytest.raises(Unauthorized):                       # attendee không vào cổng nội bộ
        core.auth.login("a@x.com", "Matkhau123", "internal")
    with pytest.raises(Unauthorized):                       # staff không vào cổng khách
        core.auth.login("staff@x.com", "x", "attendee")
    with pytest.raises(Unauthorized):
        core.auth.login("nobody@x.com", "whatever12", "internal")


def test_inactive_staff_blocked(core, admin, staff):
    tok = core.tokens.issue(staff.user_id, "STAFF")
    admin.remove_staff(staff.user_id)
    with pytest.raises(Forbidden):
        core.auth.authenticate(tok)                          # token cũ bị chặn ngay
    s2, pw = admin.add_staff("Nhân viên B", "b@x.com", "0902222333", "Matkhau123")
    admin.remove_staff(s2.user_id)
    with pytest.raises(Forbidden) as e:
        core.auth.login("b@x.com", "Matkhau123", "internal")
    assert e.value.code == "ACCOUNT_INACTIVE"
    with pytest.raises(Unauthorized):                        # sai mật khẩu vẫn là 401, không lộ trạng thái
        core.auth.login("b@x.com", "sai-mat-khau", "internal")


def test_logout_revokes_token(core, admin):
    tok = core.auth.login("admin@x.com", "Admin12345", "internal")[0]
    admin.logout(tok)
    with pytest.raises(Unauthorized):
        core.auth.authenticate(tok)


def test_duplicate_email(core, admin):
    with pytest.raises(Conflict):
        core.auth.register_attendee("Trùng", "admin@x.com", "0911222333", "Matkhau123")


# ---- Luồng 2: quản trị ----
def test_event_lifecycle_and_unique_url(admin, event):
    e, vip, _ = event
    assert e.unique_url.startswith("hoi-nghi-cong-nghe")
    assert admin.update_event_status(e.event_id, "ONGOING").status.value == "ONGOING"
    with pytest.raises(Conflict):
        admin.configure_ticket_category(e.event_id, "vip", 1, 1)       # trùng tên (không phân biệt hoa/thường)


def test_cannot_delete_event_or_shrink_below_sold(core, admin, event):
    e, vip, _ = event
    guest(core, 1).submit_registration_form(e.event_id, vip.ticket_type_id)
    with pytest.raises(Conflict):
        admin.delete_event(e.event_id)
    with pytest.raises(ValidationError):
        admin.edit_event(e.event_id, max_capacity=0)
    with pytest.raises(ValidationError):
        admin.configure_ticket_category(e.event_id, "VIP", 1, 0, vip.ticket_type_id)
    with pytest.raises(Conflict):
        admin.remove_ticket_category(vip.ticket_type_id)


def test_assignment_rules(core, admin, event, staff):
    e, *_ = event
    with pytest.raises(Conflict):
        admin.assign_staff_schedule(staff.user_id, e.event_id, "Cổng B")
    a = admin.list_staff_assignments(e.event_id)[0]
    admin.update_staff_assignment(a["assignment_id"], work_area="Khu VIP")
    assert staff.view_assigned_schedule()[0]["work_area"] == "Khu VIP"
    admin.unassign_staff(a["assignment_id"])
    assert staff.view_assigned_schedule() == []


def test_attendee_list_filters_and_report(core, admin, event, staff):
    e, vip, std = event
    r1, t1 = guest(core, 1).submit_registration_form(e.event_id, vip.ticket_type_id)
    guest(core, 2).submit_registration_form(e.event_id, std.ticket_type_id)
    staff.scan_qr_code(t1.qr_code_data, e.event_id)
    assert admin.view_attendee_list(e.event_id, status="CHECKED_IN")["total"] == 1
    assert admin.view_attendee_list(e.event_id, ticket_type_id=std.ticket_type_id)["total"] == 1
    assert admin.view_attendee_list(e.event_id, q="khách 2")["total"] == 1
    rep = admin.report_exporter().generate_report(e.event_id)
    assert (rep["registered"], rep["checked_in"], rep["attendance_rate"]) == (2, 1, 50.0)
    assert admin.report_exporter().export_excel(e.event_id)[:2] == b"PK"


def test_csv_injection_neutralised(core, admin, event):
    e, vip, _ = event
    from app.domain import Attendee
    Attendee.guest(core, "=HYPERLINK(1)", "inj@x.com", "0911222333").submit_registration_form(e.event_id, vip.ticket_type_id)
    assert b"'=HYPERLINK" in admin.report_exporter().export_csv(e.event_id)


# ---- Luồng 3: đăng ký ----
def test_registration_creates_ticket_and_email(core, event):
    e, vip, _ = event
    reg, t = guest(core, 1).submit_registration_form(e.event_id, vip.ticket_type_id)
    assert t.email_status.value == "SENT" and len(list(__import__("os").scandir(core.settings.outbox_dir))) == 1


def test_duplicate_soldout_and_capacity(core, event):
    e, vip, std = event
    a = guest(core, 1)
    a.submit_registration_form(e.event_id, vip.ticket_type_id)
    with pytest.raises(Conflict) as d:
        a.submit_registration_form(e.event_id, std.ticket_type_id)
    assert d.value.code == "DUPLICATE"
    guest(core, 2).submit_registration_form(e.event_id, vip.ticket_type_id)
    with pytest.raises(Conflict) as s:
        guest(core, 3).submit_registration_form(e.event_id, vip.ticket_type_id)
    assert s.value.code == "SOLD_OUT"
    guest(core, 3).submit_registration_form(e.event_id, std.ticket_type_id)      # đủ 3/3
    with pytest.raises(Conflict) as c:
        guest(core, 4).submit_registration_form(e.event_id, std.ticket_type_id)
    assert c.value.code == "CLOSED"


def test_no_overselling_under_concurrency(core, admin):
    e = admin.create_event(event_name="Đua vé", max_capacity=100)
    c = admin.configure_ticket_category(e.event_id, "Hot", 0, 5)
    users = [guest(core, i) for i in range(20)]
    ok, fail = [], []

    def go(u):
        try:
            u.submit_registration_form(e.event_id, c.ticket_type_id); ok.append(1)
        except Conflict:
            fail.append(1)
    th = [threading.Thread(target=go, args=(u,)) for u in users]
    [t.start() for t in th]; [t.join() for t in th]
    assert len(ok) == 5 and len(fail) == 15


def test_guest_cannot_hijack_account_email(core):
    core.auth.register_attendee("Chủ", "own@x.com", "0911222333", "Matkhau123")
    with pytest.raises(Conflict) as e:
        Attendee.guest(core, "Kẻ lạ", "own@x.com", "0999888777")
    assert e.value.code == "LOGIN_REQUIRED"


def test_ticket_visible_only_to_owner(core, event):
    e, vip, _ = event
    reg, _ = guest(core, 1).submit_registration_form(e.event_id, vip.ticket_type_id)
    other = guest(core, 2)
    with pytest.raises(Forbidden):
        core.tickets.view_ticket(reg.registration_id, other.user_id)


# ---- Luồng 4: check-in ----
def test_check_in_outcomes(core, event, staff):
    e, vip, _ = event
    reg, t = guest(core, 1).submit_registration_form(e.event_id, vip.ticket_type_id)
    r = staff.scan_qr_code(t.qr_code_data, e.event_id)
    assert r.outcome == CheckInOutcome.VALID and r.signal == "GREEN" and r.work_area == "Cổng A"
    r2 = staff.scan_qr_code(t.qr_code_data, e.event_id)
    assert r2.outcome == CheckInOutcome.ALREADY_USED and r2.first_check_in["by"] == "Nhân Viên A"
    assert staff.scan_qr_code("khong-ton-tai", e.event_id).outcome == CheckInOutcome.INVALID


def test_wrong_event(core, admin, event, staff):
    e, vip, _ = event
    other = admin.create_event(event_name="Sự kiện khác", max_capacity=5)
    c2 = admin.configure_ticket_category(other.event_id, "Std", 0, 5)
    _, t = guest(core, 1).submit_registration_form(other.event_id, c2.ticket_type_id)
    r = staff.scan_qr_code(t.qr_code_data, e.event_id)
    assert r.outcome == CheckInOutcome.WRONG_EVENT and r.signal == "YELLOW"
    assert admin.view_attendee_list(other.event_id, status="CHECKED_IN")["total"] == 0


def test_shift_and_assignment_enforced(core, admin, event, staff):
    e, vip, _ = event
    _, t = guest(core, 1).submit_registration_form(e.event_id, vip.ticket_type_id)
    core.clock.advance(hours=4)                      # 13:00 – hết ca
    with pytest.raises(Forbidden) as x:
        staff.scan_qr_code(t.qr_code_data, e.event_id)
    assert x.value.code == "OUTSIDE_SHIFT"
    core.clock.advance(hours=-8)                     # 05:00 – chưa tới ca
    with pytest.raises(Forbidden):
        staff.scan_qr_code(t.qr_code_data, e.event_id)
    s2, pw = admin.add_staff("Chưa phân công", "s2@x.com", "0901111222")
    with pytest.raises(Forbidden) as y:
        s2.scan_qr_code(t.qr_code_data, e.event_id)
    assert y.value.code == "NOT_ASSIGNED"


def test_manual_check_in_needs_note_and_logs(core, event, staff):
    e, vip, _ = event
    reg, _ = guest(core, 1).submit_registration_form(e.event_id, vip.ticket_type_id)
    with pytest.raises(ValidationError):
        staff.manual_check_in(reg.registration_id, "", e.event_id)
    assert staff.manual_check_in(reg.registration_id, "CCCD", e.event_id).is_valid
    assert staff.check_in_stats(e.event_id)["checked_in"] == 1
    assert staff.search_attendees(e.event_id, "khách 1")[0]["check_in_note"] == "CCCD"


def test_concurrent_scan_single_valid(core, event, staff):
    e, vip, _ = event
    _, t = guest(core, 1).submit_registration_form(e.event_id, vip.ticket_type_id)
    out = []
    th = [threading.Thread(target=lambda: out.append(staff.scan_qr_code(t.qr_code_data, e.event_id).outcome)) for _ in range(8)]
    [x.start() for x in th]; [x.join() for x in th]
    assert out.count(CheckInOutcome.VALID) == 1 and out.count(CheckInOutcome.ALREADY_USED) == 7
