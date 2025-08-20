"""
Test object factories for calendar domain models.

These factories provide minimal test objects with sensible defaults and easy
customization for specific test scenarios, following the successful pattern
from CLI tests.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

from cal.domain import (
    CalendarEvent,
    CalendarEventStatus,
    Attendee,
    AttendeeResponseStatus,
    TimeBlock,
    TimeBlockType,
    TimeBlockDecision,
    ExecutiveDecision,
    Schedule,
    ScheduleStatus,
)


def minimal_calendar_event(
    event_id: str = "test-event-1",
    calendar_id: str = "test-calendar",
    title: str = "Test Event",
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    status: CalendarEventStatus = CalendarEventStatus.CONFIRMED,
    attendees: Optional[List[Attendee]] = None,
    organizer: Optional[str] = None,
    description: Optional[str] = None,
    location: Optional[str] = None,
    all_day: bool = False,
    last_modified: Optional[datetime] = None,
    etag: Optional[str] = None,
) -> CalendarEvent:
    """
    Create a minimal CalendarEvent with sensible defaults.

    Args:
        event_id: Unique identifier for the event
        calendar_id: Calendar containing the event
        title: Event title
        start_time: Event start time (defaults to now)
        end_time: Event end time (defaults to start_time + 1 hour)
        status: Event status
        attendees: List of attendees (defaults to empty list)
        organizer: Event organizer email
        description: Event description
        location: Event location
        all_day: Whether this is an all-day event
        last_modified: Last modification time (defaults to start_time)
        etag: ETag for change detection

    Returns:
        CalendarEvent with specified or default values
    """
    if start_time is None:
        start_time = datetime.now(timezone.utc).replace(
            hour=9, minute=0, second=0, microsecond=0
        )

    if end_time is None:
        end_time = start_time + timedelta(hours=1)

    if last_modified is None:
        last_modified = start_time

    if attendees is None:
        attendees = []

    return CalendarEvent(
        event_id=event_id,
        calendar_id=calendar_id,
        title=title,
        description=description,
        start_time=start_time,
        end_time=end_time,
        all_day=all_day,
        location=location,
        status=status,
        attendees=attendees,
        organizer=organizer,
        last_modified=last_modified,
        etag=etag,
    )


def minimal_attendee(
    email: str = "attendee@example.com",
    display_name: Optional[str] = "Test Attendee",
    response_status: AttendeeResponseStatus = (
        AttendeeResponseStatus.NEEDS_ACTION
    ),
) -> Attendee:
    """
    Create a minimal Attendee with sensible defaults.

    Args:
        email: Attendee email address
        display_name: Attendee display name
        response_status: Attendee's response status

    Returns:
        Attendee with specified or default values
    """
    return Attendee(
        email=email,
        display_name=display_name,
        response_status=response_status,
    )


def minimal_time_block(
    time_block_id: str = "test-block-1",
    title: str = "Test Time Block",
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    type: TimeBlockType = TimeBlockType.MEETING,
    suggested_decision: Optional[
        ExecutiveDecision
    ] = ExecutiveDecision.ATTEND,
    decision_reason: Optional[str] = "Test reason",
    decision: TimeBlockDecision = TimeBlockDecision.PENDING_REVIEW,
    source_calendar_event_id: Optional[str] = None,
    meeting_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    created_at: Optional[datetime] = None,
    last_updated_at: Optional[datetime] = None,
) -> TimeBlock:
    """
    Create a minimal TimeBlock with sensible defaults.

    Args:
        time_block_id: Unique identifier for the time block
        title: Time block title
        start_time: Start time (defaults to now)
        end_time: End time (defaults to start_time + 1 hour)
        type: Time block type
        suggested_decision: AI-suggested decision
        decision_reason: Reason for the suggested decision
        decision: Executive's decision
        source_calendar_event_id: Link to source calendar event
        meeting_id: Link to meeting domain object
        metadata: Additional metadata
        created_at: Creation timestamp
        last_updated_at: Last update timestamp

    Returns:
        TimeBlock with specified or default values
    """
    if start_time is None:
        start_time = datetime.now(timezone.utc).replace(
            hour=9, minute=0, second=0, microsecond=0
        )

    if end_time is None:
        end_time = start_time + timedelta(hours=1)

    if metadata is None:
        metadata = {}

    return TimeBlock(
        time_block_id=time_block_id,
        title=title,
        start_time=start_time,
        end_time=end_time,
        type=type,
        suggested_decision=suggested_decision,
        decision_reason=decision_reason,
        decision=decision,
        decision_notes=None,
        delegated_to=None,
        source_calendar_event_id=source_calendar_event_id,
        meeting_id=meeting_id,
        metadata=metadata,
        created_at=created_at,
        last_updated_at=last_updated_at,
    )


def minimal_schedule(
    schedule_id: str = "test-schedule-1",
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    time_blocks: Optional[List[TimeBlock]] = None,
    status: ScheduleStatus = ScheduleStatus.DRAFT,
    created_at: Optional[datetime] = None,
    last_updated_at: Optional[datetime] = None,
) -> Schedule:
    """
    Create a minimal Schedule with sensible defaults.

    Args:
        schedule_id: Unique identifier for the schedule
        start_date: Schedule start date (defaults to today)
        end_date: Schedule end date (defaults to end of start_date)
        time_blocks: List of time blocks (defaults to empty list)
        status: Schedule status
        created_at: Creation timestamp
        last_updated_at: Last update timestamp

    Returns:
        Schedule with specified or default values
    """
    if start_date is None:
        start_date = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

    if end_date is None:
        end_date = start_date.replace(
            hour=23, minute=59, second=59, microsecond=999999
        )

    if time_blocks is None:
        time_blocks = []

    return Schedule(
        schedule_id=schedule_id,
        start_date=start_date,
        end_date=end_date,
        time_blocks=time_blocks,
        status=status,
        created_at=created_at,
        last_updated_at=last_updated_at,
    )


# Convenience functions for common test scenarios


def create_meeting_event(
    title: str = "Team Meeting",
    attendee_count: int = 3,
    organizer: str = "organizer@example.com",
    **kwargs: Any,
) -> CalendarEvent:
    """Create a calendar event that looks like a typical meeting."""
    attendees = [
        minimal_attendee(
            email=f"attendee{i}@example.com",
            display_name=f"Attendee {i}",
            response_status=AttendeeResponseStatus.ACCEPTED,
        )
        for i in range(1, attendee_count + 1)
    ]

    return minimal_calendar_event(
        title=title,
        attendees=attendees,
        organizer=organizer,
        location="Conference Room A",
        **kwargs,
    )


def create_large_meeting_event(
    title: str = "All-Hands Meeting", attendee_count: int = 15, **kwargs: Any
) -> CalendarEvent:
    """Create a calendar event with many attendees (suitable for DELEGATE
    triage)."""
    return create_meeting_event(
        title=title, attendee_count=attendee_count, **kwargs
    )


def create_optional_event(
    title: str = "Optional: Training Session (FYI)", **kwargs: Any
) -> CalendarEvent:
    """Create a calendar event that should be triaged as SKIP."""
    return minimal_calendar_event(
        title=title, status=CalendarEventStatus.TENTATIVE, **kwargs
    )


def create_one_on_one_event(
    title: str = "1:1 with Manager", **kwargs: Any
) -> CalendarEvent:
    """Create a calendar event that should be triaged as ATTEND."""
    return create_meeting_event(
        title=title,
        attendee_count=1,
        organizer="manager@example.com",
        **kwargs,
    )
