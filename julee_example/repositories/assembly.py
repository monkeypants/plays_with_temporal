"""
Assembly repository interface defined as Protocol for the Capture, Extract,
Assemble, Publish workflow.

This module defines the core assembly storage and retrieval repository
protocol. The repository works with Assembly domain objects that contain
AssemblyIteration entities within the aggregate boundary.

All repository operations follow the same principles as the sample
repositories:

- **Idempotency**: All methods are designed to be idempotent and safe for
  retry. Multiple calls with the same parameters will produce the same
  result without unintended side effects.

- **Workflow Safety**: All operations are safe to call from deterministic
  workflow contexts. Non-deterministic operations (like ID generation) are
  explicitly delegated to activities.

- **Domain Objects**: Methods accept and return domain objects or primitives,
  never framework-specific types. Assembly aggregate contains all its
  iterations.

- **Aggregate Boundary**: Repository handles the complete Assembly aggregate
  including all contained AssemblyIteration entities. No separate iteration
  repository is needed.

In Temporal workflow contexts, these protocols are implemented by workflow
stubs that delegate to activities for durability and proper error handling.
"""

from typing import Protocol, Optional, runtime_checkable
from julee_example.domain import Assembly


@runtime_checkable
class AssemblyRepository(Protocol):
    """Handles assembly aggregate storage and retrieval operations.

    This repository manages Assembly aggregates within the Capture, Extract,
    Assemble, Publish workflow. Each Assembly contains its complete iteration
    history as entities within the aggregate boundary.
    """

    async def get(self, assembly_id: str) -> Optional[Assembly]:
        """Retrieve an assembly with all its iterations.

        Args:
            assembly_id: Unique assembly identifier

        Returns:
            Assembly aggregate with all iterations if found, None otherwise

        Implementation Notes:
        - Must be idempotent: multiple calls return same result
        - Should handle missing assemblies gracefully (return None)
        - Must load complete aggregate including all AssemblyIteration entities
        - Iterations should be ordered by iteration_id
        """
        ...

    async def add_iteration(self, assembly_id: str, document_id: str) -> Assembly:
        """Add a new iteration to an assembly and persist it immediately.

        Args:
            assembly_id: ID of the assembly to add iteration to
            document_id: ID of the document produced by this iteration

        Returns:
            Updated Assembly aggregate with the new iteration included

        Implementation Notes:
        - Idempotent: only creates iteration if document_id is not already
          used in an iteration
        - If document_id is same as another iteration, returns assembly
          unchanged
        - If different (or no iterations exist), creates new iteration
        - Automatically assigns sequential iteration_id (1, 2, 3...)
        - Persists the iteration immediately, not on assembly save
        - Updates assembly's updated_at timestamp
        - Returns complete assembly with new iteration in iterations list
        """
        ...

    async def save(self, assembly: Assembly) -> None:
        """Save assembly metadata (status, updated_at, etc.).

        Args:
            assembly: Assembly aggregate

        Implementation Notes:
        - Must be idempotent: saving same assembly state is safe
        - Should update the updated_at timestamp
        - Saves only Assembly root entity fields (not iterations)
        - Iterations are persisted via add_iteration(), not here
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
