"""
Temporal workflows for calendar operations.

Workflows orchestrate the business logic and activities
in a deterministic manner.
"""

from datetime import datetime
from typing import Optional, Literal

import logging

# Re-import these at module level for clarity and consistency,
# ensuring they are always available.
# from datetime import datetime # Already imported
# from typing import Optional, Literal # Already imported

from temporalio import workflow

from .repositories import CalendarRepository
from .repos.temporal.proxies.schedule import WorkflowScheduleRepositoryProxy
from .repos.temporal.proxies.time_block_classifier import (
    WorkflowTimeBlockClassifierRepositoryProxy,
)
from .repos.temporal.proxies.postgresql_calendar import (
    WorkflowPostgreSQLCalendarRepositoryProxy,
)
from .repos.temporal.proxies.google_calendar import (
    WorkflowGoogleCalendarRepositoryProxy,
)
from .repos.temporal.proxies.calendar import (
    WorkflowMockCalendarRepositoryProxy,
)
from .repos.temporal.proxies.calendar_config import (
    WorkflowCalendarConfigurationRepositoryProxy,
)
from util.repos.temporal.proxies.file_storage import (
    WorkflowFileStorageRepositoryProxy,
)

logger = logging.getLogger(__name__)


@workflow.defn
class CalendarSyncWorkflow:
    """
    Workflow that orchestrates the synchronization of calendar data from
    Google Calendar to PostgreSQL storage.

    This workflow follows the saga pattern with proper compensation for
    partial failures, ensuring data consistency across sync operations.
    """

    @workflow.run
    async def run(
        self,
        source_calendar_id: str,
        sink_calendar_id: str,
        full_sync: bool = False,
    ) -> bool:
        """
        Executes the calendar sync workflow.

        Args:
            source_calendar_id: ID of the source calendar (e.g., Google
                Calendar)
            sink_calendar_id: ID of the sink calendar (PostgreSQL storage)
            full_sync: Whether to perform full sync (ignore sync tokens)

        Returns:
            True if sync completed successfully, False otherwise
        """
        logger.info(
            "Starting CalendarSyncWorkflow",
            extra={
                "source_calendar_id": source_calendar_id,
                "sink_calendar_id": sink_calendar_id,
                "full_sync": full_sync,
            },
        )

        # Create repository proxies following the established pattern
        google_calendar_repo = WorkflowGoogleCalendarRepositoryProxy()
        postgresql_calendar_repo = WorkflowPostgreSQLCalendarRepositoryProxy()
        file_storage_repo = WorkflowFileStorageRepositoryProxy()

        # Import use case at module level to allow for patching in tests
        from cal.usecase import CalendarSyncUseCase

        # Create use case with repository dependencies
        sync_use_case = CalendarSyncUseCase(
            source_repo=google_calendar_repo,
            sink_repo=postgresql_calendar_repo,
            file_storage_repo=file_storage_repo,
        )

        try:
            # Execute the sync use case
            await sync_use_case.execute(
                source_calendar_id=source_calendar_id,
                sink_calendar_id=sink_calendar_id,
                full_sync=full_sync,
            )

            logger.info(
                "CalendarSyncWorkflow completed successfully",
                extra={
                    "source_calendar_id": source_calendar_id,
                    "sink_calendar_id": sink_calendar_id,
                },
            )
            return True

        except Exception as e:
            logger.error(
                "CalendarSyncWorkflow failed",
                extra={
                    "source_calendar_id": source_calendar_id,
                    "sink_calendar_id": sink_calendar_id,
                    "error": str(e),
                },
                exc_info=True,
            )
            return False


@workflow.defn
class PublishScheduleWorkflow:
    """
    Workflow that orchestrates the creation of a schedule from calendar events
    and publishes it to an org-mode file.

    This workflow follows the pattern established in systemPatterns.md:
    1. Use a use case to handle business logic
    2. Delegate non-deterministic operations (file I/O) to activities
    """

    @workflow.run
    async def run(
        self,
        calendar_id: str,
        output_path: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        calendar_source_type: Literal["google", "postgresql", "mock"] = (
            "mock"
        ),
    ) -> bool:
        # Validate calendar_source_type early
        valid_types = {"google", "postgresql", "mock"}
        if calendar_source_type not in valid_types:
            logger.warning(
                f"Unsupported calendar_source_type: {calendar_source_type}. "
                f"Valid types are: {valid_types}"
            )
            return False
        """
        Executes the workflow to create and publish a schedule.

        Args:
            calendar_id: ID of the calendar to create a schedule from
            output_path: Path where the org file should be written
            start_date: Optional start date for the schedule
            end_date: Optional end date for the schedule
            calendar_source_type: Explicitly specify the type of calendar
                                  repository to use (e.g., "google",
                                  "mock"). Defaults to "mock" for
                                  testing/demo purposes.

        Returns:
            True if successful, False otherwise
        """
        logger.info(
            "Starting PublishScheduleWorkflow",
            extra={
                "calendar_id": calendar_id,
                "output_path": output_path,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
                "calendar_source_type": calendar_source_type,
            },
        )

        # Create deterministic repository proxies
        schedule_repo = WorkflowScheduleRepositoryProxy()
        time_block_classifier_repo = (
            WorkflowTimeBlockClassifierRepositoryProxy()
        )
        config_repo = WorkflowCalendarConfigurationRepositoryProxy()

        # Determine which CalendarRepository proxy to use based on source type
        calendar_repo: CalendarRepository
        if calendar_source_type == "google":
            calendar_repo = WorkflowGoogleCalendarRepositoryProxy()
        elif calendar_source_type == "postgresql":
            calendar_repo = WorkflowPostgreSQLCalendarRepositoryProxy()
        else:  # calendar_source_type == "mock"
            calendar_repo = WorkflowMockCalendarRepositoryProxy()

        # Use the use case with proper repository dependency injection
        # Import at module level to allow for patching in tests
        from cal.usecase import CreateScheduleUseCase

        use_case = CreateScheduleUseCase(
            calendar_repo=calendar_repo,
            schedule_repo=schedule_repo,
            time_block_classifier_repo=time_block_classifier_repo,
            config_repo=config_repo,  # Use the proxy for config
        )

        # Execute the use case - this follows Clean Architecture principles
        schedule = await use_case.execute(
            calendar_id=calendar_id,
            start_date=start_date,
            end_date=end_date,
        )

        # 2. Write the schedule to an org file using an activity
        result = await workflow.execute_activity(
            "cal.publish_schedule.org_file_writer.local.write_schedule_to_org_file",
            [
                schedule.schedule_id,
                output_path,
            ],
            start_to_close_timeout=workflow.timedelta(seconds=30),
        )

        logger.info(
            "PublishScheduleWorkflow completed", extra={"result": result}
        )

        return bool(result)
