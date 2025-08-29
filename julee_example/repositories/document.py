"""
Document repository interface defined as Protocol for the Capture, Extract,
Assemble, Publish workflow.

This module defines the core document storage and retrieval repository
protocol.
All repository operations follow the same principles as the sample
repositories:

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

from typing import Protocol, Optional, runtime_checkable
from julee_example.domain import Document, DocumentMetadata, DocumentStatus


@runtime_checkable
class DocumentRepository(Protocol):
    """Handles document storage and retrieval operations.

    This repository manages the core document storage and metadata
    operations within the Capture, Extract, Assemble, Publish workflow.
    """

    async def retrieve_document(self, document_id: str) -> Optional[Document]:
        """Retrieve a complete document with content and metadata.

        Args:
            document_id: Unique document identifier

        Returns:
            Document object if found, None otherwise

        Implementation Notes:
        - Must be idempotent: multiple calls return same result
        - Should handle missing documents gracefully (return None)
        - Returns complete Document object with both content and metadata
        - Primary method for document retrieval in CEAP workflow
        """
        ...

    async def retrieve_content(self, document_id: str) -> Optional[bytes]:
        """Retrieve the raw content of a document.

        Args:
            document_id: Unique document identifier

        Returns:
            Raw document content as bytes, None if not found

        Implementation Notes:
        - Must be idempotent: multiple calls return same result
        - Should handle missing documents gracefully (return None)
        - May retrieve from object storage (Minio, S3, etc.)
        - Critical for extraction phase where raw content is needed
        - Consider using retrieve_document() for complete object
        """
        ...

    async def retrieve_metadata(
        self, document_id: str
    ) -> Optional[DocumentMetadata]:
        """Retrieve metadata for a document.

        Args:
            document_id: Unique document identifier

        Returns:
            DocumentMetadata object if found, None otherwise

        Implementation Notes:
        - Must be idempotent: multiple calls return same result
        - Should include status, knowledge service ID, assembly types
        - Used throughout workflow to track document state
        - Essential for workflow decision making
        """
        ...

    async def update_document(self, document: Document) -> None:
        """Update a complete document with content and metadata.

        Args:
            document: Updated Document object

        Implementation Notes:
        - Must be idempotent: updating with same document is safe
        - Should update the updated_at timestamp in metadata
        - Updates both content and metadata atomically
        - Primary method for document updates in CEAP workflow
        """
        ...

    async def update_metadata(
        self, document_id: str, metadata: DocumentMetadata
    ) -> None:
        """Update metadata for a document.

        Args:
            document_id: Unique document identifier
            metadata: Updated DocumentMetadata object

        Implementation Notes:
        - Must be idempotent: updating with same metadata is safe
        - Should update the updated_at timestamp
        - Critical for tracking document progress through CEAP pipeline
        - Used after each major workflow stage
        - Consider using update_document() for complete object updates
        """
        ...

    async def store_document(self, document: Document) -> str:
        """Store a new document with its content and metadata.

        Args:
            document: Document object to store

        Returns:
            Document ID of the stored document

        Implementation Notes:
        - Must be idempotent: storing same document returns same ID
        - Should generate unique document ID if not provided in metadata
        - Must store both content and metadata atomically
        - Entry point for the "Capture" phase of Capture, Extract, Assemble,
          Publish
        - Primary method for document storage in CEAP workflow
        """
        ...

    async def store_document_parts(
        self, content: bytes, metadata: DocumentMetadata
    ) -> str:
        """Store a new document with its metadata (legacy method).

        Args:
            content: Raw document content
            metadata: Document metadata

        Returns:
            Document ID of the stored document

        Implementation Notes:
        - Must be idempotent: storing same content returns same ID
        - Should generate unique document ID if not provided
        - Must store both content and metadata atomically
        - Consider using store_document() with Document object instead
        """
        ...

    async def update_status(
        self,
        document_id: str,
        status: DocumentStatus,
        knowledge_service_id: Optional[str] = None,
    ) -> None:
        """Update document status and optionally knowledge service ID.

        Args:
            document_id: Unique document identifier
            status: New document status
            knowledge_service_id: ID from knowledge service (e.g., RagFlow)

        Implementation Notes:
        - Must be idempotent: updating to same status is safe
        - Should update the updated_at timestamp
        - Knowledge service ID typically set during REGISTERED status
        - Used to track progress through each Capture, Extract, Assemble,
          Publish phase
        """
        ...
