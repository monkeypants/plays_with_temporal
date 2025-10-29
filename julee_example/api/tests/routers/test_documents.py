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
