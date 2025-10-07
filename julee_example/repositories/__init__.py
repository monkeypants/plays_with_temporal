"""
Repository implementations and infrastructure.

This package contains concrete implementations of the repository interfaces
defined in julee_example.domain.repositories.

Implementation packages:
- memory: In-memory implementations for testing
- minio: MinIO-based implementations for production
- temporal: Temporal workflow proxy implementations

Import implementations using their full module paths, e.g.:
    from julee_example.repositories.memory import MemoryDocumentRepository
    from julee_example.repositories.minio.document import (
        MinioDocumentRepository,
    )
"""
