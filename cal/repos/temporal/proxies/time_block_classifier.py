"""
Workflow implementation of TimeBlockClassifierRepository that calls
activities.
"""

import logging
from datetime import timedelta
from typing import Optional

from temporalio import workflow

from ....domain import CalendarEvent, ExecutiveDecision, TimeBlockType
from ....repositories import TimeBlockClassifierRepository


logger = logging.getLogger(__name__)


class WorkflowTimeBlockClassifierRepositoryProxy(
    TimeBlockClassifierRepository
):
    """
    Workflow implementation of TimeBlockClassifierRepository that calls
    activities.
    This proxy ensures that all interactions with the
    TimeBlockClassifierRepository are performed via Temporal activities,
    maintaining workflow determinism.
    """

    def __init__(self):
        # The default activity timeout.
        self._start_to_close_timeout = timedelta(seconds=10)

    async def classify_block_type(
        self, event: CalendarEvent
    ) -> TimeBlockType:
        """Calls the classify_block_type activity."""
        logger.info("Executing classify_block_type activity")
        result_str = await workflow.execute_activity(
            "cal.create_schedule.time_block_classifier_repo.local.classify_block_type",
            event,
            start_to_close_timeout=self._start_to_close_timeout,
        )
        return TimeBlockType(result_str)

    async def classify_responsibility_area(
        self, event: CalendarEvent
    ) -> Optional[str]:
        """Calls the classify_responsibility_area activity."""
        logger.info("Executing classify_responsibility_area activity")
        result = await workflow.execute_activity(
            "cal.create_schedule.time_block_classifier_repo.local.classify_responsibility_area",
            event,
            start_to_close_timeout=self._start_to_close_timeout,
        )
        return result  # type: ignore[no-any-return]

    async def triage_event(
        self, event: CalendarEvent
    ) -> tuple[ExecutiveDecision, str]:
        """Calls the triage_event activity."""
        logger.info("Executing triage_event activity")
        result_tuple = await workflow.execute_activity(
            "cal.create_schedule.time_block_classifier_repo.local.triage_event",
            event,
            start_to_close_timeout=self._start_to_close_timeout,
        )
        # Enums will be passed as their string values
        return (ExecutiveDecision(result_tuple[0]), result_tuple[1])
