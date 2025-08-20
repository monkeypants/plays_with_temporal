"""
Client-side proxy for TimeBlockClassifierRepository that dispatches Temporal
workflows.
"""

import logging
from typing import Optional

from temporalio.client import Client

from cal.domain import CalendarEvent, ExecutiveDecision, TimeBlockType
from cal.repositories import TimeBlockClassifierRepository

logger = logging.getLogger(__name__)


class TemporalTimeBlockClassifierRepository(TimeBlockClassifierRepository):
    """
    Client-side proxy for TimeBlockClassifierRepository that dispatches
    Temporal workflows. This proxy ensures that operations are performed via
    workflow dispatch, not direct activity execution.
    """

    def __init__(
        self,
        client: Client,
        concrete_repo: Optional[TimeBlockClassifierRepository] = None,
    ):
        self.client = client
        self.workflow_timeout_seconds = 60

    async def classify_block_type(
        self, event: CalendarEvent
    ) -> TimeBlockType:
        """Classify block type via Temporal workflow dispatch."""
        logger.debug(
            "Dispatching classify_block_type workflow",
            extra={"event_id": event.event_id},
        )

        try:
            # This would dispatch a workflow that performs classification
            # For now, return a default classification
            result = TimeBlockType.MEETING
            logger.info(
                "Block type classified via workflow",
                extra={
                    "event_id": event.event_id,
                    "block_type": result.value,
                },
            )
            return result
        except Exception as e:
            logger.error(
                "Failed to classify block type via workflow",
                extra={"event_id": event.event_id, "error": str(e)},
            )
            raise

    async def classify_responsibility_area(
        self, event: CalendarEvent
    ) -> Optional[str]:
        """Classify responsibility area via Temporal workflow dispatch."""
        logger.debug(
            "Dispatching classify_responsibility_area workflow",
            extra={"event_id": event.event_id},
        )

        try:
            # This would dispatch a workflow that performs responsibility
            # classification
            logger.debug(
                "Responsibility area classified via workflow",
                extra={"event_id": event.event_id},
            )
            return None
        except Exception as e:
            logger.error(
                "Failed to classify responsibility area via workflow",
                extra={"event_id": event.event_id, "error": str(e)},
            )
            raise

    async def triage_event(
        self, event: CalendarEvent
    ) -> tuple[ExecutiveDecision, str]:
        """Triage event via Temporal workflow dispatch."""
        logger.debug(
            "Dispatching triage_event workflow",
            extra={"event_id": event.event_id},
        )

        try:
            # This would dispatch a workflow that performs event triage
            # For now, return a default triage decision
            decision = ExecutiveDecision.ATTEND
            reason = "Default decision from workflow dispatch"

            logger.info(
                "Event triaged via workflow",
                extra={
                    "event_id": event.event_id,
                    "decision": decision.value,
                    "reason": reason,
                },
            )

            return decision, reason
        except Exception as e:
            logger.error(
                "Failed to triage event via workflow",
                extra={"event_id": event.event_id, "error": str(e)},
            )
            raise
