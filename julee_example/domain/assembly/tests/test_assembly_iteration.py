"""
Comprehensive tests for AssemblyIteration domain model.

This test module documents the design decisions made for the
AssemblyIteration domain model using table-based tests. It covers:

- AssemblyIteration instantiation with various field combinations
- JSON serialization behavior
- Field validation for required fields

Design decisions documented:
- AssemblyIterations must have all required fields (iteration_id,
  document_id)
- All ID fields must be non-empty and non-whitespace
- Timestamps are automatically set with timezone-aware defaults
"""

import pytest
import json
from datetime import datetime, timezone

from typing import Any

from julee_example.domain import AssemblyIteration
from .factories import AssemblyIterationFactory


class TestAssemblyIterationInstantiation:
    """Test AssemblyIteration creation with various field combinations."""

    @pytest.mark.parametrize(
        "iteration_id,document_id,expected_success",
        [
            # Valid cases
            (1, "doc-123", True),
            (2, "output-doc-789", True),
            (10, "doc_def", True),
            # Invalid cases - zero or negative iteration_id
            (0, "doc-123", False),  # Zero iteration_id
            (-1, "doc-123", False),  # Negative iteration_id
            (1, "", False),  # Empty document_id
            # Invalid cases - whitespace only
            (1, "   ", False),  # Whitespace document_id
        ],
    )
    def test_assembly_iteration_creation_validation(
        self,
        iteration_id: int,
        document_id: str,
        expected_success: bool,
    ) -> None:
        """Test iteration creation with various field validation scenarios."""
        if expected_success:
            # Should create successfully
            iteration = AssemblyIteration(
                iteration_id=iteration_id,
                document_id=document_id,
            )
            assert iteration.iteration_id == iteration_id
            assert iteration.document_id == document_id.strip()
            assert iteration.created_at is not None
            assert iteration.updated_at is not None
            assert isinstance(iteration.created_at, datetime)
            assert isinstance(iteration.updated_at, datetime)
        else:
            # Should raise validation error
            with pytest.raises(
                Exception
            ):  # Could be ValueError or ValidationError
                AssemblyIteration(
                    iteration_id=iteration_id,
                    document_id=document_id,
                )


class TestAssemblyIterationSerialization:
    """Test AssemblyIteration JSON serialization behavior."""

    def test_assembly_iteration_json_serialization(self) -> None:
        """Test that AssemblyIteration serializes to JSON correctly."""
        iteration = AssemblyIterationFactory.build(
            iteration_id=1,
            document_id="doc-output-456",
        )

        json_str = iteration.model_dump_json()
        json_data = json.loads(json_str)

        # All fields should be present in JSON
        assert json_data["iteration_id"] == iteration.iteration_id
        assert json_data["document_id"] == iteration.document_id
        assert "created_at" in json_data
        assert "updated_at" in json_data

    def test_assembly_iteration_json_roundtrip(self) -> None:
        """Test that AssemblyIteration can be serialized to JSON and
        deserialized back."""
        original_iteration = AssemblyIterationFactory.build()

        # Serialize to JSON
        json_str = original_iteration.model_dump_json()
        json_data = json.loads(json_str)

        # Deserialize back to AssemblyIteration
        reconstructed_iteration = AssemblyIteration(**json_data)

        # Should be equivalent
        assert (
            reconstructed_iteration.iteration_id
            == original_iteration.iteration_id
        )
        assert (
            reconstructed_iteration.document_id
            == original_iteration.document_id
        )
        # Timestamps might have slight differences due to serialization
        # but should be close
        assert reconstructed_iteration.created_at is not None
        assert reconstructed_iteration.updated_at is not None


class TestAssemblyIterationDefaults:
    """Test AssemblyIteration default values and behavior."""

    def test_assembly_iteration_default_values(self) -> None:
        """Test that AssemblyIteration has correct default values."""
        minimal_iteration = AssemblyIteration(
            iteration_id=1,
            document_id="test-doc",
        )

        assert minimal_iteration.created_at is not None
        assert minimal_iteration.updated_at is not None
        assert isinstance(minimal_iteration.created_at, datetime)
        assert isinstance(minimal_iteration.updated_at, datetime)
        # Should be timezone-aware
        assert minimal_iteration.created_at.tzinfo is not None
        assert minimal_iteration.updated_at.tzinfo is not None

    def test_assembly_iteration_custom_values(self) -> None:
        """Test AssemblyIteration with custom non-default values."""
        custom_created_at = datetime(
            2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc
        )
        custom_updated_at = datetime(
            2023, 1, 2, 12, 0, 0, tzinfo=timezone.utc
        )

        custom_iteration = AssemblyIteration(
            iteration_id=5,
            document_id="custom-doc",
            created_at=custom_created_at,
            updated_at=custom_updated_at,
        )

        assert custom_iteration.iteration_id == 5
        assert custom_iteration.document_id == "custom-doc"
        assert custom_iteration.created_at == custom_created_at
        assert custom_iteration.updated_at == custom_updated_at


class TestAssemblyIterationFieldValidation:
    """Test AssemblyIteration field-specific validation."""

    def test_iteration_id_validation(self) -> None:
        """Test iteration_id field validation."""
        # Valid cases
        valid_iteration = AssemblyIteration(
            iteration_id=1,
            document_id="doc-id",
        )
        assert valid_iteration.iteration_id == 1

        # Invalid cases
        with pytest.raises(Exception):
            AssemblyIteration(
                iteration_id=0,
                document_id="doc-id",
            )

        with pytest.raises(Exception):
            AssemblyIteration(
                iteration_id=-1,
                document_id="doc-id",
            )

    def test_document_id_validation(self) -> None:
        """Test document_id field validation."""
        # Valid cases
        valid_iteration = AssemblyIteration(
            iteration_id=1,
            document_id="valid-doc-id",
        )
        assert valid_iteration.document_id == "valid-doc-id"

        # Invalid cases
        with pytest.raises(Exception):
            AssemblyIteration(
                iteration_id=1,
                document_id="",
            )

        with pytest.raises(Exception):
            AssemblyIteration(
                iteration_id=1,
                document_id="   ",
            )

    def test_field_trimming(self) -> None:
        """Test that string fields are properly trimmed."""
        iteration = AssemblyIteration(
            iteration_id=1,
            document_id="  trim-doc  ",
        )

        assert iteration.iteration_id == 1
        assert iteration.document_id == "trim-doc"


class TestAssemblyIterationScorecardResults:
    """Test scorecard_results field validation."""

    @pytest.mark.parametrize(
        "scorecard_results,expected_success",
        [
            # Valid cases - empty list
            ([], True),
            # Valid cases - valid tuples with scores in range
            ([("query-1", 85)], True),
            ([("query-1", 0)], True),  # Minimum valid score
            ([("query-1", 100)], True),  # Maximum valid score
            ([("query-1", 85), ("query-2", 92)], True),  # Multiple results
            ([("very-long-query-id-name", 75)], True),  # Long query ID
            # Invalid cases - wrong types
            ("not-a-list", False),
            ({"query-1": 85}, False),  # Dict instead of list
            # Invalid cases - wrong tuple structure
            ([("query-1", 85, "extra")], False),  # 3-tuple instead of 2
            ([("query-1",)], False),  # 1-tuple instead of 2
            (["query-1", 85], False),  # List items instead of tuples
            # Invalid cases - invalid query IDs
            ([("", 85)], False),  # Empty query ID
            ([("   ", 85)], False),  # Whitespace-only query ID
            ([(123, 85)], False),  # Non-string query ID
            # Invalid cases - invalid scores
            ([("query-1", -1)], False),  # Score below 0
            ([("query-1", 101)], False),  # Score above 100
            (
                [("query-1", "not-a-number")],
                False,
            ),  # String score that can't be converted to int
            ([("query-1", 85.5)], False),  # Float score instead of int
        ],
    )
    def test_scorecard_results_validation(
        self, scorecard_results: Any, expected_success: bool
    ) -> None:
        """Test scorecard_results field validation."""
        if expected_success:
            # Should create successfully
            iteration = AssemblyIteration(
                iteration_id=1,
                document_id="test-doc",
                scorecard_results=scorecard_results,
            )
            # Verify the scorecard_results are stored correctly
            assert iteration.scorecard_results == scorecard_results
        else:
            # Should raise validation error
            with pytest.raises(Exception):
                AssemblyIteration(
                    iteration_id=1,
                    document_id="test-doc",
                    scorecard_results=scorecard_results,
                )

    def test_scorecard_results_with_valid_scores(self) -> None:
        """Test scorecard_results with valid scores are properly stored."""
        valid_scorecard_results = [
            ("extraction-query-1", 85),
            ("extraction-query-2", 92),
            ("validation-query-1", 78),
        ]

        iteration = AssemblyIterationFactory.build(
            scorecard_results=valid_scorecard_results
        )

        assert iteration.scorecard_results == valid_scorecard_results
        assert len(iteration.scorecard_results) == 3
        # Verify individual tuples
        assert iteration.scorecard_results[0] == ("extraction-query-1", 85)
        assert iteration.scorecard_results[1] == ("extraction-query-2", 92)
        assert iteration.scorecard_results[2] == ("validation-query-1", 78)

    def test_scorecard_results_default_empty(self) -> None:
        """Test that scorecard_results defaults to empty list."""
        iteration = AssemblyIteration(
            iteration_id=1,
            document_id="test-doc",
        )

        assert iteration.scorecard_results == []
        assert len(iteration.scorecard_results) == 0
