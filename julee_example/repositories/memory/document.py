"""
Memory implementation of DocumentRepository.

This module provides an in-memory implementation of the DocumentRepository
protocol that follows the Clean Architecture patterns defined in the
Fun-Police Framework. It handles document storage with content and metadata
in memory dictionaries, ensuring idempotency and proper error handling.

The implementation uses Python dictionaries to store document data, making it
ideal for testing scenarios where external dependencies should be avoided.
All operations are still async to maintain interface compatibility.
"""

import hashlib
import io
import logging
from typing import Optional, Dict, Any

from julee_example.domain import Document, ContentStream
from julee_example.repositories.document import DocumentRepository
from .base import MemoryRepositoryMixin

logger = logging.getLogger(__name__)


class MemoryDocumentRepository(
    DocumentRepository, MemoryRepositoryMixin[Document]
):
    """
    Memory implementation of DocumentRepository using Python dictionaries.

    This implementation stores document metadata and content in memory:
    - Documents: Dictionary keyed by document_id containing Document objects

    This provides a lightweight, dependency-free option for testing while
    maintaining the same interface as other implementations.
    """

    def __init__(self) -> None:
        """Initialize repository with empty in-memory storage."""
        self.logger = logger
        self.entity_name = "Document"
        self.storage_dict: Dict[str, Document] = {}

        logger.debug("Initializing MemoryDocumentRepository")

    async def get(self, document_id: str) -> Optional[Document]:
        """Retrieve a document with metadata and content.

        Args:
            document_id: Unique document identifier

        Returns:
            Document object if found, None otherwise
        """
        return self.get_entity(document_id)

    async def save(self, document: Document) -> None:
        """Save a document with its content and metadata.

        If the document has content_string, it will be converted to a
        ContentStream and the content hash will be calculated automatically.

        Args:
            document: Document object to save

        Raises:
            ValueError: If document has no content or content_string
        """
        # Fail fast if both are provided or neither are provided
        has_content = document.content is not None
        has_content_string = document.content_string is not None

        if has_content and has_content_string:
            raise ValueError(
                f"Document {document.document_id} has both content and "
                "content_string. Provide only one."
            )
        elif not has_content and not has_content_string:
            raise ValueError(
                f"Document {document.document_id} has no content or "
                "content_string. Provide one."
            )

        # Handle content_string conversion (only if no content provided)
        if has_content_string:
            # Convert content_string to ContentStream
            assert document.content_string is not None  # For MyPy
            content_bytes = document.content_string.encode("utf-8")
            content_stream = ContentStream(io.BytesIO(content_bytes))

            # Calculate content hash
            content_hash = hashlib.sha256(content_bytes).hexdigest()

            # Create new document with ContentStream and calculated hash
            document = document.model_copy(
                update={
                    "content": content_stream,
                    "content_multihash": content_hash,
                    "size_bytes": len(content_bytes),
                }
            )

            self.logger.debug(
                "Converted content_string to ContentStream for document save",
                extra={
                    "document_id": document.document_id,
                    "content_hash": content_hash,
                    "content_length": len(content_bytes),
                },
            )

        self.save_entity(document, "document_id")

    async def generate_id(self) -> str:
        """Generate a unique document identifier.

        Returns:
            Unique document ID string
        """
        return self.generate_entity_id("doc")

    def _add_entity_specific_log_data(
        self, entity: Document, log_data: Dict[str, Any]
    ) -> None:
        """Add document-specific data to log entries."""
        super()._add_entity_specific_log_data(entity, log_data)
        log_data["content_length"] = entity.size_bytes
