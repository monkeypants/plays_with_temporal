"""
Test factories for Document domain objects using factory_boy.

This module provides factory_boy factories for creating test instances of
Document domain objects with sensible defaults.
"""

import io
from datetime import datetime, timezone
from typing import Any
from factory.base import Factory
from factory.faker import Faker
from factory.declarations import LazyAttribute, LazyFunction

from julee_example.domain.models.document import Document, DocumentStatus
from julee_example.domain.models.custom_fields.content_stream import (
    ContentStream,
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
