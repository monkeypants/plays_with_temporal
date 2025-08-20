import json
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock

from cal.domain import (
    ExecutiveDecision,
    Schedule,
    ScheduleStatus,
    TimeBlockType,
)
from cal.repositories import (
    CalendarRepository,
    ScheduleRepository,
    TimeBlockClassifierRepository,
    CalendarConfigurationRepository,
)
from util.repositories import FileStorageRepository
from cal.usecase import CreateScheduleUseCase
from cal.tests.factories import minimal_calendar_event


def dt(hour: int) -> datetime:
    """Helper function to create datetime objects for testing."""
    return datetime(2024, 1, 1, hour, 0, 0, tzinfo=timezone.utc)


class TestCreateScheduleUseCase(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        """Set up mocks and the use case instance for each test."""
        self.calendar_repo = AsyncMock(spec=CalendarRepository)
        self.schedule_repo = AsyncMock(spec=ScheduleRepository)
        self.time_block_classifier_repo = AsyncMock(
            spec=TimeBlockClassifierRepository
        )
        self.config_repo = AsyncMock(spec=CalendarConfigurationRepository)
        self.file_storage_repo = AsyncMock(spec=FileStorageRepository)

        # Default mock behavior for the classifier
        self.time_block_classifier_repo.classify_block_type.return_value = (
            TimeBlockType.MEETING
        )
        self.time_block_classifier_repo.classify_responsibility_area.return_value = (  # noqa: E501
            None
        )
        self.time_block_classifier_repo.triage_event.return_value = (
            ExecutiveDecision.ATTEND,
            "Default test reason",
        )

        self.use_case = CreateScheduleUseCase(
            calendar_repo=self.calendar_repo,
            schedule_repo=self.schedule_repo,
            time_block_classifier_repo=self.time_block_classifier_repo,
            config_repo=self.config_repo,
        )

        # Set up CalendarSyncUseCase for testing file storage integration
        self.sync_use_case = None  # Will be created in tests that need it

    async def test_execute_creates_schedule_with_default_dates(self) -> None:
        """
        Tests that the use case creates a schedule for today when no dates
        provided.
        """
        # Arrange - create events for today so they pass the date filter
        base_time = datetime.now(tz=timezone.utc).replace(
            hour=9, minute=0, second=0, microsecond=0
        )

        # Create two distinct events with different times using factories
        event1 = minimal_calendar_event(
            event_id="1",
            calendar_id="source_calendar",
            title="Event 1",
            start_time=base_time,
        )
        event2 = minimal_calendar_event(
            event_id="2",
            calendar_id="source_calendar",
            title="Event 2",
            start_time=base_time.replace(hour=14),
        )
        events = [event1, event2]
        self.calendar_repo.get_events_by_date_range.return_value = events

        # Act
        await self.use_case.execute(calendar_id="test_cal")

        # Assert
        self.calendar_repo.get_events_by_date_range.assert_called_once()
        call_args = self.calendar_repo.get_events_by_date_range.call_args
        self.assertEqual(call_args[1]["calendar_id"], "test_cal")
        # Verify date range parameters are passed
        self.assertIsNotNone(call_args[1]["start_date"])
        self.assertIsNotNone(call_args[1]["end_date"])

        self.schedule_repo.save_schedule.assert_called_once()

        # Verify the schedule was created correctly
        saved_schedule = self.schedule_repo.save_schedule.call_args[0][0]
        self.assertIsInstance(saved_schedule, Schedule)
        self.assertEqual(len(saved_schedule.time_blocks), 2)
        self.assertEqual(saved_schedule.status, ScheduleStatus.DRAFT)

        # Verify time blocks were created from events
        time_block_titles = [tb.title for tb in saved_schedule.time_blocks]
        self.assertIn("Event 1", time_block_titles)
        self.assertIn("Event 2", time_block_titles)

    async def test_execute_creates_schedule_with_custom_dates(self) -> None:
        """
        Tests that the use case creates a schedule for specified date range.
        """
        # Arrange
        start_date = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 1, 23, 59, 59, tzinfo=timezone.utc)

        events = [
            minimal_calendar_event(
                event_id="1", title="Event 1", start_time=dt(9)
            ),
            minimal_calendar_event(
                event_id="2", title="Event 2", start_time=dt(14)
            ),
        ]
        self.calendar_repo.get_events_by_date_range.return_value = events

        # Act
        await self.use_case.execute(
            calendar_id="test_cal", start_date=start_date, end_date=end_date
        )

        # Assert
        self.calendar_repo.get_events_by_date_range.assert_called_once_with(
            calendar_id="test_cal", start_date=start_date, end_date=end_date
        )
        saved_schedule = self.schedule_repo.save_schedule.call_args[0][0]
        self.assertEqual(saved_schedule.start_date, start_date)
        self.assertEqual(saved_schedule.end_date, end_date)
        self.time_block_classifier_repo.classify_block_type.assert_called()
        self.time_block_classifier_repo.classify_responsibility_area.assert_called()

    async def test_execute_filters_events_by_date_range(self) -> None:
        """
        Tests that the repository is called with the correct date range.
        Note: The actual filtering is now done by the repository, not the
        use case.
        """
        # Arrange
        start_date = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 1, 23, 59, 59, tzinfo=timezone.utc)

        # Repository should return only events in range
        event_in_range = minimal_calendar_event(
            event_id="1",
            title="Event In Range",
            start_time=datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
        )

        events = [event_in_range]
        self.calendar_repo.get_events_by_date_range.return_value = events

        # Act
        await self.use_case.execute(
            calendar_id="test_cal", start_date=start_date, end_date=end_date
        )

        # Assert
        self.calendar_repo.get_events_by_date_range.assert_called_once_with(
            calendar_id="test_cal", start_date=start_date, end_date=end_date
        )
        saved_schedule = self.schedule_repo.save_schedule.call_args[0][0]
        self.assertEqual(len(saved_schedule.time_blocks), 1)
        self.assertEqual(
            saved_schedule.time_blocks[0].title, "Event In Range"
        )

    async def test_execute_converts_events_to_time_blocks_correctly(self) -> None:
        """
        Tests that calendar events are correctly converted to time blocks.
        """
        # Arrange - create event for today so it passes the date filter
        today = datetime.now(tz=timezone.utc).replace(
            hour=10, minute=0, second=0, microsecond=0
        )
        event = minimal_calendar_event(
            event_id="1", title="Test Event", start_time=today
        )
        self.calendar_repo.get_events_by_date_range.return_value = [event]

        # Act
        await self.use_case.execute(calendar_id="test_cal")

        # Assert
        saved_schedule = self.schedule_repo.save_schedule.call_args[0][0]
        time_block = saved_schedule.time_blocks[0]

        self.assertEqual(time_block.title, event.title)
        self.assertEqual(time_block.start_time, event.start_time)
        self.assertEqual(time_block.end_time, event.end_time)
        # Assert that the type is determined by the classifier
        self.assertEqual(time_block.type, TimeBlockType.MEETING)
        self.assertEqual(time_block.source_calendar_event_id, event.event_id)
        self.time_block_classifier_repo.classify_block_type.assert_called_once_with(
            event
        )

    async def test_execute_handles_empty_calendar(self) -> None:
        """
        Tests that the use case handles calendars with no events.
        """
        # Arrange
        self.calendar_repo.get_events_by_date_range.return_value = []

        # Act
        await self.use_case.execute(calendar_id="test_cal")

        # Assert
        saved_schedule = self.schedule_repo.save_schedule.call_args[0][0]
        self.assertEqual(len(saved_schedule.time_blocks), 0)
        self.assertEqual(saved_schedule.status, ScheduleStatus.DRAFT)
        self.time_block_classifier_repo.classify_block_type.assert_not_called()
        self.time_block_classifier_repo.classify_responsibility_area.assert_not_called()

    async def test_execute_uses_classifier_for_time_block_type(self) -> None:
        """
        Tests that the use case calls the classifier repository to determine
        the time block type.
        """
        # Arrange
        today = datetime.now(tz=timezone.utc).replace(
            hour=10, minute=0, second=0, microsecond=0
        )
        event = minimal_calendar_event(
            event_id="1", title="Test Event", start_time=today
        )
        self.calendar_repo.get_events_by_date_range.return_value = [event]

        # Configure classifier mock to return a specific type
        self.time_block_classifier_repo.classify_block_type.return_value = (
            TimeBlockType.FOCUS_SESSION
        )

        # Act
        await self.use_case.execute(calendar_id="test_cal")

        # Assert
        saved_schedule = self.schedule_repo.save_schedule.call_args[0][0]
        time_block = saved_schedule.time_blocks[0]

        # Verify that the classifier was called with the correct event
        self.time_block_classifier_repo.classify_block_type.assert_called_once_with(
            event
        )

        # Verify that the time block type is what the classifier returned
        self.assertEqual(time_block.type, TimeBlockType.FOCUS_SESSION)

        # Verify other fields are still correct
        self.assertEqual(time_block.title, event.title)
        self.assertEqual(time_block.start_time, event.start_time)
        self.assertEqual(time_block.end_time, event.end_time)
        self.assertEqual(time_block.source_calendar_event_id, event.event_id)

        # Verify metadata is populated with event information
        self.assertIsInstance(time_block.metadata, dict)
        self.assertIn("description", time_block.metadata)
        self.assertIn("location", time_block.metadata)
        self.assertIn("organizer", time_block.metadata)
        self.assertIn("status", time_block.metadata)
        self.assertIn("calendar_id", time_block.metadata)

        # Verify metadata is populated
        self.assertIsInstance(time_block.metadata, dict)
        self.assertEqual(
            time_block.metadata.get("description"), event.description
        )
        self.assertEqual(time_block.metadata.get("location"), event.location)
        self.assertEqual(
            time_block.metadata.get("organizer"), event.organizer
        )
        self.assertEqual(
            time_block.metadata.get("status"), event.status.value
        )
        self.assertEqual(
            time_block.metadata.get("calendar_id"), event.calendar_id
        )

    async def test_execute_uses_classifier_for_responsibility_area(self) -> None:
        """
        Tests that the use case calls the classifier repository for
        responsibility area and includes it if provided.
        """
        # Arrange
        today = datetime.now(tz=timezone.utc).replace(
            hour=10, minute=0, second=0, microsecond=0
        )
        event = minimal_calendar_event(
            event_id="1", title="Test Event", start_time=today
        )
        self.calendar_repo.get_events_by_date_range.return_value = [event]

        # Configure classifier mock to return a specific responsibility area
        expected_area = "Project X"
        self.time_block_classifier_repo.classify_responsibility_area.return_value = (  # noqa: E501
            expected_area
        )

        # Act
        await self.use_case.execute(calendar_id="test_cal")

        # Assert
        saved_schedule = self.schedule_repo.save_schedule.call_args[0][0]
        time_block = saved_schedule.time_blocks[0]

        # Verify that the classifier was called with the correct event
        self.time_block_classifier_repo.classify_responsibility_area.assert_called_once_with(
            event
        )

        # NOTE: TimeBlock currently does not have a field for
        # responsibility_area.
        # This test ensures the classifier is called, but the result isn't
        # captured in TimeBlock directly yet. This would be a future
        # enhancement
        # to the TimeBlock model itself. For now, we only assert the call.
        self.assertIsNone(
            time_block.decision_notes
        )  # Just checking a random other field to ensure TimeBlock is not
        # modified for this yet.

    async def test_execute_uses_classifier_for_event_triage(self) -> None:
        """
        Tests that the use case calls the classifier repository for event
        triage and includes the results in the TimeBlock.
        """
        # Arrange
        today = datetime.now(tz=timezone.utc).replace(
            hour=10, minute=0, second=0, microsecond=0
        )
        event = minimal_calendar_event(
            event_id="1", title="Test Event", start_time=today
        )
        self.calendar_repo.get_events_by_date_range.return_value = [event]

        # Configure classifier mock to return specific triage results
        expected_decision = ExecutiveDecision.DELEGATE
        expected_reason = "Large meeting suitable for delegation"
        self.time_block_classifier_repo.triage_event.return_value = (
            expected_decision,
            expected_reason,
        )

        # Act
        await self.use_case.execute(calendar_id="test_cal")

        # Assert
        saved_schedule = self.schedule_repo.save_schedule.call_args[0][0]
        time_block = saved_schedule.time_blocks[0]

        # Verify that the classifier was called with the correct event
        self.time_block_classifier_repo.triage_event.assert_called_once_with(
            event
        )

        # Verify that the triage results are correctly stored in the
        # TimeBlock
        self.assertEqual(time_block.suggested_decision, expected_decision)
        self.assertEqual(time_block.decision_reason, expected_reason)

        # Verify other fields are still correct
        self.assertEqual(time_block.title, event.title)
        self.assertEqual(time_block.start_time, event.start_time)
        self.assertEqual(time_block.end_time, event.end_time)
        self.assertEqual(time_block.source_calendar_event_id, event.event_id)

    async def test_execute_handles_multiple_events_with_triage(self) -> None:
        """
        Tests that the use case correctly applies triage to multiple events.
        """
        # Arrange
        today = datetime.now(tz=timezone.utc).replace(
            hour=9, minute=0, second=0, microsecond=0
        )

        event1 = minimal_calendar_event(
            event_id="1", title="Morning Standup", start_time=today
        )
        event2 = minimal_calendar_event(
            event_id="2",
            title="Large Team Meeting",
            start_time=today.replace(hour=14),
        )
        self.calendar_repo.get_events_by_date_range.return_value = [
            event1,
            event2,
        ]

        # Configure classifier mock to return different decisions for each
        # event
        def mock_triage_event(event: Any) -> tuple[ExecutiveDecision, str]:
            if "Standup" in event.title:
                return ExecutiveDecision.ATTEND, "Important team coordination"
            else:
                return ExecutiveDecision.DELEGATE, "Large meeting"

        self.time_block_classifier_repo.triage_event.side_effect = (
            mock_triage_event
        )

        # Act
        await self.use_case.execute(calendar_id="test_cal")

        # Assert
        saved_schedule = self.schedule_repo.save_schedule.call_args[0][0]
        self.assertEqual(len(saved_schedule.time_blocks), 2)

        # Verify triage was called for both events
        self.assertEqual(
            self.time_block_classifier_repo.triage_event.call_count, 2
        )

        # Find time blocks by title (they should be sorted by start time)
        standup_block = next(
            tb for tb in saved_schedule.time_blocks if "Standup" in tb.title
        )
        meeting_block = next(
            tb
            for tb in saved_schedule.time_blocks
            if "Large Team Meeting" in tb.title
        )

        # Verify different triage results
        self.assertEqual(
            standup_block.suggested_decision, ExecutiveDecision.ATTEND
        )
        self.assertEqual(
            standup_block.decision_reason, "Important team coordination"
        )

        self.assertEqual(
            meeting_block.suggested_decision, ExecutiveDecision.DELEGATE
        )
        self.assertEqual(meeting_block.decision_reason, "Large meeting")

    async def test_calendar_sync_use_case_with_file_storage(self) -> None:
        """
        Tests that CalendarSyncUseCase correctly handles file storage for
        large payloads.
        """
        # Arrange
        from cal.usecase import CalendarSyncUseCase
        from cal.repositories import CalendarChanges, SyncState

        source_repo = AsyncMock(spec=CalendarRepository)
        sink_repo = AsyncMock(spec=CalendarRepository)
        file_storage_repo = AsyncMock(spec=FileStorageRepository)

        sync_use_case = CalendarSyncUseCase(
            source_repo=source_repo,
            sink_repo=sink_repo,
            file_storage_repo=file_storage_repo,
        )

        # Mock source repo to return changes with file ID
        mock_changes = CalendarChanges(
            upserted_events=[],  # Empty list
            upserted_events_file_id="test-file-id-123",
            deleted_event_ids=[],
            new_sync_state=SyncState(sync_token="new-token"),
        )
        source_repo.get_changes.return_value = mock_changes

        # Mock file storage to return serialized events
        test_events = [
            minimal_calendar_event(event_id="1", title="Test Event 1"),
            minimal_calendar_event(event_id="2", title="Test Event 2"),
        ]
        events_json = json.dumps(
            [event.model_dump(mode="json") for event in test_events]
        )
        file_storage_repo.download_file.return_value = events_json.encode(
            "utf-8"
        )

        # Mock sink repo methods
        sink_repo.get_sync_state.return_value = None
        sink_repo.get_events_by_ids.return_value = []  # No existing events
        sink_repo.apply_changes.return_value = None
        sink_repo.store_sync_state.return_value = None

        # Act
        await sync_use_case.execute(
            source_calendar_id="source-cal",
            sink_calendar_id="sink-cal",
            full_sync=False,
        )

        # Assert
        # Verify file storage was called to download events
        file_storage_repo.download_file.assert_called_once_with(
            "test-file-id-123"
        )

        # Verify sink repo was called with the deserialized events
        sink_repo.apply_changes.assert_called_once()
        call_args = sink_repo.apply_changes.call_args
        events_to_create = call_args[1]["events_to_create"]

        # Should have 2 events to create (since sink had no existing events)
        self.assertEqual(len(events_to_create), 2)
        self.assertEqual(events_to_create[0].title, "Test Event 1")
        self.assertEqual(events_to_create[1].title, "Test Event 2")

    async def test_calendar_sync_use_case_without_file_storage(self) -> None:
        """
        Tests that CalendarSyncUseCase works normally when no file ID is
        present.
        """
        # Arrange
        from cal.usecase import CalendarSyncUseCase
        from cal.repositories import CalendarChanges, SyncState

        source_repo = AsyncMock(spec=CalendarRepository)
        sink_repo = AsyncMock(spec=CalendarRepository)
        file_storage_repo = AsyncMock(spec=FileStorageRepository)

        sync_use_case = CalendarSyncUseCase(
            source_repo=source_repo,
            sink_repo=sink_repo,
            file_storage_repo=file_storage_repo,
        )

        # Mock source repo to return changes without file ID (direct events)
        test_events = [
            minimal_calendar_event(event_id="1", title="Direct Event")
        ]
        mock_changes = CalendarChanges(
            upserted_events=test_events,
            upserted_events_file_id=None,  # No file ID
            deleted_event_ids=[],
            new_sync_state=SyncState(sync_token="new-token"),
        )
        source_repo.get_changes.return_value = mock_changes

        # Mock sink repo methods
        sink_repo.get_sync_state.return_value = None
        sink_repo.get_events_by_ids.return_value = []
        sink_repo.apply_changes.return_value = None
        sink_repo.store_sync_state.return_value = None

        # Act
        await sync_use_case.execute(
            source_calendar_id="source-cal",
            sink_calendar_id="sink-cal",
            full_sync=False,
        )

        # Assert
        # File storage should NOT be called
        file_storage_repo.download_file.assert_not_called()

        # Sink repo should still be called with direct events
        sink_repo.apply_changes.assert_called_once()
        call_args = sink_repo.apply_changes.call_args
        events_to_create = call_args[1]["events_to_create"]

        self.assertEqual(len(events_to_create), 1)
        self.assertEqual(events_to_create[0].title, "Direct Event")
