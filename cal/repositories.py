"""
Defines the repository protocol for calendar interactions.
"""

from datetime import datetime
from typing import List, Optional, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from .domain import CalendarEvent, Schedule, TimeBlockType, ExecutiveDecision

# Forward reference for CalendarCollection to avoid circular imports
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .domain import CalendarCollection


class SyncState(BaseModel):
    """Represents the state required to perform an incremental sync."""

    sync_token: str


class CalendarChanges(BaseModel):
    """
    Represents the changes fetched from a calendar since the last sync.
    """

    upserted_events: List[CalendarEvent] = Field(
        default_factory=list,
        description=(
            "List of events to create or update. For large payloads, this "
            "might be empty, with events referenced by "
            "upserted_events_file_id."
        ),
    )
    upserted_events_file_id: Optional[str] = Field(
        None,
        description=(
            "Optional ID of a file containing upserted events (for large "
            "payloads). If present, upserted_events list will be empty."
        ),
    )
    deleted_event_ids: List[str] = Field(
        default_factory=list, description="List of event IDs to delete."
    )
    new_sync_state: SyncState = Field(
        ..., description="The new sync state after fetching changes."
    )


@runtime_checkable
class CalendarRepository(Protocol):
    """
    Protocol for a repository that can interact with a calendar.

    This abstraction supports both source (e.g., Google Calendar) and
    sink (e.g., local storage) calendars for synchronization.
    """

    # Methods for fetching changes (primarily for source calendars)
    async def get_changes(
        self, calendar_id: str, sync_state: Optional[SyncState]
    ) -> CalendarChanges:
        """
        Fetches all events that have changed since the last sync state.
        If sync_state is None, this should perform a full sync.
        """
        ...

    # Methods for querying events (for source or sink)
    async def get_events_by_ids(
        self, calendar_id: str, event_ids: List[str]
    ) -> List[CalendarEvent]:
        """Retrieves a set of events by their unique identifiers."""
        ...

    async def get_all_events(self, calendar_id: str) -> List[CalendarEvent]:
        """Retrieves all events for a given calendar."""
        ...

    async def get_events_by_date_range(
        self, calendar_id: str, start_date: datetime, end_date: datetime
    ) -> List[CalendarEvent]:
        """Get events within a specific date range."""
        ...

    async def get_events_by_date_range_multi_calendar(
        self,
        calendar_ids: List[str],
        start_date: datetime,
        end_date: datetime,
    ) -> List[CalendarEvent]:
        """Get events from multiple calendars within a specific date range."""
        ...

    # Methods for applying changes (primarily for sink calendars)
    async def apply_changes(
        self,
        calendar_id: str,
        events_to_create: List[CalendarEvent],
        events_to_update: List[CalendarEvent],
        event_ids_to_delete: List[str],
    ) -> None:
        """Applies a set of creates, updates, and deletes to the calendar."""
        ...

    # Methods for managing sync state (primarily for sink calendars)
    async def get_sync_state(
        self, for_calendar_id: str
    ) -> Optional[SyncState]:
        """
        Retrieves the sync state for a given source calendar, as stored
        by the sink.
        """
        ...

    async def store_sync_state(
        self, for_calendar_id: str, sync_state: SyncState
    ) -> None:
        """
        Stores the sync state for a given source calendar, to be used in
        the next sync operation.
        """
        ...


@runtime_checkable
class ScheduleRepository(Protocol):
    """
    Protocol for a repository that handles persistence for Schedule objects.
    """

    async def save_schedule(self, schedule: Schedule) -> None:
        """Saves a schedule object."""
        ...

    async def get_schedule(self, schedule_id: str) -> Optional[Schedule]:
        """Retrieves a schedule object by its unique identifier."""
        ...

    async def generate_schedule_id(self) -> str:
        """Generates a unique schedule identifier."""
        ...


@runtime_checkable
class TimeBlockClassifierRepository(Protocol):
    """
    Protocol for a repository that analyzes calendar events to classify
    and enrich time blocks.
    """

    async def classify_block_type(
        self, event: CalendarEvent
    ) -> TimeBlockType:
        """Determines the appropriate time block type for a calendar event."""
        ...

    async def classify_responsibility_area(
        self, event: CalendarEvent
    ) -> Optional[str]:
        """Identifies the area of responsibility or project for an event."""
        ...

    async def triage_event(
        self, event: CalendarEvent
    ) -> tuple[ExecutiveDecision, str]:
        """
        Analyzes a calendar event to provide triage decision and reasoning.

        Returns:
            A tuple of (ExecutiveDecision, reasoning_string)
        """
        ...


@runtime_checkable
class CalendarConfigurationRepository(Protocol):
    """
    Protocol for a repository that manages calendar configuration data.

    This abstraction supports different configuration sources (YAML files,
    databases, environment variables) while maintaining Clean Architecture
    principles by keeping configuration logic separate from business logic.
    """

    async def get_collection(
        self, collection_id: str
    ) -> Optional["CalendarCollection"]:
        """Retrieve a calendar collection by its ID."""
        ...

    async def list_collections(self) -> List["CalendarCollection"]:
        """List all available calendar collections."""
        ...
