"""
Unit tests for MinioDocumentRepository.

These tests mock the Minio client to test the repository implementation logic
without requiring a real MinIO instance. They follow the Clean Architecture
testing patterns and verify idempotency, error handling, and content.
"""

import io
import pytest
import hashlib
import multihash
from typing import Any
from unittest.mock import Mock
from minio.error import S3Error


from julee_example.repositories.minio.document import MinioDocumentRepository
from julee_example.domain.models.document import Document, DocumentStatus
from julee_example.domain.models.custom_fields.content_stream import (
    ContentStream,
)
from .fake_client import FakeMinioClient


@pytest.fixture
def fake_minio_client() -> FakeMinioClient:
    """Provide a fake Minio client for state-based testing."""
    return FakeMinioClient()


@pytest.fixture
def repository(fake_minio_client: FakeMinioClient) -> MinioDocumentRepository:
    """Provide a repository instance with fake client."""
    return MinioDocumentRepository(fake_minio_client)


@pytest.fixture
def sample_content() -> ContentStream:
    """Sample content for testing."""
    content_bytes = b"This is test content for document storage"
    return ContentStream(io.BytesIO(content_bytes))


@pytest.fixture
def sample_document(sample_content: ContentStream) -> Document:
    """Sample document for testing."""
    # Calculate the actual multihash for this content
    content_bytes = b"This is test content for document storage"
    sha256_hash = hashlib.sha256(content_bytes).digest()
    mh = multihash.encode(sha256_hash, multihash.SHA2_256)
    actual_multihash = str(mh.hex())

    return Document(
        document_id="test-doc-123",
        original_filename="test.txt",
        content_type="text/plain",
        size_bytes=len(content_bytes),
        content_multihash=actual_multihash,
        status=DocumentStatus.CAPTURED,
        content=sample_content,
    )


class TestMinioDocumentRepositoryInitialization:
    """Test repository initialization and bucket creation."""

    def test_init_creates_buckets_when_missing(self) -> None:
        """Test that missing buckets are created during initialization."""
        fake_client = FakeMinioClient()

        # Verify no buckets exist initially
        assert not fake_client.bucket_exists("documents")
        assert not fake_client.bucket_exists("documents-content")

        # Initialize repository - should create buckets
        MinioDocumentRepository(fake_client)

        # Verify buckets were created
        assert fake_client.bucket_exists("documents")
        assert fake_client.bucket_exists("documents-content")

    def test_init_skips_existing_buckets(self) -> None:
        """Test that existing buckets are not recreated."""
        fake_client = FakeMinioClient()

        # Pre-create buckets
        fake_client.make_bucket("documents")
        fake_client.make_bucket("documents-content")

        # Initialize repository - should not fail or recreate
        MinioDocumentRepository(fake_client)

        # Verify buckets still exist (no exception thrown)
        assert fake_client.bucket_exists("documents")
        assert fake_client.bucket_exists("documents-content")

    def test_init_handles_bucket_creation_error(self) -> None:
        """Test proper error handling during bucket creation."""
        fake_client = FakeMinioClient()

        # Pre-create one bucket to cause a conflict
        fake_client.make_bucket("documents")

        # Override make_bucket to raise error for second bucket
        original_make_bucket = fake_client.make_bucket

        def failing_make_bucket(bucket_name: str) -> None:
            if bucket_name == "documents-content":
                raise S3Error(
                    code="AccessDenied",
                    message="Access denied",
                    resource="AccessDenied",
                    request_id="req123",
                    host_id="host123",
                    response=Mock(),
                )
            return original_make_bucket(bucket_name)

        fake_client.make_bucket = failing_make_bucket  # type: ignore[method-assign]

        with pytest.raises(S3Error):
            MinioDocumentRepository(fake_client)


class TestMinioDocumentRepositoryStore:
    """Test document storage operations."""

    async def test_store_new_document(
        self, fake_minio_client: FakeMinioClient, sample_document: Document
    ) -> None:
        """Test storing a new document with content."""
        repository = MinioDocumentRepository(fake_minio_client)

        # Verify buckets are empty initially
        assert fake_minio_client.get_object_count("documents") == 0
        assert fake_minio_client.get_object_count("documents-content") == 0

        # Act
        await repository.save(sample_document)

        # Assert content and metadata were stored
        assert fake_minio_client.get_object_count("documents") == 1
        assert fake_minio_client.get_object_count("documents-content") == 1

        # Verify content was stored with calculated multihash as key
        content_objects = fake_minio_client.get_stored_objects(
            "documents-content"
        )
        calculated_multihash = sample_document.content_multihash
        assert calculated_multihash in content_objects

        # Verify metadata was stored with document ID as key
        metadata_objects = fake_minio_client.get_stored_objects("documents")
        assert sample_document.document_id in metadata_objects

    async def test_store_document_with_existing_content_deduplication(
        self, fake_minio_client: FakeMinioClient, sample_document: Document
    ) -> None:
        """Test that existing content is not re-stored (deduplication)."""
        repository = MinioDocumentRepository(fake_minio_client)

        # Store first document
        await repository.save(sample_document)

        # Verify first document was stored with correct multihash
        stored_multihash = sample_document.content_multihash

        # Create second document with identical content but different metadata
        assert sample_document.content is not None
        sample_document.content.seek(0)  # Reset stream
        content_bytes = sample_document.content.read()
        sample_document.content.seek(0)  # Reset again

        second_document = Document(
            document_id="different-doc-456",
            original_filename="different.txt",
            content_type="text/plain",
            size_bytes=len(content_bytes),
            content_multihash=stored_multihash,  # Same calculated multihash
            status=DocumentStatus.CAPTURED,
            content=ContentStream(io.BytesIO(content_bytes)),
        )

        # Store second document - should reuse existing content
        await repository.save(second_document)

        # Assert: 2 metadata objects, but only 1 content object (worked)
        assert fake_minio_client.get_object_count("documents") == 2
        assert fake_minio_client.get_object_count("documents-content") == 1

        # Verify deduplication: both documents reference same content object
        content_objects = fake_minio_client.get_stored_objects(
            "documents-content"
        )
        assert len(content_objects) == 1  # Only one content object stored
        assert (
            stored_multihash in content_objects
        )  # Stored under the correct hash key

        # Verify both documents have the same multihash (share content)
        assert sample_document.content_multihash == stored_multihash
        assert second_document.content_multihash == stored_multihash

    async def test_store_updates_multihash_when_different(
        self, fake_minio_client: FakeMinioClient, sample_document: Document
    ) -> None:
        """Test that document multihash is updated when calculated differs."""
        repository = MinioDocumentRepository(fake_minio_client)

        # Deliberately set an incorrect multihash to test correction
        correct_multihash = sample_document.content_multihash
        sample_document.content_multihash = "incorrect_hash_12345"

        # Act
        await repository.save(sample_document)

        # Assert multihash was corrected to the calculated value
        assert sample_document.content_multihash == correct_multihash
        assert sample_document.content_multihash != "incorrect_hash_12345"

        # Verify content is stored under the calculated multihash
        content_objects = fake_minio_client.get_stored_objects(
            "documents-content"
        )
        assert correct_multihash in content_objects
        assert "incorrect_hash_12345" not in content_objects

    async def test_store_handles_content_storage_error(
        self, fake_minio_client: FakeMinioClient, sample_document: Document
    ) -> None:
        """Test proper error handling during content storage."""
        repository = MinioDocumentRepository(fake_minio_client)

        # Override put_object to raise error when storing content
        original_put_object = repository.client.put_object

        def failing_put_object(
            bucket_name: str,
            object_name: str,
            data: Any,
            length: int,
            **kwargs: Any,
        ) -> Any:
            if bucket_name == "documents-content":
                raise S3Error(
                    code="AccessDenied",
                    message="Access denied",
                    resource="AccessDenied",
                    request_id="req123",
                    host_id="host123",
                    response=Mock(),
                )
            return original_put_object(
                bucket_name, object_name, data, length, **kwargs
            )

        repository.client.put_object = failing_put_object  # type: ignore[method-assign, assignment]

        # Act & Assert
        with pytest.raises(S3Error):
            await repository.save(sample_document)

        # Verify no objects were stored
        assert fake_minio_client.get_object_count("documents") == 0
        assert fake_minio_client.get_object_count("documents-content") == 0


class TestMinioDocumentRepositoryGet:
    """Test document retrieval operations."""

    async def test_get_existing_document(
        self, repository: MinioDocumentRepository, sample_document: Document
    ) -> None:
        """Test retrieving an existing document with content."""
        # Store a document first
        await repository.save(sample_document)

        # Act - retrieve the document
        result = await repository.get(sample_document.document_id)

        # Assert
        assert result is not None
        assert result.document_id == sample_document.document_id
        assert result.original_filename == sample_document.original_filename
        assert result.content_type == sample_document.content_type
        assert result.size_bytes == sample_document.size_bytes

        # Verify content can be read
        assert result.content is not None
        retrieved_content = result.content.read()

        # Reset sample document content for comparison
        assert sample_document.content is not None
        sample_document.content.seek(0)
        original_content = sample_document.content.read()

        assert retrieved_content == original_content

    async def test_get_document_missing_content_multihash(
        self, repository: MinioDocumentRepository
    ) -> None:
        """Test handling document metadata without content_multihash."""
        # Manually store invalid metadata (missing content_multihash)
        invalid_metadata_json = (
            '{"document_id": "test-123", "original_filename": "test.txt"}'
        )
        repository.client.put_object(
            "documents",
            "test-123",
            io.BytesIO(invalid_metadata_json.encode("utf-8")),
            len(invalid_metadata_json),
            content_type="application/json",
        )

        # Act
        result = await repository.get("test-123")

        # Assert
        assert result is None

    async def test_get_document_with_missing_content(
        self, repository: MinioDocumentRepository
    ) -> None:
        """Test that missing content returns None."""
        # Store metadata but not content
        metadata_json = (
            '{"document_id": "test-123", "content_multihash": "missing_hash",'
            ' "original_filename": "test.txt", "content_type": "text/plain",'
            ' "size_bytes": 100, "status": "captured"}'
        )
        repository.client.put_object(
            "documents",
            "test-123",
            io.BytesIO(metadata_json.encode("utf-8")),
            len(metadata_json),
            content_type="application/json",
        )

        # Note: content with multihash "missing_hash" does not exist

        # Act
        result = await repository.get("test-123")

        # Assert - should return None when content is missing
        assert result is None

    async def test_get_nonexistent_document(
        self, repository: MinioDocumentRepository
    ) -> None:
        """Test retrieving a document that doesn't exist."""
        # Act - try to get a document that was never stored
        result = await repository.get("nonexistent-123")

        # Assert
        assert result is None


class TestMinioDocumentRepositoryUpdate:
    """Test document update operations."""

    async def test_update_document(
        self, repository: MinioDocumentRepository, sample_document: Document
    ) -> None:
        """Test updating a document."""
        # Store document initially
        await repository.save(sample_document)
        original_updated_at = sample_document.updated_at

        # Modify document
        sample_document.status = DocumentStatus.EXTRACTED

        # Act
        await repository.save(sample_document)

        # Assert updated_at was changed
        assert sample_document.updated_at != original_updated_at
        if original_updated_at and sample_document.updated_at:
            assert sample_document.updated_at > original_updated_at

        # Verify document was actually updated in storage
        retrieved_doc = await repository.get(sample_document.document_id)
        assert retrieved_doc is not None
        assert retrieved_doc.status == DocumentStatus.EXTRACTED
        assert retrieved_doc.updated_at == sample_document.updated_at


class TestMinioDocumentRepositoryGenerateId:
    """Test ID generation."""

    async def test_generate_id(
        self, repository: MinioDocumentRepository
    ) -> None:
        """Test that generate_id returns a unique string."""
        # Act
        doc_id_1 = await repository.generate_id()
        doc_id_2 = await repository.generate_id()

        # Assert
        assert isinstance(doc_id_1, str)
        assert isinstance(doc_id_2, str)
        assert doc_id_1 != doc_id_2
        assert len(doc_id_1) > 0
        assert len(doc_id_2) > 0


class TestMinioDocumentRepositoryMultihash:
    """Test multihash calculation functionality."""

    def test_calculate_multihash_from_stream(
        self, repository: MinioDocumentRepository
    ) -> None:
        """Test multihash calculation from stream."""
        content = b"test content for hashing"
        stream = ContentStream(io.BytesIO(content))

        # Act
        multihash_result = repository._calculate_multihash_from_stream(stream)

        # Assert
        assert isinstance(multihash_result, str)
        assert len(multihash_result) > 0

        # Test deterministic - same content should produce same hash
        stream.seek(0)
        multihash_result_2 = repository._calculate_multihash_from_stream(
            stream
        )
        assert multihash_result == multihash_result_2

    def test_calculate_multihash_from_empty_stream(
        self, repository: MinioDocumentRepository
    ) -> None:
        """Test multihash calculation from empty stream."""
        stream = ContentStream(io.BytesIO(b""))

        # Act
        multihash_result = repository._calculate_multihash_from_stream(stream)

        # Assert
        assert isinstance(multihash_result, str)
        assert len(multihash_result) > 0


class TestMinioDocumentRepositoryContentString:
    """Test content_string functionality."""

    async def test_save_document_with_content_string(
        self, repository: MinioDocumentRepository
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
        self, repository: MinioDocumentRepository
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

    async def test_save_excludes_content_string_from_metadata(
        self,
        repository: MinioDocumentRepository,
        fake_minio_client: FakeMinioClient,
    ) -> None:
        """Test that content_string is not stored in metadata."""
        content = '{"test": "data that should not be in metadata"}'

        document = Document(
            document_id="test-metadata-exclusion",
            original_filename="test.json",
            content_type="application/json",
            size_bytes=100,
            content_multihash="placeholder",
            status=DocumentStatus.CAPTURED,
            content_string=content,
        )

        await repository.save(document)

        # Check raw metadata stored in MinIO
        metadata_response = fake_minio_client.get_object(
            bucket_name="documents", object_name="test-metadata-exclusion"
        )
        metadata_data = metadata_response.read()
        metadata_json = metadata_data.decode("utf-8")

        import json

        metadata_dict = json.loads(metadata_json)

        # Verify content_string is not in stored metadata
        assert "content_string" not in metadata_dict
        assert "content" not in metadata_dict

        # Verify essential fields are still present
        assert metadata_dict["document_id"] == "test-metadata-exclusion"
        assert "content_multihash" in metadata_dict
        assert "status" in metadata_dict


class TestMinioDocumentRepositoryErrorHandling:
    """Test error handling scenarios."""

    async def test_store_handles_metadata_storage_error(
        self, fake_minio_client: FakeMinioClient, sample_document: Document
    ) -> None:
        """Test error handling when metadata storage fails."""
        repository = MinioDocumentRepository(fake_minio_client)

        # Override put_object to fail only for metadata storage
        original_put_object = repository.client.put_object

        def failing_put_object(
            bucket_name: str,
            object_name: str,
            data: Any,
            length: int,
            **kwargs: Any,
        ) -> Any:
            if bucket_name == "documents":
                raise S3Error(
                    code="AccessDenied",
                    message="Access denied",
                    resource="AccessDenied",
                    request_id="req123",
                    host_id="host123",
                    response=Mock(),
                )
            return original_put_object(
                bucket_name, object_name, data, length, **kwargs
            )

        repository.client.put_object = failing_put_object  # type: ignore[method-assign, assignment]

        # Act & Assert
        with pytest.raises(S3Error):
            await repository.save(sample_document)

        # Verify content was stored but metadata was not
        assert fake_minio_client.get_object_count("documents-content") == 1
        assert fake_minio_client.get_object_count("documents") == 0

    async def test_get_handles_unexpected_error(
        self, repository: MinioDocumentRepository
    ) -> None:
        """Test handling of unexpected errors during get operation."""
        # Override get_object to raise unexpected error
        original_get_object = repository.client.get_object

        def failing_get_object(bucket_name: str, object_name: str) -> Any:
            if bucket_name == "documents":
                raise Exception("Unexpected error")
            return original_get_object(bucket_name, object_name)

        repository.client.get_object = failing_get_object  # type: ignore[method-assign]

        # Act
        result = await repository.get("test-123")

        # Assert - should return None and not propagate exception
        assert result is None
