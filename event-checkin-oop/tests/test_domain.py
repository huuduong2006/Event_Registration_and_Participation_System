from datetime import datetime

import pytest

from app.domain import (Administrator, Attendee, Event, EventStaff, Registration, StaffAssignment, Ticket,
                        TicketCategory, User)
from app.errors import ValidationError


def test_user_is_abstract_and_roles():
    with pytest.raises(TypeError):
        User("x", "a", "b@c.d")
    assert {Administrator("1", "a", "a@x.vn").role.value, EventStaff("2", "b", "b@x.vn").role.value,
            Attendee("3", "c", "c@x.vn").role.value} == {"ADMIN", "STAFF", "ATTENDEE"}


def test_only_right_class_has_method():
    assert hasattr(Administrator, "create_event") and not hasattr(EventStaff, "create_event")
    assert hasattr(EventStaff, "scan_qr_code") and not hasattr(Attendee, "scan_qr_code")
    assert hasattr(Attendee, "submit_registration_form") and not hasattr(Administrator, "submit_registration_form")


def test_event_capacity_and_edit_rule():
    e = Event.create("Sự kiện thử", 5)
    e.registered_count = 4
    assert e.get_available_capacity() == 1
    with pytest.raises(ValidationError):
        e.edit("Sự kiện thử", 3)


def test_registration_validation_codes():
    e = Event.create("Sự kiện thử", 1)
    c = TicketCategory.create(e.event_id, "VIP", 0, 1)
    r = Registration.submit_form(e.event_id, "US-1", c.ticket_type_id, datetime(2026, 1, 1))
    assert r.validate_registration(e, c)
    assert r.validation_error(e, c, True)[0] == "DUPLICATE"
    c.sold_count = 1
    assert r.validation_error(e, c)[0] == "SOLD_OUT"
    e.registered_count = 1
    assert r.validation_error(e, c)[0] == "CLOSED"


def test_shift_states():
    a = StaffAssignment.create("US-1", "EV-1", "Cổng A", "2026-12-01T08:00", "2026-12-01T12:00")
    assert a.shift_state(datetime(2026, 12, 1, 7)) == "NOT_STARTED"
    assert a.is_within_shift(datetime(2026, 12, 1, 9))
    assert a.shift_state(datetime(2026, 12, 1, 13)) == "ENDED"
    with pytest.raises(ValidationError):
        StaffAssignment.create("US-1", "EV-1", "A", "2026-12-01T12:00", "2026-12-01T08:00")


def test_ticket_qr_unique():
    assert Ticket.issue("RG-1").qr_code_data != Ticket.issue("RG-2").qr_code_data
