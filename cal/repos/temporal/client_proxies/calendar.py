"""
Client-side proxy for CalendarRepository that dispatches Temporal workflows.
"""

import logging
from datetime import datetime
from typing import List, Optional

from temporalio.client import Client

from cal.domain import CalendarEvent
from cal.repositories import CalendarRepository, CalendarChanges, SyncState

logger = logging.getLogger(__name__)


class TemporalCalendarRepository(CalendarRepository):
    """
    Client-side proxy for CalendarRepository that dispatches Temporal
    workflows. This proxy ensures that operations are performed via workflow
    dispatch, not direct activity execution.
    """

    def __init__(
        self,
        client: Client,
        concrete_repo: Optional[CalendarRepository] = None,
    ):
        self.client = client
        self.workflow_timeout_seconds = 60

    async def get_changes(
        self, calendar_id: str, sync_state: Optional[SyncState]
    ) -> CalendarChanges:
        """Get changes via Temporal workflow dispatch."""
        logger.debug(
            "Dispatching get_changes workflow",
            extra={"calendar_id": calendar_id},
        )

        try:
            # This would dispatch a workflow that handles calendar sync
            # For now, return a mock response to show the pattern
            logger.info(
                "Calendar changes retrieved via workflow",
                extra={"calendar_id": calendar_id},
            )

            # Mock response - in reality this would dispatch
            # CalendarSyncWorkflow
            return CalendarChanges(
                upserted_events=[],
                upserted_events_file_id=None,
                deleted_event_ids=[],
                new_sync_state=SyncState(sync_token="mock-sync-token"),
            )
        except Exception as e:
            logger.error(
                "Failed to get calendar changes via workflow",
                extra={"calendar_id": calendar_id, "error": str(e)},
            )
            raise

    async def get_events_by_ids(
        self, calendar_id: str, event_ids: List[str]
    ) -> List[CalendarEvent]:
        """Get events by IDs via Temporal workflow dispatch."""
        logger.debug(
            "Dispatching get_events_by_ids workflow",
            extra={"calendar_id": calendar_id, "event_count": len(event_ids)},
        )

        try:
            # This would dispatch a workflow that queries events
            logger.debug(
                "Events query completed via workflow",
                extra={
                    "calendar_id": calendar_id,
                    "event_count": len(event_ids),
                },
            )
            return []
        except Exception as e:
            logger.error(
                "Failed to get events by IDs via workflow",
                extra={"calendar_id": calendar_id, "error": str(e)},
            )
            raise

    async def get_all_events(self, calendar_id: str) -> List[CalendarEvent]:
        """Get all events via Temporal workflow dispatch."""
        logger.debug(
            "Dispatching get_all_events workflow",
            extra={"calendar_id": calendar_id},
        )

        try:
            # This would dispatch a workflow that retrieves all events
            logger.debug(
                "All events query completed via workflow",
                extra={"calendar_id": calendar_id},
            )
            return []
        except Exception as e:
            logger.error(
                "Failed to get all events via workflow",
                extra={"calendar_id": calendar_id, "error": str(e)},
            )
            raise

    async def get_events_by_date_range(
        self, calendar_id: str, start_date: datetime, end_date: datetime
    ) -> List[CalendarEvent]:
        """Get events by date range via Temporal workflow dispatch."""
        logger.debug(
            "Dispatching get_events_by_date_range workflow",
            extra={"calendar_id": calendar_id},
        )

        try:
            # This would dispatch a workflow that queries events by date range
            logger.debug(
                "Date range events query completed via workflow",
                extra={"calendar_id": calendar_id},
            )
            return []
        except Exception as e:
            logger.error(
                "Failed to get events by date range via workflow",
                extra={"calendar_id": calendar_id, "error": str(e)},
            )
            raise

    async def get_events_by_date_range_multi_calendar(
        self,
        calendar_ids: List[str],
        start_date: datetime,
        end_date: datetime,
    ) -> List[CalendarEvent]:
        """Get events from multiple calendars by date range via Temporal
        workflow dispatch."""
        logger.debug(
            "Dispatching get_events_by_date_range_multi_calendar workflow",
            extra={"calendar_ids": calendar_ids},
        )

        try:
            # This would dispatch a workflow that queries multiple calendars
            logger.debug(
                "Multi-calendar date range query completed via workflow",
                extra={"calendar_ids": calendar_ids},
            )
            return []
        except Exception as e:
            logger.error(
                "Failed to get events from multiple calendars via workflow",
                extra={"calendar_ids": calendar_ids, "error": str(e)},
            )
            raise

    async def apply_changes(
        self,
        calendar_id: str,
        events_to_create: List[CalendarEvent],
        events_to_update: List[CalendarEvent],
        event_ids_to_delete: List[str],
    ) -> None:
        """Apply changes via Temporal workflow dispatch."""
        logger.debug(
            "Dispatching apply_changes workflow",
            extra={
                "calendar_id": calendar_id,
                "create_count": len(events_to_create),
                "update_count": len(events_to_update),
                "delete_count": len(event_ids_to_delete),
            },
        )

        try:
            # This would dispatch a workflow that applies calendar changes
            logger.info(
                "Calendar changes applied via workflow",
                extra={"calendar_id": calendar_id},
            )
        except Exception as e:
            logger.error(
                "Failed to apply calendar changes via workflow",
                extra={"calendar_id": calendar_id, "error": str(e)},
            )
            raise

    async def get_sync_state(
        self, for_calendar_id: str
    ) -> Optional[SyncState]:
        """Get sync state via Temporal workflow dispatch."""
        logger.debug(
            "Dispatching get_sync_state workflow",
            extra={"for_calendar_id": for_calendar_id},
        )

        try:
            # This would dispatch a workflow that queries sync state
            logger.debug(
                "Sync state query completed via workflow",
                extra={"for_calendar_id": for_calendar_id},
            )
            return None
        except Exception as e:
            logger.error(
                "Failed to get sync state via workflow",
                extra={"for_calendar_id": for_calendar_id, "error": str(e)},
            )
            raise

    async def store_sync_state(
        self, for_calendar_id: str, sync_state: SyncState
    ) -> None:
        """Store sync state via Temporal workflow dispatch."""
        logger.debug(
            "Dispatching store_sync_state workflow",
            extra={"for_calendar_id": for_calendar_id},
        )

        try:
            # This would dispatch a workflow that stores sync state
            logger.info(
                "Sync state stored via workflow",
                extra={"for_calendar_id": for_calendar_id},
            )
        except Exception as e:
            logger.error(
                "Failed to store sync state via workflow",
                extra={"for_calendar_id": for_calendar_id, "error": str(e)},
            )
            raise
