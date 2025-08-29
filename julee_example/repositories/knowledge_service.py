"""
Knowledge service repository interface defined as Protocol for the Capture,
Extract, Assemble, Publish workflow.

This module defines the repository protocol for integrating with knowledge
services like RagFlow. All repository operations follow the same principles
as the sample repositories:

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

from typing import Protocol, List, runtime_checkable
from julee_example.domain import DocumentMetadata


@runtime_checkable
class KnowledgeServiceRepository(Protocol):
    """Handles integration with knowledge services like RagFlow.

    This repository abstracts the knowledge service operations needed
    for document processing and extraction preparation.
    """

    async def register_document(
        self, document_id: str, content: bytes, metadata: DocumentMetadata
    ) -> str:
        """Register a document with the knowledge service.

        Args:
            document_id: Internal document identifier
            content: Raw document content
            metadata: Document metadata

        Returns:
            Knowledge service document identifier (e.g., RagFlow document ID)

        Implementation Notes:
        - May be non-deterministic (knowledge service generates ID)
        - Should handle parsing, chunking, semantic indexing
        - May take significant time - suitable for workflow activity
        - Must be idempotent: re-registering same doc returns same ID
        - Maps to "register with knowledge service" workflow step
        """
        ...

    async def determine_assembly_types(
        self, knowledge_service_id: str
    ) -> List[str]:
        """Determine what assembly types are needed for this document.

        Args:
            knowledge_service_id: Document ID in knowledge service

        Returns:
            List of assembly type identifiers

        Implementation Notes:
        - May use LLM queries - non-deterministic but should be idempotent
        - Could analyze document content, metadata, or structure
        - Results inform which templates and extractors to use
        - Critical decision point in CEAP workflow
        - May need special handling for determinism in workflows
        """
        ...

    async def is_document_ready(self, knowledge_service_id: str) -> bool:
        """Check if document processing is complete in knowledge service.

        Args:
            knowledge_service_id: Document ID in knowledge service

        Returns:
            True if document is fully processed and ready for extraction

        Implementation Notes:
        - Must be idempotent: multiple checks return consistent result
        - Knowledge services may have async processing
        - Should be polled until ready before proceeding to extraction
        - Prevents extraction on incomplete document processing
        """
        ...
