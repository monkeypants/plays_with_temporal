"""
usecase logic must be clean, without direct dependencies.
dependencies are injected via repository instances.
"""

from typing import Optional, Dict
import logging
from pydantic import ValidationError

from sample.api.responses import OrderStatusResponse
from sample.domain import (
    Order,
    OrderItem,
    CreateOrderRequest,
    RefundPaymentArgs,
)
from util.domain import FileMetadata, FileUploadArgs
from sample.repositories import (
    PaymentRepository,
    InventoryRepository,
    OrderRepository,
    OrderRequestRepository,
)
from util.repositories import FileStorageRepository
from sample.validation import (
    ensure_payment_repository,
    ensure_inventory_repository,
    ensure_order_repository,
    ensure_order_request_repository,
)

logger = logging.getLogger(__name__)


class OrderFulfillmentUseCase:
    """
    Use case for order fulfillment following the saga pattern.

    This class orchestrates the business logic while remaining
    framework-agnostic.
    It depends only on repository protocols, not concrete implementations.

    In workflow contexts, this use case is called from workflow code with
    repository stubs that delegate to Temporal activities for durability.
    The use case remains completely unaware of whether it's running in a
    workflow context or a simple async context - it just calls repository
    methods and expects them to work correctly.

    Architectural Notes:
    - This class contains pure business logic with no framework dependencies
    - Repository dependencies are injected via constructor
      (dependency inversion)
    - All error handling and compensation logic is contained here
    - The use case converts between API models and domain models
    - Deterministic execution is guaranteed by avoiding
      non-deterministic operations
    """

    def __init__(
        self,
        payment_repo: PaymentRepository,
        inventory_repo: InventoryRepository,
        order_repo: OrderRepository,
        order_request_repo: OrderRequestRepository,
        file_storage_repo: Optional[
            FileStorageRepository
        ] = None,  # New optional dependency
    ) -> None:
        """Initialize order fulfillment use case.

        Args:
            payment_repo: Repository for payment operations
            inventory_repo: Repository for inventory operations
            order_repo: Repository for order operations (e.g., ID generation)
            order_request_repo: Repository for request-order mapping
            file_storage_repo: Optional repository for large file storage

        Note:
            The repositories passed here may be concrete implementations
            (for testing or direct execution) or workflow stubs (for
            Temporal workflow execution). The use case doesn't know or care
            which - it just calls the methods defined in the protocols.

            Repositories are validated at construction time to catch
            configuration errors early in the application lifecycle.
        """
        # Validate at construction time for early error detection
        self.payment_repo = ensure_payment_repository(payment_repo)
        self.inventory_repo = ensure_inventory_repository(inventory_repo)
        self.order_repo = ensure_order_repository(order_repo)
        self.order_request_repo = ensure_order_request_repository(
            order_request_repo
        )
        self.file_storage_repo = (
            file_storage_repo  # No validation for optional repo for now
        )

    async def fulfill_order(
        self, request: CreateOrderRequest, request_id: str
    ) -> OrderStatusResponse:
        """
        Execute the full order fulfillment saga with compensation.

        This method:
        1. Generates a unique order ID.
        2. Stores a bidirectional mapping between the request ID and the new
           order ID.
        3. Converts the Pydantic API request to a domain Order.
        4. Processes the order using domain logic and repositories.
        5. Returns a Pydantic API response.

        Saga Pattern Implementation:
        - Forward actions: Reserve inventory → Process payment
        - Compensation actions: Release inventory ← (payment failure)
        - Each step can be compensated if subsequent steps fails
        - All operations are idempotent to handle retries safely
        """
        logger.debug(
            "Starting order fulfillment use case",
            extra={
                "request_id": request_id,
                "customer_id": request.customer_id,
                "item_count": len(request.items),
                "total_amount": str(request.total_amount),
                "debug_step": "use_case_entry",
            },
        )

        # Generate order ID (delegated to activity via repository)
        logger.debug(
            "About to generate order ID",
            extra={
                "request_id": request_id,
                "debug_step": "before_order_id_generation",
            },
        )
        try:
            order_id = await self.order_repo.generate_order_id()
            logger.debug(
                "Order ID generated successfully",
                extra={
                    "request_id": request_id,
                    "order_id": order_id,
                    "debug_step": "order_id_generated",
                },
            )
        except Exception as e:
            logger.error(
                "Failed to generate order ID",
                extra={
                    "request_id": request_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "debug_step": "order_id_generation_failed",
                },
            )
            raise

        # Store bidirectional mapping (delegated to activity via repository)
        logger.debug(
            "About to store bidirectional mapping",
            extra={
                "request_id": request_id,
                "order_id": order_id,
                "debug_step": "before_mapping_storage",
            },
        )
        try:
            await self.order_request_repo.store_bidirectional_mapping(
                request_id, order_id
            )
            logger.debug(
                "Bidirectional mapping stored successfully",
                extra={
                    "request_id": request_id,
                    "order_id": order_id,
                    "debug_step": "mapping_stored",
                },
            )
        except Exception as e:
            logger.error(
                "Failed to store bidirectional mapping",
                extra={
                    "request_id": request_id,
                    "order_id": order_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "debug_step": "mapping_storage_failed",
                },
            )
            raise

        # Convert API request to domain Order with proper validation
        logger.debug(
            "About to create domain Order object",
            extra={
                "request_id": request_id,
                "order_id": order_id,
                "debug_step": "before_domain_order_creation",
            },
        )
        try:
            order = Order(
                order_id=order_id,
                customer_id=request.customer_id,
                items=[
                    OrderItem(
                        product_id=item.product_id,
                        quantity=item.quantity,
                        price=item.price,
                    )
                    for item in request.items
                ],
                total_amount=request.total_amount,
                status="pending",  # Initial status
            )
            logger.debug(
                "Domain Order object created successfully",
                extra={
                    "order_id": order.order_id,
                    "customer_id": order.customer_id,
                    "domain_item_count": len(order.items),
                    "debug_step": "domain_order_created",
                },
            )
        except ValidationError as e:
            logger.error(
                "Invalid order data during domain object creation",
                extra={
                    "order_id": order_id,
                    "customer_id": request.customer_id,
                    "validation_errors": e.errors(),
                    "debug_step": "domain_order_validation_failed",
                },
            )
            raise ValueError(f"Invalid order data: {e}")

        # Persist initial order state
        logger.debug(
            "About to save initial order state",
            extra={
                "order_id": order.order_id,
                "debug_step": "before_initial_order_save",
            },
        )
        try:
            await self.order_repo.save_order(order)
            logger.debug(
                "Initial order state saved successfully",
                extra={
                    "order_id": order.order_id,
                    "debug_step": "initial_order_saved",
                },
            )
        except Exception as e:
            logger.error(
                "Failed to save initial order state",
                extra={
                    "order_id": order.order_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "debug_step": "initial_order_save_failed",
                },
            )
            raise

        # Track if inventory was reserved for compensation in case of
        # unexpected errors
        inventory_reserved = False

        try:
            # Step 1: Reserve inventory (Forward Action)
            logger.debug(
                "About to reserve inventory items",
                extra={
                    "order_id": order.order_id,
                    "debug_step": "before_inventory_reserve",
                },
            )
            try:
                inventory_outcome = await self.inventory_repo.reserve_items(
                    order
                )
                logger.debug(
                    "Inventory reservation activity call returned",
                    extra={
                        "order_id": order.order_id,
                        "inventory_status_outcome": inventory_outcome.status,
                        "inventory_reason_outcome": inventory_outcome.reason,
                        "debug_step": "inventory_reserve_activity_returned",
                    },
                )
                logger.debug(
                    "Inventory reservation completed",
                    extra={
                        "order_id": order.order_id,
                        "inventory_status": inventory_outcome.status,
                        "debug_step": "inventory_reserved",
                    },
                )
            except Exception as e:
                logger.error(
                    "Inventory reservation failed with exception",
                    extra={
                        "order_id": order.order_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "debug_step": "inventory_reserve_exception",
                    },
                )
                raise

            if inventory_outcome.status == "failed":
                logger.debug(
                    "Order fulfillment failed due to inventory reservation "
                    "error",
                    extra={
                        "order_id": order.order_id,
                        "customer_id": order.customer_id,
                        "error_message": inventory_outcome.reason,
                        "debug_step": "inventory_failed_status_received",  # noqa: E501
                    },
                )
                # Update order status and persist
                order.status = "FAILED"
                order.reason = (
                    "Inventory reservation failed: "
                    f"{inventory_outcome.reason}"
                )
                logger.debug(
                    "Order status updated to FAILED (INVENTORY_FAILED) and "
                    "saving",
                    extra={
                        "order_id": order.order_id,
                        "new_status": order.status,
                        "debug_step": "inventory_failed_order_save",
                    },
                )
                await self.order_repo.save_order(order)
                return OrderStatusResponse(
                    order_id=order.order_id,
                    status="INVENTORY_FAILED",
                    reason=(
                        "Inventory reservation failed: "
                        f"{inventory_outcome.reason}"
                    ),
                )

            inventory_reserved = True  # Mark as reserved
            logger.debug(
                "Inventory reserved successfully",
                extra={
                    "order_id": order.order_id,
                    "reserved_items": (
                        len(inventory_outcome.reserved_items)
                        if inventory_outcome.reserved_items
                        else 0
                    ),
                    "debug_step": "inventory_reserve_success",
                },
            )

            # Step 2: Process payment (Forward Action)
            logger.debug(
                "About to process payment",
                extra={
                    "order_id": order.order_id,
                    "amount": str(order.total_amount),
                    "debug_step": "before_payment_process",
                },
            )
            try:
                payment_outcome = await self.payment_repo.process_payment(
                    order
                )
                logger.debug(
                    "Payment processing activity call returned",
                    extra={
                        "order_id": order.order_id,
                        "payment_status_outcome": payment_outcome.status,
                        "payment_reason_outcome": payment_outcome.reason,
                        "debug_step": "payment_process_activity_returned",
                    },
                )
                logger.debug(
                    "Payment processing completed",
                    extra={
                        "order_id": order.order_id,
                        "payment_status": payment_outcome.status,
                        "debug_step": "payment_processed",
                    },
                )
            except Exception as e:
                logger.error(
                    "Payment processing failed with exception",
                    extra={
                        "order_id": order.order_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                        "debug_step": "payment_process_exception",
                    },
                )
                raise

            if payment_outcome.status == "failed":
                logger.debug(
                    "Payment failed, starting compensation",
                    extra={
                        "order_id": order.order_id,
                        "payment_status": payment_outcome.status,
                        "reason": payment_outcome.reason,
                        "debug_step": "payment_failed_status_received",  # noqa: E501
                    },
                )
                # Compensation Action: Release reserved inventory
                try:
                    logger.debug(
                        "Attempting inventory compensation due to payment "
                        "failure",
                        extra={
                            "order_id": order.order_id,
                            "debug_step": "before_inventory_compensation",
                        },
                    )
                    await self.inventory_repo.release_items(order)
                    logger.debug(
                        "Inventory compensation completed for payment "
                        "failure",
                        extra={
                            "order_id": order.order_id,
                            "debug_step": "inventory_compensation_success",
                        },
                    )
                except Exception as release_error:
                    logger.error(
                        "Inventory compensation failed during payment error "
                        "handling",
                        extra={
                            "order_id": order.order_id,
                            "compensation_error_type": type(
                                release_error
                            ).__name__,
                            "compensation_error_message": str(release_error),
                            "debug_step": "inventory_compensation_failed",
                        },
                        exc_info=True,
                    )
                    pass  # Do not re-raise compensation error

                # Update order status and persist
                order.status = "PAYMENT_FAILED"
                order.reason = (
                    f"Payment processing failed: {payment_outcome.reason}"
                )
                logger.debug(
                    "Order status updated to PAYMENT_FAILED and saving",
                    extra={
                        "order_id": order.order_id,
                        "new_status": order.status,
                        "debug_step": "payment_failed_order_save",
                    },
                )
                await self.order_repo.save_order(order)
                return OrderStatusResponse(
                    order_id=order.order_id,
                    status="PAYMENT_FAILED",
                    reason=(
                        "Payment processing failed: "
                        f"{payment_outcome.reason}"
                    ),
                )

            # If payment_outcome.status is "completed", then
            # payment_outcome.payment must be present
            payment = (
                payment_outcome.payment
            )  # Type checker knows this is not None here

            logger.debug(
                "Payment successful, updating order to completed",
                extra={
                    "order_id": order.order_id,
                    "payment_id": payment.payment_id,
                    "debug_step": "before_final_order_save",
                },
            )

            # Update order status to completed and persist
            order.status = "completed"
            await self.order_repo.save_order(order)

            logger.debug(
                "Order fulfillment completed successfully",
                extra={
                    "order_id": order.order_id,
                    "customer_id": order.customer_id,
                    "final_status": "completed",
                    "debug_step": "fulfillment_success",
                },
            )

            # Return success result as Pydantic API response
            return OrderStatusResponse(
                order_id=order.order_id,
                payment_id=payment.payment_id,
                status="completed",  # Use lowercase "completed"
                transaction_id=payment.transaction_id,
            )

        except Exception as e:
            logger.error(
                "Order fulfillment failed with unexpected exception",
                extra={
                    "order_id": order_id,
                    "customer_id": order.customer_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "debug_step": "unexpected_exception_caught",
                },
                exc_info=True,
            )

            # If inventory was reserved, attempt compensation
            if inventory_reserved:
                try:
                    logger.debug(
                        "Attempting inventory compensation due to unexpected "
                        "error",
                        extra={
                            "order_id": order.order_id,
                            "debug_step": "before_unexpected_compensation",
                        },
                    )
                    await self.inventory_repo.release_items(order)
                    logger.debug(
                        "Inventory compensation completed for unexpected "
                        "error",
                        extra={
                            "order_id": order_id,
                            "debug_step": "unexpected_compensation_success",
                        },
                    )
                except Exception as release_error:
                    logger.error(
                        "Inventory compensation failed during unexpected "
                        "error handling",
                        extra={
                            "order_id": order_id,
                            "compensation_error_type": type(
                                release_error
                            ).__name__,
                            "compensation_error_message": str(release_error),
                            "debug_step": "unexpected_compensation_failed",
                        },
                        exc_info=True,
                    )
                    pass  # Do not re-raise compensation error

            # Update order status to failed and persist
            order.status = "FAILED"
            order.reason = f"Unexpected error during fulfillment: {str(e)}"
            logger.debug(
                "Order status updated to FAILED (unexpected exception) and "
                "saving",
                extra={
                    "order_id": order.order_id,
                    "new_status": order.status,
                    "debug_step": "unexpected_exception_order_save",
                },
            )
            await self.order_repo.save_order(order)
            return OrderStatusResponse(
                order_id=order.order_id,
                status="FAILED",
                reason=f"Unexpected error during fulfillment: {str(e)}",
            )

    async def upload_order_attachment(
        self,
        order_id: str,
        file_id: str,
        data: bytes,
        metadata: Dict[str, str],
        content_type: str = "application/octet-stream",
        filename: Optional[str] = None,
    ) -> FileMetadata:
        """
        Uploads an attachment related to an order.
        Requires file_storage_repo to be configured.
        """
        if not self.file_storage_repo:
            logger.error(
                "File storage repository not configured for "
                "upload_order_attachment"
            )
            raise RuntimeError("File storage service is not available.")

        logger.info(
            "Uploading order attachment",
            extra={
                "order_id": order_id,
                "file_id": file_id,
                "size_bytes": len(data),
                "content_type": content_type,
                "upload_filename": filename,
            },
        )

        # Add order_id to metadata for traceability in storage
        full_metadata = {"order_id": order_id, **metadata}

        # Use provided filename or default to file_id
        upload_filename = filename or file_id

        upload_args = FileUploadArgs(
            file_id=file_id,
            filename=upload_filename,
            data=data,
            metadata=full_metadata,
            content_type=content_type,
        )

        file_metadata = await self.file_storage_repo.upload_file(upload_args)

        logger.info(
            "Order attachment uploaded successfully",
            extra={
                "order_id": order_id,
                "file_id": file_id,
                "stored_size_bytes": file_metadata.size_bytes,
            },
        )
        return file_metadata

    async def download_order_attachment(
        self, order_id: str, file_id: str
    ) -> Optional[bytes]:
        """
        Downloads an attachment related to an order.
        Requires file_storage_repo to be configured.
        """
        if not self.file_storage_repo:
            logger.error(
                "File storage repository not configured for "
                "download_order_attachment"
            )
            raise RuntimeError("File storage service is not available.")

        logger.info(
            "Downloading order attachment",
            extra={"order_id": order_id, "file_id": file_id},
        )

        # Optionally, you could first get metadata and verify order_id matches
        # For simplicity, we'll just download directly
        file_content = await self.file_storage_repo.download_file(file_id)

        if file_content:
            logger.info(
                "Order attachment downloaded successfully",
                extra={
                    "order_id": order_id,
                    "file_id": file_id,
                    "size_bytes": len(file_content),
                },
            )
        else:
            logger.warning(
                "Order attachment not found or failed to download",
                extra={"order_id": order_id, "file_id": file_id},
            )
        return file_content

    async def get_order_attachment_metadata(
        self, order_id: str, file_id: str
    ) -> Optional[FileMetadata]:
        """
        Retrieves metadata for an attachment related to an order.
        Requires file_storage_repo to be configured.
        """
        if not self.file_storage_repo:
            logger.error(
                "File storage repository not configured for "
                "get_order_attachment_metadata"
            )
            raise RuntimeError("File storage service is not available.")

        logger.debug(
            "Getting order attachment metadata",
            extra={"order_id": order_id, "file_id": file_id},
        )

        file_metadata = await self.file_storage_repo.get_file_metadata(
            file_id
        )

        if (
            file_metadata
            and file_metadata.metadata.get("order_id") == order_id
        ):
            logger.info(
                "Order attachment metadata retrieved successfully",
                extra={"order_id": order_id, "file_id": file_id},
            )
            return file_metadata
        elif file_metadata:
            logger.warning(
                "File found but order_id mismatch for metadata",
                extra={
                    "file_id": file_id,
                    "requested_order_id": order_id,
                    "stored_order_id": file_metadata.metadata.get("order_id"),
                },
            )
            return None  # Mismatch means it's not *this* order's attachment
        else:
            logger.warning(
                "Order attachment metadata not found",
                extra={"order_id": order_id, "file_id": file_id},
            )
            return None


class GetOrderUseCase:
    """
    Use case for retrieving order information.
    """

    def __init__(
        self, order_repo: OrderRepository, payment_repo: PaymentRepository
    ) -> None:
        self.order_repo = ensure_order_repository(order_repo)
        self.payment_repo = ensure_payment_repository(payment_repo)

    async def get_order_status(self, order_id: str) -> OrderStatusResponse:
        """
        Get the status of an order by querying repositories.

        This method:
        1. Attempts to get the Order object from the order repository.
        2. If found, returns its status.
        3. If not found, falls back to checking payment information (for
           backward compatibility or specific cases).
        """
        logger.debug("Getting order status", extra={"order_id": order_id})

        # First, try to get the Order object itself
        order = await self.order_repo.get_order(order_id)
        if order:
            logger.info(
                "Order status found via order repository",
                extra={"order_id": order_id, "status": order.status},
            )

            # Directly use refund_id and refund_status from the Order object
            # These fields are now populated by CancelOrderUseCase
            return OrderStatusResponse(
                order_id=order.order_id,
                status=order.status,
                reason=order.reason,
                refund_id=order.refund_id,  # Read from order object
                refund_status=order.refund_status,  # Read from order object
            )

        # If order not found, fall back to checking payment (old logic, or
        # for processing state)
        payment_id = f"pmt_{order_id}"
        logger.debug(
            "Order not found, querying payment repository as fallback",
            extra={"order_id": order_id, "payment_id": payment_id},
        )

        payment = await self.payment_repo.get_payment(payment_id)

        if payment:
            logger.info(
                "Order status found via payment repository (fallback)",
                extra={
                    "order_id": order_id,
                    "payment_status": payment.status,
                    "payment_id": payment.payment_id,
                },
            )

            # This fallback logic doesn't have the full order context,
            # so it can't provide detailed refund status from the order
            # object.
            # It should only provide refund status if the payment itself is
            # 'refunded'.
            refund_id = None
            refund_status = None
            if payment.status == "refunded":
                refund_id = f"ref_{payment_id}"
                refund_status = "completed"

            return OrderStatusResponse(
                order_id=order_id,
                status=payment.status,
                payment_id=payment.payment_id,
                transaction_id=payment.transaction_id,
                refund_id=refund_id,
                refund_status=refund_status,
            )

        logger.debug(
            "No order or payment found, order still processing or not found",
            extra={"order_id": order_id},
        )
        return OrderStatusResponse(order_id=order_id, status="processing")

    async def get_order(self, order_id: str) -> Optional[Order]:
        """
        Get an order by its ID.
        """
        logger.debug("Getting order", extra={"order_id": order_id})
        order: Optional[Order] = await self.order_repo.get_order(order_id)
        return order


class CancelOrderUseCase:
    """
    Use case for cancelling an order, including compensation logic.
    """

    def __init__(
        self,
        order_repo: OrderRepository,
        payment_repo: PaymentRepository,
        inventory_repo: InventoryRepository,
    ) -> None:
        self.order_repo = ensure_order_repository(order_repo)
        self.payment_repo = ensure_payment_repository(payment_repo)
        self.inventory_repo = ensure_inventory_repository(inventory_repo)

    async def cancel_order(
        self, order_id: str, reason: Optional[str] = None
    ) -> OrderStatusResponse:
        """
        Cancel an existing order. This involves:
        1. Fetching the order.
        2. Checking its current status.
        3. Updating the order status to 'CANCELLING'.
        4. Attempting to refund the payment if it was completed.
        5. Attempting to release reserved inventory.
        6. Updating the order status to 'CANCELLED'.
        """
        logger.info(
            "Starting order cancellation use case",
            extra={"order_id": order_id, "reason": reason},
        )

        order = await self.order_repo.get_order(order_id)
        if not order:
            logger.warning(
                "Cancellation failed: Order not found",
                extra={"order_id": order_id},
            )
            return OrderStatusResponse(
                order_id=order_id, status="FAILED", reason="Order not found."
            )

        if order.status in ["CANCELLED", "CANCELLING"]:
            logger.info(
                "Order already cancelled or in cancellation process",
                extra={"order_id": order_id, "current_status": order.status},
            )
            # If already cancelled, return its current status, including
            # refund info
            return OrderStatusResponse(
                order_id=order.order_id,
                status=order.status,
                reason=order.reason,
                refund_id=order.refund_id,  # Use new field
                refund_status=order.refund_status,  # Use new field
            )

        # Set status to CANCELLING and persist
        order.status = "CANCELLING"
        order.reason = reason if reason else "Cancellation initiated"
        await self.order_repo.save_order(order)
        logger.info(
            "Order status set to CANCELLING", extra={"order_id": order_id}
        )

        # Initialize refund status for the order object
        order.refund_id = None
        order.refund_status = "not_applicable"  # Default to not applicable
        # unless a refund is attempted

        try:
            # Step 1: Refund payment (if applicable and completed)
            payment_id = f"pmt_{order_id}"
            payment = await self.payment_repo.get_payment(payment_id)

            if payment and payment.status == "completed":
                logger.debug(
                    "Attempting to refund payment",
                    extra={
                        "order_id": order_id,
                        "payment_id": payment.payment_id,
                        "amount": str(payment.amount),
                    },
                )
                refund_args = RefundPaymentArgs(
                    payment_id=payment.payment_id,
                    order_id=order.order_id,
                    amount=payment.amount,
                    reason=reason or "Order cancellation",
                )
                refund_outcome = await self.payment_repo.refund_payment(
                    refund_args
                )

                logger.debug(
                    "DEBUG: CancelOrderUseCase - Refund outcome received",
                    extra={
                        "order_id": order_id,
                        "refund_status_from_repo": refund_outcome.status,
                        "refund_reason_from_repo": refund_outcome.reason,
                    },
                )

                order.refund_id = (
                    refund_outcome.refund_id
                )  # Update order object
                if refund_outcome.status == "refunded":
                    order.refund_status = "completed"  # Map 'refunded'
                    # outcome to 'completed' status on Order
                else:
                    order.refund_status = (
                        refund_outcome.status
                    )  # Use the outcome status directly for 'failed'

                if refund_outcome.status == "refunded":
                    logger.info(
                        "Payment successfully refunded",
                        extra={
                            "order_id": order_id,
                            "payment_id": payment.payment_id,
                            "refund_id": refund_outcome.refund_id,
                        },
                    )
                else:
                    logger.warning(
                        "Payment refund failed",
                        extra={
                            "order_id": order_id,
                            "payment_id": payment.payment_id,
                            "refund_reason": refund_outcome.reason,
                        },
                    )
                    # Log, but don't fail the entire cancellation. Manual
                    # intervention needed.
            elif payment and payment.status == "failed":
                logger.info(
                    "Payment already failed, no refund needed",
                    extra={"order_id": order_id},
                )
                order.refund_status = "not_applicable"  # Explicitly set
            elif payment and payment.status == "pending":
                logger.info(
                    "Payment pending, no refund needed (or will be "
                    "cancelled automatically)",
                    extra={"order_id": order_id},
                )
                order.refund_status = "not_applicable"  # Explicitly set
            else:
                logger.info(
                    "No completed payment found to refund",
                    extra={"order_id": order_id},
                )
                order.refund_status = "not_applicable"  # Explicitly set

            # Step 2: Release inventory (if reserved)
            logger.debug(
                "Attempting to release inventory",
                extra={"order_id": order_id},
            )
            await self.inventory_repo.release_items(
                order
            )  # release_items is idempotent and safe to call
            logger.info(
                "Inventory release attempted", extra={"order_id": order_id}
            )

            # Finalize order status
            order.status = "CANCELLED"
            order.reason = (
                reason if reason else "Order successfully cancelled"
            )
            await self.order_repo.save_order(
                order
            )  # Save the final state of the order, including refund status
            logger.info(
                "Order successfully cancelled", extra={"order_id": order_id}
            )

            return OrderStatusResponse(
                order_id=order.order_id,
                status="CANCELLED",
                reason=order.reason,
                payment_id=payment.payment_id if payment else None,
                transaction_id=payment.transaction_id if payment else None,
                refund_id=order.refund_id,  # Use new field
                refund_status=order.refund_status,  # Use new field
            )

        except Exception as e:
            logger.error(
                "Unexpected error during order cancellation",
                extra={
                    "order_id": order_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
                exc_info=True,
            )

            # Attempt to revert order status if possible, or mark as
            # FAILED_CANCELLATION
            order.status = (
                "FAILED_CANCELLATION"  # New status if needed, or just FAILED
            )
            order.reason = (
                f"Cancellation failed due to unexpected error: {str(e)}"
            )
            # Ensure refund_status is set to failed if an exception occurred
            # during refund process
            if (
                order.refund_status is None
                or order.refund_status == "pending"
            ):  # If not already set by a failed refund_outcome
                order.refund_status = "failed"
            await self.order_repo.save_order(order)

            return OrderStatusResponse(
                order_id=order_id,
                status="FAILED",  # Or "FAILED_CANCELLATION" if we add it
                reason=(
                    "Cancellation failed due to unexpected error: "
                    f"{str(e)}"
                ),
                refund_id=order.refund_id,  # Use new field
                refund_status=order.refund_status,  # Use new field
            )
