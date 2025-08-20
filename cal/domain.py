"""
Calendar domain models for personal assistant system.

These models represent calendar events and related data structures,
following the established Pydantic v2 patterns from the POC implementation.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from enum import Enum
import logging
import zoneinfo

logger = logging.getLogger(__name__)


# --- Multi-Calendar Support Models ---


class CalendarSource(BaseModel):
    """Represents a source calendar configuration."""

    calendar_id: str = Field(
        ..., description="Unique identifier for the calendar"
    )
    display_name: str = Field(
        ..., description="Human-readable name for the calendar"
    )
    source_type: str = Field(
        ..., description="Type of calendar source (e.g., 'google', 'outlook')"
    )
    enabled: bool = Field(
        True, description="Whether this calendar should be synced"
    )
    sync_priority: int = Field(
        1, description="Priority for sync operations (1=highest)"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional calendar-specific configuration",
    )


class CalendarCollection(BaseModel):
    """Represents a collection of calendars that should be queried
    together."""

    collection_id: str = Field(
        ..., description="Unique identifier for the collection"
    )
    display_name: str = Field(
        ..., description="Human-readable name for the collection"
    )
    calendar_sources: List[CalendarSource] = Field(
        ..., description="List of calendars in this collection"
    )
    default_calendar_id: Optional[str] = Field(
        None, description="Default calendar for new events"
    )

    @field_validator("calendar_sources")
    @classmethod
    def collection_must_have_calendars(cls, v: List[CalendarSource]) -> List[CalendarSource]:
        if not v:
            raise ValueError(
                "Calendar collection must contain at least one calendar"
            )
        return v


# --- Enums for Calendar and Time Management ---


class CalendarEventStatus(str, Enum):
    """Status of a calendar event as reported by the source calendar."""

    CONFIRMED = "confirmed"
    TENTATIVE = "tentative"
    CANCELLED = "cancelled"


class AttendeeResponseStatus(str, Enum):
    """Attendee's response status for an event."""

    NEEDS_ACTION = "needsAction"
    DECLINED = "declined"
    TENTATIVE = "tentative"
    ACCEPTED = "accepted"


class TimeBlockType(str, Enum):
    """Classification of a time block on the executive's schedule."""

    MEETING = "meeting"
    FOCUS_SESSION = "focus_session"
    PERSONAL = "personal"
    TRAVEL = "travel"


class ExecutiveDecision(str, Enum):
    """AI-suggested decision for a time block, representing the recommended
    action for the executive to take.
    """

    ATTEND = "attend"
    RESCHEDULE = "reschedule"
    DELEGATE = "delegate"
    SKIP = "skip"


class TimeBlockDecision(str, Enum):
    """The executive's decision regarding a proposed time block,
    especially for meetings.
    """

    PENDING_REVIEW = "pending_review"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    DELEGATED = "delegated"
    RESCHEDULE = "reschedule"


class ScheduleStatus(str, Enum):
    """The status of a planned schedule for a given period (e.g., day,
    week).
    """

    DRAFT = "draft"
    FINALIZED = "finalized"
    IN_PROGRESS = "in_progress"


# --- Core Domain Models ---


class Attendee(BaseModel):
    """Represents a single event attendee with their response status."""

    email: str
    display_name: Optional[str] = None
    response_status: AttendeeResponseStatus = Field(
        AttendeeResponseStatus.NEEDS_ACTION
    )


class CalendarEvent(BaseModel):
    """
    Represents the raw, external state of an event from a source calendar.
    This model is a snapshot of a single scheduling attempt in time.
    """

    event_id: str = Field(
        ..., description="Unique identifier for the event from the source"
    )
    calendar_id: str = Field(
        ..., description="Identifier of the source calendar"
    )
    title: str = Field(..., description="Event title/summary")
    description: Optional[str] = Field(
        None, description="Event description/notes"
    )

    start_time: datetime = Field(..., description="Event start time")
    end_time: datetime = Field(..., description="Event end time")
    all_day: bool = Field(
        False, description="Whether this is an all-day event"
    )

    location: Optional[str] = Field(None, description="Event location")
    status: CalendarEventStatus = Field(
        CalendarEventStatus.CONFIRMED, description="Event status from source"
    )

    attendees: List[Attendee] = Field(
        default_factory=list, description="List of attendees and their status"
    )
    organizer: Optional[str] = Field(
        None, description="Event organizer email"
    )

    last_modified: datetime = Field(
        ..., description="Last modification timestamp from source"
    )
    etag: Optional[str] = Field(
        None, description="ETag for change detection from source"
    )

    @field_validator("start_time", "end_time", "last_modified")
    @classmethod
    def ensure_timezone_aware(cls, v: datetime) -> datetime:
        """Ensure datetime fields are timezone-aware."""
        if v.tzinfo is None:
            logger.warning(
                f"Converting naive datetime {v} to UTC for MVP evaluation"
            )
            return v.replace(tzinfo=zoneinfo.ZoneInfo("UTC"))
        return v

    @field_validator("end_time")
    @classmethod
    def end_time_after_start_time(cls, v: datetime, info: Any) -> datetime:
        """Ensure end time is after start time."""
        if "start_time" in info.data and v <= info.data["start_time"]:
            logger.warning(
                f"Invalid time range detected, adjusting end time from {v} "
                f"to 1 hour after start"
            )
            start_time: datetime = info.data["start_time"]
            return start_time + timedelta(hours=1)
        return v

    @field_validator("title")
    @classmethod
    def strip_title(cls, v: str) -> str:
        """Strip whitespace from title."""
        return v.strip()


class TimeBlock(BaseModel):
    """
    Represents a block of time in the executive's schedule. This is the core
    internal entity for time management and planning. It can be created from a
    CalendarEvent or manually.
    """

    time_block_id: str
    title: str
    start_time: datetime
    end_time: datetime
    type: TimeBlockType

    # Planning and decision-making fields
    suggested_decision: Optional[ExecutiveDecision] = Field(
        None, description="AI-suggested decision for this time block."
    )
    decision_reason: Optional[str] = Field(
        None, description="AI-generated reason for the suggested decision."
    )
    decision: TimeBlockDecision = Field(TimeBlockDecision.PENDING_REVIEW)
    decision_notes: Optional[str] = Field(
        None, description="Rationale for the decision."
    )
    delegated_to: Optional[str] = Field(
        None, description="Email of person to whom the block was delegated."
    )

    # Link to source and other domains
    source_calendar_event_id: Optional[str] = Field(
        None, description="Link to the raw CalendarEvent if applicable."
    )
    meeting_id: Optional[str] = Field(
        None,
        description=(
            "Link to a detailed meeting object in the meeting domain."
        ),
    )

    # Flexible metadata for presentation and context
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Flexible metadata for storing additional context and "
            "presentation information."
        ),
    )

    created_at: Optional[datetime] = None
    last_updated_at: Optional[datetime] = None


class Schedule(BaseModel):
    """
    Represents a planned schedule for a specific period, e.g., a day or week.
    It is composed of multiple TimeBlocks.
    """

    schedule_id: str
    start_date: datetime
    end_date: datetime
    time_blocks: List[TimeBlock] = Field(default_factory=list)
    status: ScheduleStatus = Field(ScheduleStatus.DRAFT)

    created_at: Optional[datetime] = None
    last_updated_at: Optional[datetime] = None
