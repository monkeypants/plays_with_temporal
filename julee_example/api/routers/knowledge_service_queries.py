"""
Knowledge Service Queries API router for the julee_example CEAP system.

This module provides the API endpoints for knowledge service queries,
which define how to extract specific data using external knowledge services
during the assembly process.

Routes defined at root level:
- GET / - List knowledge service queries (paginated)
- POST / - Create new knowledge service query

These routes are mounted at /knowledge_service_queries in the main app.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi_pagination import Page, paginate

from julee_example.domain.models import KnowledgeServiceQuery
from julee_example.domain.repositories.knowledge_service_query import (
    KnowledgeServiceQueryRepository,
)
from julee_example.api.dependencies import (
    get_knowledge_service_query_repository,
)
from julee_example.api.requests import CreateKnowledgeServiceQueryRequest

logger = logging.getLogger(__name__)

# Create the router for knowledge service queries
router = APIRouter()


@router.get("/", response_model=Page[KnowledgeServiceQuery])
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


@router.post("/", response_model=KnowledgeServiceQuery)
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
