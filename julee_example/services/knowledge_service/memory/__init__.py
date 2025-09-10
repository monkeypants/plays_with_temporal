"""
Memory-based implementation of KnowledgeService for testing and development.

This module provides an in-memory implementation of the KnowledgeService
protocol that stores file registrations in memory and returns configurable
canned responses for queries.
"""

from .knowledge_service import MemoryKnowledgeService

__all__ = [
    "MemoryKnowledgeService",
]
