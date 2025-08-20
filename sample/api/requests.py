"""
Pydantic models for API requests.
These define the contract between the API and external clients.
"""

from typing import Optional
from pydantic import BaseModel  # Added BaseModel for CancelOrderRequest


# OrderItemRequest and CreateOrderRequest moved to sample/domain.py

# This file now only contains models specific to API request parsing
# that are not used directly by workflows.
# UploadFileRequest was previously removed.
# Keeping this file to maintain package structure.


class CancelOrderRequest(BaseModel):
    """Request model for cancelling an order."""

    reason: Optional[str] = None
