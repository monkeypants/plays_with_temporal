"""
PostgreSQL implementation of CalendarRepository.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional

from asyncpg import Connection, Pool

from cal.domain import CalendarEvent
from cal.repositories import (
    CalendarChanges,
    CalendarRepository,
    SyncState,
)

logger = logging.getLogger(__name__)


class PostgreSQLCalendarRepository(CalendarRepository):
    """
    PostgreSQL implementation of CalendarRepository.
    Uses PostgreSQL for persistence of calendar events.
    """

    def __init__(self, pool: Pool):
        """
        Initialize with an asyncpg connection pool.

        Args:
            pool: asyncpg connection pool for database operations
        """
        self.pool = pool
        logger.debug("Initialized PostgreSQLCalendarRepository")

    async def get_events_by_ids(
        self, calendar_id: str, event_ids: List[str]
    ) -> List[CalendarEvent]:
        """Retrieves events by their IDs from PostgreSQL."""
        if not event_ids:
            return []

        async with self.pool.acquire() as conn:
            query = """
                SELECT event_data
                FROM calendar_events
                WHERE calendar_id = $1 AND event_id = ANY($2)
            """
            rows = await conn.fetch(query, calendar_id, event_ids)

        events = []
        for row in rows:
            try:
                event = CalendarEvent.model_validate_json(row["event_data"])
                events.append(event)
            except Exception as e:
                logger.warning(
                    f"Failed to parse event data: {e}",
                    extra={"calendar_id": calendar_id},
                )

        logger.debug(
            f"Retrieved {len(events)} events by IDs",
            extra={
                "calendar_id": calendar_id,
                "requested": len(event_ids),
            },
        )
        return events

    async def get_all_events(self, calendar_id: str) -> List[CalendarEvent]:
        """Retrieves all events for a calendar from PostgreSQL."""
        async with self.pool.acquire() as conn:
            query = """
                SELECT event_data
                FROM calendar_events
                WHERE calendar_id = $1
                ORDER BY start_time
            """
            rows = await conn.fetch(query, calendar_id)

        events = []
        for row in rows:
            try:
                event = CalendarEvent.model_validate_json(row["event_data"])
                events.append(event)
            except Exception as e:
                logger.warning(
                    f"Failed to parse event data: {e}",
                    extra={"calendar_id": calendar_id},
                )

        logger.info(
            f"Retrieved {len(events)} events from calendar",
            extra={"calendar_id": calendar_id},
        )
        return events

    async def get_events_by_date_range(
        self, calendar_id: str, start_date: datetime, end_date: datetime
    ) -> List[CalendarEvent]:
        """Retrieves events within a specific date range from PostgreSQL."""
        async with self.pool.acquire() as conn:
            query = """
                SELECT event_data
                FROM calendar_events
                WHERE calendar_id = $1
                  AND start_time <= $3
                  AND end_time >= $2
                ORDER BY start_time
            """
            rows = await conn.fetch(query, calendar_id, start_date, end_date)

        events = []
        for row in rows:
            try:
                event = CalendarEvent.model_validate_json(row["event_data"])
                events.append(event)
            except Exception as e:
                logger.warning(
                    f"Failed to parse event data: {e}",
                    extra={"calendar_id": calendar_id},
                )

        logger.info(
            f"Retrieved {len(events)} events from calendar in date range",
            extra={
                "calendar_id": calendar_id,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        )
        return events

    async def get_events_by_date_range_multi_calendar(
        self,
        calendar_ids: List[str],
        start_date: datetime,
        end_date: datetime,
    ) -> List[CalendarEvent]:
        """Retrieves events from multiple calendars within a specific date
        range from PostgreSQL."""
        if not calendar_ids:
            return []

        async with self.pool.acquire() as conn:
            query = """
                SELECT event_data
                FROM calendar_events
                WHERE calendar_id = ANY($1)
                  AND start_time <= $3
                  AND end_time >= $2
                ORDER BY start_time, calendar_id
            """
            rows = await conn.fetch(query, calendar_ids, start_date, end_date)

        events = []
        for row in rows:
            try:
                event = CalendarEvent.model_validate_json(row["event_data"])
                events.append(event)
            except Exception as e:
                logger.warning(
                    f"Failed to parse event data: {e}",
                    extra={"calendar_ids": calendar_ids},
                )

        logger.info(
            f"Retrieved {len(events)} events from {len(calendar_ids)} "
            f"calendars in date range",
            extra={
                "calendar_ids": calendar_ids,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        )
        return events

    async def apply_changes(
        self,
        calendar_id: str,
        events_to_create: List[CalendarEvent],
        events_to_update: List[CalendarEvent],
        event_ids_to_delete: List[str],
    ) -> None:
        """Applies creates, updates, and deletes to PostgreSQL."""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Handle creates and updates
                for event in events_to_create + events_to_update:
                    await self._upsert_event(conn, calendar_id, event)

                # Handle deletes
                if event_ids_to_delete:
                    delete_query = """
                        DELETE FROM calendar_events
                        WHERE calendar_id = $1 AND event_id = ANY($2)
                    """
                    await conn.execute(
                        delete_query, calendar_id, event_ids_to_delete
                    )

        logger.info(
            "Applied calendar changes",
            extra={
                "calendar_id": calendar_id,
                "created": len(events_to_create),
                "updated": len(events_to_update),
                "deleted": len(event_ids_to_delete),
            },
        )

    async def _upsert_event(
        self, conn: Connection, calendar_id: str, event: CalendarEvent
    ) -> None:
        """Upserts a single event into PostgreSQL."""
        query = """
            INSERT INTO calendar_events (
                calendar_id, event_id, start_time, end_time,
                title, organizer, attendee_count, status, event_data,
                last_modified
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            ON CONFLICT (calendar_id, event_id)
            DO UPDATE SET
                start_time = EXCLUDED.start_time,
                end_time = EXCLUDED.end_time,
                title = EXCLUDED.title,
                organizer = EXCLUDED.organizer,
                attendee_count = EXCLUDED.attendee_count,
                status = EXCLUDED.status,
                event_data = EXCLUDED.event_data,
                last_modified = EXCLUDED.last_modified
        """

        await conn.execute(
            query,
            calendar_id,
            event.event_id,
            event.start_time,
            event.end_time,
            event.title,
            event.organizer,
            len(event.attendees),
            event.status.value,
            event.model_dump_json(),
            event.last_modified,
        )

    async def get_sync_state(
        self, for_calendar_id: str
    ) -> Optional[SyncState]:
        """Retrieves sync state from PostgreSQL."""
        async with self.pool.acquire() as conn:
            query = """
                SELECT sync_token
                FROM calendar_sync_state
                WHERE source_calendar_id = $1
            """
            row = await conn.fetchrow(query, for_calendar_id)

        if row:
            return SyncState(sync_token=row["sync_token"])
        return None

    async def store_sync_state(
        self, for_calendar_id: str, sync_state: SyncState
    ) -> None:
        """Stores sync state in PostgreSQL."""
        async with self.pool.acquire() as conn:
            query = """
                INSERT INTO calendar_sync_state (
                    source_calendar_id, sync_token, updated_at
                )
                VALUES ($1, $2, $3)
                ON CONFLICT (source_calendar_id)
                DO UPDATE SET
                    sync_token = EXCLUDED.sync_token,
                    updated_at = EXCLUDED.updated_at
            """

            await conn.execute(
                query,
                for_calendar_id,
                sync_state.sync_token,
                datetime.now(timezone.utc),
            )

        logger.debug(
            "Stored sync state",
            extra={"for_calendar_id": for_calendar_id},
        )

    async def get_changes(
        self, calendar_id: str, sync_state: Optional[SyncState]
    ) -> CalendarChanges:
        """
        PostgreSQL implementation doesn't support incremental sync directly.
        This method is primarily for source repositories like Google Calendar.
        """
        raise NotImplementedError(
            "PostgreSQLCalendarRepository is a sink repository and does not "
            "support get_changes. Use get_all_events for full sync."
        )
