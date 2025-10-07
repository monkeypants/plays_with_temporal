"""
Domain models for julee_example.

This package contains all the domain entities and value objects following
Clean Architecture principles. These models are framework-independent and
contain only business logic.

Re-exports commonly used models for convenient importing:
    from julee_example.domain.models import Document, Assembly, Policy
"""

# Document models
from .document import Document, DocumentStatus

# Custom field types
from .custom_fields.content_stream import ContentStream

# Assembly models
from .assembly import Assembly, AssemblyStatus
from .assembly_specification import (
    AssemblySpecification,
    AssemblySpecificationStatus,
    KnowledgeServiceQuery,
)

# Configuration models
from .knowledge_service_config import KnowledgeServiceConfig

# Policy models
from .policy import Policy, PolicyStatus, DocumentPolicyValidation

__all__ = [
    # Document models
    "Document",
    "DocumentStatus",
    "ContentStream",
    # Assembly models
    "Assembly",
    "AssemblyStatus",
    "AssemblySpecification",
    "AssemblySpecificationStatus",
    "KnowledgeServiceQuery",
    # Configuration models
    "KnowledgeServiceConfig",
    # Policy models
    "Policy",
    "PolicyStatus",
    "DocumentPolicyValidation",
]
