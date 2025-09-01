"""
Minio implementation of DocumentRepository.

This module provides a Minio-based implementation of the DocumentRepository
protocol that follows the Clean Architecture patterns defined in the
Fun-Police Framework. It handles document storage with both metadata and
content streams, ensuring idempotency and proper error handling.

The implementation separates document metadata (stored as JSON) from content
(stored as content-addressable binary objects) in Minio, following the large
payload handling pattern from the architectural guidelines. """

import io
import logging
import uuid
import hashlib
from datetime import datetime, timezone
from typing import Optional
from minio import Minio  # type: ignore[import-untyped]
from minio.error import S3Error  # type: ignore[import-untyped]
import multihash  # type: ignore[import-untyped]

from julee_example.domain import Document, ContentStream
from julee_example.repositories.document import DocumentRepository

logger = logging.getLogger(__name__)


class MinioDocumentRepository(DocumentRepository):
    """
    Minio implementation of DocumentRepository that uses Minio for persistence.

    This implementation stores document metadata and content separately:
    - Metadata: JSON objects in the "documents" bucket
    - Content: Binary objects in the "documents-content" bucket

    This separation allows for efficient metadata queries while supporting
    large content files without hitting Temporal's 2MB payload limits.
    """

    def __init__(self, endpoint: str):
        minio_endpoint = endpoint
        logger.debug(
            "Initializing MinioDocumentRepository",
            extra={"minio_endpoint": minio_endpoint},
        )

        # TODO: add credential management.
        self.client = Minio(
            minio_endpoint,
            access_key="minioadmin",
            secret_key="minioadmin",
            secure=False,
        )
        self.metadata_bucket = "documents"
        self.content_bucket = "documents-content"
        self._ensure_buckets_exist()

    def _ensure_buckets_exist(self) -> None:
        """Ensure both metadata and content buckets exist."""
        for bucket_name in [self.metadata_bucket, self.content_bucket]:
            try:
                if not self.client.bucket_exists(bucket_name):
                    logger.info(
                        "Creating document bucket",
                        extra={"bucket_name": bucket_name},
                    )
                    self.client.make_bucket(bucket_name)
                else:
                    logger.debug(
                        "Document bucket already exists",
                        extra={"bucket_name": bucket_name},
                    )
            except S3Error as e:
                logger.error(
                    "Failed to create document bucket",
                    extra={"bucket_name": bucket_name, "error": str(e)},
                )
                raise

    async def get(self, document_id: str) -> Optional[Document]:
        """Retrieve a document with metadata and content."""
        logger.debug(
            "MinioDocumentRepository: Attempting to retrieve document from Minio",
            extra={
                "document_id": document_id,
                "metadata_bucket": self.metadata_bucket,
                "content_bucket": self.content_bucket,
            },
        )

        try:
            # First, get the metadata
            metadata_response = self.client.get_object(
                bucket_name=self.metadata_bucket,
                object_name=document_id
            )
            metadata_data = metadata_response.read()
            metadata_response.close()
            metadata_response.release_conn()

            metadata_json = metadata_data.decode("utf-8")

            # Parse metadata without content stream
            document_dict = Document.model_validate_json(metadata_json).model_dump()

            # Now get the content stream using the content multihash as key
            content_multihash = document_dict.get("content_multihash")
            if not content_multihash:
                logger.error(
                    "MinioDocumentRepository: Document metadata missing content_multihash",
                    extra={"document_id": document_id},
                )
                return None

            try:
                content_response = self.client.get_object(
                    bucket_name=self.content_bucket,
                    object_name=content_multihash
                )

                # Create ContentStream directly from the Minio response stream
                # This avoids loading the entire content into memory
                content_stream = ContentStream(content_response)
                document_dict['content'] = content_stream

                logger.info(
                    "MinioDocumentRepository: Document retrieved successfully from Minio",
                    extra={
                        "document_id": document_id,
                        "content_multihash": content_multihash,
                        "original_filename": document_dict.get("original_filename"),
                        "content_type": document_dict.get("content_type"),
                        "size_bytes": document_dict.get("size_bytes"),
                        "status": document_dict.get("status"),
                        "retrieved_at": datetime.now(timezone.utc).isoformat(),
                        "metadata_size_bytes": len(metadata_data),
                    },
                )

                return Document(**document_dict)

            except S3Error as content_error:
                if getattr(content_error, "code", None) == "NoSuchKey":
                    logger.warning(
                        "MinioDocumentRepository: Document metadata found but content missing",
                        extra={
                            "document_id": document_id,
                            "content_multihash": content_multihash,
                            "error_code": "NoSuchKey",
                        },
                    )
                    # Return document without content stream for metadata-only operations
                    document_dict['content'] = ContentStream(io.BytesIO(b""))
                    return Document(**document_dict)
                else:
                    raise content_error

        except S3Error as e:
            if getattr(e, "code", None) == "NoSuchKey":
                logger.debug(
                    "MinioDocumentRepository: Document not found in Minio storage (NoSuchKey)",
                    extra={
                        "document_id": document_id,
                        "error_code": "NoSuchKey",
                    },
                )
                return None
            else:
                logger.error(
                    "MinioDocumentRepository: Error retrieving document metadata from Minio",
                    extra={
                        "document_id": document_id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                    exc_info=True,
                )
                return None
        except Exception as e:
            logger.error(
                "MinioDocumentRepository: Unexpected error during document retrieval",
                extra={
                    "document_id": document_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            return None

    async def store(self, document: Document) -> None:
        """Store a new document with its content and metadata."""
        logger.info(
            "MinioDocumentRepository: Storing document",
            extra={
                "document_id": document.document_id,
                "original_filename": document.original_filename,
                "content_type": document.content_type,
                "size_bytes": document.size_bytes,
                "status": document.status.value,
            },
        )

        try:
            # Store content first and get calculated multihash
            calculated_multihash = await self._store_content(document)

            # Verify and update multihash if needed
            if document.content_multihash != calculated_multihash:
                logger.warning(
                    "MinioDocumentRepository: Provided multihash differs from calculated, using calculated",
                    extra={
                        "document_id": document.document_id,
                        "provided_multihash": document.content_multihash,
                        "calculated_multihash": calculated_multihash,
                    },
                )
                document.content_multihash = calculated_multihash

            # Store metadata second (atomic operation)
            await self._store_metadata(document)

            logger.info(
                "MinioDocumentRepository: Document stored successfully",
                extra={
                    "document_id": document.document_id,
                    "content_multihash": calculated_multihash,
                    "metadata_bucket": self.metadata_bucket,
                    "content_bucket": self.content_bucket,
                },
            )

        except Exception as e:
            logger.error(
                "MinioDocumentRepository: Failed to store document",
                extra={
                    "document_id": document.document_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            raise

    async def update(self, document: Document) -> None:
        """Update a complete document with content and metadata."""
        logger.info(
            "MinioDocumentRepository: Updating document",
            extra={
                "document_id": document.document_id,
                "original_filename": document.original_filename,
                "status": document.status.value,
            },
        )

        # Update the timestamp
        document.updated_at = datetime.now(timezone.utc)

        try:
            # Store content using multihash key and get calculated multihash
            calculated_multihash = await self._store_content(document)

            # Verify and update multihash if needed
            if document.content_multihash != calculated_multihash:
                logger.warning(
                    "MinioDocumentRepository: Provided multihash differs from calculated, using calculated",
                    extra={
                        "document_id": document.document_id,
                        "provided_multihash": document.content_multihash,
                        "calculated_multihash": calculated_multihash,
                    },
                )
                document.content_multihash = calculated_multihash

            # Always update metadata (includes updated_at timestamp)
            await self._store_metadata(document)

            logger.info(
                "MinioDocumentRepository: Document updated successfully",
                extra={
                    "document_id": document.document_id,
                    "content_multihash": calculated_multihash,
                    "updated_at": document.updated_at.isoformat() if document.updated_at else None,
                },
            )

        except Exception as e:
            logger.error(
                "MinioDocumentRepository: Failed to update document",
                extra={
                    "document_id": document.document_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            raise

    async def generate_id(self) -> str:
        """Generate a unique document identifier."""
        document_id = str(uuid.uuid4())

        logger.debug(
            "MinioDocumentRepository: Generated document ID",
            extra={
                "document_id": document_id,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        return document_id

    async def _store_content(self, document: Document) -> str:
        """Store document content to Minio using content multihash as key.

        This provides natural deduplication and immutability - identical content
        is only stored once regardless of how many documents reference it.

        Returns:
            The calculated multihash of the stored content
        """
        # First, calculate the actual multihash from content stream
        document.content.seek(0)
        calculated_multihash = self._calculate_multihash_from_stream(document.content)

        # Use calculated multihash as the key (not provided multihash)
        object_name = calculated_multihash

        try:
            # Check if content already exists (idempotency via content-addressing)
            try:
                # Just check if the object exists - no need to read and compare
                self.client.stat_object(
                    bucket_name=self.content_bucket,
                    object_name=object_name
                )

                logger.debug(
                    "MinioDocumentRepository: Content already exists (content deduplication)",
                    extra={
                        "document_id": document.document_id,
                        "content_multihash": object_name,
                    },
                )
                return calculated_multihash

            except S3Error as e:
                if getattr(e, "code", None) == "NoSuchKey":
                    logger.debug(
                        "MinioDocumentRepository: Content not found, storing new",
                        extra={
                            "document_id": document.document_id,
                            "content_multihash": object_name,
                        },
                    )
                    # Continue to store the content
                else:
                    raise  # Re-raise if it's another S3 error

            # Store the content using calculated multihash
            document.content.seek(0)  # Reset stream position
            # Pass the stream directly to Minio - no need to read into memory
            self.client.put_object(
                bucket_name=self.content_bucket,
                object_name=object_name,
                data=document.content.stream,
                length=document.size_bytes,
                content_type=document.content_type,
                metadata={
                    "content_multihash": calculated_multihash,
                    "content_type": document.content_type,
                    "stored_at": datetime.now(timezone.utc).isoformat(),
                },
            )

            logger.debug(
            "MinioDocumentRepository: Content stored successfully",
            extra={
                "document_id": document.document_id,
                "content_multihash": calculated_multihash,
                "bucket": self.content_bucket,
                "content_size": document.size_bytes,
            },
        )

            return calculated_multihash

        except S3Error as e:
            logger.error(
                "MinioDocumentRepository: Failed to store content to Minio",
                extra={
                    "document_id": document.document_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                "MinioDocumentRepository: Unexpected error during content storage",
                extra={
                    "document_id": document.document_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            raise

    def _calculate_multihash_from_stream(self, stream: io.IOBase, chunk_size: int = 8192) -> str:
        """Calculate SHA-256 multihash from a stream without loading all content into memory.

        Args:
            stream: The content stream to hash
            chunk_size: Size of chunks to read at a time

        Returns:
            Hex-encoded multihash string
        """
        hasher = hashlib.sha256()

        # Process stream in chunks
        while True:
            chunk = stream.read(chunk_size)
            if not chunk:
                break
            if isinstance(chunk, str):
                chunk = chunk.encode('utf-8')
            hasher.update(chunk)

        # Create proper multihash (0x12 = SHA-256, length = 32 bytes)
        mh = multihash.encode(hasher.digest(), 'sha2-256')
        return mh.hex()



    async def _store_metadata(self, document: Document) -> None:
        """Store document metadata to Minio with idempotency check."""
        object_name = document.document_id

        # Serialize metadata (content stream is excluded from serialization)
        metadata_json = document.model_dump_json().encode("utf-8")

        try:
            # Check if metadata already exists and is identical (idempotency)
            try:
                existing_response = self.client.get_object(
                    bucket_name=self.metadata_bucket,
                    object_name=object_name
                )
                existing_data = existing_response.read()
                existing_response.close()
                existing_response.release_conn()

                if existing_data == metadata_json:
                    logger.debug(
                        "MinioDocumentRepository: Metadata already exists with correct data, skipping put (idempotent)",
                        extra={
                            "document_id": document.document_id,
                            "object_name": object_name,
                        },
                    )
                    return
                else:
                    logger.debug(
                        "MinioDocumentRepository: Metadata exists with different data, overwriting",
                        extra={
                            "document_id": document.document_id,
                            "object_name": object_name,
                        },
                    )

            except S3Error as e:
                if getattr(e, "code", None) == "NoSuchKey":
                    logger.debug(
                        "MinioDocumentRepository: Metadata not found, creating new",
                        extra={
                            "document_id": document.document_id,
                            "object_name": object_name,
                        },
                    )
                else:
                    raise  # Re-raise if it's another S3 error

            # Store the metadata
            data_stream = io.BytesIO(metadata_json)
            self.client.put_object(
                bucket_name=self.metadata_bucket,
                object_name=object_name,
                data=data_stream,
                length=len(metadata_json),
                content_type="application/json",
                metadata={
                    "document_id": document.document_id,
                    "status": document.status.value,
                    "stored_at": datetime.now(timezone.utc).isoformat(),
                },
            )

            logger.debug(
                "MinioDocumentRepository: Metadata stored successfully",
                extra={
                    "document_id": document.document_id,
                    "bucket": self.metadata_bucket,
                    "object_name": object_name,
                    "metadata_size": len(metadata_json),
                },
            )

        except S3Error as e:
            logger.error(
                "MinioDocumentRepository: Failed to store metadata to Minio",
                extra={
                    "document_id": document.document_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                "MinioDocumentRepository: Unexpected error during metadata storage",
                extra={
                    "document_id": document.document_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            raise
