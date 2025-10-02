"""
Services for julee_example domain.

This module provides service classes and factory functions for interacting
with external services in the Capture, Extract, Assemble, Publish workflow.

The services layer handles external integrations while the repository layer
handles local metadata persistence. Services are organized by service type
into submodules, each with their own protocols and implementations.
"""

# Re-export knowledge service components
from .knowledge_service import KnowledgeService

__all__ = [
    # Knowledge Service
    "KnowledgeService",
]
