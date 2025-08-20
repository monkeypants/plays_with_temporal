"""
Workflow-specific proxy for PostgreSQL ScheduleRepository.
This class is used *inside* Temporal workflows to call activities.
It ensures workflow determinism by delegating all non-deterministic
operations to activities.
"""

import logging
from typing import Optional

from temporalio import workflow

from cal.domain import Schedule
from cal.repositories import ScheduleRepository

logger = logging.getLogger(__name__)


class WorkflowPostgreSQLScheduleRepositoryProxy(ScheduleRepository):
    """
    Workflow implementation of ScheduleRepository that calls PostgreSQL
    activities.
    """

    def __init__(self):
        self.activity_timeout = workflow.timedelta(seconds=30)
        logger.debug("Initialized WorkflowPostgreSQLScheduleRepositoryProxy")

    async def generate_schedule_id(self) -> str:
        """Generate a unique schedule ID by executing an activity."""
        logger.debug(
            "Workflow: Calling postgresql generate_schedule_id activity"
        )
        result = await workflow.execute_activity(
            "cal.create_schedule.schedule_repo.postgresql.generate_schedule_id",
            start_to_close_timeout=self.activity_timeout,
        )
        logger.debug(
            "Workflow: postgresql generate_schedule_id activity completed",
            extra={"schedule_id": result},
        )
        return result  # type: ignore[no-any-return]

    async def save_schedule(self, schedule: Schedule) -> None:
        """Save a schedule by executing an activity."""
        logger.debug(
            "Workflow: Calling postgresql save_schedule activity",
            extra={"schedule_id": schedule.schedule_id},
        )
        await workflow.execute_activity(
            "cal.create_schedule.schedule_repo.postgresql.save_schedule",
            schedule,
            start_to_close_timeout=self.activity_timeout,
        )
        logger.debug(
            "Workflow: postgresql save_schedule activity completed",
            extra={"schedule_id": schedule.schedule_id},
        )

    async def get_schedule(self, schedule_id: str) -> Optional[Schedule]:
        """Retrieve a schedule by its ID by executing an activity."""
        logger.debug(
            "Workflow: Calling postgresql get_schedule activity",
            extra={"schedule_id": schedule_id},
        )
        raw_result = await workflow.execute_activity(
            "cal.create_schedule.schedule_repo.postgresql.get_schedule",
            schedule_id,
            start_to_close_timeout=self.activity_timeout,
        )

        result = None
        if raw_result is not None:
            result = Schedule.model_validate(raw_result)

        logger.debug(
            "Workflow: postgresql get_schedule activity completed",
            extra={
                "schedule_id": schedule_id,
                "found": result is not None,
                "result_type": type(result).__name__ if result else None,
            },
        )
        return result
