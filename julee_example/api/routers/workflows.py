"""
Workflows API router for the julee_example CEAP system.

This module provides workflow management API endpoints for starting,
monitoring, and managing workflows in the system.

Routes defined at root level:
- POST /extract-assemble - Start extract-assemble workflow
- GET /{workflow_id}/status - Get workflow status
- GET / - List workflows

These routes are mounted with '/workflows' prefix in the main app.
"""

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from temporalio.client import Client

from julee_example.api.dependencies import get_temporal_client
from julee_example.workflows.extract_assemble import (
    ExtractAssembleWorkflow,
    EXTRACT_ASSEMBLE_RETRY_POLICY,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class StartExtractAssembleRequest(BaseModel):
    """Request model for starting extract-assemble workflow."""

    document_id: str = Field(
        ..., min_length=1, description="Document ID to process"
    )
    assembly_specification_id: str = Field(
        ..., min_length=1, description="Assembly specification ID to use"
    )
    workflow_id: Optional[str] = Field(
        None,
        min_length=1,
        description=(
            "Optional custom workflow ID (auto-generated if not provided)"
        ),
    )


class WorkflowStatusResponse(BaseModel):
    """Response model for workflow status."""

    workflow_id: str
    run_id: str
    status: str  # "RUNNING", "COMPLETED", "FAILED", "CANCELLED", etc.
    current_step: Optional[str] = None
    assembly_id: Optional[str] = None


class StartWorkflowResponse(BaseModel):
    """Response model for starting a workflow."""

    workflow_id: str
    run_id: str
    status: str
    message: str


@router.post("/extract-assemble", response_model=StartWorkflowResponse)
async def start_extract_assemble_workflow(
    request: StartExtractAssembleRequest,
    temporal_client: Client = Depends(get_temporal_client),
) -> StartWorkflowResponse:
    """
    Start an extract-assemble workflow.

    Args:
        request: Workflow start request with document and spec IDs
        temporal_client: Temporal client dependency

    Returns:
        Workflow ID and initial status

    Raises:
        HTTPException: If workflow start fails
    """
    try:
        logger.info("Starting extract-assemble workflow request received")

        # Generate workflow ID if not provided
        workflow_id = request.workflow_id
        if not workflow_id:
            workflow_id = (
                f"extract-assemble-{request.document_id}-"
                f"{request.assembly_specification_id}-{uuid.uuid4().hex[:8]}"
            )

        logger.info(
            "Starting ExtractAssemble workflow",
            extra={
                "workflow_id": workflow_id,
                "document_id": request.document_id,
                "assembly_specification_id": (
                    request.assembly_specification_id
                ),
            },
        )

        # Start the workflow
        handle = await temporal_client.start_workflow(
            ExtractAssembleWorkflow.run,
            args=[request.document_id, request.assembly_specification_id],
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

        return StartWorkflowResponse(
            workflow_id=workflow_id,
            run_id=handle.run_id or "unknown",
            status="RUNNING",
            message="Workflow started successfully",
        )

    except Exception as e:
        logger.error(
            "Failed to start extract-assemble workflow: %s",
            e,
            extra={
                "document_id": request.document_id,
                "assembly_specification_id": (
                    request.assembly_specification_id
                ),
            },
        )
        raise HTTPException(
            status_code=500, detail="Failed to start workflow"
        ) from e


@router.get("/{workflow_id}/status", response_model=WorkflowStatusResponse)
async def get_workflow_status(
    workflow_id: str,
    temporal_client: Client = Depends(get_temporal_client),
) -> WorkflowStatusResponse:
    """
    Get the status of a workflow.

    Args:
        workflow_id: Workflow ID to query
        temporal_client: Temporal client dependency

    Returns:
        Current workflow status and details

    Raises:
        HTTPException: If workflow not found or query fails
    """
    logger.info("Getting workflow status", extra={"workflow_id": workflow_id})

    # Get workflow handle - if this fails, workflow doesn't exist
    try:
        handle = temporal_client.get_workflow_handle(workflow_id)
    except Exception as e:
        # Check if it's a workflow not found error (common patterns)
        error_message = str(e).lower()
        if any(
            pattern in error_message
            for pattern in [
                "not found",
                "notfound",
                "does not exist",
                "workflow_not_found",
            ]
        ):
            raise HTTPException(
                status_code=404,
                detail=f"Workflow with ID '{workflow_id}' not found",
            )

        # Other errors from getting workflow handle
        logger.error(
            "Failed to get workflow handle: %s",
            e,
            extra={"workflow_id": workflow_id},
        )
        raise HTTPException(
            status_code=500, detail="Failed to retrieve workflow handle"
        ) from e

    # Get workflow description - if this fails, it's a server error
    try:
        description = await handle.describe()
    except Exception as e:
        logger.error(
            "Failed to describe workflow: %s",
            e,
            extra={"workflow_id": workflow_id},
        )
        raise HTTPException(
            status_code=500, detail="Failed to retrieve workflow description"
        ) from e

    # Query current step and assembly ID if workflow supports it
    current_step = None
    assembly_id = None
    try:
        current_step = await handle.query("get_current_step")
        assembly_id = await handle.query("get_assembly_id")
    except Exception as query_error:
        logger.debug(
            "Could not query workflow details: %s",
            query_error,
            extra={"workflow_id": workflow_id},
        )

    status_response = WorkflowStatusResponse(
        workflow_id=workflow_id,
        run_id=description.run_id or "unknown",
        status=description.status.name if description.status else "UNKNOWN",
        current_step=current_step,
        assembly_id=assembly_id,
    )

    logger.info(
        "Retrieved workflow status",
        extra={
            "workflow_id": workflow_id,
            "status": status_response.status,
            "current_step": current_step,
        },
    )

    return status_response
