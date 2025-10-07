"""
Tests for knowledge_service_factory function.

This module contains tests for the factory function that creates
KnowledgeService implementations based on configuration.
"""

import pytest

from julee_example.domain.models.knowledge_service_config import (
    KnowledgeServiceConfig,
)
from julee_example.domain.models.document import Document, DocumentStatus
from julee_example.domain.models.knowledge_service_config import ServiceApi
from julee_example.domain.models.custom_fields.content_stream import (
    ContentStream,
)
from julee_example.services.knowledge_service import ensure_knowledge_service
from julee_example.services.knowledge_service.factory import (
    knowledge_service_factory,
)
from julee_example.services.knowledge_service.anthropic import (
    AnthropicKnowledgeService,
)
import io
from datetime import datetime, timezone


@pytest.fixture
def test_document() -> Document:
    """Create a test Document for testing."""
    content_text = (
        "This is test document content for knowledge service testing."
    )
    content_bytes = content_text.encode("utf-8")
    content_stream = ContentStream(io.BytesIO(content_bytes))

    return Document(
        document_id="test-doc-123",
        original_filename="test_document.txt",
        content_type="text/plain",
        size_bytes=len(content_bytes),
        content_multihash="test-hash-123",
        status=DocumentStatus.CAPTURED,
        content=content_stream,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def anthropic_config() -> KnowledgeServiceConfig:
    """Create a test KnowledgeServiceConfig for Anthropic."""
    return KnowledgeServiceConfig(
        knowledge_service_id="ks-anthropic-test",
        name="Test Anthropic Service",
        description="Anthropic service for testing",
        service_api=ServiceApi.ANTHROPIC,
    )


class TestKnowledgeServiceFactory:
    """Test cases for knowledge_service_factory function."""

    def test_factory_creates_anthropic_service(
        self,
        anthropic_config: KnowledgeServiceConfig,
    ) -> None:
        """Test factory creates AnthropicKnowledgeService for ANTHROPIC."""
        with pytest.MonkeyPatch.context() as m:
            m.setenv("ANTHROPIC_API_KEY", "test-key")
            service = knowledge_service_factory(anthropic_config)

            assert isinstance(service, AnthropicKnowledgeService)

    def test_factory_returns_validated_service(
        self,
        anthropic_config: KnowledgeServiceConfig,
    ) -> None:
        """Test factory returns service that passes protocol validation."""
        with pytest.MonkeyPatch.context() as m:
            m.setenv("ANTHROPIC_API_KEY", "test-key")
            service = knowledge_service_factory(anthropic_config)

            # Should not raise an error when validating the service
            validated_service = ensure_knowledge_service(service)
            assert validated_service == service


class TestEnsureKnowledgeService:
    """Test cases for ensure_knowledge_service function."""

    def test_ensure_knowledge_service_accepts_valid_service(
        self,
        anthropic_config: KnowledgeServiceConfig,
    ) -> None:
        """Test that ensure_knowledge_service accepts a valid service."""
        # Mock the anthropic import to avoid dependency issues in tests
        with pytest.MonkeyPatch.context() as m:
            m.setenv("ANTHROPIC_API_KEY", "test-key")
            service = AnthropicKnowledgeService()

            validated_service = ensure_knowledge_service(service)
            assert validated_service == service

    def test_ensure_knowledge_service_rejects_invalid_service(self) -> None:
        """Test that ensure_knowledge_service rejects invalid service."""
        invalid_service = "not a knowledge service"

        with pytest.raises(
            TypeError,
            match="Service str does not satisfy KnowledgeService protocol",
        ):
            ensure_knowledge_service(invalid_service)
