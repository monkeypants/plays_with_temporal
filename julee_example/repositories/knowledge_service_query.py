"""
KnowledgeServiceQuery repository interface defined as Protocol for the
Capture, Extract, Assemble, Publish workflow.

This module defines the knowledge service query repository protocol.
The repository works with KnowledgeServiceQuery domain objects for
storing and retrieving query configurations that define how to extract
data using external knowledge services.

All repository operations follow the same principles as the sample
repositories:
- Protocol-based design for Clean Architecture
- Type safety with runtime validation
- Idempotent operations
- Proper error handling
- Framework independence

The repository handles the persistence of query definitions including
prompts, assistant prompts, metadata, and service configurations
that are used during the assembly process.
"""

from typing import Protocol, runtime_checkable, Optional

from julee_example.domain.assembly_specification import KnowledgeServiceQuery


@runtime_checkable
class KnowledgeServiceQueryRepository(Protocol):
    """Handles knowledge service query persistence and retrieval.

    This repository manages the storage and retrieval of
    KnowledgeServiceQuery domain objects within the Capture, Extract,
    Assemble, Publish workflow. These queries define how to extract
    specific data using external knowledge services during assembly.
    """

    async def get(self, query_id: str) -> Optional[KnowledgeServiceQuery]:
        """Retrieve a knowledge service query by ID.

        Args:
            query_id: Unique query identifier

        Returns:
            KnowledgeServiceQuery object if found, None otherwise

        Implementation Notes:
        - Must be idempotent: multiple calls return same result
        - Should handle missing queries gracefully (return None)
        """
        ...

    async def save(self, query: KnowledgeServiceQuery) -> None:
        """Store or update a knowledge service query.

        Args:
            query: KnowledgeServiceQuery object to store

        Implementation Notes:
        - Must be idempotent: saving same query multiple times is safe
        - Should update the updated_at timestamp
        - Creates new query if it doesn't exist, updates if it does
        """
        ...

    async def generate_id(self) -> str:
        """Generate a unique query identifier.

        Returns:
            Unique string identifier for a new query

        Implementation Notes:
        - Must generate globally unique identifiers
        - Should be deterministic within the same process for testing
        - Format should be consistent across implementations
        """
        ...
