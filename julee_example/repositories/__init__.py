"""
Repository protocols for julee_example domain.

This module exports all repository protocol interfaces for the Capture,
Extract, Assemble, Publish workflow, following the Clean Architecture
patterns established in the Fun-Police framework.
"""

from .document import DocumentRepository
from .assembly import AssemblyRepository
from .assembly_specification import AssemblySpecificationRepository

__all__ = [
    "DocumentRepository",
    "AssemblyRepository",
    "AssemblySpecificationRepository",
]
