"""
Repository interfaces defined as Protocols.

All repository operations in this module follow these principles:

- **Idempotency**: All methods are designed to be idempotent and safe for
  retry. Multiple calls with the same parameters will produce the same
  result without unintended side effects.

- **Saga Pattern Support**: Operations that modify state can be
  compensated. Each forward action has a corresponding compensation action
  that can undo its effects.

- **Workflow Safety**: All operations are safe to call from deterministic
  workflow contexts. Non-deterministic operations (like ID generation) are
  explicitly delegated to activities.

- **Domain Objects**: Methods accept and return domain objects or primitives,
  never framework-specific types.

In Temporal workflow contexts, these protocols are implemented by workflow
stubs that delegate to activities for durability and proper error handling.

Architectural Notes:

- These are pure interfaces with no implementation details
- They define contracts that both concrete implementations and workflow stubs must satisfy
- The protocols ensure type safety and enable dependency inversion
- Repository implementations are free to be non-deterministic (generate
  IDs, make network calls)
- Use case classes depend on these protocols, not concrete implementations
"""

from typing import Protocol, List, Optional, runtime_checkable
from sample.domain import (
    Order,
    Payment,
    InventoryItem,
    PaymentOutcome,
    InventoryReservationOutcome,
    RefundPaymentArgs,
    RefundPaymentOutcome,
)


@runtime_checkable
class PaymentRepository(Protocol):
    """Handles payment processing operations.

    Architectural Context:
    This protocol defines the contract for payment operations without
    specifying how they're implemented. In workflow contexts, methods
    are implemented as activity stubs. In testing, they're mocked.
    In direct execution, they call real payment services.

    The protocol ensures that use cases can work with any implementation
    that satisfies this contract, enabling true dependency inversion.
    """

    async def process_payment(self, order: Order) -> PaymentOutcome:
        """Process payment for an order.

        Args:
            order: Domain order object with validated data

        Returns:
            PaymentOutcome domain object indicating success ('completed')
            or failure ('failed') with a reason.

        Implementation Notes:

        - Must be idempotent: calling multiple times with same order returns same result
        - May perform non-deterministic operations (network calls, ID
          generation)
        - Should handle partial failures gracefully
        - Must return valid PaymentOutcome domain objects that pass Pydantic
          validation
        """
        ...

    async def get_payment(self, payment_id: str) -> Optional[Payment]:
        """Retrieve payment by ID.

        Args:
            payment_id: Unique payment identifier

        Returns:
            Payment object if found, None otherwise

        Implementation Notes:
        - Must be idempotent: multiple calls return same result
        - Should handle missing payments gracefully (return None, don't raise)
        - May query external systems or local storage
        """
        ...

    async def refund_payment(
        self, args: RefundPaymentArgs
    ) -> RefundPaymentOutcome:
        """Refund a previously processed payment.

        Args:
            args: RefundPaymentArgs containing payment_id, order_id, amount,
                and reason.

        Returns:
            RefundPaymentOutcome indicating success ('refunded') or failure
            ('failed').

        Implementation Notes:

        - Must be idempotent: calling multiple times with same args returns same result.
        - Should handle cases where payment is not found or already refunded
          gracefully.
        - May interact with external payment gateways.
        """
        ...


@runtime_checkable
class InventoryRepository(Protocol):
    """Handles inventory reservation and release operations.

    Saga Pattern Implementation:
    This repository implements the forward/compensation pattern:
    - reserve_items() is the forward action
    - release_items() is the compensation action

    Both operations must be idempotent to handle workflow retries safely.
    """

    async def reserve_items(
        self, order: Order
    ) -> InventoryReservationOutcome:
        """Reserve inventory items for an order.

        Args:
            order: Domain order object with items to reserve

        Returns:
            InventoryReservationOutcome object indicating success ('reserved')
            or failure ('failed') with a reason.

        Saga Pattern Notes:

        - This is a forward action that can be compensated using release_items()
        - Must be idempotent: reserving same order multiple times has same effect
        - Should atomically reserve all items or fail completely
        - Implementations may use pessimistic locking or optimistic
          concurrency control
        """
        ...

    async def release_items(self, order: Order) -> List[InventoryItem]:
        """Release previously reserved inventory items.

        This is the compensation operation for reserve_items().
        Safe to call even if items weren't previously reserved.

        Args:
            order: Domain order object with items to release

        Returns:
            List of InventoryItem objects representing released items

        Compensation Pattern Notes:

        - This is a compensation action for reserve_items()
        - Must be idempotent: multiple calls have same effect
        - Must be safe to call without prior reserve (graceful handling)
        - Should not raise exceptions for missing reservations
        - Critical for saga pattern - failure here requires manual intervention
        """
        ...


@runtime_checkable
class OrderRepository(Protocol):
    """Handles order-related operations that must be delegated from workflows.

    Workflow Determinism Context:
    ID generation is handled here rather than in use cases because workflows
    run in deterministic contexts where non-deterministic operations must be
    delegated to activities for proper replay behaviour.

    This separation ensures:
    - Use cases remain deterministic (can be replayed safely)
    - Non-deterministic operations are isolated to activities
    - The same use case can work in both workflow and non-workflow contexts

    Architectural Decision:
    We could generate IDs in the API layer, but placing it here allows
    the same use case to work in different contexts (API-driven, event-driven,
    batch processing) while maintaining proper separation of concerns.
    """

    async def generate_order_id(self) -> str:
        """Generate a unique order identifier.

        This operation is non-deterministic and must be called from
        workflow activities, not directly from workflow code.

        Returns:
            Unique order ID string

        Implementation Notes:
        - Must generate globally unique identifiers
        - May use UUIDs, database sequences, or distributed ID generators
        - Should be fast and reliable
        - Failure here should be rare but handled gracefully

        Workflow Context:
        In Temporal workflows, this method is implemented as an activity
        to ensure the generated ID is durably stored and consistent
        across workflow replays.
        """
        ...

    async def save_order(self, order: Order) -> None:
        """Persist the state of an order.

        Args:
            order: The Order domain object to save.

        Implementation Notes:

        - Must be idempotent: saving the same order multiple times is safe.
        - Should persist the full state of the Order object, including its status.
        """
        ...

    async def get_order(self, order_id: str) -> Optional[Order]:
        """Retrieve an order by its ID.

        Args:
            order_id: The ID of the order to retrieve.

        Returns:
            The Order domain object if found, None otherwise.
        """
        ...

    async def cancel_order(
        self, order_id: str, reason: Optional[str] = None
    ) -> None:
        """Cancel an order by updating its status.

        Args:
            order_id: The ID of the order to cancel.
            reason: Optional reason for cancellation.

        Implementation Notes:

        - Must be idempotent: calling multiple times with same order_id is safe.
        - Should update the order's status to 'CANCELLED'.
        - Should handle cases where the order is not found gracefully.
        """
        ...


@runtime_checkable
class OrderRequestRepository(Protocol):
    """Provides bidirectional mapping between request IDs and order IDs.

    Supports O(1) lookup performance in both directions using dual indices.

    Architectural Purpose:
    This repository solves the problem of tracking the relationship between
    API requests (which return immediately) and orders (which are created
    asynchronously by workflows). It enables:
    - Clients to poll request status using request_id
    - Automatic redirection to order status once order is created
    - Efficient lookup in both directions without table scans

    Implementation Strategy:
    Uses dual storage objects for O(1) bidirectional lookups:
    - request-{id}.json contains the mapping
    - order-{id}.json contains the same mapping
    This avoids expensive queries while maintaining consistency.
    """

    async def store_bidirectional_mapping(
        self, request_id: str, order_id: str
    ) -> None:
        """Store bidirectional mapping between request ID and order ID.

        Creates dual indices for O(1) lookups in both directions. Partial
        failures during dual index creation are resolved on subsequent
        calls.

        Args:
            request_id: Unique request identifier
            order_id: Unique order identifier

        Implementation Notes:

        - Must be idempotent: storing same mapping multiple times is safe
        - Should handle partial failures gracefully (e.g., one index succeeds, other fails)
        - May use eventual consistency - temporary inconsistency is
          acceptable
        - Critical for API user experience - failures here affect request
          tracking
        """
        ...

    async def get_order_id_for_request(
        self, request_id: str
    ) -> Optional[str]:
        """Get order ID for a given request ID.

        Args:
            request_id: Unique request identifier

        Returns:
            Order ID if mapping exists, None otherwise

        Performance Notes:
        - Must be O(1) lookup for good API response times
        - Should handle missing mappings gracefully (return None)
        - May cache results for frequently accessed mappings
        """
        ...

    async def get_request_id_for_order(self, order_id: str) -> Optional[str]:
        """Get request ID for a given order ID.

        Args:
            order_id: Unique order identifier

        Returns:
            Request ID if mapping exists, None otherwise

        Use Case:
        Primarily used for workflow status queries where we have an
        order_id but need to find the corresponding workflow (identified
        by request_id).
        """
        ...
