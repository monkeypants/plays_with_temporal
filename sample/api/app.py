"""
FastAPI application for order processing.
"""

import logging
import os
import uuid  # New import for file_id generation
from typing import Optional, Any
import json  # New import for JSON parsing

from fastapi import (
    FastAPI,
    HTTPException,
    Response,
    Depends,
    UploadFile,
    File,
    Form,
)  # Added Form, Body
from fastapi.responses import RedirectResponse
from temporalio.client import Client

from sample.domain import (
    CreateOrderRequest,
)  # Updated import path for CreateOrderRequest
from sample.api.responses import (
    OrderStatusResponse,
    HealthCheckResponse,
    OrderRequestResponse,
    OrderRequestStatusResponse,
    FileUploadResponse,
    FileDownloadResponse,
    CancelOrderResponse,  # Added for order cancellation endpoint
)
from sample.workflow import (
    OrderFulfillmentWorkflow,
    CancelOrderWorkflow,
)
from sample.usecase import (
    OrderFulfillmentUseCase,
    GetOrderUseCase,
)
from sample.api.requests import (
    CancelOrderRequest,
)
from sample.api.dependencies import (
    get_order_fulfillment_use_case,
    get_minio_order_request_repository,
    get_get_order_use_case,
    get_temporal_client,
)


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


# Setup logging when module is imported
setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="Order Fulfillment API")


@app.get("/health", response_model=HealthCheckResponse)
async def health_check() -> HealthCheckResponse:
    """Health check endpoint"""
    logger.debug("Health check requested")
    return HealthCheckResponse(status="ok", version="1.0.0")


@app.post("/orders", response_model=OrderRequestResponse)
async def create_order(request: CreateOrderRequest) -> OrderRequestResponse:
    """
    Create a new order request and start the fulfillment workflow
    asynchronously. Returns immediately with a request_id for tracking.
    """
    logger.info(
        "Order creation requested",
        extra={
            "customer_id": request.customer_id,
            "item_count": len(request.items),
            "total_amount": str(request.total_amount),
        },
    )

    try:
        # Connect to Temporal server
        client = await get_temporal_client()

        # Generate request ID
        request_id = f"req-{hash(str(request))}"
        logger.debug("Generated request ID", extra={"request_id": request_id})

        # Start the workflow asynchronously, don't wait for result
        logger.debug(
            "Starting workflow",
            extra={
                "request_id": request_id,
                "workflow_type": "OrderFulfillmentWorkflow",
                "task_queue": "order-fulfillment-queue",
            },
        )

        await client.start_workflow(
            OrderFulfillmentWorkflow.run,
            request.model_dump(mode="json"),
            id=request_id,
            task_queue="order-fulfillment-queue",
        )

        logger.info(
            "Order workflow started",
            extra={
                "request_id": request_id,
                "customer_id": request.customer_id,
            },
        )

        # Return immediately with request ID
        return OrderRequestResponse(request_id=request_id, status="SUBMITTED")

    except Exception as e:
        logger.error(
            "Failed to create order",
            extra={
                "customer_id": request.customer_id,
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
            exc_info=True,
        )
        # Return a generic error message to prevent information leakage
        raise HTTPException(
            status_code=500,
            detail="Failed to create order due to an internal error.",
        )


@app.get("/order-requests/{request_id}")
async def get_request_status(
    request_id: str,
    request_repo: Any = Depends(
        get_minio_order_request_repository
    ),  # Changed to use direct Minio repo
) -> OrderRequestStatusResponse | RedirectResponse:
    """
    Get the status of an order request.
    If the request has progressed to order creation, redirect to the order
    endpoint.
    """
    logger.debug("Request status check", extra={"request_id": request_id})

    try:
        # Check if we have a mapping from request_id to order_id
        order_id = await request_repo.get_order_id_for_request(request_id)

        if order_id:
            logger.info(
                "Request has progressed to order, redirecting",
                extra={"request_id": request_id, "order_id": order_id},
            )
            # We have an order ID, redirect to order endpoint
            return RedirectResponse(
                url=f"/orders/{order_id}", status_code=302
            )
        else:
            logger.debug(
                "Request still processing", extra={"request_id": request_id}
            )
            # No mapping found, request is still being processed
            return OrderRequestStatusResponse(
                request_id=request_id, status="SUBMITTED"
            )

    except Exception as e:
        logger.error(
            "Failed to get request status",
            extra={
                "request_id": request_id,
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
            exc_info=True,
        )
        # Return a generic error message to prevent information leakage
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve request status due to an internal "
            "error.",
        )


@app.get("/orders/{order_id}", response_model=OrderStatusResponse)
async def get_order_status(
    order_id: str,
    use_case: GetOrderUseCase = Depends(get_get_order_use_case),
) -> OrderStatusResponse:
    """
    Get the status of an order by querying the use case directly.
    """
    logger.debug("Getting order status", extra={"order_id": order_id})

    try:
        # Directly call the use case to get the order status
        result = await use_case.get_order_status(order_id)

        logger.info(
            "Order status retrieved",
            extra={"order_id": order_id, "status": result.status},
        )

        # The use case returns OrderStatusResponse directly - FastAPI will
        # serialize it
        return result

    except Exception as e:
        logger.error(
            "Failed to get order status",
            extra={
                "order_id": order_id,
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
            exc_info=True,
        )
        # Return a generic error message to prevent information leakage
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve order status due to an internal "
            "error.",
        )


@app.post("/orders/{order_id}/attachments", response_model=FileUploadResponse)
async def upload_order_attachment(
    order_id: str,
    file: UploadFile = File(...),
    # Explicitly define form fields instead of using
    # Depends(UploadFileRequest)
    filename_form: Optional[str] = Form(None),
    content_type_form: Optional[str] = Form(None),
    metadata_json_str: str = Form(
        "{}"
    ),  # Metadata as a JSON string from form
    use_case: OrderFulfillmentUseCase = Depends(
        get_order_fulfillment_use_case
    ),
) -> FileUploadResponse:
    """
    Uploads an attachment for a specific order.
    The file content is passed directly, and additional metadata can be
    provided.
    """
    logger.info(
        "Attachment upload requested",
        extra={
            "order_id": order_id,
            "file_obj_filename": file.filename,
            "file_obj_content_type": file.content_type,
            "form_filename": filename_form,  # Log form fields
            "form_content_type": content_type_form,
            "form_raw_metadata_str": metadata_json_str,  # Log raw string
        },
    )

    try:
        file_content = await file.read()

        # Validate file is not empty
        if not file_content:
            raise HTTPException(
                status_code=400, detail="File cannot be empty"
            )

        file_id = str(
            uuid.uuid4()
        )  # Generate a unique ID for the file in storage

        # Parse the metadata string from the form into a dictionary
        parsed_metadata = json.loads(metadata_json_str)

        # Get content type, defaulting to octet-stream if not provided
        content_type = (
            content_type_form
            or file.content_type
            or "application/octet-stream"
        )

        # Get filename, defaulting to file_id if not provided
        filename = filename_form or file.filename or file_id

        # Combine metadata from request body and file object
        combined_metadata = {
            "filename": filename,
            "content_type": content_type,
            **parsed_metadata,  # Add extra metadata from parsed JSON string
        }

        logger.debug(
            "Combined metadata for upload",
            extra={
                "order_id": order_id,
                "combined_metadata": combined_metadata,
            },
        )

        # Upload via use case (security validation happens in repository
        # layer)
        file_metadata = await use_case.upload_order_attachment(
            order_id=order_id,
            file_id=file_id,
            data=file_content,
            metadata=combined_metadata,
            content_type=content_type,
            filename=filename,
        )

        logger.info(
            "Attachment uploaded successfully",
            extra={
                "order_id": order_id,
                "file_id": file_id,
                "size_bytes": file_metadata.size_bytes,
            },
        )

        return FileUploadResponse(
            file_id=file_metadata.file_id,
            message="File uploaded successfully",
            filename=file_metadata.filename,
            content_type=file_metadata.content_type,
            size_bytes=file_metadata.size_bytes,
            metadata=file_metadata.metadata,
        )
    except ValueError as e:
        # Security validation errors from domain model or repository
        raise HTTPException(status_code=400, detail=str(e))
    except json.JSONDecodeError as e:
        logger.error(
            "Invalid JSON in metadata form field",
            extra={"order_id": order_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=422, detail=f"Invalid JSON in metadata field: {e}"
        )
    except RuntimeError as e:
        logger.error(
            "File storage service not available for upload",
            extra={"order_id": order_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=503,
            detail="File storage service is currently unavailable.",
        )
    except Exception as e:
        logger.error(
            "Failed to upload attachment",
            extra={
                "order_id": order_id,
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to upload attachment due to an internal error.",
        )


@app.get("/orders/{order_id}/attachments/{file_id}")
async def download_order_attachment(
    order_id: str,
    file_id: str,
    use_case: OrderFulfillmentUseCase = Depends(
        get_order_fulfillment_use_case
    ),
) -> Response:
    """
    Downloads an attachment for a specific order.
    Returns the file content directly.
    """
    logger.info(
        "Attachment download requested",
        extra={"order_id": order_id, "file_id": file_id},
    )

    try:
        # First, get metadata to verify ownership and content type
        file_metadata = await use_case.get_order_attachment_metadata(
            order_id, file_id
        )
        if not file_metadata:
            logger.warning(
                "Attachment not found or not associated with order",
                extra={"order_id": order_id, "file_id": file_id},
            )
            raise HTTPException(
                status_code=404,
                detail="Attachment not found or not associated with this "
                "order.",
            )

        file_content = await use_case.download_order_attachment(
            order_id, file_id
        )

        if file_content is None:
            logger.error(
                "Failed to retrieve file content despite metadata existing",
                extra={"order_id": order_id, "file_id": file_id},
            )
            raise HTTPException(
                status_code=500, detail="Failed to retrieve file content."
            )

        logger.info(
            "Attachment downloaded successfully",
            extra={
                "order_id": order_id,
                "file_id": file_id,
                "size_bytes": len(file_content),
            },
        )

        return Response(
            content=file_content,
            media_type=file_metadata.content_type
            or "application/octet-stream",
            headers={
                "Content-Disposition": (
                    "attachment; "
                    f'filename="{file_metadata.filename or file_id}"'
                )
            },
        )
    except RuntimeError as e:
        logger.error(
            "File storage service not available for download",
            extra={"order_id": order_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=503,
            detail="File storage service is currently unavailable.",
        )
    except HTTPException:
        raise  # Re-raise HTTPExceptions (e.g., 404)
    except Exception as e:
        logger.error(
            "Failed to download attachment",
            extra={
                "order_id": order_id,
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to retrieve attachment metadata due to an internal "
                "error."
            ),
        )


@app.get(
    "/orders/{order_id}/attachments/{file_id}/metadata",
    response_model=FileDownloadResponse,
)
async def get_order_attachment_metadata(
    order_id: str,
    file_id: str,
    use_case: OrderFulfillmentUseCase = Depends(
        get_order_fulfillment_use_case
    ),
) -> FileDownloadResponse:
    """
    Retrieves metadata for an attachment for a specific order.
    Does not return the file content.
    """
    logger.info(
        "Attachment metadata requested",
        extra={"order_id": order_id, "file_id": file_id},
    )

    try:
        file_metadata = await use_case.get_order_attachment_metadata(
            order_id, file_id
        )

        if not file_metadata:
            logger.warning(
                "Attachment metadata not found or not associated with order",
                extra={"order_id": order_id, "file_id": file_id},
            )
            raise HTTPException(
                status_code=404,
                detail=(
                    "Attachment metadata not found or not associated with "
                    "this order."
                ),
            )

        logger.info(
            "Attachment metadata retrieved successfully",
            extra={"order_id": order_id, "file_id": file_id},
        )
        return FileDownloadResponse(
            file_id=file_metadata.file_id,
            filename=file_metadata.filename,
            content_type=file_metadata.content_type,
            size_bytes=file_metadata.size_bytes,
            uploaded_at=file_metadata.uploaded_at,
            metadata=file_metadata.metadata,
        )
    except RuntimeError as e:
        logger.error(
            "File storage service not available for metadata retrieval",
            extra={"order_id": order_id, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=503,
            detail="File storage service is currently unavailable.",
        )
    except HTTPException:
        raise  # Re-raise HTTPExceptions (e.g., 404)
    except Exception as e:
        logger.error(
            "Failed to get attachment metadata",
            extra={
                "order_id": order_id,
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to retrieve attachment metadata due to an internal "
                "error."
            ),
        )


@app.post("/orders/{order_id}/cancel", response_model=CancelOrderResponse)
async def cancel_order(
    order_id: str,
    request: CancelOrderRequest,
    client: Client = Depends(get_temporal_client),
) -> CancelOrderResponse:
    """
    Initiate the cancellation of an order by starting the CancelOrderWorkflow
    asynchronously. Returns immediately with a request_id for tracking.
    """
    logger.info(
        "Order cancellation requested via API",
        extra={
            "order_id": order_id,
            "reason": request.reason,
        },
    )

    try:
        # Generate a unique workflow ID for the cancellation request
        cancel_request_id = f"cancel-req-{order_id}-{uuid.uuid4()}"

        logger.debug(
            "Starting CancelOrderWorkflow",
            extra={
                "order_id": order_id,
                "cancel_request_id": cancel_request_id,
                "workflow_type": "CancelOrderWorkflow",
                "task_queue": "order-fulfillment-queue",
            },
        )

        # Start the cancellation workflow asynchronously, don't wait for
        # result
        await client.start_workflow(
            CancelOrderWorkflow.run,
            {"order_id": order_id, "reason": request.reason},
            id=cancel_request_id,
            task_queue="order-fulfillment-queue",
        )

        logger.info(
            "Order cancellation workflow started",
            extra={
                "order_id": order_id,
                "cancel_request_id": cancel_request_id,
            },
        )

        # Return immediately with request ID
        return CancelOrderResponse(
            order_id=order_id,
            status="CANCELLATION_INITIATED",
            reason="Cancellation workflow started",
            request_id=cancel_request_id,
        )

    except Exception as e:
        logger.error(
            "Failed to initiate order cancellation",
            extra={
                "order_id": order_id,
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to initiate order cancellation due to an "
            "internal error.",
        )
