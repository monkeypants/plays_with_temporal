"""
Anthropic implementation of KnowledgeService for the Capture, Extract,
Assemble, Publish workflow.

This module provides the Anthropic-specific implementation of the
KnowledgeService protocol. It handles interactions with Anthropic's API
for document registration and query execution.

Dependencies:
    - anthropic: Install with `pip install anthropic`
    - ANTHROPIC_API_KEY environment variable must be set
"""

import os
import logging
import time
import uuid
from typing import Optional, List
from datetime import datetime, timezone

from anthropic import AsyncAnthropic

from julee_example.domain import KnowledgeServiceConfig
from julee_example.repositories import DocumentRepository
from ..knowledge_service import (
    KnowledgeService,
    QueryResult,
    FileRegistrationResult,
)

logger = logging.getLogger(__name__)


class AnthropicKnowledgeService(KnowledgeService):
    """
    Anthropic implementation of the KnowledgeService protocol.

    This class handles interactions with Anthropic's API for document
    registration and query execution. It implements the KnowledgeService
    protocol with Anthropic-specific logic.
    """

    def __init__(
        self,
        config: KnowledgeServiceConfig,
        document_repo: DocumentRepository,
    ) -> None:
        """Initialize Anthropic knowledge service with configuration.

        Args:
            config: KnowledgeServiceConfig domain object containing metadata
                   and service configuration
            document_repo: Repository for accessing document data
        """
        logger.debug(
            "Initializing AnthropicKnowledgeService",
            extra={
                "knowledge_service_id": config.knowledge_service_id,
                "service_name": config.name,
            },
        )

        self.config = config
        self.document_repo = document_repo

        # Initialize Anthropic client
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable is required for "
                "AnthropicKnowledgeService"
            )

        self.client = AsyncAnthropic(
            api_key=api_key,
            default_headers={"anthropic-beta": "files-api-2025-04-14"},
        )

    async def register_file(self, document_id: str) -> FileRegistrationResult:
        """Register a document file with Anthropic.

        Args:
            document_id: ID of the document to register

        Returns:
            FileRegistrationResult with Anthropic-specific details
        """
        logger.debug(
            "Registering file with Anthropic",
            extra={
                "knowledge_service_id": self.config.knowledge_service_id,
                "document_id": document_id,
            },
        )

        try:
            # Get the document from the repository
            document = await self.document_repo.get(document_id)
            if not document:
                raise ValueError(f"Document {document_id} not found")

            # Reset stream position and pass directly to Anthropic
            document.content.seek(0)

            # Upload file using Anthropic beta Files API
            # Use tuple format: (filename, file_content, media_type)
            file_response = await self.client.beta.files.upload(
                file=(
                    document.original_filename,
                    document.content.stream,
                    document.content_type,
                )
            )

            anthropic_file_id = file_response.id

            result = FileRegistrationResult(
                document_id=document_id,
                knowledge_service_file_id=anthropic_file_id,
                registration_metadata={
                    "service": "anthropic",
                    "registered_via": "beta_files_api",
                    "filename": document.original_filename,
                    "content_type": document.content_type,
                    "size_bytes": document.size_bytes,
                    "content_multihash": document.content_multihash,
                    "anthropic_file_id": anthropic_file_id,
                },
                created_at=datetime.now(timezone.utc),
            )

            logger.info(
                "File registered with Anthropic beta Files API",
                extra={
                    "knowledge_service_id": self.config.knowledge_service_id,
                    "document_id": document_id,
                    "anthropic_file_id": anthropic_file_id,
                    "filename": document.original_filename,
                    "size_bytes": document.size_bytes,
                },
            )

            return result

        except Exception as e:
            logger.error(
                "Failed to register file with Anthropic",
                extra={
                    "knowledge_service_id": self.config.knowledge_service_id,
                    "document_id": document_id,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

    async def execute_query(
        self,
        query_text: str,
        service_file_ids: Optional[List[str]] = None,
    ) -> QueryResult:
        """Execute a query against Anthropic.

        Args:
            query_text: The query to execute
            service_file_ids: Optional list of Anthropic file IDs to provide
                             as context for the query

        Returns:
            QueryResult with Anthropic query results
        """
        logger.debug(
            "Executing query with Anthropic",
            extra={
                "knowledge_service_id": self.config.knowledge_service_id,
                "query_text": query_text,
                "document_count": (
                    len(service_file_ids) if service_file_ids else 0
                ),
            },
        )

        start_time = time.time()
        query_id = f"anthropic_{uuid.uuid4().hex[:12]}"

        try:
            # Prepare the message content with file attachments if provided
            content_parts = []

            # Add file attachments if service_file_ids are provided
            if service_file_ids:
                for file_id in service_file_ids:
                    content_parts.append(
                        {
                            "type": "document",
                            "source": {"type": "file", "file_id": file_id},
                        }
                    )

            # Add the text query
            content_parts.append({"type": "text", "text": query_text})

            # Execute the query using Anthropic's Messages API
            response = await self.client.messages.create(
                model="claude-sonnet-4-20250514",  # TODO: make configurable.
                max_tokens=4000,
                messages=[{"role": "user", "content": content_parts}],
            )

            # Calculate execution time
            execution_time_ms = int((time.time() - start_time) * 1000)

            # Extract response content safely
            response_text = ""
            for content_block in response.content:
                try:
                    # Try to access text attribute if it exists
                    text_content = getattr(content_block, "text", None)
                    if text_content:
                        response_text += str(text_content)
                except AttributeError:
                    # Skip content blocks that don't have text
                    continue

            # Structure the result
            result = QueryResult(
                query_id=query_id,
                query_text=query_text,
                result_data={
                    "response": response_text,
                    "model": "claude-sonnet-4-20250514",
                    "service": "anthropic",
                    "sources": service_file_ids or [],
                    "usage": {
                        "input_tokens": response.usage.input_tokens,
                        "output_tokens": response.usage.output_tokens,
                    },
                    "stop_reason": response.stop_reason,
                },
                execution_time_ms=execution_time_ms,
                created_at=datetime.now(timezone.utc),
            )

            logger.info(
                "Query executed with Anthropic successfully",
                extra={
                    "knowledge_service_id": self.config.knowledge_service_id,
                    "query_id": query_id,
                    "execution_time_ms": execution_time_ms,
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "file_count": (
                        len(service_file_ids) if service_file_ids else 0
                    ),
                },
            )

            return result

        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            logger.error(
                "Failed to execute query with Anthropic",
                extra={
                    "knowledge_service_id": self.config.knowledge_service_id,
                    "query_id": query_id,
                    "query_text": query_text,
                    "execution_time_ms": execution_time_ms,
                    "file_count": (
                        len(service_file_ids) if service_file_ids else 0
                    ),
                    "error": str(e),
                },
                exc_info=True,
            )
            raise
