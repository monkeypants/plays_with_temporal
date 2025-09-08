"""
Assembly domain package for the Capture, Extract, Assemble, Publish workflow.

This package contains the Assembly and AssemblyIteration domain objects
that work together to represent assembly processes in the CEAP workflow.

Assembly represents a specific instance of assembling a document using an
AssemblySpecification, linking an input document with the specification and
tracking multiple assembly iterations.

AssemblyIteration represents individual attempts at document assembly within
an Assembly process, each producing an output document.
"""

from .assembly import Assembly, AssemblyStatus
from .assembly_iteration import AssemblyIteration

__all__ = [
    "Assembly",
    "AssemblyStatus",
    "AssemblyIteration",
]
