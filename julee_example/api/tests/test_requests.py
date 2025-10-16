"""
Tests for API request models.

Since the request models delegate validation to domain models, these tests
focus on verifying the delegation works correctly and that the API-specific
behavior (like field copying and conversion methods) functions as expected.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from julee_example.api.requests import (
    CreateAssemblySpecificationRequest,
    CreateKnowledgeServiceQueryRequest,
)
from julee_example.domain.models import (
    AssemblySpecification,
    AssemblySpecificationStatus,
    KnowledgeServiceQuery,
)


class TestCreateAssemblySpecificationRequest:
    """Test CreateAssemblySpecificationRequest model."""

    def test_valid_request_creation(self) -> None:
        """Test that a valid request can be created."""
        request = CreateAssemblySpecificationRequest(
            name="Meeting Minutes",
            applicability="Online video meeting transcripts",
            jsonschema={
                "type": "object",
                "properties": {"title": {"type": "string"}},
            },
        )

        assert request.name == "Meeting Minutes"
        assert request.applicability == "Online video meeting transcripts"
        assert request.jsonschema == {
            "type": "object",
            "properties": {"title": {"type": "string"}},
        }
        assert request.knowledge_service_queries == {}  # Default empty dict
        assert request.version == "0.1.0"  # Default version

    def test_validation_delegation_to_domain_model(self) -> None:
        """Test that validation is properly delegated to domain model."""
        # Test that domain model validation errors are raised
        with pytest.raises(ValidationError) as err:
            CreateAssemblySpecificationRequest(
                name="",  # Invalid empty name
                applicability="Valid applicability",
                jsonschema={"type": "object"},
            )
        errors = err.value.errors()
        # Check that the error is for the 'name' field and is a value error
        assert any(
            e["loc"] == ("name",)
            and e["type"].startswith("value_error")
            and "name cannot be empty" in e["msg"]
            for e in errors
        )

        with pytest.raises(ValidationError) as err:
            CreateAssemblySpecificationRequest(
                name="Valid Name",
                applicability="Valid applicability",
                jsonschema={"invalid": "schema"},  # Missing 'type' field
            )
        errors = err.value.errors()
        # Check that the error is for the 'jsonschema' field
        assert any(
            e["loc"] == ("jsonschema",)
            and e["type"].startswith("value_error")
            and "type" in e["msg"]
            for e in errors
        )

    def test_to_domain_model_conversion(self) -> None:
        """Test conversion from request model to domain model."""
        request = CreateAssemblySpecificationRequest(
            name="Test Assembly",
            applicability="Test documents",
            jsonschema={
                "type": "object",
                "properties": {"content": {"type": "string"}},
            },
            knowledge_service_queries={"/properties/content": "query-123"},
            version="1.0.0",
        )

        domain_model = request.to_domain_model("spec-456")

        assert isinstance(domain_model, AssemblySpecification)
        assert domain_model.assembly_specification_id == "spec-456"
        assert domain_model.name == "Test Assembly"
        assert domain_model.applicability == "Test documents"
        assert domain_model.jsonschema == {
            "type": "object",
            "properties": {"content": {"type": "string"}},
        }
        assert domain_model.knowledge_service_queries == {
            "/properties/content": "query-123"
        }
        assert domain_model.version == "1.0.0"
        assert domain_model.status == AssemblySpecificationStatus.DRAFT
        assert isinstance(domain_model.created_at, datetime)
        assert isinstance(domain_model.updated_at, datetime)

    def test_field_definitions_match_domain_model(self) -> None:
        """Test that field definitions are copied from domain model."""
        request_fields = CreateAssemblySpecificationRequest.model_fields
        domain_fields = AssemblySpecification.model_fields

        # Verify shared fields have identical definitions
        shared_field_names = [
            "name",
            "applicability",
            "jsonschema",
            "knowledge_service_queries",
            "version",
        ]

        for field_name in shared_field_names:
            assert field_name in request_fields
            assert field_name in domain_fields
            # Field descriptions should match
            assert (
                request_fields[field_name].description
                == domain_fields[field_name].description
            )
            # Default values should match where applicable
            if (
                hasattr(domain_fields[field_name], "default")
                and domain_fields[field_name].default is not None
            ):
                assert (
                    request_fields[field_name].default
                    == domain_fields[field_name].default
                )


class TestCreateKnowledgeServiceQueryRequest:
    """Test CreateKnowledgeServiceQueryRequest model."""

    def test_valid_request_creation(self) -> None:
        """Test that a valid request can be created."""
        request = CreateKnowledgeServiceQueryRequest(
            name="Extract Meeting Summary",
            knowledge_service_id="anthropic-claude",
            prompt="Extract the main summary from this meeting transcript",
        )

        assert request.name == "Extract Meeting Summary"
        assert request.knowledge_service_id == "anthropic-claude"
        assert (
            request.prompt
            == "Extract the main summary from this meeting transcript"
        )
        assert request.query_metadata == {}  # Default empty dict
        assert request.assistant_prompt is None  # Default None

    def test_validation_delegation_to_domain_model(self) -> None:
        """Test that validation is properly delegated to domain model."""
        # Test that domain model validation errors are raised
        with pytest.raises(ValidationError) as err:
            CreateKnowledgeServiceQueryRequest(
                name="",  # Invalid empty name
                knowledge_service_id="valid-service",
                prompt="Valid prompt",
            )
        errors = err.value.errors()
        # Check that the error is for the 'name' field
        assert any(
            e["loc"] == ("name",)
            and e["type"].startswith("value_error")
            and "name cannot be empty" in e["msg"]
            for e in errors
        )

        with pytest.raises(ValidationError) as err:
            CreateKnowledgeServiceQueryRequest(
                name="Valid Name",
                knowledge_service_id="",  # Invalid empty service ID
                prompt="Valid prompt",
            )
        errors = err.value.errors()
        # Check that the error is for the 'knowledge_service_id' field
        assert any(
            e["loc"] == ("knowledge_service_id",)
            and e["type"].startswith("value_error")
            and "service ID cannot be empty" in e["msg"]
            for e in errors
        )

    def test_to_domain_model_conversion(self) -> None:
        """Test conversion from request model to domain model."""
        request = CreateKnowledgeServiceQueryRequest(
            name="Test Query",
            knowledge_service_id="test-service",
            prompt="Test prompt for extraction",
            query_metadata={"model": "claude-3", "temperature": 0.2},
            assistant_prompt="Please format as JSON",
        )

        domain_model = request.to_domain_model("query-456")

        assert isinstance(domain_model, KnowledgeServiceQuery)
        assert domain_model.query_id == "query-456"
        assert domain_model.name == "Test Query"
        assert domain_model.knowledge_service_id == "test-service"
        assert domain_model.prompt == "Test prompt for extraction"
        assert domain_model.query_metadata == {
            "model": "claude-3",
            "temperature": 0.2,
        }
        assert domain_model.assistant_prompt == "Please format as JSON"
        assert isinstance(domain_model.created_at, datetime)
        assert isinstance(domain_model.updated_at, datetime)
        assert domain_model.created_at == domain_model.updated_at

    def test_field_definitions_match_domain_model(self) -> None:
        """Test that field definitions are copied from domain model."""
        request_fields = CreateKnowledgeServiceQueryRequest.model_fields
        domain_fields = KnowledgeServiceQuery.model_fields

        # Verify shared fields have identical descriptions
        shared_field_names = [
            "name",
            "knowledge_service_id",
            "prompt",
            "query_metadata",
            "assistant_prompt",
        ]

        for field_name in shared_field_names:
            assert field_name in request_fields
            assert field_name in domain_fields
            # Field descriptions should match
            assert (
                request_fields[field_name].description
                == domain_fields[field_name].description
            )
            # Default values should match where applicable
            if (
                hasattr(domain_fields[field_name], "default")
                and domain_fields[field_name].default is not None
            ):
                assert (
                    request_fields[field_name].default
                    == domain_fields[field_name].default
                )
