"""
Tests for knowledge_service_factory function.

This module contains tests for the factory function that creates
KnowledgeService implementations based on configuration.
"""

import pytest

from julee_example.domain import KnowledgeServiceConfig
from julee_example.domain.knowledge_service_config import ServiceApi
from julee_example.services.knowledge_service import (
    knowledge_service_factory,
    ensure_knowledge_service,
)
from julee_example.services.knowledge_service.anthropic import (
    AnthropicKnowledgeService,
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
        self, anthropic_config: KnowledgeServiceConfig
    ) -> None:
        """Test factory creates AnthropicKnowledgeService for ANTHROPIC."""
        service = knowledge_service_factory(anthropic_config)

        assert isinstance(service, AnthropicKnowledgeService)
        assert service.config == anthropic_config

    def test_factory_returns_validated_service(
        self, anthropic_config: KnowledgeServiceConfig
    ) -> None:
        """Test factory returns service that passes protocol validation."""
        service = knowledge_service_factory(anthropic_config)

        # Should not raise an error when validating the service
        validated_service = ensure_knowledge_service(service)
        assert validated_service == service


class TestEnsureKnowledgeService:
    """Test cases for ensure_knowledge_service function."""

    def test_ensure_knowledge_service_accepts_valid_service(
        self, anthropic_config: KnowledgeServiceConfig
    ) -> None:
        """Test that ensure_knowledge_service accepts a valid service."""
        service = AnthropicKnowledgeService(anthropic_config)

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
