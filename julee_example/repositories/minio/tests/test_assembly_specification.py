"""
Tests for MinioAssemblySpecificationRepository implementation.

This module provides comprehensive tests for the Minio-based assembly
specification repository implementation, using the fake client to avoid
external dependencies during testing.
"""

import pytest
from datetime import datetime, timezone


from julee_example.domain.models.assembly_specification import (
    AssemblySpecification,
    AssemblySpecificationStatus,
)
from julee_example.repositories.minio.assembly_specification import (
    MinioAssemblySpecificationRepository,
)
from .fake_client import FakeMinioClient


@pytest.fixture
def fake_client() -> FakeMinioClient:
    """Create a fresh fake Minio client for each test."""
    return FakeMinioClient()


@pytest.fixture
def specification_repo(
    fake_client: FakeMinioClient,
) -> MinioAssemblySpecificationRepository:
    """Create assembly specification repository with fake client."""
    return MinioAssemblySpecificationRepository(fake_client)


@pytest.fixture
def sample_specification() -> AssemblySpecification:
    """Create a sample assembly specification for testing."""
    return AssemblySpecification(
        assembly_specification_id="spec-123",
        name="Meeting Minutes",
        applicability="Corporate meeting recordings and transcripts",
        jsonschema={
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "attendees": {"type": "array", "items": {"type": "string"}},
                "action_items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "description": {"type": "string"},
                            "assignee": {"type": "string"},
                            "due_date": {"type": "string"},
                        },
                    },
                },
            },
            "required": ["title"],
        },
        status=AssemblySpecificationStatus.ACTIVE,
        knowledge_service_queries={
            "/properties/title": "extract-meeting-title",
            "/properties/attendees": "extract-attendees",
            "/properties/action_items": "extract-action-items",
        },
        version="1.0.0",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def inactive_specification() -> AssemblySpecification:
    """Create an inactive assembly specification for testing."""
    return AssemblySpecification(
        assembly_specification_id="spec-inactive-456",
        name="Inactive Spec",
        applicability="This is an inactive specification",
        jsonschema={
            "type": "object",
            "properties": {"test": {"type": "string"}},
        },
        status=AssemblySpecificationStatus.INACTIVE,
        version="1.0.0",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


class TestMinioAssemblySpecificationRepositoryBasicOperations:
    """Test basic CRUD operations on assembly specifications."""

    @pytest.mark.asyncio
    async def test_save_and_get_specification(
        self,
        specification_repo: MinioAssemblySpecificationRepository,
        sample_specification: AssemblySpecification,
    ) -> None:
        """Test saving and retrieving an assembly specification."""
        # Save specification
        await specification_repo.save(sample_specification)

        # Retrieve specification
        retrieved = await specification_repo.get(
            sample_specification.assembly_specification_id
        )

        assert retrieved is not None
        assert (
            retrieved.assembly_specification_id
            == sample_specification.assembly_specification_id
        )
        assert retrieved.name == sample_specification.name
        assert retrieved.applicability == sample_specification.applicability
        assert retrieved.jsonschema == sample_specification.jsonschema
        assert retrieved.status == sample_specification.status
        assert (
            retrieved.knowledge_service_queries
            == sample_specification.knowledge_service_queries
        )
        assert retrieved.version == sample_specification.version

    @pytest.mark.asyncio
    async def test_get_nonexistent_specification(
        self, specification_repo: MinioAssemblySpecificationRepository
    ) -> None:
        """Test retrieving a non-existent specification returns None."""
        result = await specification_repo.get("nonexistent-spec")
        assert result is None

    @pytest.mark.asyncio
    async def test_generate_id(
        self, specification_repo: MinioAssemblySpecificationRepository
    ) -> None:
        """Test generating unique specification IDs."""
        id1 = await specification_repo.generate_id()
        id2 = await specification_repo.generate_id()

        assert isinstance(id1, str)
        assert isinstance(id2, str)
        assert id1 != id2
        assert len(id1) > 0
        assert len(id2) > 0

    @pytest.mark.asyncio
    async def test_save_updates_timestamp(
        self,
        specification_repo: MinioAssemblySpecificationRepository,
        sample_specification: AssemblySpecification,
    ) -> None:
        """Test that save operations update the updated_at timestamp."""
        original_updated_at = sample_specification.updated_at

        # Save specification
        await specification_repo.save(sample_specification)

        # Retrieve and check timestamp was updated
        retrieved = await specification_repo.get(
            sample_specification.assembly_specification_id
        )
        assert retrieved is not None
        assert retrieved.updated_at is not None
        assert original_updated_at is not None
        assert retrieved.updated_at > original_updated_at


class TestMinioAssemblySpecificationRepositoryStatusManagement:
    """Test specification status management."""

    @pytest.mark.asyncio
    async def test_update_specification_status(
        self,
        specification_repo: MinioAssemblySpecificationRepository,
        sample_specification: AssemblySpecification,
    ) -> None:
        """Test updating specification status."""
        # Save initial specification
        await specification_repo.save(sample_specification)

        # Update status to draft
        sample_specification.status = AssemblySpecificationStatus.DRAFT
        await specification_repo.save(sample_specification)

        # Verify update
        retrieved = await specification_repo.get(
            sample_specification.assembly_specification_id
        )
        assert retrieved is not None
        assert retrieved.status == AssemblySpecificationStatus.DRAFT

        # Update to deprecated
        sample_specification.status = AssemblySpecificationStatus.DEPRECATED
        await specification_repo.save(sample_specification)

        # Verify final state
        retrieved = await specification_repo.get(
            sample_specification.assembly_specification_id
        )
        assert retrieved is not None
        assert retrieved.status == AssemblySpecificationStatus.DEPRECATED


class TestMinioAssemblySpecificationRepositoryComplexScenarios:
    """Test complex scenarios and edge cases."""

    @pytest.mark.asyncio
    async def test_complete_specification_lifecycle(
        self, specification_repo: MinioAssemblySpecificationRepository
    ) -> None:
        """Test complete specification lifecycle from creation to
        deprecation."""
        # Generate new specification
        spec_id = await specification_repo.generate_id()

        # Create and save new specification
        specification = AssemblySpecification(
            assembly_specification_id=spec_id,
            name="Test Lifecycle Spec",
            applicability="Test specification for lifecycle testing",
            jsonschema={
                "type": "object",
                "properties": {"test_field": {"type": "string"}},
                "required": ["test_field"],
            },
            status=AssemblySpecificationStatus.DRAFT,
            knowledge_service_queries={
                "/properties/test_field": "test-query"
            },
            version="0.1.0",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        await specification_repo.save(specification)

        # Activate specification
        specification.status = AssemblySpecificationStatus.ACTIVE
        specification.version = "1.0.0"
        await specification_repo.save(specification)

        # Deprecate specification
        specification.status = AssemblySpecificationStatus.DEPRECATED
        await specification_repo.save(specification)

        # Verify can still be retrieved directly
        retrieved = await specification_repo.get(spec_id)
        assert retrieved is not None
        assert retrieved.status == AssemblySpecificationStatus.DEPRECATED

    @pytest.mark.asyncio
    async def test_complex_json_schema_handling(
        self, specification_repo: MinioAssemblySpecificationRepository
    ) -> None:
        """Test handling of complex JSON schemas."""
        complex_schema = {
            "type": "object",
            "properties": {
                "metadata": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "date": {"type": "string", "format": "date"},
                        "participants": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "role": {"type": "string"},
                                    "email": {
                                        "type": "string",
                                        "format": "email",
                                    },
                                },
                                "required": ["name"],
                            },
                        },
                    },
                    "required": ["title", "date"],
                },
                "content": {
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string"},
                        "action_items": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "task": {"type": "string"},
                                    "assignee": {"type": "string"},
                                    "due_date": {
                                        "type": "string",
                                        "format": "date",
                                    },
                                    "priority": {
                                        "type": "string",
                                        "enum": ["low", "medium", "high"],
                                    },
                                },
                                "required": ["task", "assignee"],
                            },
                        },
                        "decisions": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                },
                "attachments": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "filename": {"type": "string"},
                            "url": {"type": "string", "format": "uri"},
                        },
                    },
                },
            },
            "required": ["metadata", "content"],
        }

        complex_queries = {
            "/properties/metadata/properties/title": "extract-title",
            "/properties/metadata/properties/participants": (
                "extract-participants"
            ),
            "/properties/content/properties/action_items": (
                "extract-action-items"
            ),
            "/properties/content/properties/summary": "extract-summary",
        }

        specification = AssemblySpecification(
            assembly_specification_id="complex-spec",
            name="Complex Meeting Assembly",
            applicability="Detailed meeting documentation with full metadata",
            jsonschema=complex_schema,
            status=AssemblySpecificationStatus.ACTIVE,
            knowledge_service_queries=complex_queries,
            version="2.0.0",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        # Save and retrieve
        await specification_repo.save(specification)
        retrieved = await specification_repo.get("complex-spec")

        assert retrieved is not None
        assert retrieved.jsonschema == complex_schema
        assert retrieved.knowledge_service_queries == complex_queries
        assert len(retrieved.knowledge_service_queries) == 4

    @pytest.mark.asyncio
    async def test_specification_roundtrip_with_unicode(
        self, specification_repo: MinioAssemblySpecificationRepository
    ) -> None:
        """Test specification with unicode content survives roundtrip."""
        unicode_specification = AssemblySpecification(
            assembly_specification_id="unicode-spec",
            name="Spécification avec caractères spéciaux",
            applicability="Документы с unicode содержанием и émojis 🚀📝",
            jsonschema={
                "type": "object",
                "properties": {
                    "título": {"type": "string"},
                    "descripción": {"type": "string"},
                    "метаданные": {
                        "type": "object",
                        "properties": {"автор": {"type": "string"}},
                    },
                },
            },
            status=AssemblySpecificationStatus.ACTIVE,
            knowledge_service_queries={
                "/properties/título": "query-título",
                "/properties/метаданные": "query-metadata",
            },
            version="1.0.0",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        # Save and retrieve
        await specification_repo.save(unicode_specification)
        retrieved = await specification_repo.get("unicode-spec")

        assert retrieved is not None
        assert retrieved.name == "Spécification avec caractères spéciaux"
        assert "unicode содержанием и émojis 🚀📝" in retrieved.applicability
        assert "título" in retrieved.jsonschema["properties"]
        assert "метаданные" in retrieved.jsonschema["properties"]
        assert "/properties/título" in retrieved.knowledge_service_queries
