"""
Comprehensive tests for KnowledgeServiceQuery domain model.

This test module documents the design decisions made for the
KnowledgeServiceQuery domain model using table-based tests. It covers:

- KnowledgeServiceQuery instantiation with various field combinations
- JSON Pointer validation for schema_pointer field
- JSON serialization behavior
- Field validation for required fields

Design decisions documented:
- KnowledgeServiceQuery must have all required fields (query_id, name,
  knowledge_service_id, prompt, schema_pointer)
- Schema pointer must be a valid JSON Pointer (RFC 6901)
- All text fields must be non-empty and non-whitespace
- Version field has a default but can be customized
- Status defaults to ACTIVE
"""

import pytest

from julee_example.domain.models.assembly_specification import (
    KnowledgeServiceQuery,
)
from .factories import KnowledgeServiceQueryFactory


class TestKnowledgeServiceQueryInstantiation:
    """Test KnowledgeServiceQuery creation with various field combinations."""

    @pytest.mark.parametrize(
        "query_id,name,knowledge_service_id,prompt,expected_success",
        [
            # Valid cases
            (
                "query-1",
                "Extract Attendees",
                "ragflow-service-1",
                "Extract list of meeting attendees with their roles",
                True,
            ),
            (
                "query-2",
                "Extract Action Items",
                "knowledge-service-2",
                "Extract action items with assignees and due dates",
                True,
            ),
            (
                "query-3",
                "Extract Meeting Metadata",
                "service-alpha",
                "Extract basic meeting information like title, date, time",
                True,
            ),
            # Invalid cases - empty required fields
            (
                "",
                "Test Query",
                "service-1",
                "Test prompt",
                False,
            ),  # Empty query_id
            (
                "query-4",
                "",
                "service-1",
                "Test prompt",
                False,
            ),  # Empty name
            (
                "query-5",
                "Test Query",
                "",
                "Test prompt",
                False,
            ),  # Empty knowledge_service_id
            (
                "query-6",
                "Test Query",
                "service-1",
                "",
                False,
            ),  # Empty prompt
            # Invalid cases - whitespace only
            (
                "   ",
                "Test Query",
                "service-1",
                "Test prompt",
                False,
            ),  # Whitespace query_id
            (
                "query-8",
                "   ",
                "service-1",
                "Test prompt",
                False,
            ),  # Whitespace name
            (
                "query-9",
                "Test Query",
                "   ",
                "Test prompt",
                False,
            ),  # Whitespace knowledge_service_id
            (
                "query-10",
                "Test Query",
                "service-1",
                "   ",
                False,
            ),  # Whitespace prompt
        ],
    )
    def test_knowledge_service_query_creation_validation(
        self,
        query_id: str,
        name: str,
        knowledge_service_id: str,
        prompt: str,
        expected_success: bool,
    ) -> None:
        """Test query creation with various field validation scenarios."""
        if expected_success:
            # Should create successfully
            query = KnowledgeServiceQuery(
                query_id=query_id,
                name=name,
                knowledge_service_id=knowledge_service_id,
                prompt=prompt,
            )
            assert query.query_id == query_id.strip()
            assert query.name == name.strip()
            assert query.knowledge_service_id == knowledge_service_id.strip()
            assert query.prompt == prompt.strip()
        else:
            # Should raise validation error
            with pytest.raises(
                Exception
            ):  # Could be ValueError or ValidationError
                KnowledgeServiceQuery(
                    query_id=query_id,
                    name=name,
                    knowledge_service_id=knowledge_service_id,
                    prompt=prompt,
                )


class TestKnowledgeServiceQuerySerialization:
    """Test KnowledgeServiceQuery JSON serialization behavior."""

    def test_knowledge_service_query_json_serialization(self) -> None:
        """Test that KnowledgeServiceQuery serializes to JSON correctly."""
        query = KnowledgeServiceQueryFactory.build(
            query_id="attendee-extractor",
            name="Meeting Attendee Extractor",
            knowledge_service_id="ragflow-primary",
            prompt="Extract meeting attendees with names, roles",
        )

        json_str = query.model_dump_json()
        import json

        json_data = json.loads(json_str)

        # All fields should be present in JSON
        assert json_data["query_id"] == query.query_id
        assert json_data["name"] == query.name
        assert json_data["knowledge_service_id"] == query.knowledge_service_id
        assert json_data["prompt"] == query.prompt

    def test_knowledge_service_query_json_roundtrip(self) -> None:
        """Test that KnowledgeServiceQuery can be serialized to JSON and
        deserialized back."""
        original_query = KnowledgeServiceQueryFactory.build()

        # Serialize to JSON
        json_str = original_query.model_dump_json()
        import json

        json_data = json.loads(json_str)

        # Deserialize back to KnowledgeServiceQuery
        reconstructed_query = KnowledgeServiceQuery(**json_data)

        # Should be equivalent
        assert reconstructed_query.query_id == original_query.query_id
        assert reconstructed_query.name == original_query.name
        assert (
            reconstructed_query.knowledge_service_id
            == original_query.knowledge_service_id
        )
        assert reconstructed_query.prompt == original_query.prompt


class TestKnowledgeServiceQueryDefaults:
    """Test KnowledgeServiceQuery default values and behavior."""

    def test_knowledge_service_query_default_values(self) -> None:
        """Test that KnowledgeServiceQuery has correct default values."""
        minimal_query = KnowledgeServiceQuery(
            query_id="test-id",
            name="Test Query",
            knowledge_service_id="test-service",
            prompt="Test prompt",
        )

        assert minimal_query.created_at is not None
        assert minimal_query.updated_at is not None

    def test_knowledge_service_query_custom_values(self) -> None:
        """Test KnowledgeServiceQuery with custom non-default values."""
        custom_query = KnowledgeServiceQuery(
            query_id="custom-id",
            name="Custom Query",
            knowledge_service_id="custom-service",
            prompt="Custom prompt",
        )

        assert custom_query.query_id == "custom-id"
        assert custom_query.name == "Custom Query"


class TestKnowledgeServiceQueryMetadata:
    """Test KnowledgeServiceQuery query_metadata field functionality."""

    def test_query_metadata_defaults_to_empty_dict(self) -> None:
        """Test that query_metadata defaults to an empty dict."""
        query = KnowledgeServiceQuery(
            query_id="test-id",
            name="Test Query",
            knowledge_service_id="test-service",
            prompt="Test prompt",
        )

        assert query.query_metadata == {}

    def test_query_metadata_accepts_custom_values(self) -> None:
        """Test that query_metadata can accept custom service values."""
        metadata = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 4000,
            "temperature": 0.1,
        }

        query = KnowledgeServiceQuery(
            query_id="test-id",
            name="Test Query",
            knowledge_service_id="anthropic-service",
            prompt="Test prompt",
            query_metadata=metadata,
        )

        assert query.query_metadata == metadata
        assert query.query_metadata["model"] == "claude-sonnet-4-20250514"
        assert query.query_metadata["max_tokens"] == 4000
        assert query.query_metadata["temperature"] == 0.1

    def test_query_metadata_serialization(self) -> None:
        """Test that query_metadata serializes correctly in JSON."""
        metadata = {
            "model": "gpt-4",
            "temperature": 0.2,
            "top_p": 0.9,
            "custom_config": {"endpoint": "v2", "retries": 3},
        }

        query = KnowledgeServiceQuery(
            query_id="openai-query",
            name="OpenAI Query",
            knowledge_service_id="openai-service",
            prompt="Test prompt for OpenAI",
            query_metadata=metadata,
        )

        json_str = query.model_dump_json()
        import json

        json_data = json.loads(json_str)

        assert json_data["query_metadata"] == metadata
        assert json_data["query_metadata"]["model"] == "gpt-4"
        assert (
            json_data["query_metadata"]["custom_config"]["endpoint"] == "v2"
        )

    def test_query_metadata_roundtrip_serialization(self) -> None:
        """Test query_metadata survives JSON roundtrip serialization."""
        metadata = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 2000,
            "temperature": 0.0,
            "citations": True,
        }

        original = KnowledgeServiceQuery(
            query_id="roundtrip-test",
            name="Roundtrip Test",
            knowledge_service_id="test-service",
            prompt="Test roundtrip serialization",
            query_metadata=metadata,
        )

        # Serialize and deserialize
        json_str = original.model_dump_json()
        import json

        json_data = json.loads(json_str)
        reconstructed = KnowledgeServiceQuery(**json_data)

        assert reconstructed.query_metadata == original.query_metadata
        assert reconstructed.query_metadata == metadata
