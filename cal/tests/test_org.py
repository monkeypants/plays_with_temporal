import unittest
from datetime import datetime, timedelta, timezone

from cal.domain import TimeBlockType, ExecutiveDecision
from cal.org import generate_org_content
from cal.tests.factories import minimal_schedule, minimal_time_block


# Helper to create datetime objects
def dt(i: int) -> datetime:
    # Monday July 22, 2024
    return datetime(2024, 7, 22, i, 0, 0, tzinfo=timezone.utc)


class TestOrgGenerator(unittest.TestCase):
    def _create_schedule(self, blocks):
        """Helper to create a schedule for testing."""
        return minimal_schedule(
            schedule_id="sched1",
            start_date=dt(0),
            end_date=dt(0) + timedelta(days=1),
            time_blocks=blocks,
        )

    def test_generate_org_content_with_timed_event(self):
        """Tests org content for a timed event with time range."""
        block = minimal_time_block(
            time_block_id="1",
            title="Team Meeting",
            start_time=dt(9),
            end_time=dt(10),
            type=TimeBlockType.MEETING,
            suggested_decision=ExecutiveDecision.ATTEND,
            decision_reason="Important meeting",
            metadata={
                "location": "Conference Room A",
                "organizer": "manager@company.com",
                "attendee_count": 5,
                "status": "confirmed",
            },
        )
        schedule = self._create_schedule([block])
        content = generate_org_content(schedule)
        # Should include time range in SCHEDULED property
        self.assertIn("SCHEDULED: <2024-07-22 Mon 09:00-10:00>", content)
        self.assertIn("* Team Meeting", content)
        # Should include metadata
        self.assertIn("*Location*: Conference Room A", content)
        self.assertIn("** Organizer manager@company.com", content)
        self.assertIn("*Attendees*: 5 people", content)
        self.assertIn("*Status*: confirmed", content)

    def test_generate_org_content_with_all_day_event(self):
        """Tests org-mode content for an all-day event with a time range."""
        block = minimal_time_block(
            time_block_id="2",
            title="Public Holiday",
            start_time=dt(0),
            end_time=dt(0) + timedelta(days=1),
            type=TimeBlockType.PERSONAL,
            suggested_decision=ExecutiveDecision.ATTEND,
            decision_reason="Holiday observance",
            metadata={
                "all_day": True,
                "description": "National holiday - office closed",
            },
        )
        schedule = self._create_schedule([block])
        content = generate_org_content(schedule)
        # All-day events should show time range
        self.assertIn("SCHEDULED: <2024-07-22 Mon 00:00-00:00>", content)
        self.assertIn("* Public Holiday", content)
        # Should include all-day indicator and description
        self.assertIn("*All Day*: Yes", content)
        self.assertIn("National holiday - office closed", content)

    def test_generate_org_content_multiple_events_are_sorted(self):
        """Tests that multiple time blocks are sorted by start time."""
        block2 = minimal_time_block(
            time_block_id="2",
            title="Afternoon Sync",
            start_time=dt(14),
            end_time=dt(15),
            type=TimeBlockType.MEETING,
            suggested_decision=ExecutiveDecision.ATTEND,
            decision_reason="Team sync",
        )
        block1 = minimal_time_block(
            time_block_id="1",
            title="Morning Standup",
            start_time=dt(9),
            end_time=dt(10),
            type=TimeBlockType.MEETING,
            suggested_decision=ExecutiveDecision.ATTEND,
            decision_reason="Daily standup",
        )
        schedule = self._create_schedule([block1, block2])
        content = generate_org_content(schedule)
        # Should include time ranges and be sorted
        self.assertIn("SCHEDULED: <2024-07-22 Mon 09:00-10:00>", content)
        self.assertIn("SCHEDULED: <2024-07-22 Mon 14:00-15:00>", content)
        # Check order by finding positions
        morning_pos = content.find("Morning Standup")
        afternoon_pos = content.find("Afternoon Sync")
        self.assertLess(morning_pos, afternoon_pos)

    def test_title_sanitation(self):
        """Tests that titles are sanitized and time ranges work."""
        block = minimal_time_block(
            time_block_id="1",
            title="  Meeting\nwith newlines  ",
            start_time=dt(9),
            end_time=dt(10),
            type=TimeBlockType.MEETING,
            suggested_decision=ExecutiveDecision.ATTEND,
            decision_reason="Important meeting",
        )
        schedule = self._create_schedule([block])
        content = generate_org_content(schedule)
        # Title should be sanitized and time range should be present
        self.assertIn("* Meeting with newlines", content)
        self.assertIn("SCHEDULED: <2024-07-22 Mon 09:00-10:00>", content)

    def test_empty_title(self):
        """Tests that an empty title is handled with time range."""
        block = minimal_time_block(
            time_block_id="1",
            title=" ",
            start_time=dt(9),
            end_time=dt(10),
            type=TimeBlockType.MEETING,
            suggested_decision=ExecutiveDecision.ATTEND,
            decision_reason="Meeting",
        )
        schedule = self._create_schedule([block])
        content = generate_org_content(schedule)
        # Should handle empty title and show time range
        self.assertIn("* Untitled Event", content)
        self.assertIn("SCHEDULED: <2024-07-22 Mon 09:00-10:00>", content)
