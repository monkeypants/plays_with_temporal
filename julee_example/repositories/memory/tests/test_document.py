"""
Unit tests for MemoryDocumentRepository.

These tests verify the memory implementation logic without requiring external
dependencies. They follow the Clean Architecture testing patterns and verify
idempotency, error handling, and content operations including content_string.
"""

import io
import pytest
from julee_example.repositories.memory.document import (
    MemoryDocumentRepository,
)
from julee_example.domain.models.document import Document, DocumentStatus
from julee_example.domain.models.custom_fields.content_stream import (
    ContentStream,
)


@pytest.fixture
def repository() -> MemoryDocumentRepository:
    """Provide a repository instance for testing."""
    return MemoryDocumentRepository()


@pytest.fixture
def sample_content() -> ContentStream:
    """Sample content for testing."""
    content_bytes = b"This is test content for document storage"
    return ContentStream(io.BytesIO(content_bytes))


@pytest.fixture
def sample_document(sample_content: ContentStream) -> Document:
    """Sample document for testing."""
    return Document(
        document_id="test-doc-123",
        original_filename="test.txt",
        content_type="text/plain",
        size_bytes=41,
        content_multihash="test_hash_placeholder",
        status=DocumentStatus.CAPTURED,
        content=sample_content,
    )


class TestMemoryDocumentRepositoryContentString:
    """Test content_string functionality."""

    async def test_save_document_with_content_string(
        self, repository: MemoryDocumentRepository
    ) -> None:
        """Test saving document with content_string (small content)."""
        content = '{"assembled": "document", "data": "test"}'

        # Create document with content_string
        document = Document(
            document_id="test-doc-content-string",
            original_filename="assembled.json",
            content_type="application/json",
            size_bytes=100,  # Will be updated automatically
            content_multihash="placeholder",  # Will be updated automatically
            status=DocumentStatus.CAPTURED,
            content_string=content,
        )

        # Act - save should convert content_string to ContentStream
        await repository.save(document)

        # Assert document was saved successfully
        retrieved = await repository.get(document.document_id)
        assert retrieved is not None
        assert (
            retrieved.content_multihash != "placeholder"
        )  # Hash was calculated
        assert retrieved.size_bytes == len(content.encode("utf-8"))

        # Verify content can be read
        assert retrieved.content is not None
        retrieved_content = retrieved.content.read().decode("utf-8")
        assert retrieved_content == content

    async def test_save_document_with_content_string_unicode(
        self, repository: MemoryDocumentRepository
    ) -> None:
        """Test saving document with unicode content_string."""
        content = '{"title": "测试文档", "emoji": "🚀", "content": "éñ"}'

        document = Document(
            document_id="test-doc-unicode",
            original_filename="unicode.json",
            content_type="application/json",
            size_bytes=100,
            content_multihash="placeholder",
            status=DocumentStatus.CAPTURED,
            content_string=content,
        )

        await repository.save(document)
        retrieved = await repository.get(document.document_id)

        assert retrieved is not None
        assert retrieved.content is not None
        retrieved_content = retrieved.content.read().decode("utf-8")
        assert retrieved_content == content

    # Note: Empty content test removed because domain model requires
    # size_bytes > 0

    async def test_save_excludes_content_string_from_storage(
        self, repository: MemoryDocumentRepository
    ) -> None:
        """Test that content_string is not stored in memory storage."""
        content = '{"test": "data that should not be in storage"}'

        document = Document(
            document_id="test-storage-exclusion",
            original_filename="test.json",
            content_type="application/json",
            size_bytes=100,
            content_multihash="placeholder",
            status=DocumentStatus.CAPTURED,
            content_string=content,
        )

        await repository.save(document)

        # Check stored document directly from internal storage
        stored_document = repository.storage_dict.get(
            "test-storage-exclusion"
        )
        assert stored_document is not None

        # Verify content_string is not in stored document
        assert stored_document.content_string is None

        # Verify essential fields are still present
        assert stored_document.document_id == "test-storage-exclusion"
        assert stored_document.content_multihash is not None
        assert stored_document.content_multihash != "placeholder"

        # Verify we can still retrieve with content
        retrieved = await repository.get("test-storage-exclusion")
        assert retrieved is not None
        assert retrieved.content is not None
        retrieved_content = retrieved.content.read().decode("utf-8")
        assert retrieved_content == content


class TestMemoryDocumentRepositoryBasicOperations:
    """Test basic repository operations."""

    async def test_save_and_get_document_with_content_stream(
        self, repository: MemoryDocumentRepository, sample_document: Document
    ) -> None:
        """Test basic save and retrieve operations with ContentStream."""
        # Act
        await repository.save(sample_document)
        retrieved = await repository.get(sample_document.document_id)

        # Assert
        assert retrieved is not None
        assert retrieved.document_id == sample_document.document_id
        assert (
            retrieved.original_filename == sample_document.original_filename
        )

    async def test_get_nonexistent_document(
        self, repository: MemoryDocumentRepository
    ) -> None:
        """Test retrieving a document that doesn't exist."""
        result = await repository.get("nonexistent-123")
        assert result is None

    async def test_generate_id(
        self, repository: MemoryDocumentRepository
    ) -> None:
        """Test that generate_id returns a unique string."""
        doc_id_1 = await repository.generate_id()
        doc_id_2 = await repository.generate_id()

        assert isinstance(doc_id_1, str)
        assert isinstance(doc_id_2, str)
        assert doc_id_1 != doc_id_2
        assert len(doc_id_1) > 0
        assert len(doc_id_2) > 0


class TestMemoryDocumentRepositoryErrorHandling:
    """Test error handling scenarios."""

    async def test_save_handles_empty_document_id(
        self, repository: MemoryDocumentRepository
    ) -> None:
        """Test error handling for empty document ID."""
        with pytest.raises(ValueError, match="Document ID cannot be empty"):
            Document(
                document_id="",
                original_filename="test.txt",
                content_type="text/plain",
                size_bytes=100,
                content_multihash="test_hash",
                status=DocumentStatus.CAPTURED,
                content_string="test content",
            )

    async def test_save_handles_empty_filename(
        self, repository: MemoryDocumentRepository
    ) -> None:
        """Test error handling for empty filename."""
        with pytest.raises(
            ValueError, match="Original filename cannot be empty"
        ):
            Document(
                document_id="test-123",
                original_filename="",
                content_type="text/plain",
                size_bytes=100,
                content_multihash="test_hash",
                status=DocumentStatus.CAPTURED,
                content_string="test content",
            )
