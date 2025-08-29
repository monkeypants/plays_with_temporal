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


class DocumentMetadata(BaseModel):
    """Metadata associated with a document."""

    document_id: str
    original_filename: str
    content_type: str
    size_bytes: int = Field(gt=0, description="Size must be positive")
    status: DocumentStatus = DocumentStatus.CAPTURED
    knowledge_service_id: Optional[str] = None
    assembly_types: List[str] = Field(default_factory=list)
    created_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    additional_metadata: Dict[str, Any] = Field(default_factory=dict)

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


class Document(BaseModel):
    """Complete document entity including content and metadata.

    This is the primary domain model that represents a complete document
    in the CEAP workflow system. For performance reasons, content is
    optional to support lazy loading scenarios.
    """

    metadata: DocumentMetadata
    content: Optional[bytes] = None

    @property
    def document_id(self) -> str:
        """Convenience property to access document ID."""
        return self.metadata.document_id

    @property
    def status(self) -> DocumentStatus:
        """Convenience property to access document status."""
        return self.metadata.status

    def with_status(self, status: DocumentStatus) -> "Document":
        """Return a new Document with updated status.

        Note: I'm not sure that we'll want to provide direct access to update
        the status like this, instead using a state pattern.
        """
        updated_metadata = self.metadata.model_copy(
            update={
                "status": status,
                "updated_at": datetime.now(timezone.utc)
            }
        )
        return self.model_copy(update={"metadata": updated_metadata})

    def with_knowledge_service_id(
        self, knowledge_service_id: str
    ) -> "Document":
        """Return a new Document with knowledge service ID."""
        updated_metadata = self.metadata.model_copy(
            update={
                "knowledge_service_id": knowledge_service_id,
                "updated_at": datetime.now(timezone.utc)
            }
        )
        return self.model_copy(update={"metadata": updated_metadata})

    def with_assembly_types(self, assembly_types: List[str]) -> "Document":
        """Return a new Document with updated assembly types."""
        updated_metadata = self.metadata.model_copy(
            update={
                "assembly_types": assembly_types,
                "updated_at": datetime.now(timezone.utc)
            }
        )
        return self.model_copy(update={"metadata": updated_metadata})
