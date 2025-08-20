"""
Mock calendar repository with realistic sample events for demonstration.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from cal.domain import (
    CalendarEvent,
    CalendarEventStatus,
    Attendee,
    AttendeeResponseStatus,
)
from cal.repositories import CalendarChanges, CalendarRepository, SyncState

logger = logging.getLogger(__name__)


class MockCalendarRepository(CalendarRepository):
    """
    Mock calendar repository that provides realistic sample events
    for demonstration purposes.
    """

    def __init__(self):
        self._sample_events = self._create_sample_events()

    def _create_sample_events(self) -> List[CalendarEvent]:
        """Create a realistic set of sample calendar events."""
        base_time = datetime.now(timezone.utc).replace(
            hour=9, minute=0, second=0, microsecond=0
        )

        events = [
            # Morning standup - should be ATTEND
            CalendarEvent(
                event_id="standup-001",
                calendar_id="work",
                title="Daily Standup",
                description="Team coordination meeting",
                start_time=base_time,
                end_time=base_time + timedelta(minutes=30),
                attendees=[
                    Attendee(
                        email="alice@company.com",
                        display_name="Alice Smith",
                        response_status=AttendeeResponseStatus.ACCEPTED,
                    ),
                    Attendee(
                        email="bob@company.com",
                        display_name="Bob Jones",
                        response_status=AttendeeResponseStatus.ACCEPTED,
                    ),
                ],
                organizer="alice@company.com",
                status=CalendarEventStatus.CONFIRMED,
                last_modified=base_time - timedelta(hours=1),
                all_day=False,
                location="",
                etag="",
            ),
            # 1:1 meeting - should be ATTEND
            CalendarEvent(
                event_id="one-on-one-001",
                calendar_id="work",
                title="1:1 with Manager",
                description="Weekly check-in",
                start_time=base_time + timedelta(hours=2),
                end_time=base_time + timedelta(hours=2, minutes=30),
                attendees=[
                    Attendee(
                        email="manager@company.com",
                        display_name="Sarah Manager",
                        response_status=AttendeeResponseStatus.ACCEPTED,
                    ),
                ],
                organizer="manager@company.com",
                status=CalendarEventStatus.CONFIRMED,
                last_modified=base_time - timedelta(hours=2),
                all_day=False,
                location="",
                etag="",
            ),
            # Large all-hands meeting - should be DELEGATE
            CalendarEvent(
                event_id="all-hands-001",
                calendar_id="work",
                title="Q4 All-Hands Meeting",
                description="Quarterly company update",
                start_time=base_time + timedelta(hours=4),
                end_time=base_time + timedelta(hours=5),
                attendees=[
                    Attendee(
                        email=f"employee{i}@company.com",
                        display_name=f"Employee {i}",
                        response_status=AttendeeResponseStatus.NEEDS_ACTION,
                    )
                    for i in range(1, 16)  # 15 attendees = large meeting
                ],
                organizer="ceo@company.com",
                status=CalendarEventStatus.CONFIRMED,
                last_modified=base_time - timedelta(days=1),
                all_day=False,
                location="",
                etag="",
            ),
            # Optional meeting - should be SKIP
            CalendarEvent(
                event_id="optional-001",
                calendar_id="work",
                title="Optional: New Tool Demo (FYI)",
                description=(
                    "Demo of new productivity tool - attendance optional"
                ),
                start_time=base_time + timedelta(hours=6),
                end_time=base_time + timedelta(hours=6, minutes=45),
                attendees=[
                    Attendee(
                        email="demo@vendor.com",
                        display_name="Demo Person",
                        response_status=AttendeeResponseStatus.ACCEPTED,
                    ),
                ],
                organizer="demo@vendor.com",
                status=CalendarEventStatus.TENTATIVE,
                last_modified=base_time - timedelta(hours=3),
                all_day=False,
                location="",
                etag="",
            ),
            # Regular meeting - should default to ATTEND
            CalendarEvent(
                event_id="project-001",
                calendar_id="work",
                title="Project Alpha Planning",
                description="Planning session for Project Alpha milestone",
                start_time=base_time + timedelta(days=1, hours=2),
                end_time=base_time + timedelta(days=1, hours=3),
                attendees=[
                    Attendee(
                        email="alice@company.com",
                        display_name="Alice Smith",
                        response_status=AttendeeResponseStatus.ACCEPTED,
                    ),
                    Attendee(
                        email="charlie@company.com",
                        display_name="Charlie Brown",
                        response_status=AttendeeResponseStatus.TENTATIVE,
                    ),
                ],
                organizer="alice@company.com",
                status=CalendarEventStatus.CONFIRMED,
                last_modified=base_time - timedelta(hours=4),
                all_day=False,
                location="",
                etag="",
            ),
        ]

        return events

    async def get_all_events(self, calendar_id: str) -> List[CalendarEvent]:
        """Return all sample events."""
        logger.info(
            f"MockCalendarRepository: Returning "
            f"{len(self._sample_events)} sample events"
        )
        return self._sample_events

    async def get_events_by_date_range(
        self, calendar_id: str, start_date: datetime, end_date: datetime
    ) -> List[CalendarEvent]:
        """Return events within the specified date range."""
        # Filter events that overlap with the date range
        filtered_events = []
        for event in self._sample_events:
            # Event overlaps if: event_start <= range_end AND
            # event_end >= range_start
            if event.start_time <= end_date and event.end_time >= start_date:
                filtered_events.append(event)

        logger.info(
            f"MockCalendarRepository: Returning {len(filtered_events)} "
            f"events in date range {start_date} to {end_date}"
        )
        return filtered_events

    async def get_events_by_date_range_multi_calendar(
        self,
        calendar_ids: List[str],
        start_date: datetime,
        end_date: datetime,
    ) -> List[CalendarEvent]:
        """Return events from multiple calendars within date range."""
        if not calendar_ids:
            return []

        # For mock repository, return same events regardless of calendar_id
        # In a real implementation, this would query different calendars
        filtered_events = await self.get_events_by_date_range(
            calendar_ids[0], start_date, end_date
        )

        logger.info(
            f"MockCalendarRepository: Returning {len(filtered_events)} "
            f"events from {len(calendar_ids)} calendars in date range"
        )
        return filtered_events

    async def get_events_by_ids(
        self, calendar_id: str, event_ids: List[str]
    ) -> List[CalendarEvent]:
        """Return events matching the provided IDs."""
        matching_events = [
            event
            for event in self._sample_events
            if event.event_id in event_ids
        ]
        logger.info(
            f"MockCalendarRepository: Found {len(matching_events)} events "
            f"for IDs: {event_ids}"
        )
        return matching_events

    async def get_changes(
        self, calendar_id: str, sync_state: Optional[SyncState]
    ) -> CalendarChanges:
        """Mock implementation - simulates file storage chunking behavior."""
        # Simulate the chunking behavior by returning a file ID and empty
        # events list
        return CalendarChanges(
            upserted_events=[],  # Empty list to simulate chunking
            upserted_events_file_id="mock-file-id-12345",  # Dummy file ID
            deleted_event_ids=[],
            new_sync_state=SyncState(sync_token="mock-sync-token"),
        )

    async def apply_changes(
        self,
        calendar_id: str,
        events_to_create: List[CalendarEvent],
        events_to_update: List[CalendarEvent],
        event_ids_to_delete: List[str],
    ) -> None:
        """Mock implementation - no-op."""
        logger.info("MockCalendarRepository: apply_changes called (no-op)")

    async def get_sync_state(
        self, for_calendar_id: str
    ) -> Optional[SyncState]:
        """Mock implementation - returns None."""
        return None

    async def store_sync_state(
        self, for_calendar_id: str, sync_state: SyncState
    ) -> None:
        """Mock implementation - no-op."""
        logger.info("MockCalendarRepository: store_sync_state called (no-op)")
