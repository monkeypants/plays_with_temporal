"""
API services package for the julee_example CEAP system.

This package contains service layer components that orchestrate use cases
and provide higher-level application services. Services in this package
act as facades between the API layer and the domain layer, coordinating
multiple use cases and handling cross-cutting concerns.

Services follow clean architecture principles:
- Orchestrate domain use cases
- Handle application-level concerns
- Provide simplified interfaces for controllers
- Maintain separation between API and domain layers
"""

from .system_initialization import SystemInitializationService

__all__ = [
    "SystemInitializationService",
]
