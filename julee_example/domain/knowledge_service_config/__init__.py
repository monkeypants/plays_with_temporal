"""
Knowledge Service domain models for julee_example domain.

This module exports domain models for knowledge services in the Capture,
Extract, Assemble, Publish workflow. Knowledge services represent external
AI/ML services that can store documents and execute queries against them.
"""

from .knowledge_service_config import (
    KnowledgeServiceConfig,
    ServiceApi,
)

__all__ = [
    "KnowledgeServiceConfig",
    "ServiceApi",
]
