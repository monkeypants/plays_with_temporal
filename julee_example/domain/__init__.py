"""
Domain layer for julee_example.

This package contains the core business logic and domain models following
Clean Architecture principles. All domain concerns are framework-independent
and have no external dependencies.

Subpackages:
- models: Domain entities and value objects
- repositories: Repository interface protocols
- use_cases: Business logic and application services

Import domain components using package imports for convenience, e.g.:
    # Models from the models package
    from julee_example.domain.models import Document, Assembly, Policy

    # Repository protocols from the repositories package
    from julee_example.domain.repositories import DocumentRepository

    # Use cases from the use_cases package
    from julee_example.domain.use_cases import ValidateDocumentUseCase
"""
