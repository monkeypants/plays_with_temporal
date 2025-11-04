"""
FastAPI application for julee_example CEAP workflow system.

This module provides the HTTP API layer for the Capture, Extract, Assemble,
Publish workflow system. It follows clean architecture principles with
proper dependency injection and error handling.

The API provides endpoints for:
- Knowledge service queries (CRUD operations)
- Assembly specifications (CRUD operations)
- Health checks and system status

All endpoints use domain models for responses and follow RESTful conventions
with proper HTTP status codes and error handling.
"""

import logging
import uvicorn
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Any, Callable

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_pagination import add_pagination
from fastapi_pagination.utils import disable_installed_extensions_check

from julee_example.api.routers import (
    assembly_specifications_router,
    knowledge_service_queries_router,
    knowledge_service_configs_router,
    system_router,
    documents_router,
    workflows_router,
)
from julee_example.api.dependencies import (
    get_startup_dependencies,
    get_knowledge_service_config_repository,
)

# Disable pagination extensions check for cleaner startup
disable_installed_extensions_check()

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
        ],
    )

    # Set specific log levels
    logging.getLogger("julee_example").setLevel(logging.DEBUG)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("uvicorn").setLevel(logging.INFO)


# Setup logging
setup_logging()


def resolve_dependency(
    app: FastAPI, dependency_func: Callable[[], Any]
) -> Any:
    """Resolve a dependency, respecting test overrides."""
    override = app.dependency_overrides.get(dependency_func)
    return override() if override else dependency_func()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for application startup and shutdown."""
    # Startup
    logger.info("Starting application initialization")

    try:
        # Check if we're in test mode by looking for repository overrides
        if (
            get_knowledge_service_config_repository
            in app.dependency_overrides
        ):
            logger.info("Test mode detected, skipping system initialization")
        else:
            # Normal production initialization
            startup_deps = await resolve_dependency(
                app, get_startup_dependencies
            )
            service = await startup_deps.get_system_initialization_service()

            # Execute initialization
            results = await service.initialize()

            logger.info(
                "Application initialization completed successfully",
                extra={
                    "initialization_results": results,
                    "tasks_completed": results.get("tasks_completed", []),
                },
            )

    except Exception as e:
        logger.error(
            "Application initialization failed",
            exc_info=True,
            extra={
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
        )
        # Re-raise to prevent application startup if critical init fails
        raise

    yield

    # Shutdown (if needed)
    logger.info("Application shutdown")


# Create FastAPI app
app = FastAPI(
    title="Julee Example CEAP API",
    description="API for the Capture, Extract, Assemble, Publish workflow",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add pagination support
_ = add_pagination(app)


# Include routers
app.include_router(system_router, tags=["System"])

app.include_router(
    knowledge_service_queries_router,
    prefix="/knowledge_service_queries",
    tags=["Knowledge Service Queries"],
)

app.include_router(
    knowledge_service_configs_router,
    prefix="/knowledge_service_configs",
    tags=["Knowledge Service Configs"],
)

app.include_router(
    assembly_specifications_router,
    prefix="/assembly_specifications",
    tags=["Assembly Specifications"],
)

app.include_router(
    documents_router,
    prefix="/documents",
    tags=["Documents"],
)

app.include_router(
    workflows_router,
    prefix="/workflows",
    tags=["Workflows"],
)


if __name__ == "__main__":
    uvicorn.run(
        "julee_example.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
