"""
Document domain package for the Capture, Extract, Assemble, Publish workflow.

This package contains the Document domain object and its related functionality
for the CEAP workflow system.

Document represents complete document entities including content and metadata,
providing a stream-like interface for efficient handling of both small and
large documents.
"""

from .document import Document, DocumentStatus

__all__ = [
    "Document",
    "DocumentStatus",
]
