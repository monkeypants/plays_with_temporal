"""
Memory implementation of KnowledgeService for testing and development.

This module provides an in-memory implementation of the KnowledgeService
protocol that stores file registrations in a dictionary and returns
configurable canned query responses. Useful for testing and development
scenarios where external service dependencies should be avoided.
"""

import logging
from typing import Optional, List, Dict, Deque, Any
from datetime import datetime, timezone
from collections import deque

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


class MemoryKnowledgeService(KnowledgeService):
    """
    In-memory implementation of the KnowledgeService protocol.

    This class stores file registrations in memory using a dictionary
    keyed by knowledge_service_file_id. Query results are returned from
    a configurable queue of canned responses.

    Useful for testing and development scenarios where you want to avoid
    external service dependencies while still exercising the full
    knowledge service workflow.
    """

    def __init__(
        self,
        config: KnowledgeServiceConfig,
    ) -> None:
        """Initialize memory knowledge service with configuration.

        Args:
            config: KnowledgeServiceConfig domain object containing metadata
                   and service configuration
        """
        logger.debug(
            "Initializing MemoryKnowledgeService",
            extra={
                "knowledge_service_id": config.knowledge_service_id,
                "service_name": config.name,
            },
        )

        self.config = config

        # Storage for file registrations, keyed by knowledge_service_file_id
        self._registered_files: Dict[str, FileRegistrationResult] = {}

        # Queue of canned query results to return
        self._canned_query_results: Deque[QueryResult] = deque()

    def add_canned_query_result(self, query_result: QueryResult) -> None:
        """Add a canned query result to be returned by execute_query.

        Args:
            query_result: QueryResult to return from future execute_query
                         calls
        """
        logger.debug(
            "Adding canned query result",
            extra={
                "knowledge_service_id": self.config.knowledge_service_id,
                "query_id": query_result.query_id,
            },
        )
        self._canned_query_results.append(query_result)

    def add_canned_query_results(
        self, query_results: List[QueryResult]
    ) -> None:
        """Add multiple canned query results to be returned by execute_query.

        Args:
            query_results: List of QueryResult objects to return from future
                          execute_query calls
        """
        logger.debug(
            "Adding multiple canned query results",
            extra={
                "knowledge_service_id": self.config.knowledge_service_id,
                "count": len(query_results),
            },
        )
        self._canned_query_results.extend(query_results)

    def clear_canned_query_results(self) -> None:
        """Clear all canned query results."""
        logger.debug(
            "Clearing canned query results",
            extra={
                "knowledge_service_id": self.config.knowledge_service_id,
                "count": len(self._canned_query_results),
            },
        )
        self._canned_query_results.clear()

    def get_registered_file(
        self, knowledge_service_file_id: str
    ) -> Optional[FileRegistrationResult]:
        """Get a registered file by its knowledge service file ID.

        Args:
            knowledge_service_file_id: The file ID assigned by this service

        Returns:
            FileRegistrationResult if found, None otherwise
        """
        return self._registered_files.get(knowledge_service_file_id)

    def get_all_registered_files(self) -> Dict[str, FileRegistrationResult]:
        """Get all registered files.

        Returns:
            Dictionary mapping knowledge_service_file_id to
            FileRegistrationResult
        """
        return self._registered_files.copy()

    async def register_file(
        self, config: KnowledgeServiceConfig, document: Document
    ) -> FileRegistrationResult:
        """Register a document file by storing metadata in memory.

        Args:
            config: KnowledgeServiceConfig for this operation
            document: Document domain object to register

        Returns:
            FileRegistrationResult with memory-specific details
        """
        logger.debug(
            "Registering file with memory service",
            extra={
                "knowledge_service_id": config.knowledge_service_id,
                "document_id": document.document_id,
            },
        )

        # Check if already registered
        for existing_result in self._registered_files.values():
            if existing_result.document_id == document.document_id:
                logger.debug(
                    "Document already registered, returning existing result",
                    extra={
                        "knowledge_service_id": (config.knowledge_service_id),
                        "document_id": document.document_id,
                        "knowledge_service_file_id": (
                            existing_result.knowledge_service_file_id
                        ),
                    },
                )
                return existing_result

        # Generate a unique file ID for this service
        timestamp = int(datetime.now().timestamp())
        memory_file_id = f"memory_{document.document_id}_{timestamp}"

        # Create registration result
        result = FileRegistrationResult(
            document_id=document.document_id,
            knowledge_service_file_id=memory_file_id,
            registration_metadata={
                "service": "memory",
                "registered_via": "in_memory_storage",
                "timestamp": timestamp,
                "knowledge_service_id": config.knowledge_service_id,
                "filename": document.original_filename,
                "content_type": document.content_type,
                "size_bytes": document.size_bytes,
            },
            created_at=datetime.now(timezone.utc),
        )

        # Store in memory dictionary keyed by knowledge_service_file_id
        self._registered_files[memory_file_id] = result

        logger.info(
            "File registered with MemoryKnowledgeService",
            extra={
                "knowledge_service_id": config.knowledge_service_id,
                "document_id": document.document_id,
                "knowledge_service_file_id": memory_file_id,
                "total_registered": len(self._registered_files),
            },
        )

        return result

    async def execute_query(
        self,
        config: KnowledgeServiceConfig,
        query_text: str,
        service_file_ids: Optional[List[str]] = None,
        query_metadata: Optional[Dict[str, Any]] = None,
        assistant_prompt: Optional[str] = None,
    ) -> QueryResult:
        """Execute a query by returning a canned response.

        Args:
            config: KnowledgeServiceConfig for this operation
            query_text: The query to execute
            service_file_ids: Optional list of service file IDs for query
            query_metadata: Optional service-specific metadata (ignored in
                           memory implementation)
            assistant_prompt: Optional assistant message content (ignored in
                             memory implementation)

        Returns:
            QueryResult from the queue of canned responses

        Raises:
            ValueError: If no canned query results are available
        """
        logger.debug(
            "Executing query with MemoryKnowledgeService",
            extra={
                "knowledge_service_id": config.knowledge_service_id,
                "query_text": query_text,
                "document_count": (
                    len(service_file_ids) if service_file_ids else 0
                ),
            },
        )

        # Check if we have canned results available
        if not self._canned_query_results:
            error_msg = (
                "No canned query results available. Use "
                "add_canned_query_result() to configure responses."
            )
            logger.error(
                error_msg,
                extra={
                    "knowledge_service_id": config.knowledge_service_id,
                    "query_text": query_text,
                },
            )
            raise ValueError(error_msg)

        # Pop and return the next canned result
        result = self._canned_query_results.popleft()

        # Update the result to reflect the actual query parameters
        updated_result = QueryResult(
            query_id=result.query_id,
            query_text=query_text,  # Use actual query text
            result_data={
                **result.result_data,
                "queried_documents": service_file_ids or [],
                "service": "memory",
                "knowledge_service_id": config.knowledge_service_id,
            },
            execution_time_ms=result.execution_time_ms,
            created_at=datetime.now(timezone.utc),
        )

        logger.info(
            "Query executed with MemoryKnowledgeService",
            extra={
                "knowledge_service_id": config.knowledge_service_id,
                "query_id": updated_result.query_id,
                "execution_time_ms": updated_result.execution_time_ms,
                "remaining_canned_results": len(self._canned_query_results),
            },
        )

        return updated_result
