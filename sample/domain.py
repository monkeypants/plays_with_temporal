"""
Domain models defined as Pydantic models.
These are pure data structures with validation.
"""

from pydantic import (
    BaseModel,
    Field,
    field_validator,
)
from typing import Optional, List, Literal
from decimal import Decimal
from datetime import datetime


class OrderItem(BaseModel):
    product_id: str
    quantity: int
    price: Decimal

    @field_validator("quantity")
    @classmethod
    def quantity_must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Quantity must be positive")
        return v

    @field_validator("price")
    @classmethod
    def price_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Price must be positive")
        return v


class OrderItemRequest(BaseModel):
    """Request model for order items in API requests."""

    product_id: str
    quantity: int
    price: Decimal

    @field_validator("quantity")
    @classmethod
    def quantity_must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Quantity must be positive")
        return v

    @field_validator("price")
    @classmethod
    def price_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Price must be positive")
        return v


class CreateOrderRequest(BaseModel):
    """Request model for creating an order."""

    customer_id: str
    items: List[OrderItemRequest]

    @field_validator("items")
    @classmethod
    def items_must_not_be_empty(cls, v: List[OrderItemRequest]) -> List[OrderItemRequest]:
        if not v:
            raise ValueError("Order must contain at least one item")
        return v

    @property
    def total_amount(self) -> Decimal:
        """Calculate total amount from items."""
        return sum(item.price * item.quantity for item in self.items) or Decimal("0")


class Order(BaseModel):
    order_id: str
    customer_id: str
    items: List[OrderItem]
    total_amount: Decimal
    status: Literal[
        "pending",
        "completed",
        "FAILED",
        "PAYMENT_FAILED",
        "CANCELLING",
        "CANCELLED",
        "FAILED_CANCELLATION",
    ] = "pending"
    reason: Optional[str] = None
    refund_id: Optional[str] = None
    refund_status: Optional[
        Literal["completed", "failed", "pending", "not_applicable"]
    ] = None

    @field_validator("items")
    @classmethod
    def items_must_not_be_empty(cls, v: List[OrderItem]) -> List[OrderItem]:
        if not v:
            raise ValueError("Order must contain at least one item")
        return v

    @field_validator("total_amount")
    @classmethod
    def total_amount_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Total amount must be positive")
        return v


class Payment(BaseModel):
    payment_id: str
    order_id: str
    amount: Decimal
    status: Literal["completed", "failed", "pending", "cancelled", "refunded"]
    transaction_id: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v


class PaymentOutcome(BaseModel):
    """Result of a payment processing attempt."""

    status: Literal["completed", "failed", "refunded"]
    payment: Optional[Payment] = None
    reason: Optional[str] = None

    @field_validator("payment")
    @classmethod
    def payment_must_be_present_if_completed(cls, v: Optional[Payment], info) -> Optional[Payment]:
        if info.data.get("status") == "completed" and v is None:
            raise ValueError(
                "Payment object must be present if status is completed"
            )
        return v


class RefundPaymentArgs(BaseModel):
    """Arguments for refunding a payment."""

    payment_id: str
    order_id: str
    amount: Decimal
    reason: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v


class RefundPaymentOutcome(BaseModel):
    """Result of a payment refund attempt."""

    status: Literal["refunded", "failed"]
    refund_id: Optional[str] = None
    reason: Optional[str] = None

    @field_validator("refund_id")
    @classmethod
    def refund_id_must_be_present_if_refunded(cls, v: Optional[str], info) -> Optional[str]:
        if info.data.get("status") == "refunded" and v is None:
            raise ValueError(
                "Refund ID must be present if status is 'refunded'"
            )
        return v


class InventoryItem(BaseModel):
    product_id: str
    quantity: int
    reserved: int = 0

    @field_validator("quantity")
    @classmethod
    def quantity_must_be_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Quantity must be non-negative")
        return v

    @field_validator("reserved")
    @classmethod
    def reserved_must_be_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Reserved quantity must be non-negative")
        return v


class InventoryReservationOutcome(BaseModel):
    """Result of an inventory reservation attempt."""

    status: Literal["reserved", "failed"]
    reserved_items: Optional[List[InventoryItem]] = None
    reason: Optional[str] = None

    @field_validator("reserved_items")
    @classmethod
    def reserved_items_must_be_present_if_reserved(cls, v: Optional[List[InventoryItem]], info) -> Optional[List[InventoryItem]]:
        if info.data.get("status") == "reserved" and (v is None or not v):
            raise ValueError(
                "Reserved items must be present if status is reserved"
            )
        return v


class RequestOrderMapping(BaseModel):
    """Bidirectional mapping between request ID and order ID"""

    request_id: str
    order_id: str
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )
