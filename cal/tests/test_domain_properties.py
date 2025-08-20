"""
Property-based tests for calendar domain models.

These tests use Hypothesis to generate a wide range of inputs and verify that
domain model validation rules work correctly across all valid and invalid
cases. This complements the existing unit tests by providing broader coverage
and discovering edge cases.
"""

from datetime import datetime, timezone, timedelta
from hypothesis import given, strategies as st, example
from hypothesis.strategies import composite

from cal.domain import (
    CalendarEvent,
    CalendarEventStatus,
    Attendee,
    AttendeeResponseStatus,
    TimeBlock,
    TimeBlockType,
    TimeBlockDecision,
    ExecutiveDecision,
    Schedule,
    ScheduleStatus,
)


# Custom strategies for domain-specific types


@composite
def timezone_aware_datetime(draw):
    """Generate timezone-aware datetime objects."""
    # Generate a datetime in UTC
    dt = draw(
        st.datetimes(
            min_value=datetime(2020, 1, 1),
            max_value=datetime(2030, 12, 31),
            timezones=st.just(timezone.utc),
        )
    )
    return dt


@composite
def valid_time_range(draw):
    """Generate valid start/end time pairs where end > start."""
    start_time = draw(timezone_aware_datetime())
    # Ensure end time is after start time (minimum 1 minute)
    duration_minutes = draw(st.integers(min_value=1, max_value=24 * 60))
    end_time = start_time + timedelta(minutes=duration_minutes)
    return start_time, end_time


@composite
def attendee_strategy(draw):
    """Generate valid Attendee objects."""
    email = draw(st.emails())
    display_name = draw(
        st.one_of(st.none(), st.text(min_size=1, max_size=100))
    )
    response_status = draw(st.sampled_from(AttendeeResponseStatus))

    return Attendee(
        email=email,
        display_name=display_name,
        response_status=response_status,
    )


@composite
def calendar_event_strategy(draw):
    """Generate valid CalendarEvent objects."""
    event_id = draw(st.text(min_size=1, max_size=100))
    calendar_id = draw(st.text(min_size=1, max_size=100))
    title = draw(
        st.text(min_size=1, max_size=200).filter(lambda x: x.strip())
    )
    description = draw(st.one_of(st.none(), st.text(max_size=1000)))

    start_time, end_time = draw(valid_time_range())

    all_day = draw(st.booleans())
    location = draw(st.one_of(st.none(), st.text(max_size=200)))
    status = draw(st.sampled_from(CalendarEventStatus))

    attendees = draw(st.lists(attendee_strategy(), max_size=20))
    organizer = draw(st.one_of(st.none(), st.emails()))

    last_modified = draw(timezone_aware_datetime())
    etag = draw(st.one_of(st.none(), st.text(max_size=100)))

    return CalendarEvent(
        event_id=event_id,
        calendar_id=calendar_id,
        title=title,
        description=description,
        start_time=start_time,
        end_time=end_time,
        all_day=all_day,
        location=location,
        status=status,
        attendees=attendees,
        organizer=organizer,
        last_modified=last_modified,
        etag=etag,
    )


@composite
def time_block_strategy(draw):
    """Generate valid TimeBlock objects."""
    time_block_id = draw(st.text(min_size=1, max_size=100))
    title = draw(st.text(min_size=1, max_size=200))

    start_time, end_time = draw(valid_time_range())

    block_type = draw(st.sampled_from(TimeBlockType))
    suggested_decision = draw(
        st.one_of(st.none(), st.sampled_from(ExecutiveDecision))
    )
    decision_reason = draw(st.one_of(st.none(), st.text(max_size=500)))
    decision = draw(st.sampled_from(TimeBlockDecision))
    decision_notes = draw(st.one_of(st.none(), st.text(max_size=500)))
    delegated_to = draw(st.one_of(st.none(), st.emails()))

    source_calendar_event_id = draw(
        st.one_of(st.none(), st.text(max_size=100))
    )
    meeting_id = draw(st.one_of(st.none(), st.text(max_size=100)))

    metadata = draw(
        st.dictionaries(
            st.text(max_size=50), st.text(max_size=200), max_size=10
        )
    )

    created_at = draw(st.one_of(st.none(), timezone_aware_datetime()))
    last_updated_at = draw(st.one_of(st.none(), timezone_aware_datetime()))

    return TimeBlock(
        time_block_id=time_block_id,
        title=title,
        start_time=start_time,
        end_time=end_time,
        type=block_type,
        suggested_decision=suggested_decision,
        decision_reason=decision_reason,
        decision=decision,
        decision_notes=decision_notes,
        delegated_to=delegated_to,
        source_calendar_event_id=source_calendar_event_id,
        meeting_id=meeting_id,
        metadata=metadata,
        created_at=created_at,
        last_updated_at=last_updated_at,
    )


# Property tests for CalendarEvent


class TestCalendarEventProperties:
    """Property-based tests for CalendarEvent validation rules."""

    @given(calendar_event_strategy())
    def test_calendar_event_creation_with_valid_data(self, event):
        """Property: Valid CalendarEvent data should always create valid
        objects."""
        # If we can create the event, it should have all required fields
        assert event.event_id
        assert event.calendar_id
        assert event.title
        assert event.start_time.tzinfo is not None  # Must be timezone-aware
        assert event.end_time.tzinfo is not None  # Must be timezone-aware
        assert event.end_time > event.start_time  # End after start
        assert isinstance(event.attendees, list)
        assert event.status in CalendarEventStatus

    @given(
        st.text(min_size=1, max_size=100),  # event_id
        st.text(min_size=1, max_size=100),  # calendar_id
        st.text(min_size=1, max_size=200),  # title
        timezone_aware_datetime(),  # start_time
        timezone_aware_datetime(),  # end_time (will be invalid)
    )
    def test_calendar_event_rejects_invalid_time_ranges(
        self, event_id, calendar_id, title, start_time, raw_end_time
    ):
        """Property: CalendarEvent should handle invalid time ranges
        gracefully."""
        # Force end_time to be before or equal to start_time
        if raw_end_time > start_time:
            end_time = start_time - timedelta(
                minutes=1
            )  # Invalid: before start
        else:
            end_time = raw_end_time  # Already invalid or equal

        # The domain model should fix invalid time ranges
        event = CalendarEvent(
            event_id=event_id,
            calendar_id=calendar_id,
            title=title,
            description="",
            start_time=start_time,
            end_time=end_time,
            all_day=False,
            location="",
            status=CalendarEventStatus.CONFIRMED,
            attendees=[],
            organizer=None,
            last_modified=start_time,
            etag="",
        )

        # The validator should have fixed the invalid time range
        assert event.end_time > event.start_time

    @given(
        st.text(min_size=1, max_size=100),  # event_id
        st.text(min_size=1, max_size=100),  # calendar_id
        st.text(),  # title (can be empty or whitespace)
        timezone_aware_datetime(),  # start_time
    )
    def test_calendar_event_strips_title_whitespace(
        self, event_id, calendar_id, title, start_time
    ):
        """Property: CalendarEvent should strip whitespace from titles."""
        end_time = start_time + timedelta(hours=1)

        event = CalendarEvent(
            event_id=event_id,
            calendar_id=calendar_id,
            title=title,
            description="",
            start_time=start_time,
            end_time=end_time,
            all_day=False,
            location="",
            status=CalendarEventStatus.CONFIRMED,
            attendees=[],
            organizer=None,
            last_modified=start_time,
            etag="",
        )

        # Title should be stripped of leading/trailing whitespace
        assert event.title == title.strip()

    @given(st.lists(attendee_strategy(), max_size=50))
    def test_calendar_event_attendee_list_handling(self, attendees):
        """Property: CalendarEvent should handle any valid list of
        attendees."""
        start_time = datetime.now(timezone.utc)
        end_time = start_time + timedelta(hours=1)

        event = CalendarEvent(
            event_id="test-event",
            calendar_id="test-calendar",
            title="Test Event",
            description=None,
            start_time=start_time,
            end_time=end_time,
            all_day=False,
            location=None,
            status=CalendarEventStatus.CONFIRMED,
            attendees=attendees,
            organizer=None,
            last_modified=start_time,
            etag=None,
        )

        assert len(event.attendees) == len(attendees)
        for i, attendee in enumerate(event.attendees):
            assert attendee.email == attendees[i].email
            assert attendee.response_status in AttendeeResponseStatus


# Property tests for TimeBlock


class TestTimeBlockProperties:
    """Property-based tests for TimeBlock validation rules."""

    @given(time_block_strategy())
    def test_time_block_creation_with_valid_data(self, time_block):
        """Property: Valid TimeBlock data should always create valid
        objects."""
        assert time_block.time_block_id
        assert time_block.title
        assert time_block.start_time.tzinfo is not None
        assert time_block.end_time.tzinfo is not None
        assert time_block.end_time > time_block.start_time
        assert time_block.type in TimeBlockType
        assert time_block.decision in TimeBlockDecision
        assert isinstance(time_block.metadata, dict)

    @given(
        st.text(min_size=1, max_size=100),  # time_block_id
        st.text(min_size=1, max_size=200),  # title
        timezone_aware_datetime(),  # start_time
        st.sampled_from(TimeBlockType),  # type
    )
    def test_time_block_metadata_is_always_dict(
        self, time_block_id, title, start_time, block_type
    ):
        """Property: TimeBlock metadata should always be a dictionary."""
        end_time = start_time + timedelta(hours=1)

        # Test with no metadata provided (should default to empty dict)
        time_block = TimeBlock(
            time_block_id=time_block_id,
            title=title,
            start_time=start_time,
            end_time=end_time,
            type=block_type,
            suggested_decision=None,
            decision_reason=None,
            decision=TimeBlockDecision.PENDING_REVIEW,
            decision_notes=None,
            delegated_to=None,
            source_calendar_event_id=None,
            meeting_id=None,
        )

        assert isinstance(time_block.metadata, dict)

    @given(
        st.text(min_size=1, max_size=100),  # time_block_id
        st.text(min_size=1, max_size=200),  # title
        timezone_aware_datetime(),  # start_time
        st.sampled_from(TimeBlockType),  # type
        st.one_of(
            st.none(), st.sampled_from(ExecutiveDecision)
        ),  # suggested_decision
        st.one_of(st.none(), st.text(max_size=500)),  # decision_reason
    )
    def test_time_block_decision_fields_consistency(
        self,
        time_block_id,
        title,
        start_time,
        block_type,
        suggested_decision,
        decision_reason,
    ):
        """Property: TimeBlock decision fields should be handled
        consistently."""
        end_time = start_time + timedelta(hours=1)

        time_block = TimeBlock(
            time_block_id=time_block_id,
            title=title,
            start_time=start_time,
            end_time=end_time,
            type=block_type,
            suggested_decision=suggested_decision,
            decision_reason=decision_reason,
            decision=TimeBlockDecision.PENDING_REVIEW,
            decision_notes=None,
            delegated_to=None,
            source_calendar_event_id=None,
            meeting_id=None,
        )

        # If suggested_decision is provided, it should be preserved
        if suggested_decision is not None:
            assert time_block.suggested_decision == suggested_decision

        # Decision reason should be preserved as-is (can be None)
        assert time_block.decision_reason == decision_reason


# Property tests for Schedule


class TestScheduleProperties:
    """Property-based tests for Schedule validation rules."""

    @given(
        st.text(min_size=1, max_size=100),  # schedule_id
        timezone_aware_datetime(),  # start_date
        timezone_aware_datetime(),  # end_date (will be adjusted)
        st.lists(time_block_strategy(), max_size=20),  # time_blocks
        st.sampled_from(ScheduleStatus),  # status
    )
    def test_schedule_creation_with_valid_data(
        self, schedule_id, start_date, raw_end_date, time_blocks, status
    ):
        """Property: Valid Schedule data should always create valid
        objects."""
        # Ensure end_date is after start_date
        if raw_end_date <= start_date:
            end_date = start_date + timedelta(days=1)
        else:
            end_date = raw_end_date

        schedule = Schedule(
            schedule_id=schedule_id,
            start_date=start_date,
            end_date=end_date,
            time_blocks=time_blocks,
            status=status,
        )

        assert schedule.schedule_id == schedule_id
        assert schedule.start_date == start_date
        assert schedule.end_date == end_date
        assert schedule.end_date > schedule.start_date
        assert len(schedule.time_blocks) == len(time_blocks)
        assert schedule.status == status

    @given(
        st.text(min_size=1, max_size=100),  # schedule_id
        timezone_aware_datetime(),  # start_date
    )
    def test_schedule_with_empty_time_blocks(self, schedule_id, start_date):
        """Property: Schedule should handle empty time block lists."""
        end_date = start_date + timedelta(days=1)

        schedule = Schedule(
            schedule_id=schedule_id,
            start_date=start_date,
            end_date=end_date,
            time_blocks=[],  # Empty list
            status=ScheduleStatus.DRAFT,
        )

        assert len(schedule.time_blocks) == 0
        assert isinstance(schedule.time_blocks, list)

    @given(
        st.text(min_size=1, max_size=100),  # schedule_id
        timezone_aware_datetime(),  # base_date
        st.integers(min_value=1, max_value=30),  # duration_days
    )
    def test_schedule_date_range_properties(
        self, schedule_id, base_date, duration_days
    ):
        """Property: Schedule date ranges should be consistent."""
        start_date = base_date
        end_date = start_date + timedelta(days=duration_days)

        schedule = Schedule(
            schedule_id=schedule_id,
            start_date=start_date,
            end_date=end_date,
            status=ScheduleStatus.DRAFT,
        )

        # Date range should be preserved
        assert schedule.start_date == start_date
        assert schedule.end_date == end_date

        # Duration should be positive
        duration = schedule.end_date - schedule.start_date
        assert duration.total_seconds() > 0


# Integration property tests


class TestDomainModelIntegration:
    """Property tests for interactions between domain models."""

    @given(
        calendar_event_strategy(),
        st.text(min_size=1, max_size=100),  # time_block_id
        st.sampled_from(TimeBlockType),
    )
    def test_calendar_event_to_time_block_conversion(
        self, calendar_event, time_block_id, block_type
    ):
        """Property: CalendarEvent should convert to TimeBlock
        consistently."""
        # Simulate the conversion that happens in the use case
        time_block = TimeBlock(
            time_block_id=time_block_id,
            title=calendar_event.title,
            start_time=calendar_event.start_time,
            end_time=calendar_event.end_time,
            type=block_type,
            suggested_decision=None,
            decision_reason=None,
            decision=TimeBlockDecision.PENDING_REVIEW,
            decision_notes=None,
            delegated_to=None,
            source_calendar_event_id=calendar_event.event_id,
            meeting_id=None,
            metadata={
                "description": calendar_event.description,
                "location": calendar_event.location,
                "organizer": calendar_event.organizer,
                "attendee_count": len(calendar_event.attendees),
                "status": calendar_event.status.value,
                "calendar_id": calendar_event.calendar_id,
            },
        )

        # Verify the conversion preserved key properties
        assert time_block.title == calendar_event.title
        assert time_block.start_time == calendar_event.start_time
        assert time_block.end_time == calendar_event.end_time
        assert time_block.source_calendar_event_id == calendar_event.event_id
        assert time_block.metadata["attendee_count"] == len(
            calendar_event.attendees
        )
        assert time_block.metadata["status"] == calendar_event.status.value

    @given(
        st.lists(time_block_strategy(), min_size=1, max_size=10),
        st.text(min_size=1, max_size=100),  # schedule_id
    )
    def test_schedule_time_block_aggregation(self, time_blocks, schedule_id):
        """Property: Schedule should correctly aggregate TimeBlock
        properties."""
        # Find the overall date range from time blocks
        all_start_times = [tb.start_time for tb in time_blocks]
        all_end_times = [tb.end_time for tb in time_blocks]

        overall_start = min(all_start_times)
        overall_end = max(all_end_times)

        schedule = Schedule(
            schedule_id=schedule_id,
            start_date=overall_start,
            end_date=overall_end,
            time_blocks=time_blocks,
            status=ScheduleStatus.DRAFT,
        )

        # Schedule should contain all time blocks
        assert len(schedule.time_blocks) == len(time_blocks)

        # All time blocks should fit within the schedule date range
        for time_block in schedule.time_blocks:
            assert time_block.start_time >= schedule.start_date
            assert time_block.end_time <= schedule.end_date


# Edge case discovery tests


class TestEdgeCaseDiscovery:
    """Property tests designed to discover edge cases in domain models."""

    @given(
        st.text(min_size=1, max_size=100),
        st.text(min_size=1, max_size=100),
        st.text(min_size=0, max_size=1000),  # Can be empty
        timezone_aware_datetime(),
    )
    @example(
        "event-1",
        "cal-1",
        "",
        datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc),
    )
    @example(
        "event-2",
        "cal-2",
        "   ",
        datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
    )
    @example(
        "event-3",
        "cal-3",
        "\n\t  \n",
        datetime(2024, 1, 1, 11, 0, tzinfo=timezone.utc),
    )
    def test_calendar_event_title_edge_cases(
        self, event_id, calendar_id, title, start_time
    ):
        """Property: CalendarEvent should handle edge cases in title
        formatting."""
        end_time = start_time + timedelta(hours=1)

        event = CalendarEvent(
            event_id=event_id,
            calendar_id=calendar_id,
            title=title,
            description="",
            start_time=start_time,
            end_time=end_time,
            all_day=False,
            location="",
            status=CalendarEventStatus.CONFIRMED,
            attendees=[],
            organizer=None,
            last_modified=start_time,
            etag="",
        )

        # Title should be stripped but preserved if non-empty after stripping
        expected_title = title.strip()
        assert event.title == expected_title

    @given(
        timezone_aware_datetime(),
        st.integers(
            min_value=-1440, max_value=1440
        ),  # Minutes offset (can be negative)
    )
    def test_time_range_boundary_conditions(self, start_time, minutes_offset):
        """Property: Time range validation should handle boundary
        conditions."""
        end_time = start_time + timedelta(minutes=minutes_offset)

        event = CalendarEvent(
            event_id="boundary-test",
            calendar_id="test-cal",
            title="Boundary Test",
            description="",
            start_time=start_time,
            end_time=end_time,
            all_day=False,
            location="",
            status=CalendarEventStatus.CONFIRMED,
            attendees=[],
            organizer=None,
            last_modified=start_time,
            etag="",
        )

        # The validator should ensure end_time > start_time
        assert event.end_time > event.start_time

        # If original end_time was invalid, it should be adjusted
        if minutes_offset <= 0:
            # Should have been adjusted to be after start_time
            assert event.end_time == start_time + timedelta(hours=1)
        else:
            # Should preserve the original valid end_time
            assert event.end_time == end_time
