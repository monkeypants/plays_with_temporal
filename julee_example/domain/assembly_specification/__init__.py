"""
Assembly domain package for the Capture, Extract, Assemble, Publish workflow.

This package contains the AssemblySpecification and KnowledgeServiceQuery
domain objects that work together to define assembly configurations in the
CEAP workflow.

AssemblySpecification defines document output types (like "meeting minutes")
with their JSON schemas and applicability rules. KnowledgeServiceQuery defines
specific extraction operations that can be performed against knowledge
services to populate the AssemblySpecification's schema.
"""

from .assembly_specification import (
    AssemblySpecification,
    AssemblySpecificationStatus,
)
from .knowledge_service_query import KnowledgeServiceQuery

__all__ = [
    "AssemblySpecification",
    "AssemblySpecificationStatus",
    "KnowledgeServiceQuery",
]
