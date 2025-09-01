"""
Document repository interface defined as Protocol for the Capture, Extract,
Assemble, Publish workflow.

This module defines the core document storage and retrieval repository
protocol. The repository works with Document domain objects that use BinaryIO
streams for efficient content handling.

All repository operations follow the same principles as the sample
repositories:

- **Idempotency**: All methods are designed to be idempotent and safe for
  retry. Multiple calls with the same parameters will produce the same
  result without unintended side effects.

- **Workflow Safety**: All operations are safe to call from deterministic
  workflow contexts. Non-deterministic operations (like ID generation) are
  explicitly delegated to activities.

- **Domain Objects**: Methods accept and return domain objects or primitives,
  never framework-specific types. Content streams are handled through the
  BinaryIO interface.

- **Content Streaming**: Repository implementations should support both
  small content (via BytesIO) and large content (via file streams) through
  the unified ContentStream interface wrapping io.IOBase.

In Temporal workflow contexts, these protocols are implemented by workflow
stubs that delegate to activities for durability and proper error handling.
"""

from typing import Protocol, Optional, runtime_checkable
from julee_example.domain import Document


@runtime_checkable
class DocumentRepository(Protocol):
    """Handles document storage and retrieval operations.

    This repository manages the core document storage and metadata
    operations within the Capture, Extract, Assemble, Publish workflow.
    """

    async def get(self, document_id: str) -> Optional[Document]:
        """Retrieve a document with metadata and content.

        Args:
            document_id: Unique document identifier

        Returns:
            Document object if found, None otherwise

        Implementation Notes:
        - Must be idempotent: multiple calls return same result
        - Should handle missing documents gracefully (return None)
        """
        ...

    async def update(self, document: Document) -> None:
        """Update a complete document with content and metadata.

        Args:
            document: Updated Document object

        Implementation Notes:
        - Should update the updated_at timestamp in metadata
        - Must be idempotent (other than the updated_at timestamp in the
          metadata): updating with same document is safe
        - If document.multihash differs it must also update the content
        - Updates both content and metadata atomically
        """
        ...

    async def store(self, document: Document) -> None:
        """Store a new document with its content and metadata.

        Args:
            document: Document object with ContentStream

        Implementation Notes:
        - Must be idempotent
        - Reads content from document.content ContentStream if provided
        - Must store both content stream and metadata atomically
        - Must use document id from generate_id call
        - Entry point for the "Capture" phase of Capture, Extract, Assemble,
          Publish
        """
        ...

    async def generate_id(self) -> str:
        """Generate a unique document identifier.

        This operation is non-deterministic and must be called from
        workflow activities, not directly from workflow code.

        Returns:
            Unique document ID string

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
