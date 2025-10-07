"""
Domain layer for julee_example.

This package contains the core business logic and domain models following
Clean Architecture principles. All domain concerns are framework-independent
and have no external dependencies.

Subpackages:
- models: Domain entities and value objects
- repositories: Repository interface protocols
- use_cases: Business logic and application services

Import domain components using their full module paths, e.g.:
    from julee_example.domain.models.document import Document
    from julee_example.domain.repositories.document import DocumentRepository
    from julee_example.domain.use_cases.validate_document import (
        ValidateDocumentUseCase,
    )
"""
