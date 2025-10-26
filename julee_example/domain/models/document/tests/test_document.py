"""
Comprehensive tests for Document domain model.

This test module documents the design decisions made for the Document domain
model
using table-based tests. It covers:

- Document instantiation with various field combinations
- Content stream operations (read, seek, tell)
- Validation rules and error conditions
- JSON serialization behavior
- Stream-like interface compatibility

Design decisions documented:
- Documents must have all required fields
- Content streams are excluded from JSON serialization
- Size must be positive, filenames and content types non-empty
- Multihash is required and non-empty
- Documents act as readable streams with standard methods
"""

import pytest
import json

from julee_example.domain.models.document import Document
from .factories import DocumentFactory, ContentStreamFactory


class TestDocumentInstantiation:
    """Test Document creation with various field combinations."""

    @pytest.mark.parametrize(
        "document_id,original_filename,content_type,size_bytes,multihash,expected_success",
        [
            # Valid cases
            ("doc-1", "test.txt", "text/plain", 100, "sha256:hash", True),
            (
                "doc-2",
                "document.pdf",
                "application/pdf",
                1024,
                "sha256:pdf-hash",
                True,
            ),
            (
                "doc-3",
                "data.json",
                "application/json",
                50,
                "sha256:json-hash",
                True,
            ),
            # Invalid cases - empty required fields
            (
                "",
                "test.txt",
                "text/plain",
                100,
                "sha256:hash",
                False,
            ),  # Empty document_id
            (
                "doc-4",
                "",
                "text/plain",
                100,
                "sha256:hash",
                False,
            ),  # Empty filename
            (
                "doc-5",
                "test.txt",
                "",
                100,
                "sha256:hash",
                False,
            ),  # Empty content_type
            (
                "doc-6",
                "test.txt",
                "text/plain",
                100,
                "",
                False,
            ),  # Empty multihash
            # Invalid cases - whitespace only
            (
                "   ",
                "test.txt",
                "text/plain",
                100,
                "sha256:hash",
                False,
            ),  # Whitespace document_id
            (
                "doc-7",
                "   ",
                "text/plain",
                100,
                "sha256:hash",
                False,
            ),  # Whitespace filename
            (
                "doc-8",
                "test.txt",
                "   ",
                100,
                "sha256:hash",
                False,
            ),  # Whitespace content_type
            (
                "doc-9",
                "test.txt",
                "text/plain",
                100,
                "   ",
                False,
            ),  # Whitespace multihash
            # Invalid cases - size validation
            (
                "doc-10",
                "test.txt",
                "text/plain",
                0,
                "sha256:hash",
                False,
            ),  # Zero size
            (
                "doc-11",
                "test.txt",
                "text/plain",
                -1,
                "sha256:hash",
                False,
            ),  # Negative size
        ],
    )
    def test_document_creation_validation(
        self,
        document_id: str,
        original_filename: str,
        content_type: str,
        size_bytes: int,
        multihash: str,
        expected_success: bool,
    ) -> None:
        """Test document creation with various field validation scenarios."""
        content_stream = ContentStreamFactory.build()

        if expected_success:
            # Should create successfully
            doc = Document(
                document_id=document_id,
                original_filename=original_filename,
                content_type=content_type,
                size_bytes=size_bytes,
                content_multihash=multihash,
                content=content_stream,
            )
            assert doc.document_id == document_id
            assert doc.original_filename.strip() == original_filename.strip()
            assert doc.content_type.strip() == content_type.strip()
            assert doc.size_bytes == size_bytes
            assert doc.content_multihash.strip() == multihash.strip()
        else:
            # Should raise validation error
            with pytest.raises(
                Exception
            ):  # Could be ValueError or ValidationError
                Document(
                    document_id=document_id,
                    original_filename=original_filename,
                    content_type=content_type,
                    size_bytes=size_bytes,
                    content_multihash=multihash,
                    content=ContentStreamFactory.build(),
                )


class TestDocumentSerialization:
    """Test Document JSON serialization behavior."""

    def test_document_json_excludes_content(self) -> None:
        """Test that content stream is excluded from JSON serialization."""
        content = b"Secret content not for JSON"
        content_stream = ContentStreamFactory.build(content=content)
        doc = DocumentFactory.build(
            content=content_stream, size_bytes=len(content)
        )

        json_str = doc.model_dump_json()
        json_data = json.loads(json_str)

        # Content should not be in JSON
        assert "content" not in json_data

        # But all other fields should be present
        assert json_data["document_id"] == doc.document_id
        assert json_data["original_filename"] == doc.original_filename
        assert json_data["content_type"] == doc.content_type
        assert json_data["size_bytes"] == doc.size_bytes
        assert json_data["content_multihash"] == doc.content_multihash
        assert json_data["status"] == doc.status.value


class TestDocumentContentValidation:
    """Test Document content and content_string validation rules."""

    def test_document_with_both_content_and_content_string_fails(
        self,
    ) -> None:
        """Test that both content and content_string raises error."""
        content_stream = ContentStreamFactory.build()
        content_string = '{"type": "string"}'

        with pytest.raises(
            ValueError, match="cannot have both content and content_string"
        ):
            Document(
                document_id="test-doc-both",
                original_filename="both.json",
                content_type="application/json",
                size_bytes=100,
                content_multihash="test_hash",
                content=content_stream,
                content_string=content_string,
            )

    def test_document_without_content_or_content_string_fails(self) -> None:
        """Test that no content or content_string raises error."""
        with pytest.raises(
            ValueError, match="must have either content or content_string"
        ):
            Document(
                document_id="test-doc-no-content",
                original_filename="empty.json",
                content_type="application/json",
                size_bytes=100,
                content_multihash="test_hash",
                content=None,
                content_string=None,
            )

    def test_document_with_content_only_succeeds(self) -> None:
        """Test that document with only content field succeeds."""
        content_stream = ContentStreamFactory.build()

        doc = Document(
            document_id="test-doc-content",
            original_filename="content.json",
            content_type="application/json",
            size_bytes=100,
            content_multihash="test_hash",
            content=content_stream,
            content_string=None,
        )

        assert doc.content is not None
        assert doc.content_string is None

    def test_document_with_content_string_only_succeeds(self) -> None:
        """Test that document with only content_string field succeeds."""
        content_string = '{"type": "string"}'

        doc = Document(
            document_id="test-doc-string",
            original_filename="string.json",
            content_type="application/json",
            size_bytes=100,
            content_multihash="test_hash",
            content=None,
            content_string=content_string,
        )

        assert doc.content is None
        assert doc.content_string == content_string

    def test_document_deserialization_with_empty_content_succeeds(
        self,
    ) -> None:
        """Test Temporal deserialization allows empty content."""
        # This simulates what happens when a Document comes back from Temporal
        # activities - the ContentStream is excluded from serialization
        document_data = {
            "document_id": "test-temporal",
            "original_filename": "temporal.json",
            "content_type": "application/json",
            "size_bytes": 100,
            "content_multihash": "test_hash",
            "content": None,
            "content_string": None,
        }

        # Should succeed with temporal_validation context
        doc = Document.model_validate(
            document_data, context={"temporal_validation": True}
        )

        assert doc.document_id == "test-temporal"
        assert doc.content is None
        assert doc.content_string is None
