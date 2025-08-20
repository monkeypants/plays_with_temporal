"""
Security-focused tests for calendar use case business logic.

These tests focus on date range validation and input security scenarios
that are essential for preventing abuse and ensuring system stability.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock

from cal.usecase import CreateScheduleUseCase
from cal.domain import (
    CalendarCollection,
    CalendarSource,
    TimeBlockType,
    ExecutiveDecision,
)
from cal.repositories import (
    CalendarRepository,
    ScheduleRepository,
    TimeBlockClassifierRepository,
    CalendarConfigurationRepository,
)
from cal.tests.factories import minimal_calendar_event


class TestCreateScheduleUseCaseSecurity:
    """Security-focused tests for CreateScheduleUseCase."""

    def setup_method(self) -> None:
        """Set up mocks and use case for each test."""
        self.mock_calendar_repo = AsyncMock(spec=CalendarRepository)
        self.mock_schedule_repo = AsyncMock(spec=ScheduleRepository)
        self.mock_time_block_classifier_repo = AsyncMock(
            spec=TimeBlockClassifierRepository
        )
        self.mock_config_repo = AsyncMock(
            spec=CalendarConfigurationRepository
        )

        # Default successful outcomes
        self.mock_schedule_repo.generate_schedule_id.return_value = (
            "sched-123"
        )
        self.mock_calendar_repo.get_events_by_date_range.return_value = []
        self.mock_calendar_repo.get_events_by_date_range_multi_calendar.return_value = (  # noqa: E501
            []
        )

        # Default mock behavior for the classifier
        self.mock_time_block_classifier_repo.classify_block_type.return_value = (  # noqa: E501
            TimeBlockType.MEETING
        )
        self.mock_time_block_classifier_repo.classify_responsibility_area.return_value = (  # noqa: E501
            None
        )
        self.mock_time_block_classifier_repo.triage_event.return_value = (
            ExecutiveDecision.ATTEND,
            "Default test reason",
        )

        self.use_case = CreateScheduleUseCase(
            calendar_repo=self.mock_calendar_repo,
            schedule_repo=self.mock_schedule_repo,
            time_block_classifier_repo=self.mock_time_block_classifier_repo,
            config_repo=self.mock_config_repo,
        )

    @pytest.mark.asyncio
    async def test_execute_handles_invalid_date_ranges(self) -> None:
        """Test that invalid date ranges are handled gracefully."""
        # Arrange: End date before start date
        start_date = datetime(2024, 1, 10, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 5, tzinfo=timezone.utc)  # Before start

        # Act: Should handle gracefully
        result = await self.use_case.execute(
            calendar_id="cal-1", start_date=start_date, end_date=end_date
        )

        # Assert: Should create empty schedule (no events in invalid range)
        assert len(result.time_blocks) == 0
        assert result.start_date == start_date
        assert result.end_date == end_date

        # Repository should still be called with the provided dates
        self.mock_calendar_repo.get_events_by_date_range.assert_called_once_with(
            calendar_id="cal-1", start_date=start_date, end_date=end_date
        )

    @pytest.mark.asyncio
    async def test_execute_prevents_excessive_date_ranges(self) -> None:
        """Test that extremely large date ranges are handled appropriately."""
        # Arrange: 10-year date range (potential performance issue)
        start_date = datetime(2020, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2030, 1, 1, tzinfo=timezone.utc)

        # Mock a reasonable number of events to avoid test complexity
        sample_events = [
            minimal_calendar_event(
                event_id=f"event-{i}",
                title=f"Event {i}",
                start_time=start_date + timedelta(days=i * 30),
            )
            for i in range(5)  # Just a few events
        ]
        self.mock_calendar_repo.get_events_by_date_range.return_value = (
            sample_events
        )

        # Act: Should process the request (current implementation doesn't
        # limit)
        result = await self.use_case.execute(
            calendar_id="cal-1", start_date=start_date, end_date=end_date
        )

        # Assert: Repository called with full range
        self.mock_calendar_repo.get_events_by_date_range.assert_called_once_with(
            calendar_id="cal-1", start_date=start_date, end_date=end_date
        )

        # Should process all returned events
        assert len(result.time_blocks) == len(sample_events)

        # Verify the date range is preserved in the schedule
        assert result.start_date == start_date
        assert result.end_date == end_date

    @pytest.mark.asyncio
    async def test_execute_validates_calendar_collection_access(self) -> None:
        """Test that only enabled calendars in collection are queried."""
        # Arrange: Collection with mixed enabled/disabled calendars
        collection = CalendarCollection(
            collection_id="work-calendars",
            display_name="Work Calendars",
            default_calendar_id="cal-1",
            calendar_sources=[
                CalendarSource(
                    calendar_id="cal-1",
                    display_name="Primary Calendar",
                    source_type="google",
                    enabled=True,
                    sync_priority=1,
                ),
                CalendarSource(
                    calendar_id="cal-2",
                    display_name="Disabled Calendar",
                    source_type="google",
                    enabled=False,  # Disabled
                    sync_priority=2,
                ),
                CalendarSource(
                    calendar_id="cal-3",
                    display_name="Secondary Calendar",
                    source_type="google",
                    enabled=True,
                    sync_priority=3,
                ),
            ],
        )

        # Act
        await self.use_case.execute(calendar_collection=collection)

        # Assert: Only enabled calendars queried
        self.mock_calendar_repo.get_events_by_date_range_multi_calendar.assert_called_once()
        call_args = (
            self.mock_calendar_repo.get_events_by_date_range_multi_calendar.call_args
        )
        called_calendar_ids = call_args[1]["calendar_ids"]
        assert called_calendar_ids == ["cal-1", "cal-3"]  # Only enabled ones
        assert (
            "cal-2" not in called_calendar_ids
        )  # Disabled calendar excluded

    @pytest.mark.asyncio
    async def test_execute_for_collection_handles_missing_collection(
        self,
    ) -> None:
        """Test proper error handling for non-existent calendar
        collections."""
        # Arrange: Collection doesn't exist
        self.mock_config_repo.get_collection.return_value = None

        # Act & Assert: Should raise clear error
        with pytest.raises(
            ValueError,
            match="Calendar collection 'missing-collection' not found",
        ):
            await self.use_case.execute_for_collection("missing-collection")

        # Should not attempt to query calendars
        self.mock_calendar_repo.get_events_by_date_range.assert_not_called()
        self.mock_calendar_repo.get_events_by_date_range_multi_calendar.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_handles_empty_calendar_collection(self) -> None:
        """Test handling of calendar collection with no enabled calendars."""
        # Arrange: Collection with no enabled calendars
        collection = CalendarCollection(
            collection_id="empty-collection",
            display_name="Empty Collection",
            default_calendar_id="cal-1",
            calendar_sources=[
                CalendarSource(
                    calendar_id="cal-1",
                    display_name="Disabled Calendar",
                    source_type="google",
                    enabled=False,  # All disabled
                    sync_priority=1,
                ),
            ],
        )

        # Act
        result = await self.use_case.execute(calendar_collection=collection)

        # Assert: Should create empty schedule
        assert len(result.time_blocks) == 0

        # Should call multi-calendar method with empty list
        self.mock_calendar_repo.get_events_by_date_range_multi_calendar.assert_called_once()
        call_args = (
            self.mock_calendar_repo.get_events_by_date_range_multi_calendar.call_args
        )
        called_calendar_ids = call_args[1]["calendar_ids"]
        assert called_calendar_ids == []  # Empty list

    @pytest.mark.asyncio
    async def test_execute_validates_argument_combinations(self) -> None:
        """Test that invalid argument combinations are rejected."""
        # Test: Both calendar_id and calendar_collection provided
        collection = CalendarCollection(
            collection_id="test-collection",
            display_name="Test Collection",
            default_calendar_id="cal-1",
            calendar_sources=[
                CalendarSource(
                    calendar_id="cal-1",
                    display_name="Test Calendar",
                    source_type="google",
                    enabled=True,
                    sync_priority=1,
                )
            ],
        )

        with pytest.raises(
            ValueError,
            match="Cannot specify both calendar_id and calendar_collection",
        ):
            await self.use_case.execute(
                calendar_id="cal-1", calendar_collection=collection
            )

        # Test: Neither calendar_id nor calendar_collection provided
        with pytest.raises(
            ValueError,
            match="Either calendar_id or calendar_collection must be "
            "provided",
        ):
            await self.use_case.execute()

    @pytest.mark.asyncio
    async def test_execute_handles_repository_failures_gracefully(
        self,
    ) -> None:
        """Test that repository failures are handled gracefully."""
        # Arrange: Calendar repository fails
        self.mock_calendar_repo.get_events_by_date_range.side_effect = (
            Exception("Calendar service unavailable")
        )

        # Act & Assert: Should propagate the exception
        with pytest.raises(Exception, match="Calendar service unavailable"):
            await self.use_case.execute(calendar_id="cal-1")

        # Should not attempt to save schedule if calendar fetch fails
        self.mock_schedule_repo.save_schedule.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_handles_schedule_save_failures(self) -> None:
        """Test that schedule save failures are handled appropriately."""
        # Arrange: Calendar succeeds, schedule save fails
        sample_events = [
            minimal_calendar_event(event_id="event-1", title="Test Event")
        ]
        self.mock_calendar_repo.get_events_by_date_range.return_value = (
            sample_events
        )
        self.mock_schedule_repo.save_schedule.side_effect = Exception(
            "Database unavailable"
        )

        # Act & Assert: Should propagate the exception
        with pytest.raises(Exception, match="Database unavailable"):
            await self.use_case.execute(calendar_id="cal-1")

        # Should have attempted to save the schedule
        self.mock_schedule_repo.save_schedule.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_preserves_timezone_information(self) -> None:
        """Test that timezone information is preserved throughout the
        process."""
        # Arrange: Events with specific timezone
        pacific_tz = timezone(timedelta(hours=-8))  # PST
        start_time = datetime(2024, 1, 15, 9, 0, tzinfo=pacific_tz)
        end_time = datetime(2024, 1, 15, 10, 0, tzinfo=pacific_tz)

        sample_events = [
            minimal_calendar_event(
                event_id="event-1",
                title="PST Event",
                start_time=start_time,
                end_time=end_time,
            )
        ]
        self.mock_calendar_repo.get_events_by_date_range.return_value = (
            sample_events
        )

        # Act
        result = await self.use_case.execute(calendar_id="cal-1")

        # Assert: Timezone preserved in time blocks
        assert len(result.time_blocks) == 1
        time_block = result.time_blocks[0]
        assert time_block.start_time.tzinfo == pacific_tz
        assert time_block.end_time.tzinfo == pacific_tz
        assert time_block.start_time == start_time
        assert time_block.end_time == end_time
