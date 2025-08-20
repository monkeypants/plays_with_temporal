"""
Repository contract tests to verify that all implementations comply with
their protocol contracts.

These tests ensure that all repository implementations (local, PostgreSQL,
mock) behave consistently and follow the same interface contracts.
"""

import pytest
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import TypeVar

from cal.domain import (
    CalendarEvent,
    Schedule,
    TimeBlockType,
    ExecutiveDecision,
    CalendarCollection,
)
from cal.repositories import (
    CalendarRepository,
    ScheduleRepository,
    TimeBlockClassifierRepository,
    CalendarConfigurationRepository,
    SyncState,
)
from cal.tests.factories import (
    minimal_calendar_event,
    minimal_schedule,
)

T = TypeVar("T")


class CalendarRepositoryContractTestMixin(ABC):
    """
    Contract test mixin for CalendarRepository implementations.

    Subclasses must implement create_repository() to return a configured
    repository instance for testing.
    """

    @abstractmethod
    async def create_repository(self) -> CalendarRepository:
        """Create a repository instance for testing."""
        pass

    @pytest.mark.asyncio
    async def test_get_events_by_ids_returns_list(self) -> None:
        """Contract: get_events_by_ids must return a list of CalendarEvent."""
        repo = await self.create_repository()

        result = await repo.get_events_by_ids("test-calendar", ["event-1"])

        assert isinstance(result, list)
        for event in result:
            assert isinstance(event, CalendarEvent)

    @pytest.mark.asyncio
    async def test_get_events_by_ids_empty_list_returns_empty(self) -> None:
        """Contract: get_events_by_ids with empty list returns empty list."""
        repo = await self.create_repository()

        result = await repo.get_events_by_ids("test-calendar", [])

        assert result == []

    @pytest.mark.asyncio
    async def test_get_events_by_date_range_returns_list(self) -> None:
        """Contract: get_events_by_date_range must return a list of
        CalendarEvent."""
        repo = await self.create_repository()
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 2, tzinfo=timezone.utc)

        result = await repo.get_events_by_date_range(
            "test-calendar", start_date, end_date
        )

        assert isinstance(result, list)
        for event in result:
            assert isinstance(event, CalendarEvent)

    @pytest.mark.asyncio
    async def test_get_events_by_date_range_multi_calendar_returns_list(self) -> None:
        """Contract: get_events_by_date_range_multi_calendar must return a
        list."""
        repo = await self.create_repository()
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 2, tzinfo=timezone.utc)

        result = await repo.get_events_by_date_range_multi_calendar(
            ["cal-1", "cal-2"], start_date, end_date
        )

        assert isinstance(result, list)
        for event in result:
            assert isinstance(event, CalendarEvent)

    @pytest.mark.asyncio
    async def test_get_events_by_date_range_multi_calendar_empty_list(self) -> None:
        """Contract: multi-calendar method with empty list returns empty
        list."""
        repo = await self.create_repository()
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 2, tzinfo=timezone.utc)

        result = await repo.get_events_by_date_range_multi_calendar(
            [], start_date, end_date
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_apply_changes_accepts_empty_lists(self) -> None:
        """Contract: apply_changes must handle empty lists without error."""
        repo = await self.create_repository()

        # Should not raise an exception
        await repo.apply_changes("test-calendar", [], [], [])

    @pytest.mark.asyncio
    async def test_get_sync_state_returns_optional_sync_state(self) -> None:
        """Contract: get_sync_state returns Optional[SyncState]."""
        repo = await self.create_repository()

        result = await repo.get_sync_state("test-calendar")

        assert result is None or isinstance(result, SyncState)

    @pytest.mark.asyncio
    async def test_store_sync_state_accepts_sync_state(self) -> None:
        """Contract: store_sync_state must accept SyncState without error."""
        repo = await self.create_repository()
        sync_state = SyncState(sync_token="test-token")

        # Should not raise an exception
        await repo.store_sync_state("test-calendar", sync_state)


class ScheduleRepositoryContractTestMixin(ABC):
    """
    Contract test mixin for ScheduleRepository implementations.
    """

    @abstractmethod
    async def create_repository(self) -> ScheduleRepository:
        """Create a repository instance for testing."""
        pass

    @pytest.mark.asyncio
    async def test_generate_schedule_id_returns_string(self) -> None:
        """Contract: generate_schedule_id must return a non-empty string."""
        repo = await self.create_repository()

        result = await repo.generate_schedule_id()

        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_generate_schedule_id_returns_unique_ids(self) -> None:
        """Contract: generate_schedule_id should return unique IDs."""
        repo = await self.create_repository()

        id1 = await repo.generate_schedule_id()
        id2 = await repo.generate_schedule_id()

        assert id1 != id2

    @pytest.mark.asyncio
    async def test_save_schedule_accepts_schedule(self) -> None:
        """Contract: save_schedule must accept Schedule without error."""
        repo = await self.create_repository()
        schedule = minimal_schedule()

        # Should not raise an exception
        await repo.save_schedule(schedule)

    @pytest.mark.asyncio
    async def test_get_schedule_returns_optional_schedule(self) -> None:
        """Contract: get_schedule returns Optional[Schedule]."""
        repo = await self.create_repository()

        result = await repo.get_schedule("non-existent-id")

        assert result is None or isinstance(result, Schedule)


class TimeBlockClassifierRepositoryContractTestMixin(ABC):
    """
    Contract test mixin for TimeBlockClassifierRepository implementations.
    """

    @abstractmethod
    async def create_repository(self) -> TimeBlockClassifierRepository:
        """Create a repository instance for testing."""
        pass

    @pytest.mark.asyncio
    async def test_classify_block_type_returns_time_block_type(self) -> None:
        """Contract: classify_block_type must return TimeBlockType."""
        repo = await self.create_repository()
        event = minimal_calendar_event()

        result = await repo.classify_block_type(event)

        assert isinstance(result, TimeBlockType)

    @pytest.mark.asyncio
    async def test_classify_responsibility_area_returns_optional_string(self) -> None:
        """Contract: classify_responsibility_area returns Optional[str]."""
        repo = await self.create_repository()
        event = minimal_calendar_event()

        result = await repo.classify_responsibility_area(event)

        assert result is None or isinstance(result, str)

    @pytest.mark.asyncio
    async def test_triage_event_returns_tuple(self) -> None:
        """Contract: triage_event returns tuple[ExecutiveDecision, str]."""
        repo = await self.create_repository()
        event = minimal_calendar_event()

        result = await repo.triage_event(event)

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], ExecutiveDecision)
        assert isinstance(result[1], str)
        assert len(result[1]) > 0  # Reason should not be empty


class CalendarConfigurationRepositoryContractTestMixin(ABC):
    """
    Contract test mixin for CalendarConfigurationRepository implementations.
    """

    @abstractmethod
    async def create_repository(self) -> CalendarConfigurationRepository:
        """Create a repository instance for testing."""
        pass

    @pytest.mark.asyncio
    async def test_get_collection_returns_optional_collection(self) -> None:
        """Contract: get_collection returns Optional[CalendarCollection]."""
        repo = await self.create_repository()

        result = await repo.get_collection("non-existent-collection")

        assert result is None or isinstance(result, CalendarCollection)

    @pytest.mark.asyncio
    async def test_list_collections_returns_list(self) -> None:
        """Contract: list_collections returns List[CalendarCollection]."""
        repo = await self.create_repository()

        result = await repo.list_collections()

        assert isinstance(result, list)
        for collection in result:
            assert isinstance(collection, CalendarCollection)


# Concrete test classes for each repository implementation


class TestLocalCalendarRepositoryContract(
    CalendarRepositoryContractTestMixin
):
    """Test LocalCalendarRepository against the CalendarRepository
    contract."""

    async def create_repository(self) -> CalendarRepository:
        from cal.repos.local.calendar import LocalCalendarRepository

        return LocalCalendarRepository(base_path="test_data")


class TestLocalCalendarRepositoryScheduleContract(
    ScheduleRepositoryContractTestMixin
):
    """Test LocalCalendarRepository against the ScheduleRepository
    contract."""

    async def create_repository(self) -> ScheduleRepository:
        from cal.repos.local.calendar import LocalCalendarRepository

        return LocalCalendarRepository(base_path="test_data")


class TestMockCalendarRepositoryContract(CalendarRepositoryContractTestMixin):
    """Test MockCalendarRepository against the CalendarRepository contract."""

    async def create_repository(self) -> CalendarRepository:
        from cal.repos.mock.calendar import MockCalendarRepository

        return MockCalendarRepository()


class TestLocalTimeBlockClassifierRepositoryContract(
    TimeBlockClassifierRepositoryContractTestMixin
):
    """Test LocalTimeBlockClassifierRepository against the contract."""

    async def create_repository(self) -> TimeBlockClassifierRepository:
        from cal.repos.local.time_block_classifier import (
            LocalTimeBlockClassifierRepository,
        )

        return LocalTimeBlockClassifierRepository()


class TestMockCalendarConfigurationRepositoryContract(
    CalendarConfigurationRepositoryContractTestMixin
):
    """Test MockCalendarConfigurationRepository against the contract."""

    async def create_repository(self) -> CalendarConfigurationRepository:
        from cal.repos.mock.calendar_config import (
            MockCalendarConfigurationRepository,
        )

        return MockCalendarConfigurationRepository()


class TestLocalCalendarConfigurationRepositoryContract(
    CalendarConfigurationRepositoryContractTestMixin
):
    """Test LocalCalendarConfigurationRepository against the contract."""

    async def create_repository(self) -> CalendarConfigurationRepository:
        from cal.repos.local.calendar_config import (
            LocalCalendarConfigurationRepository,
        )

        return LocalCalendarConfigurationRepository()


# Integration tests for repository error handling


class TestRepositoryErrorHandling:
    """Test error handling behavior across repository implementations."""

    @pytest.mark.asyncio
    async def test_calendar_repo_handles_invalid_calendar_id(self) -> None:
        """Test that repositories handle invalid calendar IDs gracefully."""
        from cal.repos.mock.calendar import MockCalendarRepository

        repo = MockCalendarRepository()

        # Should not raise exception, should return empty list
        result = await repo.get_events_by_ids("invalid-calendar", ["event-1"])
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_schedule_repo_handles_invalid_schedule_id(self) -> None:
        """Test that schedule repositories handle invalid IDs gracefully."""
        from cal.repos.local.calendar import LocalCalendarRepository

        repo = LocalCalendarRepository(base_path="test_data")

        # Should return None, not raise exception
        result = await repo.get_schedule("invalid-schedule-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_classifier_repo_handles_minimal_event_data(self) -> None:
        """Test that classifiers handle events with minimal data."""
        from cal.repos.local.time_block_classifier import (
            LocalTimeBlockClassifierRepository,
        )

        repo = LocalTimeBlockClassifierRepository()

        # Create event with minimal required data
        minimal_event = minimal_calendar_event(
            title="",  # Empty title
            description=None,
            location=None,
            attendees=[],
        )

        # Should not raise exception
        block_type = await repo.classify_block_type(minimal_event)
        assert isinstance(block_type, TimeBlockType)

        responsibility = await repo.classify_responsibility_area(
            minimal_event
        )
        assert responsibility is None or isinstance(responsibility, str)

        decision, reason = await repo.triage_event(minimal_event)
        assert isinstance(decision, ExecutiveDecision)
        assert isinstance(reason, str)
        assert len(reason) > 0


# Idempotency tests


class TestRepositoryIdempotency:
    """Test that repository operations are idempotent where required."""

    @pytest.mark.asyncio
    async def test_save_schedule_is_idempotent(self) -> None:
        """Test that saving the same schedule multiple times is safe."""
        from cal.repos.local.calendar import LocalCalendarRepository

        repo = LocalCalendarRepository(base_path="test_data")
        schedule = minimal_schedule(schedule_id="idempotent-test")

        # Save the same schedule multiple times - should not raise exception
        await repo.save_schedule(schedule)
        await repo.save_schedule(schedule)
        await repo.save_schedule(schedule)

        # Should be able to retrieve it
        retrieved = await repo.get_schedule("idempotent-test")
        assert retrieved is not None
        assert retrieved.schedule_id == "idempotent-test"

    @pytest.mark.asyncio
    async def test_store_sync_state_is_idempotent(self) -> None:
        """Test that storing sync state multiple times is safe."""
        from cal.repos.local.calendar import LocalCalendarRepository

        repo = LocalCalendarRepository(base_path="test_data")
        sync_state = SyncState(sync_token="idempotent-token")

        # Store the same sync state multiple times - should not raise
        # exception
        await repo.store_sync_state("test-calendar", sync_state)
        await repo.store_sync_state("test-calendar", sync_state)
        await repo.store_sync_state("test-calendar", sync_state)

        # Should be able to retrieve it
        retrieved = await repo.get_sync_state("test-calendar")
        assert retrieved is not None
        assert retrieved.sync_token == "idempotent-token"
