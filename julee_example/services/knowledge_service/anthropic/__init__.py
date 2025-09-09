"""
Anthropic service implementations for julee_example domain.

This module exports Anthropic-specific implementations of service protocols
for the Capture, Extract, Assemble, Publish workflow.
"""

from .knowledge_service import AnthropicKnowledgeService

__all__ = [
    "AnthropicKnowledgeService",
]
