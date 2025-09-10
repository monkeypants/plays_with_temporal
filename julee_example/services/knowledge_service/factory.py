"""
Factory function for creating KnowledgeService implementations.

This module provides the factory function for creating configured
KnowledgeService instances based on the service API configuration.
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from julee_example.domain import KnowledgeServiceConfig

from .knowledge_service import KnowledgeService
from .anthropic import AnthropicKnowledgeService
from julee_example.domain.knowledge_service_config import ServiceApi
from julee_example.repositories import DocumentRepository

logger = logging.getLogger(__name__)


def knowledge_service_factory(
    knowledge_service_config: "KnowledgeServiceConfig",
    document_repo: DocumentRepository,
) -> KnowledgeService:
    """Create a configured KnowledgeService instance.

    This factory function takes a KnowledgeServiceConfig domain object
    (containing metadata and service_api information) and returns a properly
    configured KnowledgeService implementation that can handle external
    operations.

    Args:
        knowledge_service_config: KnowledgeServiceConfig domain object with
                                 configuration and API information
        document_repo: DocumentRepository for accessing document data

    Returns:
        Configured KnowledgeService implementation ready for external
        operations

    Raises:
        ValueError: If the service_api is not supported

    Example:
        >>> from julee_example.domain import KnowledgeServiceConfig
        >>> from julee_example.domain.knowledge_service_config import (
        ...     ServiceApi
        ... )
        >>> from julee_example.repositories.memory import (
        ...     MemoryDocumentRepository
        ... )
        >>> config = KnowledgeServiceConfig(
        ...     knowledge_service_id="ks-123",
        ...     name="My Anthropic Service",
        ...     description="Anthropic-powered document analysis",
        ...     service_api=ServiceApi.ANTHROPIC
        ... )
        >>> document_repo = MemoryDocumentRepository()
        >>> service = knowledge_service_factory(config, document_repo)
        >>> result = await service.register_file("doc-456")
    """
    logger.debug(
        "Creating KnowledgeService via factory",
        extra={
            "knowledge_service_id": (
                knowledge_service_config.knowledge_service_id
            ),
            "service_api": knowledge_service_config.service_api.value,
        },
    )

    # Route to appropriate implementation based on service_api
    if knowledge_service_config.service_api == ServiceApi.ANTHROPIC:
        service = AnthropicKnowledgeService(
            knowledge_service_config, document_repo
        )
    else:
        raise ValueError(
            f"Unsupported service API: {knowledge_service_config.service_api}"
        )

    # Validate that the service satisfies the protocol
    from . import ensure_knowledge_service

    validated_service = ensure_knowledge_service(service)

    logger.info(
        "KnowledgeService created successfully",
        extra={
            "knowledge_service_id": (
                knowledge_service_config.knowledge_service_id
            ),
            "service_api": knowledge_service_config.service_api.value,
            "implementation": type(validated_service).__name__,
        },
    )

    return validated_service
