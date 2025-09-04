"""
Assembly domain package for the Capture, Extract, Assemble, Publish workflow.

This package contains the Assembly and KnowledgeServiceQuery domain objects
that work together to define assembly configurations in the CEAP workflow system.

Assembly defines document output types (like "meeting minutes") with their
JSON schemas and applicability rules. KnowledgeServiceQuery defines specific
extraction operations that can be performed against knowledge services to
populate the Assembly's schema.
"""

from .assembly import Assembly, AssemblyStatus
from .knowledge_service_query import KnowledgeServiceQuery

__all__ = [
    "Assembly",
    "AssemblyStatus",
    "KnowledgeServiceQuery",
]
