"""
KnowledgeServiceConfig repository interface defined as Protocol for the
Capture, Extract, Assemble, Publish workflow.

This module defines the knowledge service configuration repository protocol.
The repository works with KnowledgeService domain objects for metadata
persistence only. External service operations are handled by the service
layer.

All repository operations follow the same principles as the sample
repositories:

- **Idempotency**: All methods are designed to be idempotent and safe for
  retry. Multiple calls with the same parameters will produce the same
  result without unintended side effects.

- **Workflow Safety**: All operations are safe to call from deterministic
  workflow contexts. Non-deterministic operations (like ID generation) are
  explicitly delegated to activities.

- **Domain Objects**: Methods accept and return domain objects or primitives,
  never framework-specific types. Results are returned as structured domain
  objects.

- **External Service Integration**: Repository implementations handle the
  complexities of integrating with external knowledge services while
  maintaining a clean, consistent interface.

In Temporal workflow contexts, these protocols are implemented by workflow
stubs that delegate to activities for durability and proper error handling.
"""

from typing import Protocol, Optional, runtime_checkable
from julee_example.domain import KnowledgeServiceConfig


@runtime_checkable
class KnowledgeServiceConfigRepository(Protocol):
    """Handles knowledge service configuration persistence.

    This repository manages knowledge service metadata and configuration
    storage within the Capture, Extract, Assemble, Publish workflow.
    External service operations are handled separately by the service layer.
    """

    async def get(
        self, knowledge_service_id: str
    ) -> Optional[KnowledgeServiceConfig]:
        """Retrieve a knowledge service configuration by ID.

        Args:
            knowledge_service_id: Unique knowledge service identifier

        Returns:
            KnowledgeServiceConfig object if found, None otherwise

        Implementation Notes:
        - Must be idempotent: multiple calls return same result
        - Should handle missing services gracefully (return None)
        - Must load complete service configuration
        """
        ...

    async def save(self, knowledge_service: KnowledgeServiceConfig) -> None:
        """Save a knowledge service configuration.

        Args:
            knowledge_service: Complete KnowledgeServiceConfig to save

        Implementation Notes:
        - Must be idempotent: saving same service state is safe
        - Should update the updated_at timestamp
        - Must save complete service configuration
        - Handles both new services and updates to existing ones
        """
        ...

    async def generate_id(self) -> str:
        """Generate a unique knowledge service identifier.

        This operation is non-deterministic and must be called from
        workflow activities, not directly from workflow code.

        Returns:
            Unique knowledge service ID string

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
