"""
Temporal worker for calendar operations.

This module sets up the Temporal worker that processes workflows and
activities for calendar operations, following the single-worker pattern
from sample/worker.py.
"""

import asyncio
import logging
import os
from typing import Optional

from temporalio.client import Client
from temporalio.worker import Worker
from temporalio.service import RPCError
from temporalio.contrib.pydantic import pydantic_data_converter

from .activities import ScheduleOrgFileWriterActivity
from .workflows import PublishScheduleWorkflow, CalendarSyncWorkflow
from .repos.local.calendar import LocalCalendarRepository
from .repos.mock.calendar import MockCalendarRepository
from .repos.local.time_block_classifier import (
    LocalTimeBlockClassifierRepository,
)
from .repos.local.calendar_config import (
    LocalCalendarConfigurationRepository,
)
from .repos.temporal.calendar_config import (
    TemporalLocalCalendarConfigurationRepository,
)
from .repos.temporal.local_calendar import (
    TemporalLocalCalendarRepository,
)
from .repos.temporal.mock_calendar import (
    TemporalMockCalendarRepository,
)
from .repos.temporal.local_time_block_classifier import (
    TemporalLocalTimeBlockClassifierRepository,
)
from util.repos.minio.file_storage import MinioFileStorageRepository
from util.repos.temporal.minio_file_storage import (
    TemporalMinioFileStorageRepository,
)

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    """Configure logging based on environment variables"""
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    # Validate log level
    numeric_level = getattr(logging, log_level, None)
    if not isinstance(numeric_level, int):
        print(f"Invalid log level: {log_level}, defaulting to INFO")
        numeric_level = logging.INFO
    else:
        pass

    log_format = os.environ.get(
        "LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    logging.basicConfig(
        level=numeric_level,
        format=log_format,
        force=True,  # Override any existing configuration
    )
    logger.info(
        "Logging configured",
        extra={"log_level": log_level, "numeric_level": numeric_level},
    )

    return None


async def get_temporal_client_with_retries(
    endpoint: str, attempts: int = 10, delay: int = 5
) -> Client:
    """Attempt to connect to Temporal with retries."""
    logger.debug(
        "Attempting to connect to Temporal",
        extra={
            "endpoint": endpoint,
            "max_attempts": attempts,
            "delay_seconds": delay,
        },
    )

    for attempt in range(attempts):
        try:
            # Use the proper Pydantic v2 data converter
            # and increase message size limit
            client = await Client.connect(
                endpoint,
                namespace="default",
                data_converter=pydantic_data_converter,
                # max_uncompressed_message_size not supported in this SDK
            )
            logger.info(
                "Successfully connected to Temporal",
                extra={
                    "endpoint": endpoint,
                    "attempt": attempt + 1,
                    "data_converter_type": type(
                        client.data_converter
                    ).__name__,
                },
            )
            return client
        except RPCError as e:
            logger.warning(
                "Failed to connect to Temporal",
                extra={
                    "endpoint": endpoint,
                    "attempt": attempt + 1,
                    "max_attempts": attempts,
                    "error": str(e),
                    "retry_in_seconds": delay,
                },
            )
            if attempt + 1 == attempts:
                logger.error(
                    "All connection attempts to Temporal failed",
                    extra={"endpoint": endpoint, "total_attempts": attempts},
                )
                raise
            await asyncio.sleep(delay)

    # This should never be reached, but mypy needs explicit handling
    raise RuntimeError("Unexpected exit from retry loop")


async def run_worker(
    temporal_address: Optional[str] = None,
    task_queue: str = "calendar-task-queue",
) -> None:
    """
    Run the Temporal worker for calendar operations.

    This consolidated worker handles both PublishScheduleWorkflow and
    CalendarSyncWorkflow, following the single-worker pattern from
    sample/worker.py.

    Args:
        temporal_address: Address of the Temporal server
        task_queue: Task queue to poll
    """
    # Setup logging first
    setup_logging()

    # Use environment variable or default
    if temporal_address is None:
        temporal_address = os.environ.get(
            "TEMPORAL_ADDRESS", "localhost:7233"
        )

    logger.info(
        "Starting consolidated calendar worker",
        extra={
            "temporal_address": temporal_address,
            "task_queue": task_queue,
        },
    )

    client = await get_temporal_client_with_retries(temporal_address)

    # 1. Instantiate pure backend repositories
    logger.debug("Instantiating pure backend repository implementations")
    local_calendar_repo_instance = LocalCalendarRepository(base_path="data")
    mock_calendar_repo_instance = MockCalendarRepository()
    time_block_classifier_repo_instance = LocalTimeBlockClassifierRepository()
    local_config_repo_instance = LocalCalendarConfigurationRepository()
    minio_file_storage_repo_instance = MinioFileStorageRepository()

    # 2. Instantiate Temporal Activity implementations, injecting pure
    # backend repos
    logger.debug("Instantiating Temporal Activity repository implementations")

    temporal_local_calendar_repo = TemporalLocalCalendarRepository(
        repository=local_calendar_repo_instance
    )
    temporal_mock_calendar_repo = TemporalMockCalendarRepository(
        repository=mock_calendar_repo_instance
    )
    temporal_time_block_classifier_repo = (
        TemporalLocalTimeBlockClassifierRepository(
            repo=time_block_classifier_repo_instance
        )
    )
    temporal_local_config_repo = TemporalLocalCalendarConfigurationRepository(
        repository=local_config_repo_instance
    )
    temporal_file_storage_repo = TemporalMinioFileStorageRepository()

    # Initialize Google Calendar repository if credentials available
    temporal_google_calendar_repo = None
    try:
        from cal.repos.google.calendar import (
            get_google_calendar_service,
            GoogleCalendarRepository,
        )
        from cal.repos.temporal.google_calendar import (
            TemporalGoogleCalendarRepository,
        )

        google_service = get_google_calendar_service()
        google_calendar_repo_instance = GoogleCalendarRepository(
            google_service
        )
        temporal_google_calendar_repo = TemporalGoogleCalendarRepository(
            google_repo=google_calendar_repo_instance,
            file_storage_repo=minio_file_storage_repo_instance,
        )
        logger.info("Google Calendar repository initialized successfully")
    except Exception as e:
        logger.warning(
            f"Could not initialize Google Calendar repository: {e}. "
            "Sync workflows will not be available."
        )

    # Initialize PostgreSQL repository if database available
    temporal_postgresql_calendar_repo = None
    temporal_postgresql_schedule_repo = None
    try:
        from cal.repos.postgresql.calendar import PostgreSQLCalendarRepository
        from cal.repos.postgresql.schedule import PostgreSQLScheduleRepository
        from cal.repos.temporal.postgresql_calendar import (
            TemporalPostgreSQLCalendarRepository,
        )
        from cal.repos.temporal.postgresql_schedule import (
            TemporalPostgreSQLScheduleRepository,
        )

        # TODO: This will fail until connection pool is implemented
        # This is tracked in cal/fixme.org
        postgresql_calendar_repo_instance = PostgreSQLCalendarRepository(
            pool=None  # type: ignore
        )
        postgresql_schedule_repo_instance = PostgreSQLScheduleRepository(
            pool=None  # type: ignore
        )
        temporal_postgresql_calendar_repo = (
            TemporalPostgreSQLCalendarRepository(
                postgresql_repo=postgresql_calendar_repo_instance
            )
        )
        temporal_postgresql_schedule_repo = (
            TemporalPostgreSQLScheduleRepository(
                postgresql_repo=postgresql_schedule_repo_instance
            )
        )
        logger.info("PostgreSQL repositories initialized successfully")
    except Exception as e:
        logger.warning(
            f"Could not initialize PostgreSQL repository: {e}. "
            "Database persistence will not be available."
        )

    # 3. Instantiate activity classes with their dependencies
    schedule_file_writer_activity = ScheduleOrgFileWriterActivity(
        schedule_repo=local_calendar_repo_instance  # Injecting real repo
    )

    # 4. Create activities list following sample/worker.py pattern
    activities = [
        # Schedule repository activities (for PublishScheduleWorkflow)
        temporal_local_calendar_repo.generate_schedule_id,
        temporal_local_calendar_repo.save_schedule,
        temporal_local_calendar_repo.get_schedule,
        # Calendar repository activities (for both workflows - mock specific)
        temporal_mock_calendar_repo.get_changes,
        temporal_mock_calendar_repo.get_events_by_ids,
        temporal_mock_calendar_repo.get_all_events,
        temporal_mock_calendar_repo.apply_changes,
        temporal_mock_calendar_repo.get_sync_state,
        temporal_mock_calendar_repo.store_sync_state,
        # Time block classifier activities (for PublishScheduleWorkflow)
        temporal_time_block_classifier_repo.classify_block_type,
        temporal_time_block_classifier_repo.classify_responsibility_area,
        temporal_time_block_classifier_repo.triage_event,
        # File writer activity (for PublishScheduleWorkflow)
        schedule_file_writer_activity.write_schedule_to_org_file,
        # Calendar configuration activities
        temporal_local_config_repo.get_collection,
        temporal_local_config_repo.list_collections,
        # File storage activities
        temporal_file_storage_repo.upload_file,
        temporal_file_storage_repo.download_file,
    ]

    # Add Google Calendar activities if available (for CalendarSyncWorkflow
    # and PublishScheduleWorkflow when Google is the source)
    if temporal_google_calendar_repo:
        activities.extend(
            [
                temporal_google_calendar_repo.get_changes,
                temporal_google_calendar_repo.get_events_by_ids,
                temporal_google_calendar_repo.get_all_events,
                temporal_google_calendar_repo.get_events_by_date_range,
                temporal_google_calendar_repo.get_events_by_date_range_multi_calendar,
            ]
        )
        logger.info("Google Calendar activities registered")

    # Add PostgreSQL activities if available (for CalendarSyncWorkflow and
    # PublishScheduleWorkflow when PostgreSQL is the source/sink)
    if temporal_postgresql_calendar_repo:
        activities.extend(
            [
                temporal_postgresql_calendar_repo.apply_changes,
                temporal_postgresql_calendar_repo.get_sync_state,
                temporal_postgresql_calendar_repo.store_sync_state,
                temporal_postgresql_calendar_repo.get_events_by_date_range,
                temporal_postgresql_calendar_repo.get_events_by_date_range_multi_calendar,
                temporal_postgresql_calendar_repo.get_events_by_ids,
                temporal_postgresql_calendar_repo.get_all_events,
            ]
        )
        logger.info("PostgreSQL calendar activities registered")
    if temporal_postgresql_schedule_repo:
        activities.extend(
            [
                temporal_postgresql_schedule_repo.generate_schedule_id,
                temporal_postgresql_schedule_repo.save_schedule,
                temporal_postgresql_schedule_repo.get_schedule,
            ]
        )
        logger.info("PostgreSQL schedule activities registered")

    # Set up periodic sync scheduling if configured
    sync_collection_id = os.environ.get("SYNC_COLLECTION_ID")
    sync_interval_minutes = int(os.environ.get("SYNC_INTERVAL_MINUTES", "15"))

    if (
        sync_collection_id
        and temporal_google_calendar_repo
        and temporal_postgresql_calendar_repo
    ):
        logger.info(
            "Scheduling periodic calendar sync",
            extra={
                "collection_id": sync_collection_id,
                "interval_minutes": sync_interval_minutes,
            },
        )

        # Schedule periodic sync workflow using new scheduled workflow
        try:
            from temporalio.client import (
                ScheduleActionStartWorkflow,
                ScheduleSpec,
                ScheduleIntervalSpec,
            )
            from datetime import timedelta

            schedule_id = f"calendar-sync-{sync_collection_id}"

            # Create schedule for periodic sync using dedicated scheduled
            # workflow
            from temporalio.client import Schedule

            schedule = Schedule(
                action=ScheduleActionStartWorkflow(
                    "CalendarSyncWorkflow",
                    args=["primary", "postgresql", False],
                    id=f"sync-{sync_collection_id}-{{.ScheduledTime.Unix}}",
                    task_queue=task_queue,
                ),
                spec=ScheduleSpec(
                    intervals=[
                        ScheduleIntervalSpec(
                            every=timedelta(minutes=sync_interval_minutes)
                        )
                    ]
                ),
            )

            await client.create_schedule(
                schedule_id,
                schedule,
            )
            logger.info(f"Created periodic sync schedule: {schedule_id}")

        except Exception as e:
            logger.warning(f"Failed to create sync schedule: {e}")
            # Continue without scheduling - manual sync still available

    logger.info(
        "Creating consolidated Temporal worker",
        extra={
            "task_queue": task_queue,
            "workflow_count": 2,
            "activity_count": len(activities),
            "google_calendar_available": temporal_google_calendar_repo
            is not None,
            "postgresql_available": temporal_postgresql_calendar_repo
            is not None,
        },
    )

    # Create worker with all workflows following sample/worker.py pattern
    from typing import cast, Sequence, Callable, Any

    worker = Worker(
        client,
        task_queue=task_queue,
        workflows=[
            PublishScheduleWorkflow,
            CalendarSyncWorkflow,
        ],
        activities=cast(Sequence[Callable[..., Any]], activities),
    )

    logger.info("Starting consolidated worker execution")
    await worker.run()


def main() -> None:
    """Entry point for the consolidated calendar worker."""
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
