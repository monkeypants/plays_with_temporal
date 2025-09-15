"""
Assembly repository interface defined as Protocol for the Capture, Extract,
Assemble, Publish workflow.

This module defines the core assembly storage and retrieval repository
protocol. The repository works with Assembly domain objects that produce
a single assembled document.

All repository operations follow the same principles as the sample
repositories:

- **Idempotency**: All methods are designed to be idempotent and safe for
  retry. Multiple calls with the same parameters will produce the same
  result without unintended side effects.

- **Workflow Safety**: All operations are safe to call from deterministic
  workflow contexts. Non-deterministic operations (like ID generation) are
  explicitly delegated to activities.

- **Domain Objects**: Methods accept and return domain objects or primitives,
  never framework-specific types. Assembly contains its assembled document ID.

- **Aggregate Boundary**: Repository handles Assembly entities with their
  assembled document references.

In Temporal workflow contexts, these protocols are implemented by workflow
stubs that delegate to activities for durability and proper error handling.
"""

from typing import Protocol, Optional, runtime_checkable
from julee_example.domain import Assembly


@runtime_checkable
class AssemblyRepository(Protocol):
    """Handles assembly storage and retrieval operations.

    This repository manages Assembly entities within the Capture, Extract,
    Assemble, Publish workflow. Each Assembly produces a single assembled
    document.
    """

    async def get(self, assembly_id: str) -> Optional[Assembly]:
        """Retrieve an assembly by ID.

        Args:
            assembly_id: Unique assembly identifier

        Returns:
            Assembly if found, None otherwise

        Implementation Notes:
        - Must be idempotent: multiple calls return same result
        - Should handle missing assemblies gracefully (return None)
        - Loads complete assembly including assembled_document_id
        """
        ...

    async def set_assembled_document(
        self, assembly_id: str, document_id: str
    ) -> Assembly:
        """Set the assembled document for an assembly.

        Args:
            assembly_id: ID of the assembly to update
            document_id: ID of the assembled document produced

        Returns:
            Updated Assembly with the assembled_document_id set

        Implementation Notes:
        - Idempotent: setting same document_id multiple times is safe
        - Updates assembly's updated_at timestamp
        - Updates assembly status to COMPLETED if successful
        - Returns complete assembly with assembled_document_id set
        """
        ...

    async def save(self, assembly: Assembly) -> None:
        """Save assembly metadata (status, updated_at, etc.).

        Args:
            assembly: Assembly entity

        Implementation Notes:
        - Must be idempotent: saving same assembly state is safe
        - Should update the updated_at timestamp
        - Saves complete assembly including assembled_document_id
        - Use for status changes, metadata updates, etc.
        """
        ...

    async def generate_id(self) -> str:
        """Generate a unique assembly identifier.

        This operation is non-deterministic and must be called from
        workflow activities, not directly from workflow code.

        Returns:
            Unique assembly ID string

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
