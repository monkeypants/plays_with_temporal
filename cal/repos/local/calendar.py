"""
Local file-based implementation of the CalendarRepository protocol.
Stores calendar data on the local filesystem.
"""

import json
import logging
import os
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional

from cal.domain import CalendarEvent, Schedule
from cal.repositories import CalendarChanges, CalendarRepository, SyncState

logger = logging.getLogger(__name__)


class LocalCalendarRepository(CalendarRepository):
    """
    A sink repository that stores calendar data as JSON files on the local
    filesystem. Each calendar is a directory, and each event is a JSON file.
    """

    def __init__(self, base_path: str):
        self._base_path = Path(base_path)

    def _get_calendar_path(self, calendar_id: str) -> Path:
        """Returns the path to the directory for a given calendar."""
        return self._base_path / calendar_id

    def _get_events_path(self, calendar_id: str) -> Path:
        """Returns the path to the events subdirectory for a calendar."""
        return self._get_calendar_path(calendar_id) / "events"

    def _get_event_path(self, calendar_id: str, event_id: str) -> Path:
        """Returns the path to a specific event file."""
        return self._get_events_path(calendar_id) / f"{event_id}.json"

    def _get_schedules_path(self) -> Path:
        """Returns the path to the schedules subdirectory."""
        return self._base_path / "schedules"

    def _get_schedule_path(self, schedule_id: str) -> Path:
        """Returns the path to a specific schedule file."""
        return self._get_schedules_path() / f"{schedule_id}.json"

    def _get_sync_state_path(self, for_calendar_id: str) -> Path:
        """Returns the path to the sync state file for a source calendar."""
        return self._get_calendar_path(for_calendar_id) / "sync_state.json"

    async def get_events_by_ids(
        self, calendar_id: str, event_ids: List[str]
    ) -> List[CalendarEvent]:
        """Retrieves events by reading their corresponding JSON files."""
        events = []
        for event_id in event_ids:
            event_path = self._get_event_path(calendar_id, event_id)
            if event_path.exists():
                try:
                    with open(event_path, "r") as f:
                        data = json.load(f)
                        events.append(CalendarEvent.model_validate(data))
                except (IOError, json.JSONDecodeError):
                    logger.warning(
                        f"Could not read or parse event file: {event_path}",
                        exc_info=True,
                    )
        return events

    async def get_all_events(self, calendar_id: str) -> List[CalendarEvent]:
        """Retrieves all events by reading all JSON files in the dir."""
        events_path = self._get_events_path(calendar_id)
        if not events_path.exists():
            return []

        events = []
        for event_file in events_path.glob("*.json"):
            try:
                with open(event_file, "r") as f:
                    data = json.load(f)
                    events.append(CalendarEvent.model_validate(data))
            except (IOError, json.JSONDecodeError):
                logger.warning(
                    f"Could not read or parse event file: {event_file}",
                    exc_info=True,
                )
        return events

    async def get_schedule(self, schedule_id: str) -> Optional[Schedule]:
        """Retrieves a schedule object from a JSON file."""
        schedule_path = self._get_schedule_path(schedule_id)
        if not schedule_path.exists():
            return None
        try:
            with open(schedule_path, "r") as f:
                data = json.load(f)
                return Schedule.model_validate(data)
        except (IOError, json.JSONDecodeError):
            logger.warning(
                f"Could not read or parse schedule file: {schedule_path}",
                exc_info=True,
            )
            return None

    async def generate_schedule_id(self) -> str:
        """Generate a unique schedule ID using uuid4"""
        return str(uuid.uuid4())

    async def save_schedule(self, schedule: Schedule) -> None:
        """Saves a schedule object to a JSON file, setting timestamps if not
        present."""
        schedules_path = self._get_schedules_path()
        os.makedirs(schedules_path, exist_ok=True)
        schedule_path = self._get_schedule_path(schedule.schedule_id)

        now = datetime.now(timezone.utc)
        if schedule.created_at is None:
            schedule.created_at = now
        schedule.last_updated_at = now

        for block in schedule.time_blocks:
            if block.created_at is None:
                block.created_at = now
            block.last_updated_at = now

        try:
            with open(schedule_path, "w") as f:
                f.write(schedule.model_dump_json(indent=2))
        except IOError:
            logger.error(
                f"Failed to write schedule file: {schedule_path}",
                exc_info=True,
            )

    async def apply_changes(
        self,
        calendar_id: str,
        events_to_create: List[CalendarEvent],
        events_to_update: List[CalendarEvent],
        event_ids_to_delete: List[str],
    ) -> None:
        """Applies creates, updates, and deletes to the filesystem."""
        events_path = self._get_events_path(calendar_id)
        os.makedirs(events_path, exist_ok=True)

        for event in events_to_create + events_to_update:
            event_path = self._get_event_path(calendar_id, event.event_id)
            try:
                with open(event_path, "w") as f:
                    f.write(event.model_dump_json(indent=2))
            except IOError:
                logger.error(
                    f"Failed to write event file: {event_path}", exc_info=True
                )

        for event_id in event_ids_to_delete:
            event_path = self._get_event_path(calendar_id, event_id)
            if event_path.exists():
                try:
                    os.remove(event_path)
                except IOError:
                    logger.error(
                        f"Failed to delete event file: {event_path}",
                        exc_info=True,
                    )

    async def get_sync_state(
        self, for_calendar_id: str
    ) -> Optional[SyncState]:
        """Retrieves sync state from a JSON file."""
        sync_state_path = self._get_sync_state_path(for_calendar_id)
        if not sync_state_path.exists():
            return None
        try:
            with open(sync_state_path, "r") as f:
                data = json.load(f)
                return SyncState.model_validate(data)
        except (IOError, json.JSONDecodeError):
            logger.warning(
                "Could not read or parse sync state file: "
                f"{sync_state_path}",
                exc_info=True,
            )
            return None

    async def store_sync_state(
        self, for_calendar_id: str, sync_state: SyncState
    ) -> None:
        """Stores sync state in a JSON file."""
        sync_state_path = self._get_sync_state_path(for_calendar_id)
        os.makedirs(sync_state_path.parent, exist_ok=True)
        try:
            with open(sync_state_path, "w") as f:
                f.write(sync_state.model_dump_json(indent=2))
        except IOError:
            logger.error(
                f"Failed to write sync state file: {sync_state_path}",
                exc_info=True,
            )

    async def get_events_by_date_range(
        self, calendar_id: str, start_date: datetime, end_date: datetime
    ) -> List[CalendarEvent]:
        """Retrieves events within a specific date range by filtering all
        events."""
        all_events = await self.get_all_events(calendar_id)

        # Filter events that overlap with the date range
        filtered_events = []
        for event in all_events:
            # Event overlaps if: event_start <= range_end AND
            # event_end >= range_start
            if event.start_time <= end_date and event.end_time >= start_date:
                filtered_events.append(event)

        return filtered_events

    async def get_events_by_date_range_multi_calendar(
        self,
        calendar_ids: List[str],
        start_date: datetime,
        end_date: datetime,
    ) -> List[CalendarEvent]:
        """Retrieves events from multiple calendars within a specific date
        range."""
        if not calendar_ids:
            return []

        all_events = []
        for calendar_id in calendar_ids:
            events = await self.get_events_by_date_range(
                calendar_id, start_date, end_date
            )
            all_events.extend(events)

        # Sort by start time for consistent ordering
        all_events.sort(key=lambda e: e.start_time)
        return all_events

    async def get_changes(
        self, calendar_id: str, sync_state: Optional[SyncState]
    ) -> CalendarChanges:
        raise NotImplementedError(
            "LocalCalendarRepository is a sink and does not support "
            "get_changes."
        )
