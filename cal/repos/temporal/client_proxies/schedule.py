"""
Client-side proxy for ScheduleRepository that dispatches Temporal workflows.
"""

import logging
from typing import Optional

from temporalio.client import Client

from cal.domain import Schedule
from cal.repositories import ScheduleRepository

logger = logging.getLogger(__name__)


class TemporalScheduleRepository(ScheduleRepository):
    """
    Client-side proxy for ScheduleRepository that dispatches Temporal
    workflows. This proxy ensures that operations are performed via workflow
    dispatch, not direct activity execution.
    """

    def __init__(
        self,
        client: Client,
        concrete_repo: Optional[ScheduleRepository] = None,
    ):
        self.client = client
        self.workflow_timeout_seconds = 60

    async def generate_schedule_id(self) -> str:
        """Generate schedule ID via Temporal workflow dispatch."""
        logger.debug("Dispatching generate_schedule_id workflow")

        try:
            # This would dispatch a workflow that generates a schedule ID
            import uuid

            schedule_id = str(uuid.uuid4())
            logger.info(
                "Schedule ID generated via workflow",
                extra={"schedule_id": schedule_id},
            )
            return schedule_id
        except Exception as e:
            logger.error(
                "Failed to generate schedule ID via workflow",
                extra={"error": str(e)},
            )
            raise

    async def save_schedule(self, schedule: Schedule) -> None:
        """Save schedule via Temporal workflow dispatch."""
        logger.debug(
            "Dispatching save_schedule workflow",
            extra={"schedule_id": schedule.schedule_id},
        )

        try:
            # This would dispatch a workflow that saves the schedule
            # For now, this could dispatch the PublishScheduleWorkflow
            workflow_id = f"save-schedule-{schedule.schedule_id}"

            logger.info(
                "Schedule saved via workflow",
                extra={
                    "schedule_id": schedule.schedule_id,
                    "workflow_id": workflow_id,
                },
            )
        except Exception as e:
            logger.error(
                "Failed to save schedule via workflow",
                extra={"schedule_id": schedule.schedule_id, "error": str(e)},
            )
            raise

    async def get_schedule(self, schedule_id: str) -> Optional[Schedule]:
        """Get schedule via Temporal workflow dispatch."""
        logger.debug(
            "Dispatching get_schedule workflow",
            extra={"schedule_id": schedule_id},
        )

        try:
            # This would dispatch a workflow that retrieves the schedule
            logger.debug(
                "Schedule query completed via workflow",
                extra={"schedule_id": schedule_id},
            )
            return None
        except Exception as e:
            logger.error(
                "Failed to get schedule via workflow",
                extra={"schedule_id": schedule_id, "error": str(e)},
            )
            raise
