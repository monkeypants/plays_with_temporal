"""
Temporal Activity implementation of ScheduleRepository.
Delegates calls to a concrete PostgreSQLScheduleRepository instance.
"""

import logging
from typing import Optional

from temporalio import activity

from cal.domain import Schedule
from cal.repositories import ScheduleRepository
from cal.repos.postgresql.schedule import PostgreSQLScheduleRepository

logger = logging.getLogger(__name__)


class TemporalPostgreSQLScheduleRepository(ScheduleRepository):
    """
    Temporal Activity implementation of ScheduleRepository.
    Delegates calls to a concrete PostgreSQLScheduleRepository instance.
    """

    def __init__(self, postgresql_repo: PostgreSQLScheduleRepository):
        """
        Initialize with a concrete PostgreSQLScheduleRepository
        implementation.

        Args:
            postgresql_repo: The concrete repository to delegate calls to
        """
        self._postgresql_repo = postgresql_repo
        logger.info(
            "TemporalPostgreSQLScheduleRepository initialized with %s",
            postgresql_repo.__class__.__name__,
        )

    @activity.defn(
        name="cal.create_schedule.schedule_repo.postgresql.generate_schedule_id"
    )
    async def generate_schedule_id(self) -> str:
        """Activity to generate a unique schedule ID."""
        logger.info("Activity: Generating schedule ID")
        return await self._postgresql_repo.generate_schedule_id()

    @activity.defn(
        name="cal.create_schedule.schedule_repo.postgresql.save_schedule"
    )
    async def save_schedule(self, schedule: Schedule) -> None:
        """Activity to save a schedule."""
        logger.info(
            "Activity: Saving schedule",
            extra={"schedule_id": schedule.schedule_id},
        )
        await self._postgresql_repo.save_schedule(schedule)

    @activity.defn(
        name="cal.create_schedule.schedule_repo.postgresql.get_schedule"
    )
    async def get_schedule(self, schedule_id: str) -> Optional[Schedule]:
        """Activity to retrieve a schedule by ID."""
        logger.info(
            "Activity: Getting schedule", extra={"schedule_id": schedule_id}
        )
        return await self._postgresql_repo.get_schedule(schedule_id)
