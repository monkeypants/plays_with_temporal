"""
Document domain models for the Capture, Extract, Assemble, Publish workflow.

This module contains the core document domain objects that represent
documents and their metadata in the CEAP workflow system.

All domain models use Pydantic BaseModel for validation, serialization,
and type safety, following the patterns established in the sample project.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from enum import Enum
from .custom_fields import ContentStream


class DocumentStatus(str, Enum):
    """Status of a document through the Capture, Extract, Assemble, Publish
    pipeline."""

    CAPTURED = "captured"
    REGISTERED = "registered"  # Registered with knowledge service
    ASSEMBLY_IDENTIFIED = "assembly_identified"  # Assembly types determined
    EXTRACTED = "extracted"  # Extractions completed
    ASSEMBLED = "assembled"  # Template rendered and policies applied
    PUBLISHED = "published"
    FAILED = "failed"


class Document(BaseModel):
    """Complete document entity including content and metadata.

    This is the primary domain model that represents a complete document
    in the CEAP workflow system. Content is provided as a ContentStream
    for efficient handling of both small and large documents.

    The content stream is excluded from JSON serialization - use separate
    content endpoints for streaming binary data over HTTP.
    """

    # Core document identification
    document_id: str
    original_filename: str
    content_type: str
    size_bytes: int = Field(gt=0, description="Size must be positive")
    content_multihash: str = Field(
        description="Multihash of document content for integrity verification"
    )

    # Document processing state
    status: DocumentStatus = DocumentStatus.CAPTURED
    knowledge_service_id: Optional[str] = None
    assembly_types: List[str] = Field(default_factory=list)

    # Timestamps
    created_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    # Additional data and content stream
    additional_metadata: Dict[str, Any] = Field(default_factory=dict)
    content: ContentStream = Field(exclude=True)

    @field_validator("original_filename")
    @classmethod
    def filename_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Original filename cannot be empty")
        return v.strip()

    @field_validator("content_type")
    @classmethod
    def content_type_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Content type cannot be empty")
        return v.strip()

    @field_validator("content_multihash")
    @classmethod
    def content_multihash_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Content multihash cannot be empty")
        return v.strip()

    def read(self, size: int = -1) -> bytes:
        """Read content from the document stream.

        Args:
            size: Number of bytes to read. -1 reads all content.

        Returns:
            Content bytes from the document stream.
        """
        return self.content.read(size)

    def seek(self, offset: int, whence: int = 0) -> int:
        """Seek to position in document stream.

        Args:
            offset: Offset to seek to
            whence: How to interpret offset (0=absolute, 1=relative, 2=from
                end)

        Returns:
            New absolute position in the stream.
        """
        return self.content.seek(offset, whence)

    def tell(self) -> int:
        """Get current position in document stream."""
        return self.content.tell()
