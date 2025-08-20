"""
Standard mock factory functions for calendar tests.

These factories provide consistent mocking patterns across all test files,
following the successful CLI test approach with sensible defaults and easy
customization.
"""

from unittest.mock import AsyncMock
from typing import Optional, List

from cal.domain import (
    CalendarEvent,
    Schedule,
    TimeBlockType,
    ExecutiveDecision,
    CalendarCollection,
    CalendarSource,
)
from cal.repositories import (
    CalendarRepository,
    ScheduleRepository,
    TimeBlockClassifierRepository,
    CalendarConfigurationRepository,
    SyncState,
    CalendarChanges,
)
from cal.tests.factories import (
    minimal_schedule,
)


def create_mock_calendar_repository(
    events: Optional[List[CalendarEvent]] = None,
    sync_state: Optional[SyncState] = None,
    **kwargs: Any,
) -> AsyncMock:
    """
    Create a mock CalendarRepository with sensible defaults.

    Args:
        events: List of events to return from queries (defaults to empty list)
        sync_state: Sync state to return (defaults to None)
        **kwargs: Additional mock configuration

    Returns:
        AsyncMock configured as CalendarRepository
    """
    if events is None:
        events = []

    mock_repo = AsyncMock(spec=CalendarRepository)

    # Configure default return values
    mock_repo.get_all_events.return_value = events
    mock_repo.get_events_by_ids.return_value = events
    mock_repo.get_events_by_date_range.return_value = events
    mock_repo.get_events_by_date_range_multi_calendar.return_value = events
    mock_repo.get_sync_state.return_value = sync_state
    mock_repo.get_changes.return_value = CalendarChanges(
        upserted_events=events,
        upserted_events_file_id=None,
        deleted_event_ids=[],
        new_sync_state=sync_state or SyncState(sync_token="mock-token"),
    )

    # Configure side effects for customization
    for key, value in kwargs.items():
        if hasattr(mock_repo, key):
            getattr(mock_repo, key).return_value = value

    return mock_repo


def create_mock_schedule_repository(
    schedule_id: str = "mock-schedule-123",
    schedule: Optional[Schedule] = None,
    **kwargs: Any,
) -> AsyncMock:
    """
    Create a mock ScheduleRepository with sensible defaults.

    Args:
        schedule_id: ID to return from generate_schedule_id
        schedule: Schedule to return from get_schedule (defaults to minimal)
        **kwargs: Additional mock configuration

    Returns:
        AsyncMock configured as ScheduleRepository
    """
    if schedule is None:
        schedule = minimal_schedule(schedule_id=schedule_id)

    mock_repo = AsyncMock(spec=ScheduleRepository)

    # Configure default return values
    mock_repo.generate_schedule_id.return_value = schedule_id
    mock_repo.get_schedule.return_value = schedule
    mock_repo.save_schedule.return_value = None

    # Configure side effects for customization
    for key, value in kwargs.items():
        if hasattr(mock_repo, key):
            getattr(mock_repo, key).return_value = value

    return mock_repo


def create_mock_classifier_repository(
    block_type: TimeBlockType = TimeBlockType.MEETING,
    responsibility_area: Optional[str] = None,
    triage_decision: ExecutiveDecision = ExecutiveDecision.ATTEND,
    triage_reason: str = "Default test reason",
    **kwargs: Any,
) -> AsyncMock:
    """
    Create a mock TimeBlockClassifierRepository with sensible defaults.

    Args:
        block_type: Type to return from classify_block_type
        responsibility_area: Area to return from classify_responsibility_area
        triage_decision: Decision to return from triage_event
        triage_reason: Reason to return from triage_event
        **kwargs: Additional mock configuration

    Returns:
        AsyncMock configured as TimeBlockClassifierRepository
    """
    mock_repo = AsyncMock(spec=TimeBlockClassifierRepository)

    # Configure default return values
    mock_repo.classify_block_type.return_value = block_type
    mock_repo.classify_responsibility_area.return_value = responsibility_area
    mock_repo.triage_event.return_value = (triage_decision, triage_reason)

    # Configure side effects for customization
    for key, value in kwargs.items():
        if hasattr(mock_repo, key):
            if key == "triage_event" and isinstance(value, tuple):
                getattr(mock_repo, key).return_value = value
            else:
                getattr(mock_repo, key).return_value = value

    return mock_repo


def create_mock_config_repository(
    collections: Optional[List[CalendarCollection]] = None, **kwargs: Any
) -> AsyncMock:
    """
    Create a mock CalendarConfigurationRepository with sensible defaults.

    Args:
        collections: List of collections to return (defaults to empty list)
        **kwargs: Additional mock configuration

    Returns:
        AsyncMock configured as CalendarConfigurationRepository
    """
    if collections is None:
        collections = []

    mock_repo = AsyncMock(spec=CalendarConfigurationRepository)

    # Configure default return values
    mock_repo.list_collections.return_value = collections
    mock_repo.get_collection.return_value = (
        collections[0] if collections else None
    )

    # Configure side effects for customization
    for key, value in kwargs.items():
        if hasattr(mock_repo, key):
            getattr(mock_repo, key).return_value = value

    return mock_repo


def create_test_calendar_collection(
    collection_id: str = "test-collection",
    display_name: str = "Test Collection",
    calendar_count: int = 2,
    enabled_count: Optional[int] = None,
) -> CalendarCollection:
    """
    Create a test CalendarCollection with configurable calendars.

    Args:
        collection_id: Collection identifier
        display_name: Human-readable collection name
        calendar_count: Total number of calendars in collection
        enabled_count: Number of enabled calendars (defaults to all)

    Returns:
        CalendarCollection for testing
    """
    if enabled_count is None:
        enabled_count = calendar_count

    calendar_sources = []
    for i in range(calendar_count):
        calendar_sources.append(
            CalendarSource(
                calendar_id=f"cal-{i+1}",
                display_name=f"Test Calendar {i+1}",
                source_type="google",
                enabled=i < enabled_count,
                sync_priority=i + 1,
            )
        )

    return CalendarCollection(
        collection_id=collection_id,
        display_name=display_name,
        default_calendar_id=(
            calendar_sources[0].calendar_id if calendar_sources else None
        ),
        calendar_sources=calendar_sources,
    )


# Convenience functions for common test scenarios


def create_mock_repositories_for_use_case(
    events: Optional[List[CalendarEvent]] = None,
    schedule_id: str = "test-schedule",
    **kwargs: Any,
) -> tuple[AsyncMock, AsyncMock, AsyncMock, AsyncMock]:
    """
    Create a complete set of mock repositories for use case testing.

    Args:
        events: Events to return from calendar repository
        schedule_id: Schedule ID to generate
        **kwargs: Additional configuration for specific repositories

    Returns:
        Tuple of (calendar_repo, schedule_repo, classifier_repo, config_repo)
    """
    calendar_repo = create_mock_calendar_repository(
        events=events, **kwargs.get("calendar_repo_config", {})
    )

    schedule_repo = create_mock_schedule_repository(
        schedule_id=schedule_id, **kwargs.get("schedule_repo_config", {})
    )

    classifier_repo = create_mock_classifier_repository(
        **kwargs.get("classifier_repo_config", {})
    )

    config_repo = create_mock_config_repository(
        **kwargs.get("config_repo_config", {})
    )

    return calendar_repo, schedule_repo, classifier_repo, config_repo


def setup_use_case_with_mocks(
    use_case_class: Any, events: Optional[List[CalendarEvent]] = None, **kwargs: Any
) -> tuple[Any, Dict[str, Any]]:
    """
    Set up a use case with standard mock repositories.

    Args:
        use_case_class: The use case class to instantiate
        events: Events to return from calendar repository
        **kwargs: Additional configuration

    Returns:
        Tuple of (use_case_instance, mock_repos_dict)
    """
    calendar_repo, schedule_repo, classifier_repo, config_repo = (
        create_mock_repositories_for_use_case(events=events, **kwargs)
    )

    use_case = use_case_class(
        calendar_repo=calendar_repo,
        schedule_repo=schedule_repo,
        time_block_classifier_repo=classifier_repo,
        config_repo=config_repo,
    )

    mock_repos = {
        "calendar_repo": calendar_repo,
        "schedule_repo": schedule_repo,
        "classifier_repo": classifier_repo,
        "config_repo": config_repo,
    }

    return use_case, mock_repos
