"""
Domain models for the Capture, Extract, Assemble, Publish workflow.

This module contains the core domain objects that represent the business
entities and value objects used throughout the Capture, Extract, Assemble,
Publish workflow system.

All domain models use Pydantic BaseModel for validation, serialization,
and type safety, following the patterns established in the sample project.
"""

from .document import Document, DocumentStatus
from .custom_fields import ContentStream
from .assembly import Assembly, AssemblyStatus
from .knowledge_service_query import KnowledgeServiceQuery

__all__ = [
    "Document",
    "DocumentStatus",
    "ContentStream",
    "Assembly",
    "AssemblyStatus",
    "KnowledgeServiceQuery",
]
