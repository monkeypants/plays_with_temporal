"""
Repository protocols for julee_example domain.

This module exports all repository protocol interfaces for the Capture,
Extract, Assemble, Publish workflow, following the Clean Architecture
patterns established in the Fun-Police framework.
"""

from .document import DocumentRepository
from .assembly import AssemblyRepository
from .assembly_specification import AssemblySpecificationRepository
from .knowledge_service_config import KnowledgeServiceConfigRepository
from .knowledge_service_query import KnowledgeServiceQueryRepository

__all__ = [
    "DocumentRepository",
    "AssemblyRepository",
    "AssemblySpecificationRepository",
    "KnowledgeServiceConfigRepository",
    "KnowledgeServiceQueryRepository",
]
