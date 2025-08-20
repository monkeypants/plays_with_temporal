"""
Calendar package for personal assistant system.

This package provides calendar functionality following Clean Architecture
principles.
"""

from .activities import ScheduleOrgFileWriterActivity  # Import the class
from .domain import (
    CalendarEvent,
    CalendarEventStatus,
    Attendee,
    AttendeeResponseStatus,
    TimeBlock,
    TimeBlockType,
    TimeBlockDecision,
    Schedule,
    ScheduleStatus,
)
from .repositories import (
    CalendarChanges,
    CalendarRepository,
    ScheduleRepository,
    SyncState,
    TimeBlockClassifierRepository,
)
from .usecase import CalendarSyncUseCase, CreateScheduleUseCase
from .workflows import PublishScheduleWorkflow

__all__ = [
    # Raw calendar event models
    "CalendarEvent",
    "CalendarEventStatus",
    "Attendee",
    "AttendeeResponseStatus",
    # Core time management models
    "TimeBlock",
    "TimeBlockType",
    "TimeBlockDecision",
    "Schedule",
    "ScheduleStatus",
    # Repository protocol and related models
    "CalendarRepository",
    "ScheduleRepository",
    "SyncState",
    "CalendarChanges",
    "TimeBlockClassifierRepository",
    # Use Cases
    "CalendarSyncUseCase",
    "CreateScheduleUseCase",
    # Workflows
    "PublishScheduleWorkflow",
    # Activities (now class-based, export the class)
    "ScheduleOrgFileWriterActivity",
]
