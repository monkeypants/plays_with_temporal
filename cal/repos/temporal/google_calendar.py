"""
Temporal Activity implementation of CalendarRepository for Google Calendar.
Delegates calls to a concrete GoogleCalendarRepository instance.
"""

import json
import logging
from datetime import datetime
from typing import List, Optional

from temporalio import activity

from cal.domain import CalendarEvent
from cal.repositories import CalendarRepository, CalendarChanges, SyncState
from cal.repos.google.calendar import GoogleCalendarRepository
from util.repositories import FileStorageRepository
from util.domain import FileUploadArgs

logger = logging.getLogger(__name__)


class TemporalGoogleCalendarRepository(CalendarRepository):
    """
    Temporal Activity implementation of CalendarRepository for Google
    Calendar. Delegates calls to a concrete GoogleCalendarRepository instance.

    This follows the three-layer repository pattern:
    1. Pure Backend (GoogleCalendarRepository)
    2. Temporal Activity (TemporalGoogleCalendarRepository) - this class
    3. Workflow Proxy (WorkflowGoogleCalendarRepositoryProxy)
    """

    def __init__(
        self,
        google_repo: GoogleCalendarRepository,
        file_storage_repo: FileStorageRepository,
    ):
        """
        Initialize with a concrete GoogleCalendarRepository implementation.

        Args:
            google_repo: The concrete repository to delegate calls to
            file_storage_repo: The file storage repository for large payloads
        """
        self._google_repo = google_repo
        self._file_storage_repo = file_storage_repo
        logger.info(
            "TemporalGoogleCalendarRepository initialized with %s and %s",
            google_repo.__class__.__name__,
            file_storage_repo.__class__.__name__,
        )

    @activity.defn(name="cal.calendar_sync.source_repo.google.get_changes")
    async def get_changes(
        self, calendar_id: str, sync_state: Optional[SyncState]
    ) -> CalendarChanges:
        """Activity to get changes from Google Calendar."""
        logger.info(
            "Activity: Getting changes from Google Calendar",
            extra={"calendar_id": calendar_id},
        )

        # Get raw changes from Google Calendar
        raw_changes = await self._google_repo.get_changes(
            calendar_id, sync_state
        )

        # Unconditionally upload events to file storage
        if raw_changes.upserted_events:
            # Generate unique file ID
            import uuid

            file_id = f"calendar-events-{calendar_id}-{uuid.uuid4()}"

            # Serialize events to JSON
            events_json = json.dumps(
                [
                    event.model_dump(mode="json")
                    for event in raw_changes.upserted_events
                ]
            )

            # Upload to file storage
            upload_args = FileUploadArgs(
                file_id=file_id,
                filename=file_id,
                data=events_json.encode("utf-8"),
                content_type="application/json",
            )

            await self._file_storage_repo.upload_file(upload_args)

            logger.info(
                "Uploaded events to file storage",
                extra={
                    "calendar_id": calendar_id,
                    "file_id": file_id,
                    "event_count": len(raw_changes.upserted_events),
                },
            )

            # Return CalendarChanges with file reference
            return CalendarChanges(
                upserted_events=[],  # Empty list
                upserted_events_file_id=file_id,
                deleted_event_ids=raw_changes.deleted_event_ids,
                new_sync_state=raw_changes.new_sync_state,
            )
        else:
            # No events to upload, return as-is
            return raw_changes

    @activity.defn(
        name="cal.create_schedule.calendar_repo.google.get_events_by_ids"
    )
    async def get_events_by_ids(
        self, calendar_id: str, event_ids: List[str]
    ) -> List[CalendarEvent]:
        """Activity to get events by IDs from Google Calendar."""
        logger.info(
            "Activity: Getting events by IDs from Google Calendar",
            extra={"calendar_id": calendar_id, "event_count": len(event_ids)},
        )
        return await self._google_repo.get_events_by_ids(
            calendar_id, event_ids
        )

    @activity.defn(
        name="cal.create_schedule.calendar_repo.google.get_all_events"
    )
    async def get_all_events(self, calendar_id: str) -> List[CalendarEvent]:
        """Activity to get all events from Google Calendar."""
        logger.info(
            "Activity: Getting all events from Google Calendar",
            extra={"calendar_id": calendar_id},
        )
        return await self._google_repo.get_all_events(calendar_id)

    @activity.defn(
        name="cal.create_schedule.calendar_repo.google.get_events_by_date_range"
    )
    async def get_events_by_date_range(
        self, calendar_id: str, start_date: datetime, end_date: datetime
    ) -> List[CalendarEvent]:
        """Activity to get events by date range from Google Calendar."""
        logger.info(
            "Activity: Getting events by date range from Google Calendar",
            extra={"calendar_id": calendar_id},
        )
        return await self._google_repo.get_events_by_date_range(
            calendar_id, start_date, end_date
        )

    @activity.defn(
        name="cal.create_schedule.calendar_repo.google.get_events_by_date_range_multi_calendar"
    )
    async def get_events_by_date_range_multi_calendar(
        self,
        calendar_ids: List[str],
        start_date: datetime,
        end_date: datetime,
    ) -> List[CalendarEvent]:
        """Activity to get events from multiple calendars by date range from
        Google Calendar."""
        logger.info(
            "Activity: Getting events from multiple calendars by date range "
            "from Google Calendar",
            extra={"calendar_ids": calendar_ids},
        )
        return (
            await self._google_repo.get_events_by_date_range_multi_calendar(
                calendar_ids, start_date, end_date
            )
        )

    async def apply_changes(
        self,
        calendar_id: str,
        events_to_create: List[CalendarEvent],
        events_to_update: List[CalendarEvent],
        event_ids_to_delete: List[str],
    ) -> None:
        """Google Calendar is a source repository and does not support
        apply_changes."""
        raise NotImplementedError(
            "Google Calendar is a source repository and does not support "
            "apply_changes"
        )

    async def get_sync_state(
        self, for_calendar_id: str
    ) -> Optional[SyncState]:
        """Google Calendar is a source repository and does not support
        get_sync_state."""
        raise NotImplementedError(
            "Google Calendar is a source repository and does not support "
            "get_sync_state"
        )

    async def store_sync_state(
        self, for_calendar_id: str, sync_state: SyncState
    ) -> None:
        """Google Calendar is a source repository and does not support
        store_sync_state."""
        raise NotImplementedError(
            "Google Calendar is a source repository and does not support "
            "store_sync_state"
        )
