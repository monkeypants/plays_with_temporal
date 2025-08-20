"""
Temporal Activity implementation of CalendarRepository.
Delegates calls to a concrete PostgreSQLCalendarRepository instance.
"""

import logging
from datetime import datetime
from typing import List, Optional

from temporalio import activity

from cal.domain import CalendarEvent
from cal.repositories import CalendarRepository, CalendarChanges, SyncState
from cal.repos.postgresql.calendar import PostgreSQLCalendarRepository

logger = logging.getLogger(__name__)


class TemporalPostgreSQLCalendarRepository(CalendarRepository):
    """
    Temporal Activity implementation of CalendarRepository.
    Delegates calls to a concrete PostgreSQLCalendarRepository instance.

    This follows the three-layer repository pattern:
    1. Pure Backend (PostgreSQLCalendarRepository)
    2. Temporal Activity (TemporalPostgreSQLCalendarRepository) - this class
    3. Workflow Proxy (WorkflowCalendarRepositoryProxy)
    """

    def __init__(self, postgresql_repo: PostgreSQLCalendarRepository):
        """
        Initialize with a concrete PostgreSQLCalendarRepository
        implementation.

        Args:
            postgresql_repo: The concrete repository to delegate calls to
        """
        self._postgresql_repo = postgresql_repo
        logger.info(
            "TemporalPostgreSQLCalendarRepository initialized with %s",
            postgresql_repo.__class__.__name__,
        )

    @activity.defn(name="cal.calendar_sync.sink_repo.postgresql.get_changes")
    async def get_changes(
        self, calendar_id: str, sync_state: Optional[SyncState]
    ) -> CalendarChanges:
        """Activity to get changes from a calendar."""
        logger.info(
            "Activity: Getting changes from calendar",
            extra={"calendar_id": calendar_id},
        )
        return await self._postgresql_repo.get_changes(
            calendar_id, sync_state
        )

    @activity.defn(
        name="cal.create_schedule.calendar_repo.postgresql.get_events_by_ids"
    )
    async def get_events_by_ids(
        self, calendar_id: str, event_ids: List[str]
    ) -> List[CalendarEvent]:
        """Activity to get events by IDs."""
        logger.info(
            "Activity: Getting events by IDs",
            extra={"calendar_id": calendar_id, "event_count": len(event_ids)},
        )
        return await self._postgresql_repo.get_events_by_ids(
            calendar_id, event_ids
        )

    @activity.defn(
        name="cal.create_schedule.calendar_repo.postgresql.get_all_events"
    )
    async def get_all_events(self, calendar_id: str) -> List[CalendarEvent]:
        """Activity to get all events from a calendar."""
        logger.info(
            "Activity: Getting all events",
            extra={"calendar_id": calendar_id},
        )
        return await self._postgresql_repo.get_all_events(calendar_id)

    @activity.defn(
        name="cal.create_schedule.calendar_repo.postgresql.get_events_by_date_range"
    )
    async def get_events_by_date_range(
        self, calendar_id: str, start_date: datetime, end_date: datetime
    ) -> List[CalendarEvent]:
        """Activity to get events by date range."""
        logger.info(
            "Activity: Getting events by date range",
            extra={"calendar_id": calendar_id},
        )
        return await self._postgresql_repo.get_events_by_date_range(
            calendar_id, start_date, end_date
        )

    @activity.defn(
        name="cal.create_schedule.calendar_repo.postgresql.get_events_by_date_range_multi_calendar"
    )
    async def get_events_by_date_range_multi_calendar(
        self,
        calendar_ids: List[str],
        start_date: datetime,
        end_date: datetime,
    ) -> List[CalendarEvent]:
        """Activity to get events from multiple calendars by date range."""
        logger.info(
            "Activity: Getting events from multiple calendars by date range",
            extra={"calendar_ids": calendar_ids},
        )
        return await self._postgresql_repo.get_events_by_date_range_multi_calendar(  # noqa: E501
            calendar_ids, start_date, end_date
        )

    @activity.defn(
        name="cal.calendar_sync.sink_repo.postgresql.apply_changes"
    )
    async def apply_changes(
        self,
        calendar_id: str,
        events_to_create: List[CalendarEvent],
        events_to_update: List[CalendarEvent],
        event_ids_to_delete: List[str],
    ) -> None:
        """Activity to apply changes to a calendar."""
        logger.info(
            "Activity: Applying changes to calendar",
            extra={
                "calendar_id": calendar_id,
                "create_count": len(events_to_create),
                "update_count": len(events_to_update),
                "delete_count": len(event_ids_to_delete),
            },
        )
        await self._postgresql_repo.apply_changes(
            calendar_id,
            events_to_create,
            events_to_update,
            event_ids_to_delete,
        )

    @activity.defn(
        name="cal.calendar_sync.sink_repo.postgresql.get_sync_state"
    )
    async def get_sync_state(
        self, for_calendar_id: str
    ) -> Optional[SyncState]:
        """Activity to get sync state for a calendar."""
        logger.info(
            "Activity: Getting sync state",
            extra={"for_calendar_id": for_calendar_id},
        )
        return await self._postgresql_repo.get_sync_state(for_calendar_id)

    @activity.defn(
        name="cal.calendar_sync.sink_repo.postgresql.store_sync_state"
    )
    async def store_sync_state(
        self, for_calendar_id: str, sync_state: SyncState
    ) -> None:
        """Activity to store sync state for a calendar."""
        logger.info(
            "Activity: Storing sync state",
            extra={"for_calendar_id": for_calendar_id},
        )
        await self._postgresql_repo.store_sync_state(
            for_calendar_id, sync_state
        )
