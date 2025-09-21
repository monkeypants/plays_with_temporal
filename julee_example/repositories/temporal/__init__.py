"""
Temporal repository wrappers for the julee_example domain.

This package contains @temporal_activity_registration decorated classes that
wrap
pure backend repositories as Temporal activities. These classes should
only be imported by workers to avoid workflow sandbox violations.
"""

from .document import (
    TemporalMinioDocumentRepository,
    WorkflowDocumentRepositoryProxy,
)
from .assembly import (
    TemporalMinioAssemblyRepository,
    WorkflowAssemblyRepositoryProxy,
)
from .assembly_specification import (
    TemporalMinioAssemblySpecificationRepository,
    WorkflowAssemblySpecificationRepositoryProxy,
)
from .knowledge_service_query import (
    TemporalMinioKnowledgeServiceQueryRepository,
    WorkflowKnowledgeServiceQueryRepositoryProxy,
)
from .knowledge_service_config import (
    TemporalMinioKnowledgeServiceConfigRepository,
    WorkflowKnowledgeServiceConfigRepositoryProxy,
)

__all__ = [
    # Activity wrappers (for worker use)
    "TemporalMinioDocumentRepository",
    "TemporalMinioAssemblyRepository",
    "TemporalMinioAssemblySpecificationRepository",
    "TemporalMinioKnowledgeServiceQueryRepository",
    "TemporalMinioKnowledgeServiceConfigRepository",
    # Workflow proxies (for workflow use)
    "WorkflowDocumentRepositoryProxy",
    "WorkflowAssemblyRepositoryProxy",
    "WorkflowAssemblySpecificationRepositoryProxy",
    "WorkflowKnowledgeServiceQueryRepositoryProxy",
    "WorkflowKnowledgeServiceConfigRepositoryProxy",
]
