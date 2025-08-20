"""
Activities for calendar operations.

Activities handle non-deterministic operations like file I/O
that should not be performed directly in workflows.
"""

import logging
import os

from temporalio import activity

from .org import generate_org_content
from .repositories import ScheduleRepository

logger = logging.getLogger(__name__)


class ScheduleOrgFileWriterActivity:
    """
    Activity to write a schedule to an org-mode file.
    This class is instantiated on the worker and its method is registered as
    an activity.
    """

    def __init__(self, schedule_repo: ScheduleRepository):
        self._schedule_repo = schedule_repo

    @activity.defn(
        name="cal.publish_schedule.org_file_writer.local.write_schedule_to_org_file"
    )
    async def write_schedule_to_org_file(
        self, schedule_id: str, output_path: str
    ) -> bool:
        """
        Activity to write a schedule to an org-mode file.

        Args:
            schedule_id: ID of the schedule to fetch and format
            output_path: Path where the org file should be written

        Returns:
            True if successful, False otherwise
        """
        logger.info(
            "Writing schedule to org file",
            extra={"schedule_id": schedule_id, "output_path": output_path},
        )

        # 1. Fetch the schedule using the injected repository
        schedule = await self._schedule_repo.get_schedule(schedule_id)
        if not schedule:
            logger.error(f"Schedule not found: {schedule_id}")
            return False

        # 2. Generate org content
        org_content = generate_org_content(schedule)

        # 3. Ensure directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        # 4. Write to file
        try:
            with open(output_path, "w") as f:
                f.write(org_content)
            logger.info(
                "Successfully wrote schedule to org file",
                extra={
                    "schedule_id": schedule_id,
                    "output_path": output_path,
                },
            )
            return True
        except Exception as e:
            logger.error(
                f"Failed to write schedule to org file: {str(e)}",
                extra={
                    "schedule_id": schedule_id,
                    "output_path": output_path,
                },
                exc_info=True,
            )
            return False
