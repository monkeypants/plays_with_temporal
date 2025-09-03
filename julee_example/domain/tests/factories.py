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
from typing import Any
from factory.base import Factory
from factory.faker import Faker
from factory.declarations import LazyAttribute, LazyFunction

from julee_example.domain import (
    Document,
    DocumentStatus,
    ContentStream,
    Assembly,
    AssemblyStatus,
    KnowledgeServiceQuery,
)


# Helper functions to generate content bytes consistently
def _get_default_content_bytes() -> bytes:
    """Generate the default content bytes for documents."""
    return b"Test document content for testing purposes"


class ContentStreamFactory(Factory):
    class Meta:
        model = ContentStream

    # Create ContentStream with BytesIO containing test content
    @classmethod
    def _create(
        cls, model_class: type[ContentStream], **kwargs: Any
    ) -> ContentStream:
        content = kwargs.get("content", b"Test stream content")
        return model_class(io.BytesIO(content))

    @classmethod
    def _build(
        cls, model_class: type[ContentStream], **kwargs: Any
    ) -> ContentStream:
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
    assembly_types: list[str] = []

    # Timestamps
    created_at = LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = LazyFunction(lambda: datetime.now(timezone.utc))

    # Additional data
    additional_metadata: dict[str, Any] = {}

    # Content - using LazyAttribute to create fresh BytesIO for each instance
    @LazyAttribute
    def size_bytes(self) -> int:
        # Calculate size from the default content
        return len(_get_default_content_bytes())

    @LazyAttribute
    def content(self) -> ContentStream:
        # Create ContentStream with default content
        return ContentStream(io.BytesIO(_get_default_content_bytes()))


class AssemblyFactory(Factory):
    """Factory for creating Assembly instances with sensible test defaults."""

    class Meta:
        model = Assembly

    # Core assembly identification
    assembly_id = Faker("uuid4")
    name = "Test Assembly"
    applicability = "Test documents for automated testing purposes"
    prompt = (
        "Extract test data from the document according to the provided "
        "JSON schema"
    )

    # Valid JSON Schema for testing
    @LazyAttribute
    def jsonschema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "content": {"type": "string"},
                "metadata": {
                    "type": "object",
                    "properties": {
                        "author": {"type": "string"},
                        "created_date": {"type": "string", "format": "date"},
                    },
                },
            },
            "required": ["title"],
        }

    # Assembly configuration
    status = AssemblyStatus.ACTIVE
    version = "0.1.0"

    # Timestamps
    created_at = LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = LazyFunction(lambda: datetime.now(timezone.utc))


class KnowledgeServiceQueryFactory(Factory):
    """Factory for creating KnowledgeServiceQuery instances with sensible
    test defaults."""

    class Meta:
        model = KnowledgeServiceQuery

    # Core query identification
    query_id = Faker("uuid4")
    name = "Test Knowledge Service Query"

    # Knowledge service configuration
    knowledge_service_id = "test-knowledge-service"
    prompt = "Extract test data from the document"

    # Query configuration

    # Timestamps
    created_at = LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = LazyFunction(lambda: datetime.now(timezone.utc))
