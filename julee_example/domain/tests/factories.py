"""
Test factories for creating domain objects using factory_boy.

This module provides factory_boy factories for creating test instances of
domain objects with sensible defaults. Uses proper factory_boy patterns for
better test object creation.

Design decisions documented:
- ContentStream wraps io.BytesIO for small test content
- Documents have required fields: id, filename, content_type, size, multihash
- Default status is CAPTURED (entry point of CEAP pipeline)
- Timestamps are UTC timezone-aware
- Content and metadata are kept in sync (size matches actual content)
"""

import io
from datetime import datetime, timezone
from factory import Factory, Faker, LazyAttribute, LazyFunction

from julee_example.domain import Document, DocumentStatus, ContentStream


# Helper functions to generate content bytes consistently
def _get_default_content_bytes():
    """Generate the default content bytes for documents."""
    return b"Test document content for testing purposes"


def _get_pdf_content_bytes():
    """Generate PDF content bytes for documents."""
    return b"%PDF-1.4 fake PDF content for testing"


def _get_json_content_bytes():
    """Generate JSON content bytes for documents."""
    return b'{"test": "data", "numbers": [1, 2, 3]}'


def _get_large_content_bytes():
    """Generate large content bytes for streaming tests."""
    chunk = b"Large document content for testing streaming operations. "
    target_bytes = 10 * 1024  # 10KB
    repeat_count = target_bytes // len(chunk)
    content_bytes = chunk * repeat_count
    # Add extra chunks to ensure we meet minimum size
    while len(content_bytes) < target_bytes:
        content_bytes += chunk
    return content_bytes


class ContentStreamFactory(Factory):
    class Meta:
        model = ContentStream

    # Create ContentStream with BytesIO containing test content
    @classmethod
    def _create(cls, model_class, **kwargs):
        content = kwargs.get("content", b"Test stream content")
        return model_class(io.BytesIO(content))


class DocumentFactory(Factory):
    """Factory for creating Document instances with sensible test defaults."""

    class Meta:
        model = Document

    # Core document identification
    document_id = Faker("uuid4")
    original_filename = "test_document.txt"
    content_type = "text/plain"
    content_multihash = Faker("sha256")

    # Document processing state
    status = DocumentStatus.CAPTURED
    knowledge_service_id = None
    assembly_types = []

    # Timestamps
    created_at = LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = LazyFunction(lambda: datetime.now(timezone.utc))

    # Additional data
    additional_metadata = {}

    # Content - using LazyAttribute to create fresh BytesIO for each instance
    @LazyAttribute
    def size_bytes(self):
        # Calculate size from the default content
        return len(_get_default_content_bytes())

    @LazyAttribute
    def content(self):
        # Create ContentStream with default content
        return ContentStream(io.BytesIO(_get_default_content_bytes()))
