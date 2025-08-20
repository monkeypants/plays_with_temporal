"""
Temporal Activity implementation of TimeBlockClassifierRepository.
"""

import logging
from typing import Optional

from temporalio import activity

from ...domain import CalendarEvent, ExecutiveDecision, TimeBlockType
from ...repos.local.time_block_classifier import (
    LocalTimeBlockClassifierRepository,
)
from ...repositories import TimeBlockClassifierRepository

logger = logging.getLogger(__name__)


class TemporalLocalTimeBlockClassifierRepository(
    TimeBlockClassifierRepository
):
    """
    Temporal Activity implementation of TimeBlockClassifierRepository.
    Delegates calls to a concrete LocalTimeBlockClassifierRepository instance.

    This follows the three-layer repository pattern:
    1. Pure Backend (LocalTimeBlockClassifierRepository)
    2. Temporal Activity (TemporalLocalTimeBlockClassifierRepository)
    3. Workflow Proxy (WorkflowTimeBlockClassifierRepositoryProxy)
    """

    def __init__(self, repo: LocalTimeBlockClassifierRepository):
        self._repo = repo
        logger.info(
            "TemporalLocalTimeBlockClassifierRepository initialized with %s",
            repo.__class__.__name__,
        )

    @activity.defn(
        name="cal.create_schedule.time_block_classifier_repo.local.classify_block_type"
    )
    async def classify_block_type(
        self, event: CalendarEvent
    ) -> TimeBlockType:
        """Activity wrapper for classify_block_type."""
        return await self._repo.classify_block_type(event)

    @activity.defn(
        name="cal.create_schedule.time_block_classifier_repo.local.classify_responsibility_area"
    )
    async def classify_responsibility_area(
        self, event: CalendarEvent
    ) -> Optional[str]:
        """Activity wrapper for classify_responsibility_area."""
        return await self._repo.classify_responsibility_area(event)

    @activity.defn(
        name="cal.create_schedule.time_block_classifier_repo.local.triage_event"
    )
    async def triage_event(
        self, event: CalendarEvent
    ) -> tuple[ExecutiveDecision, str]:
        """Activity wrapper for triage_event."""
        return await self._repo.triage_event(event)
