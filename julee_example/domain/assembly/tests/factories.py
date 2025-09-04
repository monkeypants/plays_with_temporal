"""
Test factories for Assembly domain objects using factory_boy.

This module provides factory_boy factories for creating test instances of
Assembly domain objects with sensible defaults.
"""

from datetime import datetime, timezone
from typing import Any
from factory.base import Factory
from factory.faker import Faker
from factory.declarations import LazyAttribute, LazyFunction

from julee_example.domain.assembly import (
    Assembly,
    AssemblyStatus,
    KnowledgeServiceQuery,
)


class AssemblyFactory(Factory):
    """Factory for creating Assembly instances with sensible test defaults."""

    class Meta:
        model = Assembly

    # Core assembly identification
    assembly_id = Faker("uuid4")
    name = "Test Assembly"
    applicability = "Test documents for automated testing purposes"

    # Valid JSON Schema for testing
    @LazyAttribute
    def jsonschema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "content": {"type": "string"},
                "metadata": {
                    "type": "object",
                    "properties": {
                        "author": {"type": "string"},
                        "created_date": {"type": "string", "format": "date"},
                    },
                },
            },
            "required": ["title"],
        }

    # Assembly configuration
    status = AssemblyStatus.ACTIVE
    version = "0.1.0"

    # Timestamps
    created_at = LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = LazyFunction(lambda: datetime.now(timezone.utc))


class KnowledgeServiceQueryFactory(Factory):
    """Factory for creating KnowledgeServiceQuery instances with sensible
    test defaults."""

    class Meta:
        model = KnowledgeServiceQuery

    # Core query identification
    query_id = Faker("uuid4")
    name = "Test Knowledge Service Query"

    # Knowledge service configuration
    knowledge_service_id = "test-knowledge-service"
    prompt = "Extract test data from the document"

    # Timestamps
    created_at = LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = LazyFunction(lambda: datetime.now(timezone.utc))
