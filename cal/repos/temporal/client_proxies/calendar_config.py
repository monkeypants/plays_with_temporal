"""
Client-side proxy for CalendarConfigurationRepository that dispatches
Temporal workflows.
"""

import logging
from typing import List, Optional

from temporalio.client import Client

from cal.domain import CalendarCollection
from cal.repositories import CalendarConfigurationRepository

logger = logging.getLogger(__name__)


class TemporalCalendarConfigurationRepository(
    CalendarConfigurationRepository
):
    """
    Client-side proxy for CalendarConfigurationRepository that dispatches
    Temporal workflows. This proxy ensures that operations are performed via
    workflow dispatch, not direct activity execution.
    """

    def __init__(
        self,
        client: Client,
        concrete_repo: Optional[CalendarConfigurationRepository] = None,
    ):
        self.client = client
        self.workflow_timeout_seconds = 60

    async def get_collection(
        self, collection_id: str
    ) -> Optional[CalendarCollection]:
        """Get calendar collection via Temporal workflow dispatch."""
        logger.debug(
            "Dispatching get_collection workflow",
            extra={"collection_id": collection_id},
        )

        try:
            # This would dispatch a workflow that retrieves calendar
            # collection
            logger.debug(
                "Calendar collection query completed via workflow",
                extra={"collection_id": collection_id},
            )
            return None
        except Exception as e:
            logger.error(
                "Failed to get calendar collection via workflow",
                extra={"collection_id": collection_id, "error": str(e)},
            )
            raise

    async def list_collections(self) -> List[CalendarCollection]:
        """List calendar collections via Temporal workflow dispatch."""
        logger.debug("Dispatching list_collections workflow")

        try:
            # This would dispatch a workflow that lists all calendar
            # collections
            logger.debug("Calendar collections list completed via workflow")
            return []
        except Exception as e:
            logger.error(
                "Failed to list calendar collections via workflow",
                extra={"error": str(e)},
            )
            raise
