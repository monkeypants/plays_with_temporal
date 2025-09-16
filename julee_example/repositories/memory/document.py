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
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict

from julee_example.domain import Document
from julee_example.repositories.document import DocumentRepository

logger = logging.getLogger(__name__)


class MemoryDocumentRepository(DocumentRepository):
    """
    Memory implementation of DocumentRepository using Python dictionaries.

    This implementation stores document metadata and content in memory:
    - Documents: Dictionary keyed by document_id containing Document objects

    This provides a lightweight, dependency-free option for testing while
    maintaining the same interface as other implementations.
    """

    def __init__(self) -> None:
        """Initialize repository with empty in-memory storage."""
        logger.debug("Initializing MemoryDocumentRepository")

        # Storage dictionary
        self._documents: Dict[str, Document] = {}

    async def get(self, document_id: str) -> Optional[Document]:
        """Retrieve a document with metadata and content.

        Args:
            document_id: Unique document identifier

        Returns:
            Document object if found, None otherwise
        """
        logger.debug(
            "MemoryDocumentRepository: Attempting to retrieve document",
            extra={"document_id": document_id},
        )

        document = self._documents.get(document_id)
        if document is None:
            logger.debug(
                "MemoryDocumentRepository: Document not found",
                extra={"document_id": document_id},
            )
            return None

        logger.info(
            "MemoryDocumentRepository: Document retrieved successfully",
            extra={
                "document_id": document_id,
                "content_length": (
                    len(document.content.read()) if document.content else 0
                ),
            },
        )

        return document

    async def save(self, document: Document) -> None:
        """Save a document with its content and metadata.

        Args:
            document: Document object to save
        """
        logger.debug(
            "MemoryDocumentRepository: Saving document",
            extra={"document_id": document.document_id},
        )

        # Ensure timestamps are set
        now = datetime.now(timezone.utc)
        if document.created_at is None:
            document.created_at = now
        document.updated_at = now

        # Store the document (idempotent - will overwrite if exists)
        self._documents[document.document_id] = document

        logger.info(
            "MemoryDocumentRepository: Document saved successfully",
            extra={
                "document_id": document.document_id,
                "content_length": (
                    len(document.content.read()) if document.content else 0
                ),
            },
        )

    async def generate_id(self) -> str:
        """Generate a unique document identifier.

        Returns:
            Unique document ID string
        """
        document_id = f"doc-{uuid.uuid4()}"

        logger.debug(
            "MemoryDocumentRepository: Generated document ID",
            extra={"document_id": document_id},
        )

        return document_id
