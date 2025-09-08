"""
Comprehensive tests for Assembly domain model.

This test module documents the design decisions made for the Assembly domain
model using table-based tests. It covers:

- Assembly instantiation with various field combinations
- JSON serialization behavior
- Field validation for required fields
- Assembly status transitions
- Assembly iteration management

Design decisions documented:
- Assemblies must have all required fields (assembly_id,
  assembly_specification_id, input_document_id)
- All ID fields must be non-empty and non-whitespace
- Status defaults to PENDING
- Iterations list defaults to empty list
- Timestamps are automatically set with timezone-aware defaults
"""

import pytest
import json
from datetime import datetime, timezone

from julee_example.domain import Assembly, AssemblyStatus
from .factories import AssemblyFactory, AssemblyIterationFactory


class TestAssemblyInstantiation:
    """Test Assembly creation with various field combinations."""

    @pytest.mark.parametrize(
        "assembly_id,assembly_specification_id,input_document_id,expected_success",
        [
            # Valid cases
            ("asm-1", "spec-1", "doc-1", True),
            ("assembly-uuid-456", "spec-uuid-789", "input-doc-123", True),
            ("asm_abc", "spec_def", "doc_ghi", True),
            # Invalid cases - empty required fields
            ("", "spec-1", "doc-1", False),  # Empty assembly_id
            ("asm-1", "", "doc-1", False),  # Empty assembly_specification_id
            ("asm-1", "spec-1", "", False),  # Empty input_document_id
            # Invalid cases - whitespace only
            ("   ", "spec-1", "doc-1", False),  # Whitespace assembly_id
            (
                "asm-1",
                "   ",
                "doc-1",
                False,
            ),  # Whitespace assembly_specification_id
            ("asm-1", "spec-1", "   ", False),  # Whitespace input_document_id
        ],
    )
    def test_assembly_creation_validation(
        self,
        assembly_id: str,
        assembly_specification_id: str,
        input_document_id: str,
        expected_success: bool,
    ) -> None:
        """Test assembly creation with various field validation scenarios."""
        if expected_success:
            # Should create successfully
            assembly = Assembly(
                assembly_id=assembly_id,
                assembly_specification_id=assembly_specification_id,
                input_document_id=input_document_id,
            )
            assert assembly.assembly_id == assembly_id.strip()
            assert (
                assembly.assembly_specification_id
                == assembly_specification_id.strip()
            )
            assert assembly.input_document_id == input_document_id.strip()
            assert assembly.status == AssemblyStatus.PENDING  # Default
            assert assembly.iterations == []  # Default empty list
            assert assembly.created_at is not None
            assert assembly.updated_at is not None
        else:
            # Should raise validation error
            with pytest.raises(
                Exception
            ):  # Could be ValueError or ValidationError
                Assembly(
                    assembly_id=assembly_id,
                    assembly_specification_id=assembly_specification_id,
                    input_document_id=input_document_id,
                )


class TestAssemblySerialization:
    """Test Assembly JSON serialization behavior."""

    def test_assembly_json_serialization(self) -> None:
        """Test that Assembly serializes to JSON correctly."""
        iteration1 = AssemblyIterationFactory.build(
            iteration_id=1, document_id="output-1"
        )
        iteration2 = AssemblyIterationFactory.build(
            iteration_id=2, document_id="output-2"
        )

        assembly = AssemblyFactory.build(
            assembly_id="test-assembly-123",
            assembly_specification_id="spec-456",
            input_document_id="input-789",
            status=AssemblyStatus.IN_PROGRESS,
            iterations=[iteration1, iteration2],
        )

        json_str = assembly.model_dump_json()
        json_data = json.loads(json_str)

        # All fields should be present in JSON
        assert json_data["assembly_id"] == assembly.assembly_id
        assert (
            json_data["assembly_specification_id"]
            == assembly.assembly_specification_id
        )
        assert json_data["input_document_id"] == assembly.input_document_id
        assert json_data["status"] == assembly.status.value
        assert "created_at" in json_data
        assert "updated_at" in json_data

        # Iterations should be serialized as nested objects
        assert len(json_data["iterations"]) == 2
        assert json_data["iterations"][0]["iteration_id"] == 1
        assert json_data["iterations"][0]["document_id"] == "output-1"
        assert json_data["iterations"][1]["iteration_id"] == 2
        assert json_data["iterations"][1]["document_id"] == "output-2"

    def test_assembly_json_roundtrip(self) -> None:
        """Test that Assembly can be serialized to JSON and deserialized
        back."""
        original_assembly = AssemblyFactory.build()
        iteration = AssemblyIterationFactory.build(
            assembly_id=original_assembly.assembly_id
        )
        original_assembly = AssemblyFactory.build(
            assembly_id=original_assembly.assembly_id, iterations=[iteration]
        )

        # Serialize to JSON
        json_str = original_assembly.model_dump_json()
        json_data = json.loads(json_str)

        # Deserialize back to Assembly
        reconstructed_assembly = Assembly(**json_data)

        # Should be equivalent
        assert (
            reconstructed_assembly.assembly_id
            == original_assembly.assembly_id
        )
        assert (
            reconstructed_assembly.assembly_specification_id
            == original_assembly.assembly_specification_id
        )
        assert (
            reconstructed_assembly.input_document_id
            == original_assembly.input_document_id
        )
        assert reconstructed_assembly.status == original_assembly.status
        assert len(reconstructed_assembly.iterations) == len(
            original_assembly.iterations
        )

        if original_assembly.iterations:
            assert (
                reconstructed_assembly.iterations[0].iteration_id
                == original_assembly.iterations[0].iteration_id
            )
            assert (
                reconstructed_assembly.iterations[0].document_id
                == original_assembly.iterations[0].document_id
            )


class TestAssemblyDefaults:
    """Test Assembly default values and behavior."""

    def test_assembly_default_values(self) -> None:
        """Test that Assembly has correct default values."""
        minimal_assembly = Assembly(
            assembly_id="test-id",
            assembly_specification_id="spec-id",
            input_document_id="doc-id",
        )

        assert minimal_assembly.status == AssemblyStatus.PENDING
        assert minimal_assembly.iterations == []
        assert minimal_assembly.created_at is not None
        assert minimal_assembly.updated_at is not None
        assert isinstance(minimal_assembly.created_at, datetime)
        assert isinstance(minimal_assembly.updated_at, datetime)
        # Should be timezone-aware
        assert minimal_assembly.created_at.tzinfo is not None
        assert minimal_assembly.updated_at.tzinfo is not None

    def test_assembly_custom_values(self) -> None:
        """Test Assembly with custom non-default values."""
        custom_iteration = AssemblyIterationFactory.build(
            assembly_id="custom-id"
        )
        custom_created_at = datetime(
            2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc
        )
        custom_updated_at = datetime(
            2023, 1, 2, 12, 0, 0, tzinfo=timezone.utc
        )

        custom_assembly = Assembly(
            assembly_id="custom-id",
            assembly_specification_id="custom-spec",
            input_document_id="custom-doc",
            status=AssemblyStatus.COMPLETED,
            iterations=[custom_iteration],
            created_at=custom_created_at,
            updated_at=custom_updated_at,
        )

        assert custom_assembly.status == AssemblyStatus.COMPLETED
        assert len(custom_assembly.iterations) == 1
        assert custom_assembly.iterations[0] == custom_iteration
        assert custom_assembly.created_at == custom_created_at
        assert custom_assembly.updated_at == custom_updated_at

    @pytest.mark.parametrize(
        "status",
        [
            AssemblyStatus.PENDING,
            AssemblyStatus.IN_PROGRESS,
            AssemblyStatus.COMPLETED,
            AssemblyStatus.FAILED,
            AssemblyStatus.CANCELLED,
        ],
    )
    def test_assembly_status_values(self, status: AssemblyStatus) -> None:
        """Test Assembly with different status values."""
        assembly = AssemblyFactory.build(status=status)
        assert assembly.status == status


class TestAssemblyFieldValidation:
    """Test Assembly field-specific validation."""

    def test_assembly_id_validation(self) -> None:
        """Test assembly_id field validation."""
        # Valid cases
        valid_assembly = Assembly(
            assembly_id="valid-id",
            assembly_specification_id="spec-id",
            input_document_id="doc-id",
        )
        assert valid_assembly.assembly_id == "valid-id"

        # Invalid cases
        with pytest.raises(Exception):
            Assembly(
                assembly_id="",
                assembly_specification_id="spec-id",
                input_document_id="doc-id",
            )

        with pytest.raises(Exception):
            Assembly(
                assembly_id="   ",
                assembly_specification_id="spec-id",
                input_document_id="doc-id",
            )

    def test_assembly_specification_id_validation(self) -> None:
        """Test assembly_specification_id field validation."""
        # Valid cases
        valid_assembly = Assembly(
            assembly_id="asm-id",
            assembly_specification_id="valid-spec-id",
            input_document_id="doc-id",
        )
        assert valid_assembly.assembly_specification_id == "valid-spec-id"

        # Invalid cases
        with pytest.raises(Exception):
            Assembly(
                assembly_id="asm-id",
                assembly_specification_id="",
                input_document_id="doc-id",
            )

        with pytest.raises(Exception):
            Assembly(
                assembly_id="asm-id",
                assembly_specification_id="   ",
                input_document_id="doc-id",
            )

    def test_input_document_id_validation(self) -> None:
        """Test input_document_id field validation."""
        # Valid cases
        valid_assembly = Assembly(
            assembly_id="asm-id",
            assembly_specification_id="spec-id",
            input_document_id="valid-doc-id",
        )
        assert valid_assembly.input_document_id == "valid-doc-id"

        # Invalid cases
        with pytest.raises(Exception):
            Assembly(
                assembly_id="asm-id",
                assembly_specification_id="spec-id",
                input_document_id="",
            )

        with pytest.raises(Exception):
            Assembly(
                assembly_id="asm-id",
                assembly_specification_id="spec-id",
                input_document_id="   ",
            )

    def test_field_trimming(self) -> None:
        """Test that string fields are properly trimmed."""
        assembly = Assembly(
            assembly_id="  trim-asm  ",
            assembly_specification_id="  trim-spec  ",
            input_document_id="  trim-doc  ",
        )

        assert assembly.assembly_id == "trim-asm"
        assert assembly.assembly_specification_id == "trim-spec"
        assert assembly.input_document_id == "trim-doc"


class TestAssemblyIterationManagement:
    """Test Assembly iteration list management."""

    def test_empty_iterations_list(self) -> None:
        """Test Assembly with empty iterations list."""
        assembly = AssemblyFactory.build(iterations=[])
        assert assembly.iterations == []

    def test_single_iteration(self) -> None:
        """Test Assembly with single iteration."""
        iteration = AssemblyIterationFactory.build(assembly_id="asm-id")
        assembly = AssemblyFactory.build(iterations=[iteration])

        assert len(assembly.iterations) == 1
        assert assembly.iterations[0] == iteration

    def test_multiple_iterations(self) -> None:
        """Test Assembly with multiple iterations."""
        iteration1 = AssemblyIterationFactory.build(
            iteration_id=1, assembly_id="asm-id"
        )
        iteration2 = AssemblyIterationFactory.build(
            iteration_id=2, assembly_id="asm-id"
        )
        iteration3 = AssemblyIterationFactory.build(
            iteration_id=3, assembly_id="asm-id"
        )

        assembly = AssemblyFactory.build(
            assembly_id="asm-id",
            iterations=[iteration1, iteration2, iteration3],
        )

        assert len(assembly.iterations) == 3
        assert assembly.iterations[0].iteration_id == 1
        assert assembly.iterations[1].iteration_id == 2
        assert assembly.iterations[2].iteration_id == 3

    def test_iterations_maintain_order(self) -> None:
        """Test that iterations maintain their order in the list."""
        iterations = [
            AssemblyIterationFactory.build(iteration_id=i + 1)
            for i in range(5)
        ]

        assembly = AssemblyFactory.build(iterations=iterations)

        for i, iteration in enumerate(assembly.iterations):
            assert iteration.iteration_id == i + 1
