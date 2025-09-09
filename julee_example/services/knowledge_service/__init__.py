"""
Knowledge Service module for julee_example domain.

This module provides the KnowledgeService protocol and factory function for
creating configured knowledge service instances. The factory routes to the
appropriate implementation based on the service_api configuration.
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from julee_example.domain import KnowledgeServiceConfig

from .knowledge_service import (
    KnowledgeService,
    QueryResult,
    FileRegistrationResult,
)
from .anthropic import AnthropicKnowledgeService
from julee_example.domain.knowledge_service_config import ServiceApi

logger = logging.getLogger(__name__)


def knowledge_service_factory(
    knowledge_service_config: "KnowledgeServiceConfig",
) -> KnowledgeService:
    """Create a configured KnowledgeService instance.

    This factory function takes a KnowledgeServiceConfig domain object
    (containing metadata and service_api information) and returns a properly
    configured KnowledgeService implementation that can handle external
    operations.

    Args:
        knowledge_service_config: KnowledgeServiceConfig domain object with
                                 configuration and API information

    Returns:
        Configured KnowledgeService implementation ready for external
        operations

    Raises:
        ValueError: If the service_api is not supported

    Example:
        >>> from julee_example.domain import KnowledgeServiceConfig
        >>> from julee_example.domain.knowledge_service import ServiceApi
        >>> config = KnowledgeServiceConfig(
        ...     knowledge_service_id="ks-123",
        ...     name="My Anthropic Service",
        ...     description="Anthropic-powered document analysis",
        ...     service_api=ServiceApi.ANTHROPIC
        ... )
        >>> service = knowledge_service_factory(config)
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
        service = AnthropicKnowledgeService(knowledge_service_config)
    else:
        raise ValueError(
            f"Unsupported service API: {knowledge_service_config.service_api}"
        )

    logger.info(
        "KnowledgeService created successfully",
        extra={
            "knowledge_service_id": (
                knowledge_service_config.knowledge_service_id
            ),
            "service_api": knowledge_service_config.service_api.value,
            "implementation": type(service).__name__,
        },
    )

    return service


__all__ = [
    "KnowledgeService",
    "knowledge_service_factory",
    "QueryResult",
    "FileRegistrationResult",
]
