"""
Anthropic implementation of KnowledgeService for the Capture, Extract,
Assemble, Publish workflow.

This module provides the Anthropic-specific implementation of the
KnowledgeService protocol. It handles interactions with Anthropic's API
for document registration and query execution.

Requirements:
    - ANTHROPIC_API_KEY environment variable must be set
"""

import os
import logging
import time
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from anthropic import AsyncAnthropic

from julee_example.domain.models.knowledge_service_config import (
    KnowledgeServiceConfig,
)
from julee_example.domain.models.document import Document
from ..knowledge_service import (
    KnowledgeService,
    QueryResult,
    FileRegistrationResult,
)

logger = logging.getLogger(__name__)

# Default configuration constants
DEFAULT_MODEL = "claude-sonnet-4-20250514"
DEFAULT_MAX_TOKENS = 4000


class AnthropicKnowledgeService(KnowledgeService):
    """
    Anthropic implementation of the KnowledgeService protocol.

    This class handles interactions with Anthropic's API for document
    registration and query execution. It implements the KnowledgeService
    protocol with Anthropic-specific logic.
    """

    def __init__(self) -> None:
        """Initialize Anthropic knowledge service without configuration.

        Configuration will be provided per method call to maintain
        stateless operation compatible with Temporal workflows.
        """
        # No initialization needed - everything happens per method call
        pass

    def _get_client(self, config: KnowledgeServiceConfig) -> AsyncAnthropic:
        """Get an initialized Anthropic client.

        Args:
            config: KnowledgeServiceConfig (for future extensibility)

        Returns:
            Configured AsyncAnthropic client instance

        Raises:
            ValueError: If ANTHROPIC_API_KEY environment variable is not set
        """
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable is required for "
                "AnthropicKnowledgeService"
            )

        return AsyncAnthropic(
            api_key=api_key,
            default_headers={"anthropic-beta": "files-api-2025-04-14"},
        )

    async def register_file(
        self, config: KnowledgeServiceConfig, document: Document
    ) -> FileRegistrationResult:
        """Register a document file with Anthropic.

        Args:
            config: KnowledgeServiceConfig for this operation
            document: Document domain object to register

        Returns:
            FileRegistrationResult with Anthropic-specific details
        """
        logger.debug(
            "Registering file with Anthropic",
            extra={
                "knowledge_service_id": config.knowledge_service_id,
                "document_id": document.document_id,
            },
        )

        try:
            # Get Anthropic client for this operation
            client = self._get_client(config)

            # Ensure content stream is positioned at beginning for upload
            if document.content:
                document.content.seek(0)

            # Upload file using Anthropic beta Files API
            # Use tuple format: (filename, file_stream, media_type)
            if not document.content:
                raise ValueError(
                    "Document content stream is required for upload"
                )

            # Anthropic only supports PDF and plaintext files
            # Convert JSON content type to text/plain for compatibility
            content_type = document.content_type
            if content_type == "application/json":
                content_type = "text/plain"

            file_response = await client.beta.files.upload(
                file=(
                    document.original_filename,
                    document.content.stream,  # type: ignore[arg-type]
                    content_type,
                )
            )

            anthropic_file_id = file_response.id

            result = FileRegistrationResult(
                document_id=document.document_id,
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
                    "knowledge_service_id": config.knowledge_service_id,
                    "document_id": document.document_id,
                    "anthropic_file_id": anthropic_file_id,
                    "original_filename": document.original_filename,
                    "size_bytes": document.size_bytes,
                },
            )

            return result

        except Exception as e:
            logger.error(
                "Failed to register file with Anthropic",
                extra={
                    "knowledge_service_id": config.knowledge_service_id,
                    "document_id": document.document_id,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

    async def execute_query(
        self,
        config: KnowledgeServiceConfig,
        query_text: str,
        service_file_ids: Optional[List[str]] = None,
        query_metadata: Optional[Dict[str, Any]] = None,
        assistant_prompt: Optional[str] = None,
    ) -> QueryResult:
        """Execute a query against Anthropic.

        Args:
            config: KnowledgeServiceConfig for this operation
            query_text: The query to execute
            service_file_ids: Optional list of Anthropic file IDs to provide
                             as context for the query
            query_metadata: Optional Anthropic-specific configuration such as
                           model, temperature, max_tokens, etc.
            assistant_prompt: Optional assistant message content to constrain
                             or prime the model's response

        Returns:
            QueryResult with Anthropic query results
        """
        logger.debug(
            "Executing query with Anthropic",
            extra={
                "knowledge_service_id": config.knowledge_service_id,
                "query_text": query_text,
                "document_count": (
                    len(service_file_ids) if service_file_ids else 0
                ),
                "file_count": (
                    len(service_file_ids) if service_file_ids else 0
                ),
            },
        )

        start_time = time.time()
        query_id = f"anthropic_{uuid.uuid4().hex[:12]}"

        # Extract configuration from query_metadata
        metadata = query_metadata or {}
        model = metadata.get("model", DEFAULT_MODEL)
        max_tokens = metadata.get("max_tokens", DEFAULT_MAX_TOKENS)
        temperature = metadata.get("temperature")

        try:
            # Get Anthropic client for this operation
            client = self._get_client(config)

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

            # Prepare messages for the API
            messages = [{"role": "user", "content": content_parts}]

            # Add assistant message if provided to constrain response
            if assistant_prompt:
                messages.append(
                    {"role": "assistant", "content": assistant_prompt}
                )

            create_params = {
                "model": model,
                "max_tokens": max_tokens,
                "messages": messages,
            }

            # Add temperature if specified
            if temperature is not None:
                create_params["temperature"] = temperature

            response = await client.messages.create(**create_params)

            # Calculate execution time
            execution_time_ms = int((time.time() - start_time) * 1000)

            # Validate response has exactly one content block of type 'text'
            if len(response.content) != 1:
                raise ValueError(
                    f"Expected exactly 1 content block, got "
                    f"{len(response.content)}"
                )

            content_block = response.content[0]

            if (
                not hasattr(content_block, "type")
                or content_block.type != "text"
            ):
                block_type = getattr(content_block, "type", "unknown")
                raise ValueError(
                    f"Expected content block type 'text', got '{block_type}'"
                )

            if not hasattr(content_block, "text"):
                raise ValueError(
                    "Text content block missing 'text' attribute"
                )

            response_text = str(content_block.text)

            logger.debug(
                "Single text content block validated and extracted",
                extra={
                    "knowledge_service_id": config.knowledge_service_id,
                    "query_id": query_id,
                    "response_length": len(response_text),
                },
            )

            # Structure the result with single text content
            result_data = {
                "response": response_text,
                "model": model,
                "service": "anthropic",
                "sources": service_file_ids or [],
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                },
                "stop_reason": response.stop_reason,
            }

            result = QueryResult(
                query_id=query_id,
                query_text=query_text,
                result_data=result_data,
                execution_time_ms=execution_time_ms,
                created_at=datetime.now(timezone.utc),
            )

            logger.info(
                "Query executed with Anthropic successfully",
                extra={
                    "knowledge_service_id": config.knowledge_service_id,
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
                    "knowledge_service_id": config.knowledge_service_id,
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
