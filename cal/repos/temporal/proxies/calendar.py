"""
Workflow-specific proxy for MockCalendarRepository.
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


class WorkflowMockCalendarRepositoryProxy(CalendarRepository):
    """
    Workflow implementation of CalendarRepository that calls mock activities.
    This proxy ensures that all interactions with the MockCalendarRepository
    are performed via Temporal activities, maintaining workflow determinism.
    """

    def __init__(self):
        self.activity_timeout = workflow.timedelta(seconds=10)
        logger.debug("Initialized WorkflowMockCalendarRepositoryProxy")

    async def get_changes(
        self, calendar_id: str, sync_state: Optional[SyncState]
    ) -> CalendarChanges:
        """Get changes by executing an activity."""
        logger.debug(
            "Workflow: Calling mock get_changes activity",
            extra={"calendar_id": calendar_id},
        )
        raw_result = await workflow.execute_activity(
            "cal.calendar_sync.source_repo.mock.get_changes",
            (calendar_id, sync_state),
            start_to_close_timeout=self.activity_timeout,
        )
        result = CalendarChanges.model_validate(raw_result)
        logger.debug(
            "Workflow: mock get_changes activity completed",
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
            "Workflow: Calling mock get_events_by_ids activity",
            extra={"calendar_id": calendar_id, "event_ids": event_ids},
        )
        raw_result = await workflow.execute_activity(
            "cal.create_schedule.calendar_repo.mock.get_events_by_ids",
            (calendar_id, event_ids),
            start_to_close_timeout=self.activity_timeout,
        )
        result = [CalendarEvent.model_validate(event) for event in raw_result]
        logger.debug(
            "Workflow: mock get_events_by_ids activity completed",
            extra={
                "calendar_id": calendar_id,
                "event_count": len(result),
            },
        )
        return result

    async def get_all_events(self, calendar_id: str) -> List[CalendarEvent]:
        """Get all events by executing an activity."""
        logger.debug(
            "Workflow: Calling mock get_all_events activity",
            extra={"calendar_id": calendar_id},
        )
        raw_result = await workflow.execute_activity(
            "cal.create_schedule.calendar_repo.mock.get_all_events",
            calendar_id,
            start_to_close_timeout=self.activity_timeout,
        )
        result = [CalendarEvent.model_validate(event) for event in raw_result]
        logger.debug(
            "Workflow: mock get_all_events activity completed",
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
        logger.debug(
            "Workflow: Calling mock apply_changes activity",
            extra={
                "calendar_id": calendar_id,
                "create_count": len(events_to_create),
                "update_count": len(events_to_update),
                "delete_count": len(event_ids_to_delete),
            },
        )
        await workflow.execute_activity(
            "cal.calendar_sync.sink_repo.mock.apply_changes",
            (
                calendar_id,
                events_to_create,
                events_to_update,
                event_ids_to_delete,
            ),
            start_to_close_timeout=self.activity_timeout,
        )
        logger.debug(
            "Workflow: mock apply_changes activity completed",
            extra={"calendar_id": calendar_id},
        )

    async def get_sync_state(
        self, for_calendar_id: str
    ) -> Optional[SyncState]:
        """Get sync state by executing an activity."""
        logger.debug(
            "Workflow: Calling mock get_sync_state activity",
            extra={"for_calendar_id": for_calendar_id},
        )
        raw_result = await workflow.execute_activity(
            "cal.calendar_sync.sink_repo.mock.get_sync_state",
            for_calendar_id,
            start_to_close_timeout=self.activity_timeout,
        )
        result = SyncState.model_validate(raw_result) if raw_result else None
        logger.debug(
            "Workflow: mock get_sync_state activity completed",
            extra={
                "for_calendar_id": for_calendar_id,
                "found": result is not None,
            },
        )
        return result

    async def store_sync_state(
        self, for_calendar_id: str, sync_state: SyncState
    ) -> None:
        """Store sync state by executing an activity."""
        logger.debug(
            "Workflow: Calling mock store_sync_state activity",
            extra={"for_calendar_id": for_calendar_id},
        )
        await workflow.execute_activity(
            "cal.calendar_sync.sink_repo.mock.store_sync_state",
            (for_calendar_id, sync_state),
            start_to_close_timeout=self.activity_timeout,
        )
        logger.debug(
            "Workflow: mock store_sync_state activity completed",
            extra={"for_calendar_id": for_calendar_id},
        )

    async def get_events_by_date_range(
        self, calendar_id: str, start_date: datetime, end_date: datetime
    ) -> List[CalendarEvent]:
        """Get events by date range by executing an activity."""
        logger.debug(
            "Workflow: Calling mock get_events_by_date_range activity",
            extra={"calendar_id": calendar_id},
        )
        raw_result = await workflow.execute_activity(
            "cal.create_schedule.calendar_repo.mock.get_events_by_date_range",
            (calendar_id, start_date, end_date),
            start_to_close_timeout=self.activity_timeout,
        )
        result = [CalendarEvent.model_validate(event) for event in raw_result]
        logger.debug(
            "Workflow: mock get_events_by_date_range activity completed",
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
            "Workflow: Calling mock get_events_by_date_range_multi_calendar "
            "activity",
            extra={"calendar_ids": calendar_ids},
        )
        raw_result = await workflow.execute_activity(
            "cal.create_schedule.calendar_repo.mock.get_events_by_date_range_multi_calendar",
            (calendar_ids, start_date, end_date),
            start_to_close_timeout=self.activity_timeout,
        )
        result = [CalendarEvent.model_validate(event) for event in raw_result]
        logger.debug(
            "Workflow: mock get_events_by_date_range_multi_calendar activity "
            "completed",
            extra={
                "calendar_ids": calendar_ids,
                "event_count": len(result),
            },
        )
        return result
