"""
Temporal activity wrapper classes for the julee_example knowledge service
domain.

This module contains the @temporal_activity_registration decorated class
that wraps knowledge service operations as Temporal activities. This class is
imported by the worker to register activities with Temporal.

The class follows the naming pattern documented in systemPatterns.org:
- Activity names: {domain}.{service_name}.{method}
- The knowledge service gets its own activity prefix
"""

import io
import logging
from typing_extensions import override

from util.temporal.decorators import temporal_activity_registration
from julee_example.services.knowledge_service.factory import (
    ConfigurableKnowledgeService,
)
from julee_example.domain.repositories.document import DocumentRepository
from julee_example.domain.models.knowledge_service_config import (
    KnowledgeServiceConfig,
)
from julee_example.domain.models.document import Document
from ..knowledge_service import FileRegistrationResult

# Import activity name bases from shared module
from julee_example.services.temporal.activity_names import (
    KNOWLEDGE_SERVICE_ACTIVITY_BASE,
)


@temporal_activity_registration(KNOWLEDGE_SERVICE_ACTIVITY_BASE)
class TemporalKnowledgeService(ConfigurableKnowledgeService):
    """Temporal activity wrapper for KnowledgeService operations.

    This class handles the issue where ContentStream objects don't survive
    Temporal's serialization by re-fetching document content from the
    injected DocumentRepository before performing operations that require it.
    """

    def __init__(self, document_repo: DocumentRepository) -> None:
        super().__init__()
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.document_repo: DocumentRepository = document_repo

    @override
    async def register_file(
        self, config: KnowledgeServiceConfig, document: Document
    ) -> FileRegistrationResult:
        """Register a document file, re-fetching content if needed.

        This method checks if the document's ContentStream is None (due to
        Temporal serialization) and re-fetches content from MinIO if needed.
        """
        if document.content is None:
            self.logger.info(
                f"Document {document.document_id} has no content stream, "
                f"re-fetching from repo"
            )
            # Re-fetch the document with proper content
            fresh_document = await self.document_repo.get(
                document.document_id
            )
            if fresh_document and fresh_document.content:
                # Read the MinIO stream content into a seekable buffer
                # This prevents the stream from being consumed during upload
                content_data = fresh_document.content.read()
                seekable_stream = io.BytesIO(content_data)
                fresh_document.content._stream = seekable_stream
                document = fresh_document
            else:
                raise ValueError(
                    f"Could not re-fetch document {document.document_id} "
                    f"from repository"
                )

        # Now call the parent method with the document that has proper content
        return await super().register_file(config, document)


# Export the temporal service class for use in worker.py
__all__ = [
    "TemporalKnowledgeService",
    "KNOWLEDGE_SERVICE_ACTIVITY_BASE",
]
