"""Tầng domain – các lớp OOP theo tài liệu thiết kế."""
from .check_in_result import CheckInResult
from .enums import (CheckInMethod, CheckInOutcome, CheckInStatus, EmailStatus, EventStatus, Role, StaffStatus)
from .event import Event
from .registration import Registration
from .staff_assignment import StaffAssignment
from .ticket import Ticket
from .ticket_category import TicketCategory
from .user import Administrator, Attendee, EventStaff, User

__all__ = [
    "User", "Administrator", "EventStaff", "Attendee",
    "Event", "TicketCategory", "Registration", "Ticket", "StaffAssignment", "CheckInResult",
    "Role", "StaffStatus", "EventStatus", "CheckInStatus", "CheckInOutcome", "CheckInMethod", "EmailStatus",
]
