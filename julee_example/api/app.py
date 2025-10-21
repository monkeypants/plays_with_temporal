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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_pagination import add_pagination
from fastapi_pagination.utils import disable_installed_extensions_check

from julee_example.api.routers import (
    assembly_specifications_router,
    knowledge_service_queries_router,
    knowledge_service_configs_router,
    system_router,
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

# Create FastAPI app
app = FastAPI(
    title="Julee Example CEAP API",
    description="API for the Capture, Extract, Assemble, Publish workflow",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
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


if __name__ == "__main__":
    uvicorn.run(
        "julee_example.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
