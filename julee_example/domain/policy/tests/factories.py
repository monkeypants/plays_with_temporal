"""
Test factories for Policy domain models.

These factories provide convenient ways to create Policy
instances for testing purposes.
"""

from datetime import datetime, timezone
from typing import List, Tuple, Optional

from julee_example.domain.policy import (
    Policy,
    PolicyStatus,
)


class PolicyFactory:
    """Factory for creating Policy test instances."""

    @staticmethod
    def create_minimal(
        policy_id: str = "test-policy-001",
        title: str = "Test Policy",
        description: str = "A test policy",
        validation_scores: Optional[List[Tuple[str, int]]] = None,
    ) -> Policy:
        """Create a minimal Policy for testing.

        Args:
            policy_id: Unique ID for the policy
            title: Policy title
            description: Policy description
            validation_scores: List of (query_id, required_score) tuples

        Returns:
            A Policy instance with minimal configuration
        """
        if validation_scores is None:
            validation_scores = [("default-validation-query", 80)]

        return Policy(
            policy_id=policy_id,
            title=title,
            description=description,
            validation_scores=validation_scores,
        )

    @staticmethod
    def create_validation_only(
        policy_id: str = "validation-policy-001",
        title: str = "Validation Only Policy",
        description: str = (
            "A policy that only validates without transformations"
        ),
        validation_scores: Optional[List[Tuple[str, int]]] = None,
    ) -> Policy:
        """Create a validation-only Policy for testing.

        Args:
            policy_id: Unique ID for the policy
            title: Policy title
            description: Policy description
            validation_scores: List of (query_id, required_score) tuples

        Returns:
            A Policy instance in validation-only mode
        """
        if validation_scores is None:
            validation_scores = [
                ("grammar-check-query", 85),
                ("clarity-check-query", 75),
                ("completeness-check-query", 90),
            ]

        return Policy(
            policy_id=policy_id,
            title=title,
            description=description,
            validation_scores=validation_scores,
            transformation_queries=None,  # Explicitly validation-only
        )

    @staticmethod
    def create_with_transformations(
        policy_id: str = "transform-policy-001",
        title: str = "Transformation Policy",
        description: str = "A policy that validates and transforms content",
        validation_scores: Optional[List[Tuple[str, int]]] = None,
        transformation_queries: Optional[List[str]] = None,
    ) -> Policy:
        """Create a Policy with transformations for testing.

        Args:
            policy_id: Unique ID for the policy
            title: Policy title
            description: Policy description
            validation_scores: List of (query_id, required_score) tuples
            transformation_queries: List of transformation query IDs

        Returns:
            A Policy instance with transformations enabled
        """
        if validation_scores is None:
            validation_scores = [
                ("grammar-check-query", 85),
                ("clarity-check-query", 75),
                ("style-check-query", 80),
            ]

        if transformation_queries is None:
            transformation_queries = [
                "grammar-fix-query",
                "clarity-improvement-query",
                "style-enhancement-query",
            ]

        return Policy(
            policy_id=policy_id,
            title=title,
            description=description,
            validation_scores=validation_scores,
            transformation_queries=transformation_queries,
        )

    @staticmethod
    def create_full(
        policy_id: str = "full-policy-001",
        title: str = "Complete Policy",
        description: str = "A policy with all fields specified",
        status: PolicyStatus = PolicyStatus.ACTIVE,
        validation_scores: Optional[List[Tuple[str, int]]] = None,
        transformation_queries: Optional[List[str]] = None,
        version: str = "1.0.0",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> Policy:
        """Create a complete Policy with all fields for testing.

        Args:
            policy_id: Unique ID for the policy
            title: Policy title
            description: Policy description
            status: Policy status
            validation_scores: List of (query_id, required_score) tuples
            transformation_queries: List of transformation query IDs
            version: Policy version
            created_at: Creation timestamp
            updated_at: Update timestamp

        Returns:
            A Policy instance with all fields specified
        """
        if validation_scores is None:
            validation_scores = [
                ("content-quality-query", 85),
                ("technical-accuracy-query", 90),
                ("readability-query", 75),
            ]

        if transformation_queries is None:
            transformation_queries = [
                "content-enhancement-query",
                "technical-review-query",
                "readability-improvement-query",
            ]

        if created_at is None:
            created_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        if updated_at is None:
            updated_at = datetime(2024, 1, 2, 12, 0, 0, tzinfo=timezone.utc)

        return Policy(
            policy_id=policy_id,
            title=title,
            description=description,
            status=status,
            validation_scores=validation_scores,
            transformation_queries=transformation_queries,
            version=version,
            created_at=created_at,
            updated_at=updated_at,
        )

    @staticmethod
    def create_draft(
        policy_id: str = "draft-policy-001",
        title: str = "Draft Policy",
        description: str = "A policy in draft status",
    ) -> Policy:
        """Create a draft Policy for testing.

        Args:
            policy_id: Unique ID for the policy
            title: Policy title
            description: Policy description

        Returns:
            A Policy instance in draft status
        """
        return Policy(
            policy_id=policy_id,
            title=title,
            description=description,
            status=PolicyStatus.DRAFT,
            validation_scores=[("draft-validation-query", 70)],
            version="0.1.0",
        )

    @staticmethod
    def create_deprecated(
        policy_id: str = "deprecated-policy-001",
        title: str = "Deprecated Policy",
        description: str = "A deprecated policy",
    ) -> Policy:
        """Create a deprecated Policy for testing.

        Args:
            policy_id: Unique ID for the policy
            title: Policy title
            description: Policy description

        Returns:
            A Policy instance in deprecated status
        """
        return Policy(
            policy_id=policy_id,
            title=title,
            description=description,
            status=PolicyStatus.DEPRECATED,
            validation_scores=[("legacy-validation-query", 60)],
            version="0.9.0",
        )

    @staticmethod
    def create_high_standards(
        policy_id: str = "high-standards-policy-001",
        title: str = "High Standards Policy",
        description: str = "A policy with very high validation standards",
    ) -> Policy:
        """Create a Policy with high validation standards.

        Args:
            policy_id: Unique ID for the policy
            title: Policy title
            description: Policy description

        Returns:
            A Policy instance with high validation scores
        """
        return Policy(
            policy_id=policy_id,
            title=title,
            description=description,
            validation_scores=[
                ("excellence-check-query", 95),
                ("perfection-check-query", 98),
                ("mastery-check-query", 92),
            ],
            transformation_queries=[
                "excellence-enhancement-query",
                "perfection-tuning-query",
                "mastery-refinement-query",
            ],
        )

    @staticmethod
    def create_minimal_standards(
        policy_id: str = "minimal-standards-policy-001",
        title: str = "Minimal Standards Policy",
        description: str = "A policy with minimal validation standards",
    ) -> Policy:
        """Create a Policy with minimal validation standards.

        Args:
            policy_id: Unique ID for the policy
            title: Policy title
            description: Policy description

        Returns:
            A Policy instance with low validation scores
        """
        return Policy(
            policy_id=policy_id,
            title=title,
            description=description,
            validation_scores=[
                ("basic-check-query", 50),
                ("minimum-viability-query", 40),
            ],
        )
