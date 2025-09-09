"""
KnowledgeService protocol for external service operations in the Capture,
Extract, Assemble, Publish workflow.

This module defines the KnowledgeService protocol that handles interactions
with external knowledge services, including document registration and query
execution. This protocol is separate from the repository layer which only
handles local metadata persistence.

Concrete implementations of this protocol are provided for different external
services (Anthropic, OpenAI, etc.) and are created via factory functions.
"""

from typing import Protocol, Optional, List, runtime_checkable, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class QueryResult(BaseModel):
    """Result of a knowledge service query execution."""

    query_id: str = Field(
        description="Unique identifier for this query execution"
    )
    query_text: str = Field(
        description="The original query text that was executed"
    )
    result_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="The structured result data from the query",
    )
    execution_time_ms: Optional[int] = Field(
        default=None,
        description="Time taken to execute the query in milliseconds",
    )
    created_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class FileRegistrationResult(BaseModel):
    """Result of registering a file with a knowledge service."""

    document_id: str = Field(
        description="The original document ID from our system"
    )
    knowledge_service_file_id: str = Field(
        description="The file identifier assigned by the knowledge service"
    )
    registration_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata from the registration process",
    )
    created_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


@runtime_checkable
class KnowledgeService(Protocol):
    """
    Protocol for interacting with external knowledge services.

    This protocol defines the interface for external operations that were
    moved out of the repository layer. Implementations handle the specifics
    of different knowledge service APIs (Anthropic, OpenAI, etc.).
    """

    async def register_file(self, document_id: str) -> FileRegistrationResult:
        """Register a document file with the external knowledge service.

        This method registers a document with the external knowledge service,
        allowing that service to analyze and index the document content for
        future queries.

        Args:
            document_id: ID of the document to register

        Returns:
            FileRegistrationResult containing registration details and the
            service's internal file identifier

        Implementation Notes:
        - Must be idempotent: re-registering same document returns same result
        - Should handle service unavailability gracefully
        - Must return the service's internal file ID for future queries
        - May involve uploading document content to external service
        - Should handle various document formats and sizes

        Workflow Context:
        In Temporal workflows, this method is implemented as an activity
        to ensure registration results are durably stored and consistent
        across workflow replays.
        """
        ...

    async def execute_query(
        self,
        query_text: str,
        document_ids: Optional[List[str]] = None,
    ) -> QueryResult:
        """Execute a query against the external knowledge service.

        This method executes a text query against the knowledge service,
        optionally scoping the query to specific documents that have been
        previously registered with the service.

        Args:
            query_text: The query to execute (natural language or structured)
            document_ids: Optional list of document IDs to scope the query to.
                         If None, query runs against all registered documents.

        Returns:
            QueryResult containing query results and execution metadata

        Implementation Notes:
        - Must be idempotent: same query returns consistent results
        - Document IDs are translated to service's internal file identifiers
        - Should handle service unavailability gracefully
        - Query results should be structured as domain objects
        - Should track execution time and metadata
        - Must handle various query formats (natural language, structured,
          etc.)
        - Should validate that document_ids have been registered before
          querying

        Workflow Context:
        In Temporal workflows, this method is implemented as an activity
        to ensure query results are durably stored and can be replayed
        consistently.
        """
        ...
