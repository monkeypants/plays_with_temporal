"""
Local implementation of the TimeBlockClassifierRepository protocol.
Provides default classification behavior.
"""

import logging
from typing import Optional

from cal.domain import CalendarEvent, TimeBlockType, ExecutiveDecision
from cal.repositories import TimeBlockClassifierRepository

logger = logging.getLogger(__name__)


class LocalTimeBlockClassifierRepository(TimeBlockClassifierRepository):
    """
    A simple classifier that provides default values for time block
    classification.
    """

    async def classify_block_type(
        self, event: CalendarEvent
    ) -> TimeBlockType:
        """
        Defaults to MEETING type for all calendar events.
        Future implementations might use keywords, attendees, or AI.
        """
        logger.debug(
            f"Classifying block type for event: {event.title} "
            f"(ID: {event.event_id}) -> Defaulting to MEETING"
        )
        return TimeBlockType.MEETING

    async def classify_responsibility_area(
        self, event: CalendarEvent
    ) -> Optional[str]:
        """
        Currently returns None for responsibility area.
        Future implementations might analyze event content or user context.
        """
        logger.debug(
            f"Classifying responsibility area for event: {event.title} "
            f"(ID: {event.event_id}) -> Defaulting to None"
        )
        return None

    async def triage_event(
        self, event: CalendarEvent
    ) -> tuple[ExecutiveDecision, str]:
        """
        Provides basic event triage based on simple keyword analysis.
        Future implementations might use AI or more sophisticated analysis.
        """
        title_lower = event.title.lower()

        # Simple keyword-based triage logic
        if any(
            keyword in title_lower
            for keyword in ["1:1", "one-on-one", "check-in"]
        ):
            decision = ExecutiveDecision.ATTEND
            reason = (
                "One-on-one meetings are high priority for relationship "
                "building"
            )
        elif any(
            keyword in title_lower
            for keyword in ["standup", "daily", "scrum"]
        ):
            decision = ExecutiveDecision.ATTEND
            reason = (
                "Team coordination meetings are important for project "
                "alignment"
            )
        elif any(
            keyword in title_lower
            for keyword in ["all-hands", "company", "town hall"]
        ):
            decision = ExecutiveDecision.ATTEND
            reason = "Company-wide meetings provide strategic context"
        elif any(
            keyword in title_lower for keyword in ["optional", "fyi", "info"]
        ):
            decision = ExecutiveDecision.SKIP
            reason = "Optional meetings can be skipped if schedule is tight"
        elif len(event.attendees) > 10:
            decision = ExecutiveDecision.DELEGATE
            reason = "Large meetings may be suitable for delegation"
        else:
            decision = ExecutiveDecision.ATTEND
            reason = (
                "Default to attending unless specific criteria suggest "
                "otherwise"
            )

        logger.debug(
            f"Triaging event: {event.title} (ID: {event.event_id}) -> "
            f"{decision.value}: {reason}"
        )

        return decision, reason
