"""
Test factories for Assembly domain objects using factory_boy.

This module provides factory_boy factories for creating test instances of
Assembly domain objects with sensible defaults.
"""

from datetime import datetime, timezone
from factory.base import Factory
from factory.faker import Faker
from factory.declarations import LazyFunction

from julee_example.domain.models.assembly import (
    Assembly,
    AssemblyStatus,
)


class AssemblyFactory(Factory):
    """Factory for creating Assembly instances with sensible test defaults."""

    class Meta:
        model = Assembly

    # Core assembly identification
    assembly_id = Faker("uuid4")
    assembly_specification_id = Faker("uuid4")
    input_document_id = Faker("uuid4")
    workflow_id = Faker("uuid4")

    # Assembly process tracking
    status = AssemblyStatus.PENDING
    assembled_document_id = None

    # Timestamps
    created_at = LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = LazyFunction(lambda: datetime.now(timezone.utc))
