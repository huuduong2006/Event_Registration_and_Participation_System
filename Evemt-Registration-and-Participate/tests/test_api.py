"""Kiểm thử qua HTTP: phân quyền theo vai trò & định dạng lỗi."""
import pytest

from .conftest import guest


def login(client, email, pw, portal="internal"):
    r = client.post("/api/auth/login", json={"email": email, "password": pw, "portal": portal})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


def test_role_matrix(client, core, admin, event, staff):
    e, vip, _ = event
    A = login(client, "admin@x.com", "Admin12345")
    core.auth.register_attendee("Khách", "att@x.com", "0911222333", "Matkhau123")
    T = login(client, "att@x.com", "Matkhau123", "attendee")
    s2, pw = admin.add_staff("NV", "nv@x.com", "0901112223")
    S = login(client, "nv@x.com", pw)
    assert client.get("/api/admin/events").status_code == 401                       # chưa đăng nhập
    assert client.get("/api/admin/events", headers=A).status_code == 200
    assert client.get("/api/admin/events", headers=S).status_code == 403            # staff ≠ admin
    assert client.get("/api/admin/events", headers=T).status_code == 403            # attendee ≠ admin
    assert client.post("/api/staff/check-in/scan", headers=A, json={"qrCodeData": "x"}).status_code == 403
    assert client.get("/api/attendee/registrations", headers=S).status_code == 403
    r = client.get("/api/admin/events", headers=T).json()
    assert set(r) == {"error", "code"}


def test_public_registration_and_ticket_flow(client, core, event, staff):
    e, vip, _ = event
    pub = client.get(f"/api/public/events/{e.unique_url}").json()
    assert pub["availableCapacity"] == 3 and len(pub["ticketCategories"]) == 2
    r = client.post(f"/api/public/events/{e.event_id}/register", json={
        "fullName": "Trần Thị B", "email": "b@x.com", "phoneNumber": "0901234567", "ticketTypeId": vip.ticket_type_id})
    assert r.status_code == 201 and r.json()["qrImage"].startswith("data:image/png")
    again = client.post(f"/api/public/events/{e.event_id}/register", json={
        "fullName": "Trần Thị B", "email": "b@x.com", "phoneNumber": "0901234567", "ticketTypeId": vip.ticket_type_id})
    assert again.status_code == 409 and again.json()["code"] == "DUPLICATE"
    bad = client.post(f"/api/public/events/{e.event_id}/register", json={"fullName": "", "email": "x", "phoneNumber": "1"})
    assert bad.status_code == 400
    S = login(client, "staff@x.com", "x") if False else None


def test_staff_scan_over_http(client, core, admin, event):
    e, vip, _ = event
    s, pw = admin.add_staff("NV", "nv@x.com", "0901112223")
    admin.assign_staff_schedule(s.user_id, e.event_id, "Cổng 1")
    S = login(client, "nv@x.com", pw)
    _, t = guest(core, 1).submit_registration_form(e.event_id, vip.ticket_type_id)
    j = client.post("/api/staff/check-in/scan", headers=S, json={"qrCodeData": t.qr_code_data, "eventId": e.event_id}).json()
    assert j["result"] == "VALID" and j["signal"] == "GREEN" and j["workArea"] == "Cổng 1"
    j2 = client.post("/api/staff/check-in/scan", headers=S, json={"qrCodeData": t.qr_code_data, "eventId": e.event_id}).json()
    assert j2["result"] == "ALREADY_USED" and "firstCheckin" in j2
    st = client.get(f"/api/staff/events/{e.event_id}/stats", headers=S).json()
    assert st["checkedIn"] == 1


def test_attendee_history_and_privacy(client, core, event):
    e, vip, std = event
    core.auth.register_attendee("Khách A", "a@x.com", "0911222333", "Matkhau123")
    core.auth.register_attendee("Khách B", "b@x.com", "0911222444", "Matkhau123")
    A, B = login(client, "a@x.com", "Matkhau123", "attendee"), login(client, "b@x.com", "Matkhau123", "attendee")
    r = client.post(f"/api/attendee/events/{e.event_id}/register", headers=A, json={"ticketTypeId": vip.ticket_type_id})
    rid = r.json()["registrationId"]
    assert len(client.get("/api/attendee/registrations", headers=A).json()) == 1
    assert client.get("/api/attendee/registrations", headers=B).json() == []
    assert client.get(f"/api/attendee/registrations/{rid}/ticket", headers=B).status_code == 403
    assert client.get(f"/api/attendee/registrations/{rid}/qr.png", headers=A).headers["content-type"] == "image/png"


def test_exports_and_pages(client, core, admin, event):
    e, *_ = event
    A = login(client, "admin@x.com", "Admin12345")
    assert client.get(f"/api/admin/events/{e.event_id}/export.xlsx", headers=A).status_code == 200
    assert client.get(f"/api/admin/events/{e.event_id}/export.csv", headers=A).content.startswith(b"\xef\xbb\xbf")
    for p in ["/", f"/e/{e.unique_url}", "/admin/", "/staff/", "/account/"]:
        assert client.get(p).status_code == 200
    assert "script-src 'self'" in client.get("/").headers["content-security-policy"]


def test_rate_limit_login(core, client):
    import dataclasses
    core.settings = dataclasses.replace(core.settings, login_rate_max=3)
    codes = [client.post("/api/auth/login", json={"email": "x@x.com", "password": "y"}).status_code for _ in range(5)]
    assert codes[-1] == 429
