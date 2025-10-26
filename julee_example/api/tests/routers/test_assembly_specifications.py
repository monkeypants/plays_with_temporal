"""
Tests for the assembly specifications API router.

This module provides comprehensive tests for the assembly specifications
endpoints, focusing on testing the router behavior with proper dependency
injection and mocking patterns.
"""

import pytest
from typing import Generator
from fastapi.testclient import TestClient
from fastapi import FastAPI
from fastapi_pagination import add_pagination

from julee_example.api.routers.assembly_specifications import router
from julee_example.api.dependencies import (
    get_assembly_specification_repository,
)
from julee_example.domain.models import (
    AssemblySpecification,
    AssemblySpecificationStatus,
)
from julee_example.repositories.memory import (
    MemoryAssemblySpecificationRepository,
)


@pytest.fixture
def memory_repo() -> MemoryAssemblySpecificationRepository:
    """Create a memory assembly specification repository for testing."""
    return MemoryAssemblySpecificationRepository()


@pytest.fixture
def app_with_router(
    memory_repo: MemoryAssemblySpecificationRepository,
) -> FastAPI:
    """Create a FastAPI app with just the assembly specifications router."""
    app = FastAPI()

    # Override the dependency with our memory repository
    app.dependency_overrides[get_assembly_specification_repository] = (
        lambda: memory_repo
    )

    # Add pagination support (required for the paginate function)
    add_pagination(app)

    # Include the router with the prefix
    app.include_router(
        router,
        prefix="/assembly_specifications",
        tags=["Assembly Specifications"],
    )

    return app


@pytest.fixture
def client(
    app_with_router: FastAPI,
) -> Generator[TestClient, None, None]:
    """Create a test client with the router app."""
    with TestClient(app_with_router) as test_client:
        yield test_client


@pytest.fixture
def sample_assembly_specification() -> AssemblySpecification:
    """Create a sample assembly specification for testing."""
    return AssemblySpecification(
        assembly_specification_id="test-spec-123",
        name="Meeting Minutes",
        applicability="Online video meeting transcripts",
        jsonschema={
            "type": "object",
            "properties": {
                "attendees": {"type": "array", "items": {"type": "string"}},
                "summary": {"type": "string"},
            },
        },
        knowledge_service_queries={
            "/properties/attendees": "query-123",
            "/properties/summary": "query-456",
        },
        status=AssemblySpecificationStatus.ACTIVE,
        version="1.0.0",
    )


class TestGetAssemblySpecifications:
    """Test the GET / endpoint for assembly specifications."""

    def test_get_assembly_specifications_empty_list(
        self,
        client: TestClient,
        memory_repo: MemoryAssemblySpecificationRepository,
    ) -> None:
        """Test getting specifications when repository is empty."""
        response = client.get("/assembly_specifications/")

        assert response.status_code == 200
        data = response.json()

        # Verify pagination structure
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert "pages" in data

        # Should return empty list when repository is empty
        assert data["items"] == []
        assert data["total"] == 0

    def test_get_assembly_specifications_with_pagination_params(
        self,
        client: TestClient,
        memory_repo: MemoryAssemblySpecificationRepository,
    ) -> None:
        """Test getting specifications with pagination parameters."""
        response = client.get("/assembly_specifications/?page=2&size=10")

        assert response.status_code == 200
        data = response.json()

        # Verify pagination parameters are handled
        assert "items" in data
        assert "page" in data
        assert "size" in data

        # Even with pagination params, should work with empty repository
        assert data["items"] == []

    async def test_get_assembly_specifications_with_data(
        self,
        client: TestClient,
        memory_repo: MemoryAssemblySpecificationRepository,
        sample_assembly_specification: AssemblySpecification,
    ) -> None:
        """Test getting specifications when repository contains data."""
        # Create a second specification for testing
        spec2 = AssemblySpecification(
            assembly_specification_id="test-spec-456",
            name="Project Report",
            applicability="Project documentation and status updates",
            jsonschema={
                "type": "object",
                "properties": {
                    "project_name": {"type": "string"},
                    "status": {"type": "string"},
                },
            },
            knowledge_service_queries={
                "/properties/project_name": "query-789",
                "/properties/status": "query-101",
            },
        )

        # Save specifications to the repository
        await memory_repo.save(sample_assembly_specification)
        await memory_repo.save(spec2)

        response = client.get("/assembly_specifications/")

        assert response.status_code == 200
        data = response.json()

        # Verify pagination structure
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data

        # Should return both specifications
        assert data["total"] == 2
        assert len(data["items"]) == 2

        # Verify the specifications are returned (order may vary)
        returned_ids = {
            item["assembly_specification_id"] for item in data["items"]
        }
        expected_ids = {
            sample_assembly_specification.assembly_specification_id,
            spec2.assembly_specification_id,
        }
        assert returned_ids == expected_ids

        # Verify specification data structure
        for item in data["items"]:
            assert "assembly_specification_id" in item
            assert "name" in item
            assert "applicability" in item
            assert "jsonschema" in item
            assert "status" in item

    async def test_get_assembly_specifications_pagination(
        self,
        client: TestClient,
        memory_repo: MemoryAssemblySpecificationRepository,
    ) -> None:
        """Test pagination with multiple specifications."""
        # Create several specifications
        specifications = []
        for i in range(5):
            spec = AssemblySpecification(
                assembly_specification_id=f"spec-{i:03d}",
                name=f"Specification {i}",
                applicability=f"Test applicability {i}",
                jsonschema={"type": "object", "properties": {}},
            )
            specifications.append(spec)
            await memory_repo.save(spec)

        # Test first page with size 2
        response = client.get("/assembly_specifications/?page=1&size=2")
        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 5
        assert data["page"] == 1
        assert data["size"] == 2
        assert len(data["items"]) == 2

        # Test second page
        response = client.get("/assembly_specifications/?page=2&size=2")
        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 5
        assert data["page"] == 2
        assert data["size"] == 2
        assert len(data["items"]) == 2


class TestGetAssemblySpecification:
    """Test the GET /{id} endpoint for getting a specific specification."""

    async def test_get_assembly_specification_success(
        self,
        client: TestClient,
        memory_repo: MemoryAssemblySpecificationRepository,
        sample_assembly_specification: AssemblySpecification,
    ) -> None:
        """Test successfully getting a specific assembly specification."""
        # Save the specification to the repository
        await memory_repo.save(sample_assembly_specification)

        response = client.get(
            f"/assembly_specifications/{sample_assembly_specification.assembly_specification_id}"
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure and content
        assert (
            data["assembly_specification_id"]
            == sample_assembly_specification.assembly_specification_id
        )
        assert data["name"] == sample_assembly_specification.name
        assert (
            data["applicability"]
            == sample_assembly_specification.applicability
        )
        assert data["jsonschema"] == sample_assembly_specification.jsonschema
        assert (
            data["knowledge_service_queries"]
            == sample_assembly_specification.knowledge_service_queries
        )
        assert data["status"] == sample_assembly_specification.status.value
        assert data["version"] == sample_assembly_specification.version
        assert "created_at" in data
        assert "updated_at" in data

    def test_get_assembly_specification_not_found(
        self,
        client: TestClient,
        memory_repo: MemoryAssemblySpecificationRepository,
    ) -> None:
        """Test getting a non-existent assembly specification."""
        nonexistent_id = "nonexistent-spec-123"
        response = client.get(f"/assembly_specifications/{nonexistent_id}")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
        assert nonexistent_id in data["detail"]

    async def test_get_assembly_specification_with_complex_schema(
        self,
        client: TestClient,
        memory_repo: MemoryAssemblySpecificationRepository,
    ) -> None:
        """Test getting specification with complex JSON schema."""
        complex_spec = AssemblySpecification(
            assembly_specification_id="complex-spec-123",
            name="Complex Meeting Minutes",
            applicability="Detailed meeting transcripts with metadata",
            jsonschema={
                "type": "object",
                "properties": {
                    "metadata": {
                        "type": "object",
                        "properties": {
                            "date": {"type": "string", "format": "date"},
                            "duration": {"type": "integer"},
                        },
                    },
                    "attendees": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "role": {"type": "string"},
                            },
                        },
                    },
                    "agenda": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["metadata", "attendees"],
            },
            knowledge_service_queries={
                "/properties/metadata/properties/date": "date-query",
                "/properties/attendees": "attendees-query",
                "/properties/agenda": "agenda-query",
            },
        )

        await memory_repo.save(complex_spec)

        response = client.get(
            f"/assembly_specifications/{complex_spec.assembly_specification_id}"
        )

        assert response.status_code == 200
        data = response.json()

        # Verify complex schema is preserved
        assert data["jsonschema"]["properties"]["metadata"]["properties"]
        assert data["jsonschema"]["required"] == ["metadata", "attendees"]
        assert len(data["knowledge_service_queries"]) == 3

    def test_get_assembly_specification_invalid_id_format(
        self,
        client: TestClient,
        memory_repo: MemoryAssemblySpecificationRepository,
    ) -> None:
        """Test getting specification with various ID formats."""
        # Test with empty string (should be handled by FastAPI routing)
        response = client.get("/assembly_specifications/")
        assert response.status_code == 200  # This hits the list endpoint

        # Test with special characters
        response = client.get("/assembly_specifications/test@spec#123")
        assert response.status_code == 404  # Not found is expected

    async def test_get_assembly_specification_different_statuses(
        self,
        client: TestClient,
        memory_repo: MemoryAssemblySpecificationRepository,
    ) -> None:
        """Test getting specifications with different status values."""
        for status in AssemblySpecificationStatus:
            spec = AssemblySpecification(
                assembly_specification_id=f"spec-{status.value}",
                name=f"Spec {status.value}",
                applicability="Test applicability",
                jsonschema={"type": "object", "properties": {}},
                status=status,
            )
            await memory_repo.save(spec)

            response = client.get(
                f"/assembly_specifications/{spec.assembly_specification_id}"
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == status.value


class TestCreateAssemblySpecification:
    """Test the POST / endpoint for creating assembly specifications."""

    def test_create_assembly_specification_success(
        self,
        client: TestClient,
        memory_repo: MemoryAssemblySpecificationRepository,
    ) -> None:
        """Test successful creation of an assembly specification."""
        request_data = {
            "name": "Meeting Minutes Template",
            "applicability": "Online video meeting transcripts",
            "jsonschema": {
                "type": "object",
                "properties": {
                    "attendees": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "summary": {"type": "string"},
                    "action_items": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
            },
            "knowledge_service_queries": {
                "/properties/attendees": "attendee-extractor-query",
                "/properties/summary": "summary-extractor-query",
            },
            "version": "1.0.0",
        }

        response = client.post("/assembly_specifications/", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "assembly_specification_id" in data
        assert data["name"] == request_data["name"]
        assert data["applicability"] == request_data["applicability"]
        assert data["jsonschema"] == request_data["jsonschema"]
        assert (
            data["knowledge_service_queries"]
            == request_data["knowledge_service_queries"]
        )
        assert data["version"] == request_data["version"]
        assert data["status"] == "draft"  # Default status
        assert "created_at" in data
        assert "updated_at" in data

        # Verify the specification was saved to repository
        spec_id = data["assembly_specification_id"]
        assert spec_id is not None
        assert spec_id != ""

    async def test_create_assembly_specification_persisted(
        self,
        client: TestClient,
        memory_repo: MemoryAssemblySpecificationRepository,
    ) -> None:
        """Test that created specification is persisted in repository."""
        request_data = {
            "name": "Project Status Report",
            "applicability": "Weekly project status documents",
            "jsonschema": {
                "type": "object",
                "properties": {
                    "project_name": {"type": "string"},
                    "status": {"type": "string"},
                    "milestones": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
            },
            "knowledge_service_queries": {
                "/properties/project_name": "project-name-query",
                "/properties/status": "status-query",
            },
        }

        response = client.post("/assembly_specifications/", json=request_data)
        assert response.status_code == 200

        spec_id = response.json()["assembly_specification_id"]

        # Verify specification was saved by retrieving it
        saved_spec = await memory_repo.get(spec_id)
        assert saved_spec is not None
        assert saved_spec.name == request_data["name"]
        assert saved_spec.applicability == request_data["applicability"]
        assert saved_spec.jsonschema == request_data["jsonschema"]
        assert (
            saved_spec.knowledge_service_queries
            == request_data["knowledge_service_queries"]
        )

    def test_create_assembly_specification_minimal_fields(
        self,
        client: TestClient,
        memory_repo: MemoryAssemblySpecificationRepository,
    ) -> None:
        """Test creation with only required fields."""
        request_data = {
            "name": "Minimal Spec",
            "applicability": "Test applicability",
            "jsonschema": {"type": "object", "properties": {}},
        }

        response = client.post("/assembly_specifications/", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == request_data["name"]
        assert data["applicability"] == request_data["applicability"]
        assert data["jsonschema"] == request_data["jsonschema"]
        assert data["knowledge_service_queries"] == {}
        assert data["version"] == "0.1.0"  # Default version
        assert data["status"] == "draft"  # Default status

    def test_create_assembly_specification_validation_errors(
        self,
        client: TestClient,
        memory_repo: MemoryAssemblySpecificationRepository,
    ) -> None:
        """Test validation error handling."""
        # Test empty name
        request_data = {
            "name": "",
            "applicability": "Test applicability",
            "jsonschema": {"type": "object", "properties": {}},
        }

        response = client.post("/assembly_specifications/", json=request_data)
        assert response.status_code == 422

        # Test empty applicability
        request_data = {
            "name": "Test Spec",
            "applicability": "",
            "jsonschema": {"type": "object", "properties": {}},
        }

        response = client.post("/assembly_specifications/", json=request_data)
        assert response.status_code == 422

        # Test invalid JSON schema
        request_data = {
            "name": "Test Spec",
            "applicability": "Test applicability",
            "jsonschema": {
                "invalid": "schema"
            },  # Invalid JSON schema: contains an unrecognized keyword
        }

        response = client.post("/assembly_specifications/", json=request_data)
        assert response.status_code == 422

    def test_create_assembly_specification_missing_required_fields(
        self,
        client: TestClient,
        memory_repo: MemoryAssemblySpecificationRepository,
    ) -> None:
        """Test handling of missing required fields."""
        # Missing name
        request_data = {
            "applicability": "Test applicability",
            "jsonschema": {"type": "object", "properties": {}},
        }

        response = client.post("/assembly_specifications/", json=request_data)
        assert response.status_code == 422

        # Missing applicability
        request_data = {
            "name": "Test Spec",
            "jsonschema": {"type": "object", "properties": {}},
        }

        response = client.post("/assembly_specifications/", json=request_data)
        assert response.status_code == 422

        # Missing jsonschema
        request_data = {
            "name": "Test Spec",
            "applicability": "Test applicability",
        }

        response = client.post("/assembly_specifications/", json=request_data)
        assert response.status_code == 422

    def test_create_assembly_specification_invalid_json_pointers(
        self,
        client: TestClient,
        memory_repo: MemoryAssemblySpecificationRepository,
    ) -> None:
        """Test validation of JSON pointer paths in knowledge queries."""
        # Invalid JSON pointer (doesn't exist in schema)
        request_data = {
            "name": "Test Spec",
            "applicability": "Test applicability",
            "jsonschema": {
                "type": "object",
                "properties": {"summary": {"type": "string"}},
            },
            "knowledge_service_queries": {
                "/properties/nonexistent": "some-query-id",  # Path not found
            },
        }

        response = client.post("/assembly_specifications/", json=request_data)
        assert response.status_code == 422

        # Invalid JSON pointer format
        request_data = {
            "name": "Test Spec",
            "applicability": "Test applicability",
            "jsonschema": {
                "type": "object",
                "properties": {"summary": {"type": "string"}},
            },
            "knowledge_service_queries": {
                "invalid-pointer": "some-query-id",  # Invalid format
            },
        }

        response = client.post("/assembly_specifications/", json=request_data)
        assert response.status_code == 422

    def test_create_assembly_specification_complex_schema(
        self,
        client: TestClient,
        memory_repo: MemoryAssemblySpecificationRepository,
    ) -> None:
        """Test creation with complex JSON schema and query mappings."""
        request_data = {
            "name": "Complex Meeting Minutes",
            "applicability": "Detailed enterprise meeting transcripts",
            "jsonschema": {
                "type": "object",
                "properties": {
                    "metadata": {
                        "type": "object",
                        "properties": {
                            "meeting_date": {
                                "type": "string",
                                "format": "date",
                            },
                            "duration_minutes": {"type": "integer"},
                            "location": {"type": "string"},
                        },
                        "required": ["meeting_date"],
                    },
                    "attendees": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "role": {"type": "string"},
                                "department": {"type": "string"},
                            },
                            "required": ["name"],
                        },
                    },
                    "agenda_items": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "decisions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "description": {"type": "string"},
                                "owner": {"type": "string"},
                                "due_date": {
                                    "type": "string",
                                    "format": "date",
                                },
                            },
                        },
                    },
                },
                "required": ["metadata", "attendees"],
            },
            "knowledge_service_queries": {
                "/properties/metadata/properties/meeting_date": (
                    "date-extractor"
                ),
                "/properties/metadata/properties/location": (
                    "location-extractor"
                ),
                "/properties/attendees": "attendee-extractor",
                "/properties/agenda_items": "agenda-extractor",
                "/properties/decisions": "decision-extractor",
            },
            "version": "2.1.0",
        }

        response = client.post("/assembly_specifications/", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # Verify complex schema is preserved
        assert data["jsonschema"]["properties"]["metadata"]["properties"]
        assert data["jsonschema"]["required"] == ["metadata", "attendees"]
        assert len(data["knowledge_service_queries"]) == 5
        assert data["version"] == "2.1.0"

    def test_post_and_get_integration(
        self,
        client: TestClient,
        memory_repo: MemoryAssemblySpecificationRepository,
    ) -> None:
        """Test that POST and GET endpoints work together."""
        # Create a specification via POST
        request_data = {
            "name": "Integration Test Specification",
            "applicability": "Test integration between endpoints",
            "jsonschema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                },
            },
            "knowledge_service_queries": {
                "/properties/title": "title-query",
                "/properties/content": "content-query",
            },
        }

        post_response = client.post(
            "/assembly_specifications/", json=request_data
        )
        assert post_response.status_code == 200
        created_spec = post_response.json()

        # Verify the specification appears in GET list response
        list_response = client.get("/assembly_specifications/")
        assert list_response.status_code == 200
        list_data = list_response.json()

        # Should find our created specification in the list
        assert list_data["total"] == 1
        assert len(list_data["items"]) == 1

        returned_spec = list_data["items"][0]
        assert (
            returned_spec["assembly_specification_id"]
            == created_spec["assembly_specification_id"]
        )
        assert returned_spec["name"] == request_data["name"]

        # Verify the specification can be retrieved by ID
        spec_id = created_spec["assembly_specification_id"]
        get_response = client.get(f"/assembly_specifications/{spec_id}")
        assert get_response.status_code == 200
        retrieved_spec = get_response.json()

        assert (
            retrieved_spec["assembly_specification_id"]
            == created_spec["assembly_specification_id"]
        )
        assert retrieved_spec["name"] == request_data["name"]
        assert (
            retrieved_spec["applicability"] == request_data["applicability"]
        )
        assert (
            retrieved_spec["knowledge_service_queries"]
            == request_data["knowledge_service_queries"]
        )
