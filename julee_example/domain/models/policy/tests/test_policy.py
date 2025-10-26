"""
Tests for Policy domain models.

These tests verify the behavior of Policy domain objects,
including validation, serialization, and business logic.
"""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from julee_example.domain.models.policy import (
    Policy,
    PolicyStatus,
)


class TestPolicy:
    """Tests for Policy domain model."""

    def test_create_minimal_policy(self) -> None:
        """Test creating a policy with minimal fields."""
        policy = Policy(
            policy_id="policy-001",
            title="Content Quality Policy",
            description="Validates content meets quality standards",
            validation_scores=[("quality-check-query", 80)],
        )

        assert policy.policy_id == "policy-001"
        assert policy.title == "Content Quality Policy"
        assert (
            policy.description == "Validates content meets quality standards"
        )
        assert policy.validation_scores == [("quality-check-query", 80)]
        assert policy.transformation_queries is None
        assert policy.status == PolicyStatus.ACTIVE
        assert policy.version == "0.1.0"
        assert isinstance(policy.created_at, datetime)
        assert policy.updated_at is None
        assert policy.is_validation_only is True
        assert policy.has_transformations is False

    def test_create_policy_with_transformations(self) -> None:
        """Test creating a policy with transformations."""
        policy = Policy(
            policy_id="policy-002",
            title="Content Enhancement Policy",
            description="Validates and enhances content quality",
            validation_scores=[
                ("grammar-check-query", 85),
                ("clarity-check-query", 75),
            ],
            transformation_queries=[
                "grammar-fix-query",
                "clarity-improvement-query",
            ],
        )

        assert policy.validation_scores == [
            ("grammar-check-query", 85),
            ("clarity-check-query", 75),
        ]
        assert policy.transformation_queries == [
            "grammar-fix-query",
            "clarity-improvement-query",
        ]
        assert policy.is_validation_only is False
        assert policy.has_transformations is True

    def test_create_policy_with_all_fields(self) -> None:
        """Test creating a policy with all fields specified."""
        created_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        updated_at = datetime(2024, 1, 2, 12, 0, 0, tzinfo=timezone.utc)

        policy = Policy(
            policy_id="policy-003",
            title="Complete Policy",
            description="A policy with all fields specified",
            status=PolicyStatus.DRAFT,
            validation_scores=[("test-query", 90)],
            transformation_queries=["transform-query"],
            version="1.0.0",
            created_at=created_at,
            updated_at=updated_at,
        )

        assert policy.policy_id == "policy-003"
        assert policy.title == "Complete Policy"
        assert policy.description == "A policy with all fields specified"
        assert policy.status == PolicyStatus.DRAFT
        assert policy.validation_scores == [("test-query", 90)]
        assert policy.transformation_queries == ["transform-query"]
        assert policy.version == "1.0.0"
        assert policy.created_at == created_at
        assert policy.updated_at == updated_at

    def test_policy_id_validation(self) -> None:
        """Test policy ID validation."""
        # Empty ID should fail
        with pytest.raises(ValidationError) as exc_info:
            Policy(
                policy_id="",
                title="Test Policy",
                description="Test description",
                validation_scores=[("test-query", 80)],
            )
        assert "Policy ID cannot be empty" in str(exc_info.value)

        # Whitespace-only ID should fail
        with pytest.raises(ValidationError) as exc_info:
            Policy(
                policy_id="   ",
                title="Test Policy",
                description="Test description",
                validation_scores=[("test-query", 80)],
            )
        assert "Policy ID cannot be empty" in str(exc_info.value)

        # Valid ID with whitespace should be stripped
        policy = Policy(
            policy_id="  policy-001  ",
            title="Test Policy",
            description="Test description",
            validation_scores=[("test-query", 80)],
        )
        assert policy.policy_id == "policy-001"

    def test_title_validation(self) -> None:
        """Test title validation."""
        # Empty title should fail
        with pytest.raises(ValidationError) as exc_info:
            Policy(
                policy_id="policy-001",
                title="",
                description="Test description",
                validation_scores=[("test-query", 80)],
            )
        assert "Policy title cannot be empty" in str(exc_info.value)

        # Whitespace-only title should fail
        with pytest.raises(ValidationError) as exc_info:
            Policy(
                policy_id="policy-001",
                title="   ",
                description="Test description",
                validation_scores=[("test-query", 80)],
            )
        assert "Policy title cannot be empty" in str(exc_info.value)

        # Valid title with whitespace should be stripped
        policy = Policy(
            policy_id="policy-001",
            title="  Test Policy  ",
            description="Test description",
            validation_scores=[("test-query", 80)],
        )
        assert policy.title == "Test Policy"

    def test_description_validation(self) -> None:
        """Test description validation."""
        # Empty description should fail
        with pytest.raises(ValidationError) as exc_info:
            Policy(
                policy_id="policy-001",
                title="Test Policy",
                description="",
                validation_scores=[("test-query", 80)],
            )
        assert "Policy description cannot be empty" in str(exc_info.value)

        # Whitespace-only description should fail
        with pytest.raises(ValidationError) as exc_info:
            Policy(
                policy_id="policy-001",
                title="Test Policy",
                description="   ",
                validation_scores=[("test-query", 80)],
            )
        assert "Policy description cannot be empty" in str(exc_info.value)

        # Valid description with whitespace should be stripped
        policy = Policy(
            policy_id="policy-001",
            title="Test Policy",
            description="  Test description  ",
            validation_scores=[("test-query", 80)],
        )
        assert policy.description == "Test description"

    def test_validation_scores_validation(self) -> None:
        """Test validation scores validation."""
        # Empty list should fail
        with pytest.raises(ValidationError) as exc_info:
            Policy(
                policy_id="policy-001",
                title="Test Policy",
                description="Test description",
                validation_scores=[],
            )
        assert "Validation scores list cannot be empty" in str(exc_info.value)

        # Non-list should fail
        with pytest.raises(ValidationError) as exc_info:
            Policy(
                policy_id="policy-001",
                title="Test Policy",
                description="Test description",
                validation_scores="not-a-list",  # type: ignore
            )
        assert "Input should be a valid list" in str(exc_info.value)

        # Invalid tuple length should fail
        with pytest.raises(ValidationError) as exc_info:
            Policy(
                policy_id="policy-001",
                title="Test Policy",
                description="Test description",
                validation_scores=[("query-id",)],  # type: ignore
            )
        assert "Field required" in str(exc_info.value)

        # Non-string query ID should fail
        with pytest.raises(ValidationError) as exc_info:
            Policy(
                policy_id="policy-001",
                title="Test Policy",
                description="Test description",
                validation_scores=[(123, 80)],  # type: ignore
            )
        assert "Input should be a valid string" in str(exc_info.value)

        # Empty query ID should fail
        with pytest.raises(ValidationError) as exc_info:
            Policy(
                policy_id="policy-001",
                title="Test Policy",
                description="Test description",
                validation_scores=[("", 80)],
            )
        assert (
            "Query ID in validation scores must be a non-empty string"
            in str(exc_info.value)
        )

        # Non-integer score should fail
        with pytest.raises(ValidationError) as exc_info:
            Policy(
                policy_id="policy-001",
                title="Test Policy",
                description="Test description",
                validation_scores=[("query-id", "not-a-number")],  # type: ignore
            )
        assert "Input should be a valid integer" in str(exc_info.value)

        # Score below 0 should fail
        with pytest.raises(ValidationError) as exc_info:
            Policy(
                policy_id="policy-001",
                title="Test Policy",
                description="Test description",
                validation_scores=[("query-id", -1)],
            )
        assert "Required score -1 must be between 0 and 100" in str(
            exc_info.value
        )

        # Score above 100 should fail
        with pytest.raises(ValidationError) as exc_info:
            Policy(
                policy_id="policy-001",
                title="Test Policy",
                description="Test description",
                validation_scores=[("query-id", 101)],
            )
        assert "Required score 101 must be between 0 and 100" in str(
            exc_info.value
        )

        # Duplicate query IDs should fail
        with pytest.raises(ValidationError) as exc_info:
            Policy(
                policy_id="policy-001",
                title="Test Policy",
                description="Test description",
                validation_scores=[
                    ("query-id", 80),
                    ("query-id", 90),
                ],
            )
        assert "Duplicate query ID 'query-id' in validation scores" in str(
            exc_info.value
        )

        # Valid scores with whitespace should be stripped
        policy = Policy(
            policy_id="policy-001",
            title="Test Policy",
            description="Test description",
            validation_scores=[("  query-id  ", 80)],
        )
        assert policy.validation_scores == [("query-id", 80)]

        # Boundary values should work
        policy = Policy(
            policy_id="policy-001",
            title="Test Policy",
            description="Test description",
            validation_scores=[
                ("min-score", 0),
                ("max-score", 100),
            ],
        )
        assert policy.validation_scores == [
            ("min-score", 0),
            ("max-score", 100),
        ]

    def test_transformation_queries_validation(self) -> None:
        """Test transformation queries validation."""
        # None should be valid
        policy = Policy(
            policy_id="policy-001",
            title="Test Policy",
            description="Test description",
            validation_scores=[("test-query", 80)],
            transformation_queries=None,
        )
        assert policy.transformation_queries is None
        assert policy.is_validation_only is True

        # Empty list should be valid
        policy = Policy(
            policy_id="policy-001",
            title="Test Policy",
            description="Test description",
            validation_scores=[("test-query", 80)],
            transformation_queries=[],
        )
        assert policy.transformation_queries == []
        assert policy.is_validation_only is True

        # Non-list should fail
        with pytest.raises(ValidationError) as exc_info:
            Policy(
                policy_id="policy-001",
                title="Test Policy",
                description="Test description",
                validation_scores=[("test-query", 80)],
                transformation_queries="not-a-list",  # type: ignore
            )
        assert "Input should be a valid list" in str(exc_info.value)

        # Non-string query ID should fail
        with pytest.raises(ValidationError) as exc_info:
            Policy(
                policy_id="policy-001",
                title="Test Policy",
                description="Test description",
                validation_scores=[("test-query", 80)],
                transformation_queries=[123],  # type: ignore
            )
        assert "Input should be a valid string" in str(exc_info.value)

        # Empty string query ID should fail
        with pytest.raises(ValidationError) as exc_info:
            Policy(
                policy_id="policy-001",
                title="Test Policy",
                description="Test description",
                validation_scores=[("test-query", 80)],
                transformation_queries=[""],
            )
        assert (
            "Each transformation query ID must be a non-empty string"
            in str(exc_info.value)
        )

        # Duplicate query IDs should fail
        with pytest.raises(ValidationError) as exc_info:
            Policy(
                policy_id="policy-001",
                title="Test Policy",
                description="Test description",
                validation_scores=[("test-query", 80)],
                transformation_queries=["query-1", "query-1"],
            )
        assert (
            "Duplicate query ID 'query-1' in transformation queries"
            in str(exc_info.value)
        )

        # Valid queries with whitespace should be stripped
        policy = Policy(
            policy_id="policy-001",
            title="Test Policy",
            description="Test description",
            validation_scores=[("test-query", 80)],
            transformation_queries=["  query-1  ", "  query-2  "],
        )
        assert policy.transformation_queries == ["query-1", "query-2"]
        assert policy.has_transformations is True

    def test_version_validation(self) -> None:
        """Test version validation."""
        # Empty version should fail
        with pytest.raises(ValidationError) as exc_info:
            Policy(
                policy_id="policy-001",
                title="Test Policy",
                description="Test description",
                validation_scores=[("test-query", 80)],
                version="",
            )
        assert "Policy version cannot be empty" in str(exc_info.value)

        # Whitespace-only version should fail
        with pytest.raises(ValidationError) as exc_info:
            Policy(
                policy_id="policy-001",
                title="Test Policy",
                description="Test description",
                validation_scores=[("test-query", 80)],
                version="   ",
            )
        assert "Policy version cannot be empty" in str(exc_info.value)

        # Valid version with whitespace should be stripped
        policy = Policy(
            policy_id="policy-001",
            title="Test Policy",
            description="Test description",
            validation_scores=[("test-query", 80)],
            version="  1.0.0  ",
        )
        assert policy.version == "1.0.0"

    def test_policy_status_enum(self) -> None:
        """Test PolicyStatus enum values."""
        # Test all valid status values
        for status in PolicyStatus:
            policy = Policy(
                policy_id="policy-001",
                title="Test Policy",
                description="Test description",
                validation_scores=[("test-query", 80)],
                status=status,
            )
            assert policy.status == status

        # Test enum values
        assert PolicyStatus.ACTIVE == "active"
        assert PolicyStatus.INACTIVE == "inactive"
        assert PolicyStatus.DRAFT == "draft"
        assert PolicyStatus.DEPRECATED == "deprecated"

    def test_is_validation_only_property(self) -> None:
        """Test is_validation_only property logic."""
        # No transformation queries (empty list)
        policy = Policy(
            policy_id="policy-001",
            title="Test Policy",
            description="Test description",
            validation_scores=[("test-query", 80)],
            transformation_queries=[],
        )
        assert policy.is_validation_only is True

        # Non-empty transformation queries
        policy = Policy(
            policy_id="policy-001",
            title="Test Policy",
            description="Test description",
            validation_scores=[("test-query", 80)],
            transformation_queries=["transform-query"],
        )
        assert policy.is_validation_only is False

    def test_has_transformations_property(self) -> None:
        """Test has_transformations property logic."""
        # No transformation queries (empty list)
        policy = Policy(
            policy_id="policy-001",
            title="Test Policy",
            description="Test description",
            validation_scores=[("test-query", 80)],
            transformation_queries=[],
        )
        assert policy.has_transformations is False

        # Non-empty transformation queries
        policy = Policy(
            policy_id="policy-001",
            title="Test Policy",
            description="Test description",
            validation_scores=[("test-query", 80)],
            transformation_queries=["transform-query"],
        )
        assert policy.has_transformations is True

    def test_policy_serialization(self) -> None:
        """Test Policy serialization and deserialization."""
        original_policy = Policy(
            policy_id="policy-001",
            title="Test Policy",
            description="Test description",
            validation_scores=[
                ("grammar-query", 85),
                ("clarity-query", 75),
            ],
            transformation_queries=["fix-grammar", "improve-clarity"],
            status=PolicyStatus.DRAFT,
            version="1.2.0",
        )

        # Serialize to dict
        policy_dict = original_policy.model_dump()

        # Deserialize from dict
        restored_policy = Policy.model_validate(policy_dict)

        # Verify all fields match
        assert restored_policy.policy_id == original_policy.policy_id
        assert restored_policy.title == original_policy.title
        assert restored_policy.description == original_policy.description
        assert (
            restored_policy.validation_scores
            == original_policy.validation_scores
        )
        assert (
            restored_policy.transformation_queries
            == original_policy.transformation_queries
        )
        assert restored_policy.status == original_policy.status
        assert restored_policy.version == original_policy.version
        assert restored_policy.created_at == original_policy.created_at
        assert restored_policy.updated_at == original_policy.updated_at

    def test_policy_json_serialization(self) -> None:
        """Test Policy JSON serialization and deserialization."""
        original_policy = Policy(
            policy_id="policy-001",
            title="Test Policy",
            description="Test description",
            validation_scores=[("test-query", 80)],
        )

        # Serialize to JSON
        policy_json = original_policy.model_dump_json()

        # Deserialize from JSON
        restored_policy = Policy.model_validate_json(policy_json)

        # Verify core fields match
        assert restored_policy.policy_id == original_policy.policy_id
        assert restored_policy.title == original_policy.title
        assert restored_policy.description == original_policy.description
        assert (
            restored_policy.validation_scores
            == original_policy.validation_scores
        )
