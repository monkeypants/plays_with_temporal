"""
Minio repository implementations for julee_example domain.

This module exports Minio-based implementations of all repository protocols
for the Capture, Extract, Assemble, Publish workflow. These implementations
use Minio for object storage and are suitable for production environments
where persistent, scalable storage is required.

All implementations maintain the same async interfaces as their memory
counterparts while providing durable, distributed storage capabilities.
"""

from .assembly import MinioAssemblyRepository
from .assembly_specification import MinioAssemblySpecificationRepository
from .document import MinioDocumentRepository
from .document_policy_validation import (
    MinioDocumentPolicyValidationRepository,
)
from .knowledge_service_config import MinioKnowledgeServiceConfigRepository
from .knowledge_service_query import MinioKnowledgeServiceQueryRepository
from .policy import MinioPolicyRepository

__all__ = [
    "MinioAssemblyRepository",
    "MinioAssemblySpecificationRepository",
    "MinioDocumentRepository",
    "MinioDocumentPolicyValidationRepository",
    "MinioKnowledgeServiceConfigRepository",
    "MinioKnowledgeServiceQueryRepository",
    "MinioPolicyRepository",
]
