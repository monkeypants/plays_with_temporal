"""
Temporal worker that runs the workflow and activities.
"""

import asyncio
import logging
import os
from temporalio.client import Client
from temporalio.service import RPCError
from temporalio.worker import Worker
from temporalio.contrib.pydantic import pydantic_data_converter

from sample.workflow import (
    OrderFulfillmentWorkflow,
    CancelOrderWorkflow,
)  # Added CancelOrderWorkflow
from sample.repos.activities import (
    TemporalMinioOrderRepository,
    TemporalMinioPaymentRepository,
    TemporalMinioInventoryRepository,
    TemporalMinioOrderRequestRepository,
)
from util.repos.temporal.minio_file_storage import (
    TemporalMinioFileStorageRepository,
)

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    """Configure logging based on environment variables"""
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    log_format = os.environ.get(
        "LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Validate log level
    numeric_level = getattr(logging, log_level, None)
    if not isinstance(numeric_level, int):
        print(f"Invalid log level: {log_level}, defaulting to INFO")
        numeric_level = logging.INFO

    logging.basicConfig(
        level=numeric_level,
        format=log_format,
        force=True,  # Override any existing configuration
    )

    logger.info(
        "Logging configured",
        extra={"log_level": log_level, "numeric_level": numeric_level},
    )


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
            # Use the proper Pydantic v2 data converter and connect to the
            # 'default' namespace
            client = await Client.connect(
                endpoint,
                data_converter=pydantic_data_converter,
                namespace="default",
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

    # This should never be reached due to the raise in the loop, but mypy
    # needs it
    raise RuntimeError("Failed to connect to Temporal after all attempts")


async def run_worker() -> None:
    """Run the Temporal worker"""
    # Setup logging first
    setup_logging()

    # Connect to Temporal server using environment variable
    temporal_endpoint = os.environ.get("TEMPORAL_ENDPOINT", "temporal:7233")
    logger.info(
        "Starting Temporal worker",
        extra={"temporal_endpoint": temporal_endpoint},
    )

    client = await get_temporal_client_with_retries(temporal_endpoint)

    # Get Minio endpoint for repositories
    logger.debug("Preparing repository configurations")
    minio_endpoint = os.environ.get("MINIO_ENDPOINT", "minio:9000")

    # Instantiate temporal repository classes (imported from sample.repos)
    logger.debug("Creating Temporal Activity repository implementations")
    temporal_order_repo = TemporalMinioOrderRepository(
        endpoint=minio_endpoint
    )
    temporal_payment_repo = TemporalMinioPaymentRepository(
        endpoint=minio_endpoint
    )
    temporal_inventory_repo = TemporalMinioInventoryRepository(
        endpoint=minio_endpoint
    )
    temporal_order_request_repo = TemporalMinioOrderRequestRepository()
    temporal_file_storage_repo = (
        TemporalMinioFileStorageRepository()
    )  # New Temporal activity repo

    # Create a worker that hosts workflow and activities
    # The worker automatically uses the data converter from the client.
    activities = [
        temporal_order_repo.generate_order_id,
        temporal_order_repo.save_order,
        temporal_order_repo.get_order,
        temporal_order_repo.cancel_order,  # New activity
        temporal_payment_repo.process_payment,
        temporal_payment_repo.get_payment,
        temporal_payment_repo.refund_payment,  # New activity
        temporal_inventory_repo.reserve_items,
        temporal_inventory_repo.release_items,
        temporal_order_request_repo.store_bidirectional_mapping,
        temporal_order_request_repo.get_order_id_for_request,
        temporal_order_request_repo.get_request_id_for_order,
        temporal_file_storage_repo.upload_file,  # New activity
        temporal_file_storage_repo.download_file,  # New activity
        temporal_file_storage_repo.get_file_metadata,  # New activity
    ]

    logger.info(
        "Creating Temporal worker",
        extra={
            "task_queue": "order-fulfillment-queue",
            "workflow_count": 1,
            "activity_count": len(activities),
            "data_converter_type": type(client.data_converter).__name__,
        },
    )

    worker = Worker(
        client,
        task_queue="order-fulfillment-queue",
        workflows=[
            OrderFulfillmentWorkflow,
            CancelOrderWorkflow,
        ],  # Added CancelOrderWorkflow
        activities=activities,  # type: ignore[arg-type]
    )

    logger.info("Starting worker execution")

    # Run the worker
    await worker.run()


if __name__ == "__main__":
    asyncio.run(run_worker())
