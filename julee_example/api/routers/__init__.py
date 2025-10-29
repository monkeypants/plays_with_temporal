"""
API routers for the julee_example CEAP system.

This package contains APIRouter modules that organize endpoints by domain.
Each router module defines routes at the root level and is mounted with a
prefix in the main app.

Organization:
- knowledge_service_queries: CRUD operations for knowledge service queries
- assembly_specifications: CRUD operations for assembly specifications
- documents: CRUD operations for documents
- workflows: Workflow management and execution endpoints
- system: Health checks and system status endpoints

Router modules follow the pattern:
1. Define routes at root level ("/" and "/{id}")
2. Include proper dependency injection
3. Use domain models for request/response
4. Follow consistent error handling patterns
"""

# Import routers for convenient access
from julee_example.api.routers.knowledge_service_queries import (
    router as knowledge_service_queries_router,
)
from julee_example.api.routers.knowledge_service_configs import (
    router as knowledge_service_configs_router,
)
from julee_example.api.routers.assembly_specifications import (
    router as assembly_specifications_router,
)
from julee_example.api.routers.system import router as system_router
from julee_example.api.routers.documents import router as documents_router
from julee_example.api.routers.workflows import router as workflows_router

__all__ = [
    "knowledge_service_queries_router",
    "knowledge_service_configs_router",
    "assembly_specifications_router",
    "documents_router",
    "workflows_router",
    "system_router",
]
