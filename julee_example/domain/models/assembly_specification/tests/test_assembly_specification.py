"""
Comprehensive tests for AssemblySpecification domain model.

This test module documents the design decisions made for the
AssemblySpecification domain model using table-based tests. It covers:

- AssemblySpecification instantiation with various field combinations
- JSON Schema validation rules and error conditions
- JSON serialization behavior
- Field validation for required fields

Design decisions documented:
- AssemblySpecifications must have all required fields (id, name,
  applicability, prompt, jsonschema)
- JSON Schema field must be a valid JSON Schema dictionary
- All text fields must be non-empty and non-whitespace
- Version field has a default but can be customized
- Status defaults to ACTIVE
"""

import pytest
import json
from typing import Dict, Any

from julee_example.domain.models.assembly_specification import (
    AssemblySpecification,
    AssemblySpecificationStatus,
)
from .factories import AssemblyFactory


class TestAssemblyInstantiation:
    """Test AssemblySpecification creation with various field combinations."""

    @pytest.mark.parametrize(
        "assembly_specification_id,name,applicability,jsonschema,expected_success",
        [
            # Valid cases
            (
                "assembly-specification-1",
                "Meeting Minutes",
                "Corporate meeting recordings and transcripts",
                {
                    "type": "object",
                    "properties": {"title": {"type": "string"}},
                },
                True,
            ),
            (
                "assembly-specification-2",
                "Project Report",
                "Technical project documentation and status reports",
                {
                    "type": "object",
                    "properties": {
                        "project_name": {"type": "string"},
                        "status": {
                            "type": "string",
                            "enum": ["active", "completed"],
                        },
                        "milestones": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["project_name"],
                },
                True,
            ),
            # Invalid cases - empty required fields
            (
                "",
                "Test Assembly",
                "Test applicability",
                {
                    "type": "object",
                    "properties": {"test": {"type": "string"}},
                },
                False,
            ),  # Empty assembly_specification_id
            (
                "assembly-specification-3",
                "",
                "Test applicability",
                {
                    "type": "object",
                    "properties": {"test": {"type": "string"}},
                },
                False,
            ),  # Empty name
            (
                "assembly-specification-4",
                "Test Assembly",
                "",
                {
                    "type": "object",
                    "properties": {"test": {"type": "string"}},
                },
                False,
            ),  # Empty applicability
            # Invalid cases - whitespace only
            (
                "   ",
                "Test Assembly",
                "Test applicability",
                {
                    "type": "object",
                    "properties": {"test": {"type": "string"}},
                },
                False,
            ),  # Whitespace assembly_specification_id
            (
                "assembly-specification-6",
                "   ",
                "Test applicability",
                {
                    "type": "object",
                    "properties": {"test": {"type": "string"}},
                },
                False,
            ),  # Whitespace name
            (
                "assembly-specification-7",
                "Test Assembly",
                "   ",
                {
                    "type": "object",
                    "properties": {"test": {"type": "string"}},
                },
                False,
            ),  # Whitespace applicability
        ],
    )
    def test_assembly_creation_validation(
        self,
        assembly_specification_id: str,
        name: str,
        applicability: str,
        jsonschema: Dict[str, Any],
        expected_success: bool,
    ) -> None:
        """Test assembly creation with various field validation scenarios."""
        if expected_success:
            # Should create successfully
            assembly = AssemblySpecification(
                assembly_specification_id=assembly_specification_id,
                name=name,
                applicability=applicability,
                jsonschema=jsonschema,
            )
            assert (
                assembly.assembly_specification_id
                == assembly_specification_id.strip()
            )
            assert assembly.name == name.strip()
            assert assembly.applicability == applicability.strip()
            assert assembly.jsonschema == jsonschema
            assert (
                assembly.status == AssemblySpecificationStatus.ACTIVE
            )  # Default
            assert assembly.version == "0.1.0"  # Default
        else:
            # Should raise validation error
            with pytest.raises(
                Exception
            ):  # Could be ValueError or ValidationError
                AssemblySpecification(
                    assembly_specification_id=assembly_specification_id,
                    name=name,
                    applicability=applicability,
                    jsonschema=jsonschema,
                )


class TestAssemblyKnowledgeServiceQueriesValidation:
    """Test knowledge_service_queries field validation."""

    @pytest.mark.parametrize(
        "knowledge_service_queries,expected_success",
        [
            # Valid cases - empty dict
            ({}, True),
            # Valid cases - valid JSON pointers that exist in schema
            ({"/properties/test": "query-1"}, True),
            ({"": "root-query"}, True),  # Empty string for root
            ({"/properties/test": "query-1", "": "root-query"}, True),
            # Invalid cases - malformed pointers
            ({"invalid-pointer": "query-1"}, False),
            ({"test": "query-1"}, False),  # Missing /properties/
            # Invalid cases - pointers that don't exist in schema
            ({"/properties/nonexistent": "query-1"}, False),
            # Invalid cases - wrong types
            ("not-a-dict", False),
            (["/properties/test", "query-1"], False),
            # Invalid cases - invalid query IDs
            ({"/properties/test": ""}, False),  # Empty query ID
            ({"/properties/test": 123}, False),  # Non-string query ID
        ],
    )
    def test_knowledge_service_queries_validation(
        self,
        knowledge_service_queries: Any,
        expected_success: bool,
    ) -> None:
        """Test knowledge_service_queries field validation."""
        if expected_success:
            # Should create successfully
            assembly = AssemblySpecification(
                assembly_specification_id="test-id",
                name="Test Assembly",
                applicability="Test applicability",
                jsonschema={
                    "type": "object",
                    "properties": {"test": {"type": "string"}},
                },
                knowledge_service_queries=knowledge_service_queries,
            )
            assert (
                assembly.knowledge_service_queries
                == knowledge_service_queries
            )
        else:
            # Should raise validation error
            with pytest.raises(Exception):
                AssemblySpecification(
                    assembly_specification_id="test-id",
                    name="Test Assembly",
                    applicability="Test applicability",
                    jsonschema={
                        "type": "object",
                        "properties": {"test": {"type": "string"}},
                    },
                    knowledge_service_queries=knowledge_service_queries,
                )


class TestAssemblyJsonSchemaValidation:
    """Test JSON Schema field validation."""

    @pytest.mark.parametrize(
        "jsonschema,error_message_contains",
        [
            # Valid JSON Schemas
            (
                {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                },
                None,
            ),
            (
                {"type": "array", "items": {"type": "string"}, "minItems": 1},
                None,
            ),
            (
                {"type": "string", "pattern": "^[A-Z]+$"},
                None,
            ),
            (
                {
                    "type": "object",
                    "properties": {
                        "user": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "age": {"type": "integer", "minimum": 0},
                            },
                            "required": ["name"],
                        }
                    },
                    "required": ["user"],
                },
                None,
            ),
            # Invalid cases - not a dict
            ("not a dict", "Input should be a valid dictionary"),
            (123, "Input should be a valid dictionary"),
            ([], "Input should be a valid dictionary"),
            # Invalid cases - missing required fields
            (
                {"properties": {"name": {"type": "string"}}},
                "JSON Schema must have a 'type' field",
            ),
            ({}, "JSON Schema must have a 'type' field"),
            # Invalid JSON Schema structure
            (
                {"type": "invalid_type"},
                "Invalid JSON Schema",
            ),
            (
                {
                    "type": "object",
                    "properties": {"invalid_prop": {"type": "invalid_type"}},
                },
                "Invalid JSON Schema",
            ),
            (
                {
                    "type": "object",
                    "additionalProperties": "invalid",
                },  # additionalProperties must be boolean or object
                "Invalid JSON Schema",
            ),
        ],
    )
    def test_jsonschema_validation(
        self,
        jsonschema: Any,
        error_message_contains: str | None,
    ) -> None:
        """Test JSON Schema field validation with various schemas."""
        if error_message_contains is None:
            # Should create successfully
            assembly = AssemblySpecification(
                assembly_specification_id="test-id",
                name="Test Assembly",
                applicability="Test applicability",
                jsonschema=jsonschema,
            )
            assert assembly.jsonschema == jsonschema
        else:
            # Should raise validation error
            with pytest.raises(Exception) as exc_info:
                AssemblySpecification(
                    assembly_specification_id="test-id",
                    name="Test Assembly",
                    applicability="Test applicability",
                    jsonschema=jsonschema,
                )

            assert error_message_contains in str(exc_info.value)


class TestAssemblySerialization:
    """Test AssemblySpecification JSON serialization behavior."""

    def test_assembly_json_serialization(self) -> None:
        """Test that AssemblySpecification serializes to JSON correctly."""
        complex_schema = {
            "type": "object",
            "properties": {
                "meeting_info": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "date": {"type": "string", "format": "date"},
                        "participants": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["title", "date"],
                },
                "action_items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "description": {"type": "string"},
                            "assignee": {"type": "string"},
                            "due_date": {"type": "string", "format": "date"},
                        },
                        "required": ["description"],
                    },
                },
            },
            "required": ["meeting_info"],
        }

        assembly = AssemblyFactory.build(
            assembly_specification_id="meeting-minutes-v1",
            name="Meeting Minutes",
            applicability="Corporate meeting recordings",
            jsonschema=complex_schema,
        )

        json_str = assembly.model_dump_json()
        json_data = json.loads(json_str)

        # All fields should be present in JSON
        assert (
            json_data["assembly_specification_id"]
            == assembly.assembly_specification_id
        )
        assert json_data["name"] == assembly.name
        assert json_data["applicability"] == assembly.applicability
        assert json_data["status"] == assembly.status.value
        assert json_data["version"] == assembly.version

        # JSON Schema should be preserved as structured data
        assert json_data["jsonschema"] == complex_schema
        assert json_data["jsonschema"]["type"] == "object"
        assert "meeting_info" in json_data["jsonschema"]["properties"]
        assert "action_items" in json_data["jsonschema"]["properties"]

    def test_assembly_json_roundtrip(self) -> None:
        """Test that AssemblySpecification can be serialized to JSON and
        deserialized back."""
        original_assembly = AssemblyFactory.build()

        # Serialize to JSON
        json_str = original_assembly.model_dump_json()
        json_data = json.loads(json_str)

        # Deserialize back to AssemblySpecification
        reconstructed_assembly = AssemblySpecification(**json_data)

        # Should be equivalent
        assert (
            reconstructed_assembly.assembly_specification_id
            == original_assembly.assembly_specification_id
        )
        assert reconstructed_assembly.name == original_assembly.name
        assert (
            reconstructed_assembly.applicability
            == original_assembly.applicability
        )
        assert (
            reconstructed_assembly.jsonschema == original_assembly.jsonschema
        )
        assert reconstructed_assembly.status == original_assembly.status
        assert reconstructed_assembly.version == original_assembly.version


class TestAssemblyDefaults:
    """Test AssemblySpecification default values and behavior."""

    def test_assembly_default_values(self) -> None:
        """Test that AssemblySpecification has correct default values."""
        minimal_assembly = AssemblySpecification(
            assembly_specification_id="test-id",
            name="Test Assembly",
            applicability="Test applicability",
            jsonschema={
                "type": "object",
                "properties": {"test": {"type": "string"}},
            },
        )

        assert minimal_assembly.status == AssemblySpecificationStatus.ACTIVE
        assert minimal_assembly.version == "0.1.0"
        assert minimal_assembly.created_at is not None
        assert minimal_assembly.updated_at is not None

    def test_assembly_custom_values(self) -> None:
        """Test AssemblySpecification with custom non-default values."""
        custom_assembly = AssemblySpecification(
            assembly_specification_id="custom-id",
            name="Custom Assembly",
            applicability="Custom applicability",
            jsonschema={
                "type": "object",
                "properties": {"custom": {"type": "string"}},
            },
            status=AssemblySpecificationStatus.DRAFT,
            version="2.0.0",
            knowledge_service_queries={
                "/properties/custom": "custom-query-1"
            },
        )

        assert custom_assembly.status == AssemblySpecificationStatus.DRAFT
        assert custom_assembly.version == "2.0.0"
        assert custom_assembly.knowledge_service_queries == {
            "/properties/custom": "custom-query-1"
        }

    @pytest.mark.parametrize(
        "status",
        [
            AssemblySpecificationStatus.ACTIVE,
            AssemblySpecificationStatus.INACTIVE,
            AssemblySpecificationStatus.DRAFT,
            AssemblySpecificationStatus.DEPRECATED,
        ],
    )
    def test_assembly_status_values(
        self, status: AssemblySpecificationStatus
    ) -> None:
        """Test AssemblySpecification with different status values."""
        assembly = AssemblyFactory.build(status=status)
        assert assembly.status == status


class TestAssemblyVersionValidation:
    """Test AssemblySpecification version field validation."""

    @pytest.mark.parametrize(
        "version,expected_success",
        [
            ("1.0.0", True),
            ("0.1.0", True),
            ("2.5.1-beta", True),
            ("v1.0", True),
            ("", False),  # Empty version
            ("   ", False),  # Whitespace only
        ],
    )
    def test_version_validation(
        self, version: str, expected_success: bool
    ) -> None:
        """Test version field validation - we can add semver checks later, not
        needed yet (if at all)."""
        if expected_success:
            assembly = AssemblyFactory.build(version=version)
            assert assembly.version == version.strip()
        else:
            with pytest.raises(Exception):
                AssemblyFactory.build(version=version)
