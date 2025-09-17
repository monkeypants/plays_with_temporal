"""
Memory repository implementations for julee_example domain.

This module exports in-memory implementations of all repository protocols
for the Capture, Extract, Assemble, Publish workflow. These implementations
use Python dictionaries for storage and are ideal for testing scenarios
where external dependencies should be avoided.

All implementations maintain the same async interfaces as their production
counterparts while providing lightweight, dependency-free alternatives.
"""

from .assembly import MemoryAssemblyRepository
from .assembly_specification import MemoryAssemblySpecificationRepository
from .document import MemoryDocumentRepository
from .document_policy_validation import (
    MemoryDocumentPolicyValidationRepository,
)
from .knowledge_service_config import MemoryKnowledgeServiceConfigRepository
from .knowledge_service_query import MemoryKnowledgeServiceQueryRepository
from .policy import MemoryPolicyRepository

__all__ = [
    "MemoryAssemblyRepository",
    "MemoryAssemblySpecificationRepository",
    "MemoryDocumentRepository",
    "MemoryDocumentPolicyValidationRepository",
    "MemoryKnowledgeServiceConfigRepository",
    "MemoryKnowledgeServiceQueryRepository",
    "MemoryPolicyRepository",
]
