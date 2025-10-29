"""
Tests for documents API router.

This module provides unit tests for the documents API endpoints,
focusing on the core functionality of listing documents with pagination.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from fastapi_pagination import add_pagination

from julee_example.api.routers.documents import (
    router,
)
from julee_example.api.dependencies import get_document_repository
from julee_example.domain.models.document import Document, DocumentStatus


@pytest.fixture
def app():
    """Create FastAPI app with documents router for testing."""
    app = FastAPI()
    app.include_router(router, prefix="/documents")
    add_pagination(app)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_repository():
    """Create mock document repository."""
    return AsyncMock()


@pytest.fixture
def sample_documents():
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

    def test_list_documents_success(
        self, app, client, mock_repository, sample_documents
    ):
        """Test successful document listing."""
        # Setup mock
        mock_repository.list_documents.return_value = sample_documents
        mock_repository.count_documents.return_value = 2

        # Override dependency
        app.dependency_overrides[get_document_repository] = (
            lambda: mock_repository
        )

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

        # Check first document
        doc1 = data["items"][0]
        assert doc1["document_id"] == "doc-1"
        assert doc1["original_filename"] == "test-document-1.txt"
        assert doc1["content_type"] == "text/plain"
        assert doc1["size_bytes"] == 1024
        assert doc1["status"] == "captured"
        assert doc1["additional_metadata"] == {"type": "test"}

        # Verify repository calls
        mock_repository.list_all.assert_called_once()

    def test_list_documents_with_pagination(
        self, app, client, mock_repository, sample_documents
    ):
        """Test document listing with custom pagination."""
        # Setup mock
        mock_repository.list_all.return_value = sample_documents

        # Override dependency
        app.dependency_overrides[get_document_repository] = (
            lambda: mock_repository
        )

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

        # Verify repository calls
        mock_repository.list_all.assert_called_once()

    def test_list_documents_empty_result(self, app, client, mock_repository):
        """Test document listing when no documents exist."""
        # Setup mock
        mock_repository.list_all.return_value = []

        # Override dependency
        app.dependency_overrides[get_document_repository] = (
            lambda: mock_repository
        )

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

    def test_list_documents_invalid_page(self, client):
        """Test document listing with invalid page parameter."""
        response = client.get("/documents/?page=0")
        assert response.status_code == 422  # Validation error

    def test_list_documents_invalid_size(self, client):
        """Test document listing with invalid size parameter."""
        response = client.get("/documents/?size=101")
        assert response.status_code == 422  # Validation error

    def test_list_documents_repository_error(
        self, app, client, mock_repository
    ):
        """Test document listing when repository raises exception."""
        # Setup mock to raise exception
        mock_repository.list_all.side_effect = Exception("Database error")

        # Override dependency
        app.dependency_overrides[get_document_repository] = (
            lambda: mock_repository
        )

        # Make request
        response = client.get("/documents/")

        # Assertions
        assert response.status_code == 500
        data = response.json()
        assert "Failed to retrieve documents" in data["detail"]
