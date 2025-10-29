"""
Tests for documents API router.

This module provides unit tests for the documents API endpoints,
focusing on the core functionality of listing documents with pagination.
"""

import pytest
from datetime import datetime, timezone
from typing import Generator
from fastapi.testclient import TestClient
from fastapi import FastAPI
from fastapi_pagination import add_pagination

from julee_example.api.routers.documents import router
from julee_example.api.dependencies import get_document_repository
from julee_example.domain.models.document import Document, DocumentStatus
from julee_example.repositories.memory import MemoryDocumentRepository


@pytest.fixture
def memory_repo() -> MemoryDocumentRepository:
    """Create a memory document repository for testing."""
    return MemoryDocumentRepository()


@pytest.fixture
def app(memory_repo: MemoryDocumentRepository) -> FastAPI:
    """Create FastAPI app with documents router for testing."""
    app = FastAPI()

    # Override the dependency with our memory repository
    app.dependency_overrides[get_document_repository] = lambda: memory_repo

    # Add pagination support (required for the paginate function)
    add_pagination(app)

    app.include_router(router, prefix="/documents")
    return app


@pytest.fixture
def client(app: FastAPI) -> Generator[TestClient, None, None]:
    """Create test client."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sample_documents() -> list[Document]:
    """Create sample documents for testing."""
    return [
        Document(
            document_id="doc-1",
            original_filename="test-document-1.txt",
            content_type="text/plain",
            size_bytes=1024,
            content_multihash="QmTest1",
            status=DocumentStatus.CAPTURED,
            created_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            additional_metadata={"type": "test"},
            content_string="test content",
        ),
        Document(
            document_id="doc-2",
            original_filename="test-document-2.pdf",
            content_type="application/pdf",
            size_bytes=2048,
            content_multihash="QmTest2",
            status=DocumentStatus.REGISTERED,
            created_at=datetime(2024, 1, 2, 12, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2024, 1, 2, 12, 0, 0, tzinfo=timezone.utc),
            additional_metadata={"type": "report"},
            content_string="pdf content",
        ),
    ]


class TestListDocuments:
    """Test cases for the list documents endpoint."""

    @pytest.mark.asyncio
    async def test_list_documents_success(
        self,
        client: TestClient,
        memory_repo: MemoryDocumentRepository,
        sample_documents: list[Document],
    ) -> None:
        """Test successful document listing."""
        # Setup - add documents to repository
        for doc in sample_documents:
            await memory_repo.save(doc)

        # Make request
        response = client.get("/documents/")

        # Assertions
        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 2
        assert data["page"] == 1
        assert data["size"] == 50  # Default fastapi-pagination size
        assert data["pages"] == 1
        assert len(data["items"]) == 2

        # Check first document (documents may not be in insertion order)
        doc_ids = [item["document_id"] for item in data["items"]]
        assert "doc-1" in doc_ids
        assert "doc-2" in doc_ids

        # Find doc-1 and verify its details
        doc1 = next(
            item for item in data["items"] if item["document_id"] == "doc-1"
        )
        assert doc1["original_filename"] == "test-document-1.txt"
        assert doc1["content_type"] == "text/plain"
        assert doc1["size_bytes"] == 12  # Length of "test content"
        assert doc1["status"] == "captured"
        assert doc1["additional_metadata"] == {"type": "test"}

    @pytest.mark.asyncio
    async def test_list_documents_with_pagination(
        self,
        client: TestClient,
        memory_repo: MemoryDocumentRepository,
        sample_documents: list[Document],
    ) -> None:
        """Test document listing with custom pagination."""
        # Setup - add documents to repository
        for doc in sample_documents:
            await memory_repo.save(doc)

        # Make request with pagination
        response = client.get("/documents/?page=1&size=1")

        # Assertions
        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 2
        assert data["page"] == 1
        assert data["size"] == 1
        assert data["pages"] == 2
        assert len(data["items"]) == 1

    def test_list_documents_empty_result(
        self, client: TestClient, memory_repo: MemoryDocumentRepository
    ) -> None:
        """Test document listing when no documents exist."""
        # No setup needed - memory repo starts empty

        # Make request
        response = client.get("/documents/")

        # Assertions
        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 0
        assert data["page"] == 1
        assert data["size"] == 50  # Default fastapi-pagination size
        assert data["pages"] == 0
        assert len(data["items"]) == 0

    def test_list_documents_invalid_page(self, client: TestClient) -> None:
        """Test document listing with invalid page parameter."""
        response = client.get("/documents/?page=0")
        assert response.status_code == 422  # Validation error

    def test_list_documents_invalid_size(self, client: TestClient) -> None:
        """Test document listing with invalid size parameter."""
        response = client.get("/documents/?size=101")
        assert response.status_code == 422  # Validation error


class TestGetDocument:
    """Test cases for the get document metadata endpoint."""

    @pytest.mark.asyncio
    async def test_get_document_metadata_success(
        self,
        client: TestClient,
        memory_repo: MemoryDocumentRepository,
        sample_documents: list[Document],
    ) -> None:
        """Test successful document metadata retrieval."""
        # Setup - add document to repository
        doc = sample_documents[0]
        await memory_repo.save(doc)

        # Make request
        response = client.get(f"/documents/{doc.document_id}")

        # Assertions
        assert response.status_code == 200
        data = response.json()

        assert data["document_id"] == doc.document_id
        assert data["original_filename"] == doc.original_filename
        assert data["content_type"] == doc.content_type
        assert data["status"] == doc.status.value
        assert data["additional_metadata"] == doc.additional_metadata

        # Content should NOT be included in metadata endpoint
        assert data["content_string"] is None
        # Content field is excluded from JSON response
        assert "content" not in data

    @pytest.mark.asyncio
    async def test_get_document_metadata_not_found(
        self, client: TestClient, memory_repo: MemoryDocumentRepository
    ) -> None:
        """Test document metadata retrieval when document doesn't exist."""
        response = client.get("/documents/nonexistent-id")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_get_document_metadata_invalid_id_format(
        self, client: TestClient
    ) -> None:
        """Test document metadata retrieval with invalid ID format."""
        # Test with empty ID (should be handled by FastAPI path validation)
        response = client.get("/documents/")
        # This should hit the list endpoint instead
        assert response.status_code == 200

        # Test with very long ID
        very_long_id = "x" * 1000
        response = client.get(f"/documents/{very_long_id}")
        assert response.status_code == 404  # Not found, but valid request


class TestGetDocumentContent:
    """Test cases for the get document content endpoint."""

    @pytest.mark.asyncio
    async def test_get_document_content_success(
        self,
        client: TestClient,
        memory_repo: MemoryDocumentRepository,
        sample_documents: list[Document],
    ) -> None:
        """Test successful document content retrieval."""
        # Setup - add document to repository
        doc = sample_documents[0]
        await memory_repo.save(doc)

        # Make request
        response = client.get(f"/documents/{doc.document_id}/content")

        # Assertions
        assert response.status_code == 200
        assert response.content.decode("utf-8") == "test content"
        assert response.headers["content-type"].startswith(doc.content_type)
        assert (
            doc.original_filename in response.headers["content-disposition"]
        )

    @pytest.mark.asyncio
    async def test_get_document_content_not_found(
        self, client: TestClient, memory_repo: MemoryDocumentRepository
    ) -> None:
        """Test content retrieval when document doesn't exist."""
        response = client.get("/documents/nonexistent-id/content")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_document_content_no_content(
        self,
        client: TestClient,
        memory_repo: MemoryDocumentRepository,
    ) -> None:
        """Test content retrieval when document has no content."""
        # Create document with content_string first to pass validation
        doc = Document(
            document_id="doc-no-content",
            original_filename="empty.txt",
            content_type="text/plain",
            size_bytes=1,
            content_multihash="empty_hash",
            status=DocumentStatus.CAPTURED,
            additional_metadata={"type": "empty"},
            content_string="temp",
        )

        # Save document normally, then manually remove content from storage
        await memory_repo.save(doc)
        stored_doc = memory_repo.storage_dict[doc.document_id]
        # Remove content from the stored document
        memory_repo.storage_dict[doc.document_id] = stored_doc.model_copy(
            update={"content": None, "content_string": None}
        )

        # Make request
        response = client.get(f"/documents/{doc.document_id}/content")

        # Assertions
        assert response.status_code == 422
        data = response.json()
        assert "has no content" in data["detail"].lower()
