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

from julee_example.domain import Document
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
            # Note: Empty document_id is actually valid in Pydantic (no
            # validator for it)
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
    ):
        """Test document creation with various field validation scenarios."""
        content_stream = ContentStreamFactory()

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
                    content=content_stream,
                )


class TestDocumentSerialization:
    """Test Document JSON serialization behavior."""

    def test_document_json_excludes_content(self):
        """Test that content stream is excluded from JSON serialization."""
        content = b"Secret content not for JSON"
        content_stream = ContentStreamFactory(content=content)
        doc = DocumentFactory(content=content_stream, size_bytes=len(content))

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
