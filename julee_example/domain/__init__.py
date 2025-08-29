"""
Domain models for the Capture, Extract, Assemble, Publish workflow.

This module contains the core domain objects that represent the business
entities and value objects used throughout the Capture, Extract, Assemble,
Publish workflow system.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class DocumentStatus(Enum):
    """Status of a document through the Capture, Extract, Assemble, Publish
    pipeline."""

    CAPTURED = "captured"
    REGISTERED = "registered"  # Registered with knowledge service
    ASSEMBLY_IDENTIFIED = "assembly_identified"  # Assembly types determined
    EXTRACTED = "extracted"  # Extractions completed
    ASSEMBLED = "assembled"  # Template rendered and policies applied
    PUBLISHED = "published"
    FAILED = "failed"


class DocumentMetadata:
    """Metadata associated with a document."""

    def __init__(
        self,
        document_id: str,
        original_filename: str,
        content_type: str,
        size_bytes: int,
        status: DocumentStatus = DocumentStatus.CAPTURED,
        knowledge_service_id: Optional[str] = None,
        assembly_types: Optional[List[str]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        **kwargs
    ):
        self.document_id = document_id
        self.original_filename = original_filename
        self.content_type = content_type
        self.size_bytes = size_bytes
        self.status = status
        self.knowledge_service_id = knowledge_service_id
        self.assembly_types = assembly_types or []
        self.created_at = created_at
        self.updated_at = updated_at
        self.additional_metadata = kwargs


class ExtractionResult:
    """Result of an extraction operation."""

    def __init__(
        self,
        extractor_name: str,
        extracted_data: Dict[str, Any],
        success: bool,
        error_message: Optional[str] = None,
    ):
        self.extractor_name = extractor_name
        self.extracted_data = extracted_data
        self.success = success
        self.error_message = error_message


class AssemblySpec:
    """Specification for a document assembly type."""

    def __init__(
        self,
        assembly_id: str,
        template_path: str,
        required_extractors: List[str],
        pre_transform_policies: List[str],
        transform_policies: List[str],
        post_transform_policies: List[str],
    ):
        self.assembly_id = assembly_id
        self.template_path = template_path
        self.required_extractors = required_extractors
        self.pre_transform_policies = pre_transform_policies
        self.transform_policies = transform_policies
        self.post_transform_policies = post_transform_policies
