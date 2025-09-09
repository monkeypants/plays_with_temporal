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
from .knowledge_service_config import MemoryKnowledgeServiceConfigRepository

__all__ = [
    "MemoryAssemblyRepository",
    "MemoryAssemblySpecificationRepository",
    "MemoryDocumentRepository",
    "MemoryKnowledgeServiceConfigRepository",
]
