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

import logging
from typing import Optional, Dict, Any

from julee_example.domain import Document
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

        Args:
            document: Document object to save
        """
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
        log_data["content_length"] = (
            len(entity.content.read()) if entity.content else 0
        )
