"""
AssemblySpecification repository interface defined as Protocol for the
Capture, Extract, Assemble, Publish workflow.

This module defines the core assembly specification storage and retrieval
repository protocol. The repository works with AssemblySpecification domain
objects that define how to assemble documents of specific types.

All repository operations follow the same principles as the sample
repositories:

- **Idempotency**: All methods are designed to be idempotent and safe for
  retry. Multiple calls with the same parameters will produce the same
  result without unintended side effects.

- **Workflow Safety**: All operations are safe to call from deterministic
  workflow contexts. Non-deterministic operations (like ID generation) are
  explicitly delegated to activities.

- **Domain Objects**: Methods accept and return domain objects or primitives,
  never framework-specific types. AssemblySpecification contains its JSON
  schema and knowledge service query configurations.

- **Specification Management**: Repository handles complete
  AssemblySpecification entities including their JSON schemas and knowledge
  service query mappings for document assembly workflows.

In Temporal workflow contexts, these protocols are implemented by workflow
stubs that delegate to activities for durability and proper error handling.
"""

from typing import Protocol, Optional, runtime_checkable
from julee_example.domain import AssemblySpecification


@runtime_checkable
class AssemblySpecificationRepository(Protocol):
    """Handles assembly specification storage and retrieval operations.

    This repository manages AssemblySpecification entities within the Capture,
    Extract, Assemble, Publish workflow. Specifications define how to assemble
    documents of specific types, including JSON schemas and knowledge service
    query configurations.
    """

    async def get(
        self, assembly_specification_id: str
    ) -> Optional[AssemblySpecification]:
        """Retrieve an assembly specification by ID.

        Args:
            assembly_specification_id: Unique specification identifier

        Returns:
            AssemblySpecification if found, None otherwise

        Implementation Notes:
        - Must be idempotent: multiple calls return same result
        - Should handle missing specifications gracefully (return None)
        - Must load complete specification including JSON schema and
          knowledge service queries
        """
        ...

    async def save(
        self, assembly_specification: AssemblySpecification
    ) -> None:
        """Save an assembly specification.

        Args:
            assembly_specification: Complete AssemblySpecification to save

        Implementation Notes:
        - Must be idempotent: saving same specification state is safe
        - Should update the updated_at timestamp
        - Must save complete specification including JSON schema and
          knowledge service query configurations
        - Handles both new specifications and updates to existing ones
        """
        ...

    async def generate_id(self) -> str:
        """Generate a unique assembly specification identifier.

        This operation is non-deterministic and must be called from
        workflow activities, not directly from workflow code.

        Returns:
            Unique assembly specification ID string

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
