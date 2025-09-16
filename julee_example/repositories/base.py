"""
Generic base repository protocol for common CRUD operations.

This module defines a generic BaseRepository protocol that captures the common
patterns shared across all domain repositories in the Capture, Extract,
Assemble, Publish workflow. This reduces code duplication while maintaining
type safety and clean interfaces.

All repository operations follow the same principles:

- **Idempotency**: All methods are designed to be idempotent and safe for
  retry. Multiple calls with the same parameters will produce the same
  result without unintended side effects.

- **Workflow Safety**: All operations are safe to call from deterministic
  workflow contexts. Non-deterministic operations (like ID generation) are
  explicitly delegated to activities.

- **Domain Objects**: Methods accept and return domain objects or primitives,
  never framework-specific types.

In Temporal workflow contexts, these protocols are implemented by workflow
stubs that delegate to activities for durability and proper error handling.
"""

from typing import Protocol, Optional, runtime_checkable, TypeVar
from pydantic import BaseModel

# Type variable bound to Pydantic BaseModel for domain entities
T = TypeVar("T", bound=BaseModel)


@runtime_checkable
class BaseRepository(Protocol[T]):
    """Generic base repository protocol for common CRUD operations.

    This protocol defines the common interface shared by all domain
    repositories in the system. It uses generics to provide type safety
    while eliminating code duplication.

    Type Parameter:
        T: The domain entity type (must extend Pydantic BaseModel)
    """

    async def get(self, entity_id: str) -> Optional[T]:
        """Retrieve an entity by ID.

        Args:
            entity_id: Unique entity identifier

        Returns:
            Entity if found, None otherwise

        Implementation Notes:
        - Must be idempotent: multiple calls return same result
        - Should handle missing entities gracefully (return None)
        - Loads complete entity with all relationships
        """
        ...

    async def save(self, entity: T) -> None:
        """Save an entity.

        Args:
            entity: Complete entity to save

        Implementation Notes:
        - Must be idempotent: saving same entity state is safe
        - Should update the updated_at timestamp
        - Must save complete entity with all relationships
        - Handles both new entities and updates to existing ones
        """
        ...

    async def generate_id(self) -> str:
        """Generate a unique entity identifier.

        This operation is non-deterministic and must be called from
        workflow activities, not directly from workflow code.

        Returns:
            Unique entity ID string

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
