"""
Assembly domain package for the Capture, Extract, Assemble, Publish workflow.

This package contains the Assembly domain object that represents assembly
processes in the CEAP workflow.

Assembly represents a specific instance of assembling a document using an
AssemblySpecification, linking an input document with the specification and
producing a single assembled document as output.
"""

from .assembly import Assembly, AssemblyStatus

__all__ = [
    "Assembly",
    "AssemblyStatus",
]
