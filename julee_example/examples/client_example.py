"""
Example client for starting ExtractAssemble workflows in julee_example.

This demonstrates how to start document extraction and assembly workflows
using Temporal's client API. It shows proper workflow configuration,
error handling, and result retrieval.
"""

import asyncio
import logging
import os
from typing import Optional
from temporalio.client import Client
from util.repos.temporal.data_converter import temporal_data_converter
from minio import Minio

from julee_example.workflows import (
    ExtractAssembleWorkflow,
    EXTRACT_ASSEMBLE_RETRY_POLICY,
)
from julee_example.domain import Assembly
from julee_example.examples.populate_example_data import populate_example_data
from julee_example.repositories.minio.document import MinioDocumentRepository

logger = logging.getLogger(__name__)


async def start_extract_assemble_workflow(
    temporal_endpoint: str,
    document_id: str,
    assembly_specification_id: str,
    workflow_id: Optional[str] = None,
) -> str:
    """
    Start an ExtractAssemble workflow.

    Args:
        temporal_endpoint: Temporal server endpoint
        document_id: ID of the document to assemble
        assembly_specification_id: ID of the specification to use
        workflow_id: Optional custom workflow ID (generated if not provided)

    Returns:
        The workflow ID of the started workflow

    Raises:
        Exception: If workflow start fails
    """
    # Connect to Temporal
    client = await Client.connect(
        temporal_endpoint,
        data_converter=temporal_data_converter,
        namespace="default",
    )

    # Generate workflow ID if not provided
    if not workflow_id:
        workflow_id = (
            f"extract-assemble-{document_id}-{assembly_specification_id}"
        )

    logger.info(
        "Starting ExtractAssemble workflow",
        extra={
            "workflow_id": workflow_id,
            "document_id": document_id,
            "assembly_specification_id": assembly_specification_id,
        },
    )

    # Start the workflow
    handle = await client.start_workflow(
        ExtractAssembleWorkflow.run,
        args=[document_id, assembly_specification_id],
        id=workflow_id,
        task_queue="julee-extract-assemble-queue",
        retry_policy=EXTRACT_ASSEMBLE_RETRY_POLICY,
    )

    logger.info(
        "ExtractAssemble workflow started successfully",
        extra={
            "workflow_id": workflow_id,
            "run_id": handle.run_id,
        },
    )

    return workflow_id


async def wait_for_workflow_result(
    temporal_endpoint: str, workflow_id: str
) -> Assembly:
    """
    Wait for a workflow to complete and return its result.

    Args:
        temporal_endpoint: Temporal server endpoint
        workflow_id: ID of the workflow to wait for

    Returns:
        The Assembly result from the workflow

    Raises:
        Exception: If workflow fails or times out
    """
    # Connect to Temporal
    client = await Client.connect(
        temporal_endpoint,
        data_converter=temporal_data_converter,
        namespace="default",
    )

    # Get workflow handle
    handle = client.get_workflow_handle(workflow_id)

    logger.info(
        "Waiting for workflow completion", extra={"workflow_id": workflow_id}
    )

    try:
        # Wait for the workflow result
        result = await handle.result()

        # Debug: Check what we actually got back
        print(f"DEBUG: Workflow result type: {type(result)}")
        print(f"DEBUG: Workflow result value: {result}")

        if not isinstance(result, Assembly):
            print(f"DEBUG: Expected Assembly, got {type(result)}")
            if isinstance(result, dict):
                print("DEBUG: Converting dict to Assembly object")
                print(f"Dict keys: {list(result.keys())}")
                try:
                    # Convert dict back to Assembly object
                    result = Assembly(**result)
                    print("DEBUG: Successfully converted dict to Assembly")
                except Exception as e:
                    print(f"DEBUG: Failed to convert dict to Assembly: {e}")
                    print(f"Dict content: {result}")
                    raise
            else:
                raise ValueError(
                    f"Workflow returned {type(result)} instead of Assembly"
                )

        logger.info(
            "Workflow completed successfully",
            extra={
                "workflow_id": workflow_id,
                "assembly_id": result.assembly_id,
                "status": result.status.value,
                "assembled_document_id": result.assembled_document_id,
            },
        )

        return result

    except Exception as e:
        logger.error(
            "Workflow failed",
            extra={
                "workflow_id": workflow_id,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        raise


async def query_workflow_status(
    temporal_endpoint: str, workflow_id: str
) -> dict:
    """
    Query the current status of a running workflow.

    Args:
        temporal_endpoint: Temporal server endpoint
        workflow_id: ID of the workflow to query

    Returns:
        Dict containing current step and assembly ID (if available)
    """
    # Connect to Temporal
    client = await Client.connect(
        temporal_endpoint,
        data_converter=temporal_data_converter,
        namespace="default",
    )

    # Get workflow handle
    handle = client.get_workflow_handle(workflow_id)

    try:
        # Query the current step
        current_step = await handle.query(
            ExtractAssembleWorkflow.get_current_step
        )
        assembly_id = await handle.query(
            ExtractAssembleWorkflow.get_assembly_id
        )

        status = {
            "workflow_id": workflow_id,
            "current_step": current_step,
            "assembly_id": assembly_id,
        }

        logger.info("Workflow status queried", extra=status)

        return status

    except Exception as e:
        logger.error(
            "Failed to query workflow status",
            extra={
                "workflow_id": workflow_id,
                "error": str(e),
            },
        )
        raise


async def cancel_workflow(
    temporal_endpoint: str,
    workflow_id: str,
    reason: str = "User requested cancellation",
) -> None:
    """
    Cancel a running workflow.

    Args:
        temporal_endpoint: Temporal server endpoint
        workflow_id: ID of the workflow to cancel
        reason: Reason for cancellation
    """
    # Connect to Temporal
    client = await Client.connect(
        temporal_endpoint,
        data_converter=temporal_data_converter,
        namespace="default",
    )

    # Get workflow handle
    handle = client.get_workflow_handle(workflow_id)

    try:
        # Send cancellation signal
        await handle.signal(ExtractAssembleWorkflow.cancel_assembly, reason)

        # Also cancel the workflow execution
        await handle.cancel()

        logger.info(
            "Workflow cancelled",
            extra={
                "workflow_id": workflow_id,
                "reason": reason,
            },
        )

    except Exception as e:
        logger.error(
            "Failed to cancel workflow",
            extra={
                "workflow_id": workflow_id,
                "error": str(e),
            },
        )
        raise


async def fetch_assembled_document_content(document_id: str) -> Optional[str]:
    """
    Fetch the assembled document content from MinIO and return it as a string.

    Args:
        document_id: ID of the assembled document to fetch

    Returns:
        The document content as a string, or None if not found
    """
    try:
        # Initialize MinIO client
        minio_endpoint = os.environ.get("MINIO_ENDPOINT", "localhost:9000")
        minio_client = Minio(
            endpoint=minio_endpoint,
            access_key="minioadmin",
            secret_key="minioadmin",
            secure=False,
        )

        # Create document repository
        doc_repo = MinioDocumentRepository(minio_client)

        # Fetch the document
        document = await doc_repo.get(document_id)
        if not document or not document.content:
            print(f"Document {document_id} not found or has no content")
            return None

        # Read the content (stream is already at beginning)
        content_bytes = document.content.read()
        content_str = content_bytes.decode("utf-8")

        return content_str

    except Exception as e:
        print(f"Error fetching document {document_id}: {e}")
        return None


async def main() -> None:
    """
    Example usage of the ExtractAssemble workflow client.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Get temporal endpoint once
    temporal_endpoint = os.environ.get("TEMPORAL_ENDPOINT", "localhost:7234")
    print(f"Using Temporal endpoint: {temporal_endpoint}")

    try:
        # First, populate example data
        print("Populating example data...")
        example_data = await populate_example_data()

        # Extract the IDs we need for the workflow
        document_id = example_data["document_id"]
        assembly_specification_id = example_data["assembly_specification_id"]

        print(f"Using document ID: {document_id}")
        print(f"Using assembly specification ID: {assembly_specification_id}")

        # Start the workflow
        workflow_id = await start_extract_assemble_workflow(
            temporal_endpoint=temporal_endpoint,
            document_id=document_id,
            assembly_specification_id=assembly_specification_id,
        )

        # Query status periodically
        for i in range(3):
            await asyncio.sleep(2)  # Wait a bit between queries
            status = await query_workflow_status(
                temporal_endpoint, workflow_id
            )
            print(f"Status check {i+1}: {status}")

        # Wait for completion (in production, you might want a timeout)
        print("Waiting for workflow to complete...")
        result = await wait_for_workflow_result(
            temporal_endpoint, workflow_id
        )

        print(f"Workflow completed! Assembly ID: {result.assembly_id}")
        print(f"Assembled document ID: {result.assembled_document_id}")
        print(f"Final status: {result.status.value}")

        # Fetch and display the assembled document content
        if result.assembled_document_id:
            print("\n" + "=" * 50)
            print("ASSEMBLED DOCUMENT CONTENT:")
            print("=" * 50)

            content = await fetch_assembled_document_content(
                result.assembled_document_id
            )
            if content:
                print(content)
            else:
                print("No content found or failed to fetch content")

            print("=" * 50)

    except KeyboardInterrupt:
        print("\nCancelling workflow due to user interrupt...")
        if "workflow_id" in locals():
            await cancel_workflow(
                temporal_endpoint, workflow_id, "User interrupted"
            )
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
