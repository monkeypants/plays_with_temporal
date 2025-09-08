"""
Test factories for Assembly domain objects using factory_boy.

This module provides factory_boy factories for creating test instances of
Assembly domain objects with sensible defaults.
"""

from datetime import datetime, timezone
from factory.base import Factory
from factory.faker import Faker
from factory.declarations import LazyFunction, Sequence
from factory import LazyAttribute

from julee_example.domain.assembly import (
    Assembly,
    AssemblyStatus,
    AssemblyIteration,
)


class AssemblyIterationFactory(Factory):
    """Factory for creating AssemblyIteration instances with sensible
    test defaults."""

    class Meta:
        model = AssemblyIteration

    # Core iteration identification
    iteration_id = Sequence(
        lambda n: n + 1
    )  # Sequential integers: 1, 2, 3, ...
    assembly_id = Faker("uuid4")
    document_id = Faker("uuid4")

    # Timestamps
    created_at = LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = LazyFunction(lambda: datetime.now(timezone.utc))


class AssemblyFactory(Factory):
    """Factory for creating Assembly instances with sensible test defaults."""

    class Meta:
        model = Assembly

    # Core assembly identification
    assembly_id = Faker("uuid4")
    assembly_specification_id = Faker("uuid4")
    input_document_id = Faker("uuid4")

    # Assembly process tracking
    status = AssemblyStatus.PENDING
    iterations = LazyAttribute(lambda obj: [])

    # Timestamps
    created_at = LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = LazyFunction(lambda: datetime.now(timezone.utc))
