"""
Minio implementation of DocumentRepository.

This module provides a Minio-based implementation of the DocumentRepository
protocol that follows the Clean Architecture patterns defined in the
Fun-Police Framework. It handles document storage with both metadata and
content streams, ensuring idempotency and proper error handling.

The implementation separates document metadata (stored as JSON) from content
(stored as content-addressable binary objects) in Minio, following the large
payload handling pattern from the architectural guidelines.
"""

import io
import json
import hashlib
import logging
from datetime import datetime, timezone
from typing import Optional

from minio.error import S3Error  # type: ignore[import-untyped]
import multihash  # type: ignore[import-untyped]

from julee_example.domain import Document, ContentStream
from julee_example.repositories.document import DocumentRepository
from .client import MinioClient, MinioRepositoryMixin


class MinioDocumentRepository(DocumentRepository, MinioRepositoryMixin):
    """
    Minio implementation of DocumentRepository using Minio for persistence.

    This implementation stores document metadata and content separately:
    - Metadata: JSON objects in the "documents" bucket
    - Content: Binary objects in the "documents-content" bucket

    This separation allows for efficient metadata queries while supporting
    large content files without hitting Temporal's 2MB payload limits.
    """

    def __init__(self, client: MinioClient) -> None:
        """Initialize repository with Minio client.

        Args:
            client: MinioClient protocol implementation (real or fake)
        """
        self.client = client
        self.logger = logging.getLogger("MinioDocumentRepository")
        self.metadata_bucket = "documents"
        self.content_bucket = "documents-content"
        self.ensure_buckets_exist([self.metadata_bucket, self.content_bucket])

    async def get(self, document_id: str) -> Optional[Document]:
        """Retrieve a document with metadata and content."""
        try:
            # First, get the metadata
            metadata_response = self.client.get_object(
                bucket_name=self.metadata_bucket, object_name=document_id
            )
            metadata_data = metadata_response.read()
            metadata_response.close()
            metadata_response.release_conn()

            metadata_json = metadata_data.decode("utf-8")

            # Parse metadata JSON directly to dict (content field excluded)
            document_dict = json.loads(metadata_json)

            # Now get the content stream using the content multihash as key
            content_multihash = document_dict.get("content_multihash")
            if not content_multihash:
                self.logger.error(
                    "Document metadata missing content_multihash",
                    extra={"document_id": document_id},
                )
                return None

            try:
                content_response = self.client.get_object(
                    bucket_name=self.content_bucket,
                    object_name=content_multihash,
                )

                # Create ContentStream directly from the Minio response stream
                # This avoids loading the entire content into memory
                content_stream = ContentStream(content_response)
                document_dict["content"] = content_stream

                self.logger.info(
                    "Document retrieved successfully",
                    extra={
                        "document_id": document_id,
                        "content_multihash": content_multihash,
                        "retrieved_at": datetime.now(
                            timezone.utc
                        ).isoformat(),
                    },
                )

                return Document(**document_dict)

            except S3Error as content_error:
                if getattr(content_error, "code", None) == "NoSuchKey":
                    self.logger.error(
                        "Data integrity error: Document metadata exists but "
                        "content missing",
                        extra={
                            "document_id": document_id,
                            "content_multihash": content_multihash,
                        },
                    )
                    raise ValueError(
                        f"Document {document_id} metadata exists but content "
                        f"is missing. Content multihash: {content_multihash}"
                    )
                else:
                    raise content_error

        except S3Error as e:
            if getattr(e, "code", None) == "NoSuchKey":
                self.logger.debug(
                    "Document not found",
                    extra={"document_id": document_id},
                )
                return None
            else:
                self.logger.error(
                    "Error retrieving document metadata",
                    extra={"document_id": document_id, "error": str(e)},
                )
                raise
        except Exception as e:
            self.logger.error(
                "Unexpected error during document retrieval",
                extra={
                    "document_id": document_id,
                    "error": str(e),
                },
                exc_info=True,
            )
            return None

    async def save(self, document: Document) -> None:
        """Save a document with its content and metadata.

        If the document has content_string, it will be converted to a
        ContentStream and stored. The content_string field should only be
        used for small content (few KB) when saving from workflows/use-cases.
        Call-sites in activities should always use the content stream.
        """
        self.logger.info(
            "Saving document",
            extra={
                "document_id": document.document_id,
                "original_filename": document.original_filename,
                "content_type": document.content_type,
                "size_bytes": document.size_bytes,
                "status": document.status.value,
            },
        )

        # Update timestamp
        self.update_timestamps(document)

        try:
            # Handle content_string conversion (only if no content provided)
            if document.content_string is not None:
                # Convert content_string to ContentStream
                assert document.content_string is not None  # For MyPy
                content_bytes = document.content_string.encode("utf-8")
                content_stream = ContentStream(io.BytesIO(content_bytes))

                # Create new document with ContentStream
                document = document.model_copy(
                    update={
                        "content": content_stream,
                        "size_bytes": len(content_bytes),
                    }
                )

                self.logger.debug(
                    "Converted content_string to ContentStream",
                    extra={
                        "document_id": document.document_id,
                        "content_length": len(content_bytes),
                    },
                )

            # Store content first and get calculated multihash
            calculated_multihash = await self._store_content(document)

            # Verify and update multihash if needed
            if document.content_multihash != calculated_multihash:
                self.logger.warning(
                    "Provided multihash differs from calculated, using "
                    "calculated",
                    extra={
                        "document_id": document.document_id,
                        "provided_multihash": document.content_multihash,
                        "calculated_multihash": calculated_multihash,
                    },
                )
                document.content_multihash = calculated_multihash

            # Store metadata second (atomic operation)
            await self._store_metadata(document)

            self.logger.info(
                "Document saved successfully",
                extra={
                    "document_id": document.document_id,
                    "content_multihash": calculated_multihash,
                },
            )

        except Exception as e:
            self.logger.error(
                "Failed to save document",
                extra={
                    "document_id": document.document_id,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

    async def generate_id(self) -> str:
        """Generate a unique document identifier."""
        return self.generate_id_with_prefix("doc")

    async def _store_content(self, document: Document) -> str:
        """Store document content to content-addressable storage and return
        multihash."""
        if not document.content:
            raise ValueError(
                f"Document {document.document_id} has no content"
            )

        # Calculate multihash from the content stream
        calculated_multihash = self._calculate_multihash_from_stream(
            document.content
        )
        object_name = calculated_multihash

        try:
            # Check if content already exists (deduplication)
            try:
                self.client.stat_object(
                    bucket_name=self.content_bucket, object_name=object_name
                )
                # Content already exists, no need to store again
                self.logger.debug(
                    "Content already exists, skipping storage",
                    extra={
                        "document_id": document.document_id,
                        "content_multihash": calculated_multihash,
                    },
                )
                return calculated_multihash

            except S3Error as e:
                if getattr(e, "code", None) == "NoSuchKey":
                    # Content doesn't exist, continue to store it
                    pass
                else:
                    raise  # Re-raise if it's another S3 error

            # Store the content using calculated multihash
            content_data = document.content.read()
            self.client.put_object(
                bucket_name=self.content_bucket,
                object_name=object_name,
                data=io.BytesIO(content_data),
                length=len(content_data),
                content_type=document.content_type
                or "application/octet-stream",
                metadata={
                    "document_id": document.document_id,
                    "original_filename": document.original_filename or "",
                },
            )

            self.logger.debug(
                "Content stored successfully",
                extra={
                    "document_id": document.document_id,
                    "content_multihash": calculated_multihash,
                    "content_size": len(content_data),
                },
            )

            return calculated_multihash

        except Exception as e:
            self.logger.error(
                "Failed to store content",
                extra={
                    "document_id": document.document_id,
                    "error": str(e),
                },
            )
            raise

    def _calculate_multihash_from_stream(
        self, content_stream: ContentStream
    ) -> str:
        """Calculate multihash from content stream."""
        if not content_stream:
            raise ValueError("Content stream is required")

        # Read content and calculate SHA-256 hash
        content_data = content_stream.read()
        sha256_hash = hashlib.sha256(content_data).digest()

        # Reset stream position for future reads
        content_stream.seek(0)

        # Create multihash with SHA-256 (code 0x12)
        mhash = multihash.encode(sha256_hash, multihash.SHA2_256)
        return str(mhash.hex())

    async def _store_metadata(self, document: Document) -> None:
        """Store document metadata to Minio with idempotency check."""
        object_name = document.document_id

        # Serialize metadata (content stream and content_string excluded)
        metadata_json = document.model_dump_json(
            exclude={"content", "content_string"}
        ).encode("utf-8")

        try:
            # Check if metadata already exists and is identical (idempotency)
            try:
                existing_response = self.client.get_object(
                    bucket_name=self.metadata_bucket, object_name=object_name
                )
                existing_data = existing_response.read()
                existing_response.close()
                existing_response.release_conn()

                if existing_data == metadata_json:
                    self.logger.debug(
                        "Metadata unchanged, skipping storage",
                        extra={"document_id": document.document_id},
                    )
                    return

            except S3Error as e:
                if getattr(e, "code", None) == "NoSuchKey":
                    # Metadata doesn't exist, continue to store it
                    pass
                else:
                    raise

            # Store the metadata
            self.client.put_object(
                bucket_name=self.metadata_bucket,
                object_name=object_name,
                data=io.BytesIO(metadata_json),
                length=len(metadata_json),
                content_type="application/json",
                metadata={
                    "content_multihash": document.content_multihash or "",
                    "original_filename": document.original_filename or "",
                },
            )

            self.logger.debug(
                "Metadata stored successfully",
                extra={
                    "document_id": document.document_id,
                    "metadata_size": len(metadata_json),
                },
            )

        except Exception as e:
            self.logger.error(
                "Failed to store metadata",
                extra={
                    "document_id": document.document_id,
                    "error": str(e),
                },
            )
            raise
