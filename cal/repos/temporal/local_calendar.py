"""
Temporal activity implementation of the ScheduleRepository protocol.
Delegates calls to a concrete LocalCalendarRepository instance.
"""

import logging
from typing import Optional

from temporalio import activity

from cal.repositories import ScheduleRepository
from cal.domain import Schedule

logger = logging.getLogger(__name__)


class TemporalLocalCalendarRepository(ScheduleRepository):
    """
    Temporal Activity implementation of ScheduleRepository.
    Delegates calls to a concrete LocalCalendarRepository instance.

    This follows the three-layer repository pattern:
    1. Pure Backend (LocalCalendarRepository)
    2. Temporal Activity (TemporalLocalCalendarRepository) - this class
    3. Workflow Proxy (to be implemented)
    """

    def __init__(self, repository: ScheduleRepository):
        """
        Initialize with a concrete ScheduleRepository implementation.

        Args:
            repository: The concrete repository to delegate calls to
        """
        self._repository = repository

    @activity.defn(
        name="cal.create_schedule.schedule_repo.local.generate_schedule_id"
    )
    async def generate_schedule_id(self) -> str:
        """Activity to generate a unique schedule ID."""
        logger.info("Activity: Generating schedule ID")
        return await self._repository.generate_schedule_id()

    @activity.defn(
        name="cal.create_schedule.schedule_repo.local.save_schedule"
    )
    async def save_schedule(self, schedule: Schedule) -> None:
        """
        Activity to save a schedule.

        Args:
            schedule: The schedule to save
        """
        logger.info(
            "Activity: Saving schedule",
            extra={"schedule_id": schedule.schedule_id},
        )
        await self._repository.save_schedule(schedule)

    @activity.defn(
        name="cal.create_schedule.schedule_repo.local.get_schedule"
    )
    async def get_schedule(self, schedule_id: str) -> Optional[Schedule]:
        """
        Activity to retrieve a schedule by ID.

        Args:
            schedule_id: The ID of the schedule to retrieve

        Returns:
            The retrieved schedule or None if not found
        """
        logger.info(
            "Activity: Getting schedule", extra={"schedule_id": schedule_id}
        )
        return await self._repository.get_schedule(schedule_id)
