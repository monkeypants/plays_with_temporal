"""
Pydantic models for API responses.
These define the contract between the API and external clients.
"""

from typing import Optional, Dict
from pydantic import BaseModel, Field  # Added Field


class OrderResponse(BaseModel):
    """Response for order creation"""

    order_id: str
    status: str


class OrderStatusResponse(BaseModel):
    """Response for order status query"""

    order_id: str
    status: str
    payment_id: Optional[str] = None
    transaction_id: Optional[str] = None
    reason: Optional[str] = None
    current_step: Optional[str] = None
    refund_id: Optional[str] = None  # Added for cancellation/refund status
    refund_status: Optional[str] = (
        None  # Added for cancellation/refund status
    )


class CancelOrderResponse(BaseModel):
    """Response for order cancellation request."""

    order_id: str
    status: str  # e.g., "SUBMITTED", "CANCELLATION_INITIATED"
    reason: Optional[str] = None
    request_id: Optional[str] = (
        None  # Added for tracking cancellation request
    )


class HealthCheckResponse(BaseModel):
    status: str
    version: str


class OrderRequestResponse(BaseModel):
    """Response for order request creation"""

    request_id: str
    status: str


class OrderRequestStatusResponse(BaseModel):
    """Response for order request status query"""

    request_id: str
    status: str


class FileUploadResponse(BaseModel):
    """Response for file upload operation."""

    file_id: str
    message: str
    filename: Optional[str] = None
    content_type: Optional[str] = None
    size_bytes: Optional[int] = None
    metadata: Dict[str, str] = Field(default_factory=dict)


class FileDownloadResponse(BaseModel):
    """Response for file download operation (metadata only, content is
    direct).
    """

    file_id: str
    filename: Optional[str] = None
    content_type: Optional[str] = None
    size_bytes: Optional[int] = None
    uploaded_at: Optional[str] = None
    metadata: Dict[str, str] = Field(default_factory=dict)
