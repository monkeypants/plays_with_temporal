"""
Temporal worker for julee_example domain workflows and activities.

This worker runs workflows and activities for document processing,
assembly, and knowledge service operations within the julee_example domain.
"""

import asyncio
import logging
import os
from temporalio.client import Client
from temporalio.service import RPCError
from temporalio.worker import Worker
from util.repos.temporal.data_converter import temporal_data_converter

from julee_example.workflows import (
    ExtractAssembleWorkflow,
    ValidateDocumentWorkflow,
)
from julee_example.repositories.temporal.activities import (
    TemporalMinioAssemblyRepository,
    TemporalMinioAssemblySpecificationRepository,
    TemporalMinioDocumentRepository,
    TemporalMinioKnowledgeServiceConfigRepository,
    TemporalMinioKnowledgeServiceQueryRepository,
    TemporalMinioPolicyRepository,
    TemporalMinioDocumentPolicyValidationRepository,
)
from julee_example.services.temporal.activities import (
    TemporalKnowledgeService,
)
from minio import Minio
from julee_example.repositories.minio.client import MinioClient
from util.temporal.activities import collect_activities_from_instances

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
                data_converter=temporal_data_converter,
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
    """Run the Temporal worker for julee_example domain"""
    # Setup logging first
    setup_logging()

    # Connect to Temporal server using environment variable
    temporal_endpoint = os.environ.get("TEMPORAL_ENDPOINT", "localhost:7234")
    logger.info(
        "Starting julee_example Temporal worker",
        extra={"temporal_endpoint": temporal_endpoint},
    )

    client = await get_temporal_client_with_retries(temporal_endpoint)

    # Get Minio endpoint and create client for repositories
    logger.debug("Preparing repository configurations")
    minio_endpoint = os.environ.get("MINIO_ENDPOINT", "localhost:9000")

    # Create Minio client for repositories
    # minio.Minio implements the MinioClient protocol
    minio_client: MinioClient = Minio(  # type: ignore[assignment]
        endpoint=minio_endpoint,
        access_key="minioadmin",
        secret_key="minioadmin",
        secure=False,
    )

    # Instantiate temporal repository classes for activity registration
    logger.debug("Creating Temporal Activity repository implementations")
    temporal_assembly_repo = TemporalMinioAssemblyRepository(
        client=minio_client
    )
    temporal_assembly_spec_repo = (
        TemporalMinioAssemblySpecificationRepository(client=minio_client)
    )
    temporal_document_repo = TemporalMinioDocumentRepository(
        client=minio_client
    )
    temporal_knowledge_config_repo = (
        TemporalMinioKnowledgeServiceConfigRepository(client=minio_client)
    )
    temporal_knowledge_query_repo = (
        TemporalMinioKnowledgeServiceQueryRepository(client=minio_client)
    )

    # Create policy repositories for validation workflow
    temporal_policy_repo = TemporalMinioPolicyRepository(client=minio_client)
    temporal_document_policy_validation_repo = (
        TemporalMinioDocumentPolicyValidationRepository(client=minio_client)
    )

    # Create temporal knowledge service for activity registration
    # Pass the document repository for dependency injection
    temporal_knowledge_service = TemporalKnowledgeService(
        document_repo=temporal_document_repo
    )

    # Automatically collect all activities from decorated instances
    # This uses the same _discover_protocol_methods that the decorator uses,
    # ensuring we never miss activities and eliminating boilerplate
    activities = collect_activities_from_instances(
        temporal_assembly_repo,
        temporal_assembly_spec_repo,
        temporal_document_repo,
        temporal_knowledge_config_repo,
        temporal_knowledge_query_repo,
        temporal_policy_repo,
        temporal_document_policy_validation_repo,
        temporal_knowledge_service,
    )

    logger.info(
        "Creating Temporal worker for julee_example domain",
        extra={
            "task_queue": "julee-extract-assemble-queue",
            "workflow_count": 2,
            "activity_count": len(activities),
            "data_converter_type": type(client.data_converter).__name__,
        },
    )

    # Create worker with workflow retry policy
    worker = Worker(
        client,
        task_queue="julee-extract-assemble-queue",
        workflows=[ExtractAssembleWorkflow, ValidateDocumentWorkflow],
        activities=activities,  # type: ignore[arg-type]
    )

    logger.info("Starting julee_example worker execution")

    # Run the worker
    await worker.run()


if __name__ == "__main__":
    asyncio.run(run_worker())
