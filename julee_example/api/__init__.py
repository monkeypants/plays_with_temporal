"""
FastAPI interface adapters for the julee_example CEAP workflow system.

This package contains the HTTP API layer that provides external access to the
CEAP (Capture, Extract, Assemble, Publish) workflow functionality.

The API follows clean architecture patterns:
- Request models for external client contracts (API-specific validation)
- Domain models returned directly as responses (no wrapper models needed)
- Dependency injection for use cases and repositories
- HTTPException for error responses with appropriate status codes

Modules:
- requests: Pydantic models for API request validation
- responses: Minimal API-specific response models (health checks, etc.)
- app: FastAPI application setup and endpoint definitions
- dependencies: Dependency injection configuration
"""

__all__: list[str] = []
