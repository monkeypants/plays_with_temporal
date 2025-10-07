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
    ValidateDocumentWorkflow,
    VALIDATE_DOCUMENT_RETRY_POLICY,
)
from julee_example.domain.models.assembly import Assembly
from julee_example.domain.models.policy import DocumentPolicyValidation
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


async def start_validate_document_workflow(
    temporal_endpoint: str,
    document_id: str,
    policy_id: str,
    workflow_id: Optional[str] = None,
) -> str:
    """
    Start a ValidateDocument workflow.

    Args:
        temporal_endpoint: Temporal server endpoint
        document_id: ID of the document to validate
        policy_id: ID of the policy to validate against
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
        workflow_id = f"validate-document-{document_id}-{policy_id}"

    logger.info(
        "Starting ValidateDocument workflow",
        extra={
            "workflow_id": workflow_id,
            "document_id": document_id,
            "policy_id": policy_id,
        },
    )

    # Start the workflow
    handle = await client.start_workflow(
        ValidateDocumentWorkflow.run,
        args=[document_id, policy_id],
        id=workflow_id,
        task_queue="julee-extract-assemble-queue",
        retry_policy=VALIDATE_DOCUMENT_RETRY_POLICY,
    )

    logger.info(
        "ValidateDocument workflow started successfully",
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

        # Handle result conversion if needed
        if not isinstance(result, Assembly):
            if isinstance(result, dict):
                try:
                    # Convert dict back to Assembly object
                    result = Assembly(**result)
                except Exception as e:
                    raise ValueError(
                        f"Failed to convert workflow result to Assembly: {e}"
                    )
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


async def wait_for_validation_result(
    temporal_endpoint: str, workflow_id: str
) -> DocumentPolicyValidation:
    """
    Wait for a validation workflow to complete and return its result.

    Args:
        temporal_endpoint: Temporal server endpoint
        workflow_id: ID of the workflow to wait for

    Returns:
        The DocumentPolicyValidation result from the workflow

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
        "Waiting for validation workflow completion",
        extra={"workflow_id": workflow_id},
    )

    try:
        # Wait for the workflow result
        result = await handle.result()

        # Handle result conversion if needed
        if not isinstance(result, DocumentPolicyValidation):
            if isinstance(result, dict):
                try:
                    # Convert dict back to DocumentPolicyValidation object
                    result = DocumentPolicyValidation(**result)
                except Exception as e:
                    raise ValueError(
                        f"Failed to convert workflow result to "
                        f"DocumentPolicyValidation: {e}"
                    )
            else:
                raise ValueError(
                    f"Workflow returned {type(result)} instead of "
                    f"DocumentPolicyValidation"
                )

        logger.info(
            "Validation workflow completed successfully",
            extra={
                "workflow_id": workflow_id,
                "validation_id": result.validation_id,
                "status": result.status.value,
                "passed": result.passed,
            },
        )

        return result

    except Exception as e:
        logger.error(
            "Validation workflow failed",
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
        # Query the current step (try both workflow types)
        try:
            current_step = await handle.query(
                ExtractAssembleWorkflow.get_current_step
            )
            assembly_id = await handle.query(
                ExtractAssembleWorkflow.get_assembly_id
            )
        except Exception:
            # Try validation workflow queries
            current_step = await handle.query(
                ValidateDocumentWorkflow.get_current_step
            )
            assembly_id = await handle.query(
                ValidateDocumentWorkflow.get_validation_id
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
        logger.debug(f"Error fetching document {document_id}: {e}")
        return None


async def main() -> None:
    """
    Example usage of the ExtractAssemble workflow client.

    This demo shows how JuLEE processes meeting transcripts using AI to
    extract structured information like attendees, agenda items, and action
    items.

    Environment Variables:
        LOG_LEVEL: Set to DEBUG, INFO, or WARNING (default: WARNING for
                   clean output)
        TEMPORAL_ENDPOINT: Temporal server address (default: localhost:7234)
        ANTHROPIC_API_KEY: Required for AI processing
    """
    # Configure logging based on environment or default to WARNING for clean
    # output
    log_level = os.environ.get("LOG_LEVEL", "WARNING").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.WARNING),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Get temporal endpoint once
    temporal_endpoint = os.environ.get("TEMPORAL_ENDPOINT", "localhost:7234")

    print("🚀 JuLEE Document Assembly Demo")
    print("=" * 40)
    print("📋 Processes meeting transcripts with AI to extract:")
    print("   • Meeting metadata (attendees, time, etc.)")
    print("   • Structured agenda items and discussions")
    print("   • Action items with assignees and due dates")
    print()
    print(f"🔗 Temporal endpoint: {temporal_endpoint}")
    if log_level != "WARNING":
        print(f"🔍 Log level: {log_level}")
    print("💡 Tip: Set LOG_LEVEL=DEBUG for detailed logging")
    print()

    try:
        # First, populate example data
        print("📝 Setting up example data...")
        example_data = await populate_example_data()

        # Extract the IDs we need for the workflow
        document_id = example_data["document_id"]
        assembly_specification_id = example_data["assembly_specification_id"]

        # Start the workflow
        print("🔄 Starting document assembly workflow...")
        workflow_id = await start_extract_assemble_workflow(
            temporal_endpoint=temporal_endpoint,
            document_id=document_id,
            assembly_specification_id=assembly_specification_id,
        )

        print("✅ Workflow started successfully!")
        print(f"   Workflow ID: {workflow_id}")
        print()

        # Query status periodically
        print("⏳ Monitoring workflow progress...")
        for i in range(3):
            await asyncio.sleep(2)  # Wait a bit between queries
            status = await query_workflow_status(
                temporal_endpoint, workflow_id
            )
            step = status.get("current_step", "unknown")
            assembly_id = status.get("assembly_id")
            if assembly_id:
                print(f"   Step {i + 1}: {step} (Assembly: {assembly_id})")
            else:
                print(f"   Step {i + 1}: {step}")

        # Wait for completion (in production, you might want a timeout)
        print("\n⏱️  Waiting for workflow completion...")
        result = await wait_for_workflow_result(
            temporal_endpoint, workflow_id
        )

        print("\n🎉 Workflow completed successfully!")
        print(f"   Assembly ID: {result.assembly_id}")
        print(f"   Assembled Document: {result.assembled_document_id}")
        print(f"   Status: {result.status.value}")

        # Fetch and display the assembled document content
        if result.assembled_document_id:
            print("\n📄 ASSEMBLED DOCUMENT CONTENT")
            print("=" * 50)

            content = await fetch_assembled_document_content(
                result.assembled_document_id
            )
            if content:
                print(content)
            else:
                print("❌ No content found or failed to fetch content")

            print("=" * 50)

        # Now run validation workflow on the assembled document
        print("\n🔍 DOCUMENT VALIDATION PHASE")
        print("=" * 40)
        print("Validating the assembled document against policies...")

        # Check if we have an assembled document to validate
        if not result.assembled_document_id:
            print("❌ No assembled document ID available for validation")
            print("   Skipping validation workflow")
        else:
            # Use the actual policy ID from the populated example data
            validation_workflow_id = await start_validate_document_workflow(
                temporal_endpoint=temporal_endpoint,
                document_id=result.assembled_document_id,  # type: ignore[arg-type]
                policy_id=example_data["policy_id"],
            )

            print("✅ Validation workflow started!")
            print(f"   Workflow ID: {validation_workflow_id}")

            # Wait for validation completion
            print("\n⏱️  Waiting for validation completion...")
            try:
                validation_result = await wait_for_validation_result(
                    temporal_endpoint, validation_workflow_id
                )

                print("\n🎯 Validation completed!")
                print(f"   Validation ID: {validation_result.validation_id}")
                print(f"   Status: {validation_result.status.value}")
                passed_text = (
                    "✅ YES" if validation_result.passed else "❌ NO"
                )
                print(f"   Passed: {passed_text}")
                if hasattr(validation_result, "validation_scores"):
                    # Create a mapping from query IDs to human-readable names
                    query_id_to_name = {}
                    if "offensive_language_check_id" in example_data:
                        query_id_to_name[
                            example_data["offensive_language_check_id"]
                        ] = "Offensive Language Check"
                    if "professionalism_check_id" in example_data:
                        query_id_to_name[
                            example_data["professionalism_check_id"]
                        ] = "Professionalism Check"

                    # Display scores with human-readable names
                    print("   Scores:")
                    for (
                        query_id,
                        score,
                    ) in validation_result.validation_scores:
                        query_name = query_id_to_name.get(
                            query_id, f"Query {query_id}"
                        )
                        print(f"     • {query_name}: {score}/100")

                print(
                    "\n✨ Demo completed! The AI successfully extracted "
                    "structured"
                )
                print(
                    "   data from the meeting transcript and validated it "
                    "against"
                )
                print("   policies to ensure compliance and quality.")

            except Exception as validation_error:
                print(
                    f"⚠️  Validation workflow failed: "
                    f"{type(validation_error).__name__}: {validation_error}"
                )
                print(
                    "   This is expected if policy data hasn't been set up "
                    "yet."
                )
                print("\n✨ Assembly phase completed successfully!")
                print(
                    "   The document has been processed and structured data"
                )
                print("   extracted using AI-powered knowledge services.")

    except KeyboardInterrupt:
        print("\n❌ Cancelled by user")
        if "workflow_id" in locals():
            print("🛑 Cancelling workflow...")
            await cancel_workflow(
                temporal_endpoint, workflow_id, "User interrupted"
            )
    except Exception as e:
        print(f"❌ Error: {e}")
        if log_level == "DEBUG":
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
