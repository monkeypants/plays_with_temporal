"""
Workflow-specific proxy for Google Calendar CalendarRepository.
This class is used *inside* Temporal workflows to call activities.
It ensures workflow determinism by delegating all non-deterministic
operations to activities.
"""

import logging
from datetime import datetime
from typing import List, Optional

from temporalio import workflow

from cal.domain import CalendarEvent
from cal.repositories import CalendarRepository, CalendarChanges, SyncState

logger = logging.getLogger(__name__)


class WorkflowGoogleCalendarRepositoryProxy(CalendarRepository):
    """
    Workflow implementation of CalendarRepository that calls Google Calendar
    activities. This proxy ensures that all interactions with the Google
    CalendarRepository are performed via Temporal activities, maintaining
    workflow determinism.
    """

    def __init__(self):
        self.activity_timeout = workflow.timedelta(
            seconds=60
        )  # Longer timeout for API calls
        logger.debug("Initialized WorkflowGoogleCalendarRepositoryProxy")

    async def get_changes(
        self, calendar_id: str, sync_state: Optional[SyncState]
    ) -> CalendarChanges:
        """Get changes by executing an activity."""
        logger.debug(
            "Workflow: Calling google get_changes activity",
            extra={"calendar_id": calendar_id},
        )
        raw_result = await workflow.execute_activity(
            "cal.calendar_sync.source_repo.google.get_changes",
            (calendar_id, sync_state),
            start_to_close_timeout=self.activity_timeout,
        )
        result = CalendarChanges.model_validate(raw_result)
        logger.debug(
            "Workflow: google get_changes activity completed",
            extra={
                "calendar_id": calendar_id,
                "upserted_count": len(result.upserted_events),
                "deleted_count": len(result.deleted_event_ids),
            },
        )
        return result

    async def get_events_by_ids(
        self, calendar_id: str, event_ids: List[str]
    ) -> List[CalendarEvent]:
        """Get events by IDs by executing an activity."""
        logger.debug(
            "Workflow: Calling google get_events_by_ids activity",
            extra={"calendar_id": calendar_id, "event_ids": event_ids},
        )
        raw_result = await workflow.execute_activity(
            "cal.create_schedule.calendar_repo.google.get_events_by_ids",
            (calendar_id, event_ids),
            start_to_close_timeout=self.activity_timeout,
        )
        result = [CalendarEvent.model_validate(event) for event in raw_result]
        logger.debug(
            "Workflow: google get_events_by_ids activity completed",
            extra={
                "calendar_id": calendar_id,
                "event_count": len(result),
            },
        )
        return result

    async def get_all_events(self, calendar_id: str) -> List[CalendarEvent]:
        """Get all events by executing an activity."""
        logger.debug(
            "Workflow: Calling google get_all_events activity",
            extra={"calendar_id": calendar_id},
        )
        raw_result = await workflow.execute_activity(
            "cal.create_schedule.calendar_repo.google.get_all_events",
            calendar_id,
            start_to_close_timeout=self.activity_timeout,
        )
        result = [CalendarEvent.model_validate(event) for event in raw_result]
        logger.debug(
            "Workflow: google get_all_events activity completed",
            extra={
                "calendar_id": calendar_id,
                "event_count": len(result),
            },
        )
        return result

    async def apply_changes(
        self,
        calendar_id: str,
        events_to_create: List[CalendarEvent],
        events_to_update: List[CalendarEvent],
        event_ids_to_delete: List[str],
    ) -> None:
        """Apply changes by executing an activity."""
        raise NotImplementedError(
            "Google Calendar is a source repository and does not support "
            "apply_changes"
        )

    async def get_sync_state(
        self, for_calendar_id: str
    ) -> Optional[SyncState]:
        """Get sync state by executing an activity."""
        raise NotImplementedError(
            "Google Calendar is a source repository and does not support "
            "get_sync_state"
        )

    async def store_sync_state(
        self, for_calendar_id: str, sync_state: SyncState
    ) -> None:
        """Store sync state by executing an activity."""
        raise NotImplementedError(
            "Google Calendar is a source repository and does not support "
            "store_sync_state"
        )

    async def get_events_by_date_range(
        self, calendar_id: str, start_date: datetime, end_date: datetime
    ) -> List[CalendarEvent]:
        """Get events by date range by executing an activity."""
        logger.debug(
            "Workflow: Calling google get_events_by_date_range activity",
            extra={"calendar_id": calendar_id},
        )
        raw_result = await workflow.execute_activity(
            "cal.create_schedule.calendar_repo.google.get_events_by_date_range",
            (calendar_id, start_date, end_date),
            start_to_close_timeout=self.activity_timeout,
        )
        result = [CalendarEvent.model_validate(event) for event in raw_result]
        logger.debug(
            "Workflow: google get_events_by_date_range activity completed",
            extra={
                "calendar_id": calendar_id,
                "event_count": len(result),
            },
        )
        return result

    async def get_events_by_date_range_multi_calendar(
        self,
        calendar_ids: List[str],
        start_date: datetime,
        end_date: datetime,
    ) -> List[CalendarEvent]:
        """Get events from multiple calendars by date range by executing an
        activity."""
        logger.debug(
            "Workflow: Calling google "
            "get_events_by_date_range_multi_calendar activity",
            extra={"calendar_ids": calendar_ids},
        )
        raw_result = await workflow.execute_activity(
            "cal.create_schedule.calendar_repo.google.get_events_by_date_range_multi_calendar",
            (calendar_ids, start_date, end_date),
            start_to_close_timeout=self.activity_timeout,
        )
        result = [CalendarEvent.model_validate(event) for event in raw_result]
        logger.debug(
            "Workflow: google get_events_by_date_range_multi_calendar "
            "activity completed",
            extra={
                "calendar_ids": calendar_ids,
                "event_count": len(result),
            },
        )
        return result
