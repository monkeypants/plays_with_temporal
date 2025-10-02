"""
Knowledge Service module for julee_example domain.

This module provides the KnowledgeService protocol and factory function for
creating configured knowledge service instances. The factory routes to the
appropriate implementation based on the service_api configuration.
"""

import logging

from .knowledge_service import (
    KnowledgeService,
    QueryResult,
    FileRegistrationResult,
)


logger = logging.getLogger(__name__)


def ensure_knowledge_service(service: object) -> KnowledgeService:
    """Ensure an object satisfies the KnowledgeService protocol.

    Args:
        service: The service implementation to validate

    Returns:
        The validated service (type checker knows it satisfies
        KnowledgeService)

    Raises:
        TypeError: If the service doesn't satisfy the protocol
    """
    if not isinstance(service, KnowledgeService):
        raise TypeError(
            f"Service {type(service).__name__} does not satisfy "
            f"KnowledgeService protocol"
        )

    return service


__all__ = [
    "KnowledgeService",
    "ensure_knowledge_service",
    "QueryResult",
    "FileRegistrationResult",
]
