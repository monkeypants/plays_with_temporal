"""
Workflow-specific proxy for CalendarConfigurationRepository.
This class is used *inside* Temporal workflows to call activities.
It ensures workflow determinism by delegating all non-deterministic
operations to activities.
"""

import logging
from typing import List, Optional

from temporalio import workflow

from cal.domain import CalendarCollection
from cal.repositories import CalendarConfigurationRepository

logger = logging.getLogger(__name__)


class WorkflowCalendarConfigurationRepositoryProxy(
    CalendarConfigurationRepository
):
    """
    Workflow implementation of CalendarConfigurationRepository that calls
    activities.
    This proxy ensures that all interactions with the
    CalendarConfigurationRepository are performed via Temporal activities,
    maintaining workflow determinism.
    """

    def __init__(self) -> None:
        self.activity_timeout = workflow.timedelta(seconds=10)
        logger.debug(
            "Initialized WorkflowCalendarConfigurationRepositoryProxy"
        )

    async def get_collection(
        self, collection_id: str
    ) -> Optional[CalendarCollection]:
        """Get a calendar collection by ID by executing an activity."""
        logger.debug(
            "Workflow: Calling get_collection activity",
            extra={"collection_id": collection_id},
        )
        raw_result = await workflow.execute_activity(
            "cal.create_schedule.config_repo.local.get_collection",
            collection_id,
            start_to_close_timeout=self.activity_timeout,
        )
        result = (
            CalendarCollection.model_validate(raw_result)
            if raw_result
            else None
        )
        logger.debug(
            "Workflow: get_collection activity completed",
            extra={
                "collection_id": collection_id,
                "found": result is not None,
            },
        )
        return result

    async def list_collections(self) -> List[CalendarCollection]:
        """List all calendar collections by executing an activity."""
        logger.debug("Workflow: Calling list_collections activity")
        raw_result = await workflow.execute_activity(
            "cal.create_schedule.config_repo.local.list_collections",
            start_to_close_timeout=self.activity_timeout,
        )
        result = [
            CalendarCollection.model_validate(collection)
            for collection in raw_result
        ]
        logger.debug(
            "Workflow: list_collections activity completed",
            extra={"count": len(result)},
        )
        return result
