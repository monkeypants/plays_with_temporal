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
from datetime import datetime, timezone


from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi_pagination import Page, add_pagination, paginate
from fastapi_pagination.utils import disable_installed_extensions_check

from julee_example.domain.models import KnowledgeServiceQuery
from julee_example.domain.repositories.knowledge_service_query import (
    KnowledgeServiceQueryRepository,
)
from julee_example.api.dependencies import (
    get_knowledge_service_query_repository,
)
from julee_example.api.responses import HealthCheckResponse
from julee_example.api.requests import CreateKnowledgeServiceQueryRequest

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


@app.get("/health", response_model=HealthCheckResponse)
async def health_check() -> HealthCheckResponse:
    """Health check endpoint."""
    return HealthCheckResponse(
        status="healthy",
        version="0.1.0",
        timestamp=datetime.now(timezone.utc),
    )


@app.get(
    "/knowledge_service_queries", response_model=Page[KnowledgeServiceQuery]
)
async def get_knowledge_service_queries(
    repository: KnowledgeServiceQueryRepository = Depends(  # type: ignore[misc]
        get_knowledge_service_query_repository
    ),
) -> Page[KnowledgeServiceQuery]:
    """
    Get a paginated list of knowledge service queries.

    This endpoint returns all knowledge service queries in the system
    with pagination support. Each query contains the configuration needed to
    extract specific data using external knowledge services.

    Returns:
        Page[KnowledgeServiceQuery]: Paginated list of queries
    """
    logger.info("Knowledge service queries requested")

    try:
        # Get all knowledge service queries from the repository
        queries = await repository.list_all()

        logger.info(
            "Knowledge service queries retrieved successfully",
            extra={"count": len(queries)},
        )

        # Use fastapi-pagination to paginate the results
        return paginate(queries)  # type: ignore[no-any-return]

    except Exception as e:
        logger.error(
            "Failed to retrieve knowledge service queries",
            exc_info=True,
            extra={"error_type": type(e).__name__, "error_message": str(e)},
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve queries due to an internal error.",
        )


@app.post("/knowledge_service_queries", response_model=KnowledgeServiceQuery)
async def create_knowledge_service_query(
    request: CreateKnowledgeServiceQueryRequest,
    repository: KnowledgeServiceQueryRepository = Depends(  # type: ignore[misc]
        get_knowledge_service_query_repository
    ),
) -> KnowledgeServiceQuery:
    """
    Create a new knowledge service query.

    This endpoint creates a new knowledge service query configuration that
    defines how to extract specific data using external knowledge services
    during the assembly process.

    Args:
        request: The knowledge service query creation request
        repository: Injected repository for persistence

    Returns:
        KnowledgeServiceQuery: The created query with generated ID and timestamps
    """
    logger.info(
        "Knowledge service query creation requested",
        extra={"query_name": request.name},
    )

    try:
        # Generate unique ID for the new query
        query_id = await repository.generate_id()

        # Convert request to domain model with generated ID
        query = request.to_domain_model(query_id)

        # Save the query via repository
        await repository.save(query)

        logger.info(
            "Knowledge service query created successfully",
            extra={
                "query_id": query.query_id,
                "query_name": query.name,
                "knowledge_service_id": query.knowledge_service_id,
            },
        )

        return query

    except Exception as e:
        logger.error(
            "Failed to create knowledge service query",
            exc_info=True,
            extra={
                "error_type": type(e).__name__,
                "error_message": str(e),
                "query_name": request.name,
            },
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to create query due to an internal error.",
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "julee_example.api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
