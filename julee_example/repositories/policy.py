"""
Policy repository interface defined as Protocol for the Capture, Extract,
Assemble, Publish workflow.

This module defines the core policy storage and retrieval repository
protocol. The repository works with Policy domain objects that define
validation criteria and optional transformations for documents.

All repository operations follow the same principles as the sample
repositories:

- **Idempotency**: All methods are designed to be idempotent and safe for
  retry. Multiple calls with the same parameters will produce the same
  result without unintended side effects.

- **Workflow Safety**: All operations are safe to call from deterministic
  workflow contexts. Non-deterministic operations (like ID generation) are
  explicitly delegated to activities.

- **Domain Objects**: Methods accept and return domain objects or primitives,
  never framework-specific types. Policy contains validation scores and
  optional transformation queries.

- **Policy Management**: Repository handles Policy entities with their
  validation criteria, transformation queries, and status management for
  the quality assurance workflow.

In Temporal workflow contexts, these protocols are implemented by workflow
stubs that delegate to activities for durability and proper error handling.
"""

from typing import Protocol, Optional, runtime_checkable
from julee_example.domain import Policy


@runtime_checkable
class PolicyRepository(Protocol):
    """Handles policy storage and retrieval operations.

    This repository manages Policy entities within the Capture, Extract,
    Assemble, Publish workflow. Policies define validation criteria and
    optional transformations for documents in the quality assurance process.
    """

    async def get(self, policy_id: str) -> Optional[Policy]:
        """Retrieve a policy by ID.

        Args:
            policy_id: Unique policy identifier

        Returns:
            Policy if found, None otherwise

        Implementation Notes:
        - Must be idempotent: multiple calls return same result
        - Should handle missing policies gracefully (return None)
        - Loads complete policy including validation scores and
          transformation queries
        """
        ...

    async def save(self, policy: Policy) -> None:
        """Save a policy.

        Args:
            policy: Complete Policy to save

        Implementation Notes:
        - Must be idempotent: saving same policy state is safe
        - Should update the updated_at timestamp
        - Must save complete policy including validation scores and
          transformation queries
        - Handles both new policies and updates to existing ones
        """
        ...

    async def generate_id(self) -> str:
        """Generate a unique policy identifier.

        This operation is non-deterministic and must be called from
        workflow activities, not directly from workflow code.

        Returns:
            Unique policy ID string

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
