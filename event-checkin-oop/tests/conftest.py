import dataclasses
import os
from datetime import datetime

os.environ.setdefault("BCRYPT_ROUNDS", "4")
import pytest
from fastapi.testclient import TestClient

from app.application import Application
from app.clock import FixedClock
from app.config import Settings
from app.main import create_app

NOW = datetime(2026, 12, 1, 9, 0)


@pytest.fixture
def core(tmp_path):
    s = dataclasses.replace(Settings.from_env(), db_path=str(tmp_path / "t.db"), outbox_dir=str(tmp_path / "out"),
                            smtp_host=None, production=False, login_rate_max=1000, signup_rate_max=1000,
                            register_rate_max=1000, read_rate_max=1000)
    return Application(s, FixedClock(NOW))


@pytest.fixture
def admin(core):
    core.auth.create_admin("Admin", "admin@x.com", "Admin12345")
    return core.auth.authenticate(core.auth.login("admin@x.com", "Admin12345", "internal")[0])


@pytest.fixture
def event(admin):
    """Sự kiện sức chứa 3, hạng VIP (2 vé) & Standard (5 vé), ca trực 08:00-12:00 ngày 01/12."""
    e = admin.create_event(event_name="Hội nghị Công nghệ", max_capacity=3, start_time="2026-12-01T08:00",
                           end_time="2026-12-01T17:00", location="Hà Nội")
    vip = admin.configure_ticket_category(e.event_id, "VIP", 500000, 2)
    std = admin.configure_ticket_category(e.event_id, "Standard", 100000, 5)
    return e, vip, std


@pytest.fixture
def staff(core, admin, event):
    e, *_ = event
    s, pw = admin.add_staff("Nhân Viên A", "staff@x.com", "0901234567")
    admin.assign_staff_schedule(s.user_id, e.event_id, "Cổng A", "2026-12-01T08:00", "2026-12-01T12:00")
    return core.auth.authenticate(core.auth.login("staff@x.com", pw, "internal")[0])


@pytest.fixture
def client(core):
    return TestClient(create_app(core))


def guest(core, n):
    from app.domain import Attendee
    return Attendee.guest(core, f"Khách {n}", f"k{n}@x.com", "09112223%02d" % n)
