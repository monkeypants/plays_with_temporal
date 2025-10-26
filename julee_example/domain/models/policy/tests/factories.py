"""
Test factories for Policy domain objects using factory_boy.

This module provides factory_boy factories for creating test instances of
Policy domain objects with sensible defaults.
"""

from datetime import datetime, timezone
from factory.base import Factory
from factory.faker import Faker
from factory.declarations import LazyFunction

from julee_example.domain.models.policy import (
    DocumentPolicyValidation,
    DocumentPolicyValidationStatus,
)


class DocumentPolicyValidationFactory(Factory):
    """Factory for creating DocumentPolicyValidation instances with sensible
    test defaults."""

    class Meta:
        model = DocumentPolicyValidation

    # Core validation identification
    validation_id = Faker("uuid4")
    input_document_id = Faker("uuid4")
    policy_id = Faker("uuid4")

    # Validation process status
    status = DocumentPolicyValidationStatus.PENDING

    # Initial validation results (empty by default)
    validation_scores: list[tuple[str, int]] = []

    # Transformation results (None by default)
    transformed_document_id = None
    post_transform_validation_scores = None

    # Validation metadata
    started_at = LazyFunction(lambda: datetime.now(timezone.utc))
    completed_at = None
    error_message = None

    # Results summary
    passed = None
