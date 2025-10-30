"""
Knowledge Service Queries API router for the julee_example CEAP system.

This module provides the API endpoints for knowledge service queries,
which define how to extract specific data using external knowledge services
during the assembly process.

Routes defined at root level:
- GET / - List knowledge service queries (paginated)
- GET /{query_id} - Get individual query details
- POST / - Create new knowledge service query

These routes are mounted at /knowledge_service_queries in the main app.
"""

import logging
from typing import Optional, cast
from fastapi import APIRouter, Depends, HTTPException, Query
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
    ids: Optional[str] = Query(
        None,
        description="Comma-separated list of query IDs for bulk retrieval",
        openapi_examples={
            "bulk_query": {
                "summary": "Bulk retrieval example",
                "value": "query-123,query-456,query-789",
            }
        },
    ),
    repository: KnowledgeServiceQueryRepository = Depends(  # type: ignore[misc]
        get_knowledge_service_query_repository
    ),
) -> Page[KnowledgeServiceQuery]:
    """
    Get knowledge service queries by IDs or list all with pagination.

    This endpoint supports two modes:
    1. Bulk retrieval: Pass comma-separated IDs to get specific queries
    2. List all: Without IDs parameter, returns paginated list of all queries

    Each query contains the configuration needed to extract specific data
    using external knowledge services.

    Args:
        ids: Optional comma-separated list of query IDs for bulk retrieval

    Returns:
        Page[KnowledgeServiceQuery]: List of queries (bulk) or paginated
            list (all)
    """
    if ids is not None:
        # Check for empty or whitespace-only parameter
        if not ids.strip():
            raise HTTPException(
                status_code=400,
                detail="Invalid ids parameter: must contain at least one "
                "valid ID",
            )

        # Bulk retrieval mode
        logger.info(
            "Bulk knowledge service queries requested",
            extra={"ids_param": ids},
        )

        try:
            # Parse and validate IDs
            id_list = [id.strip() for id in ids.split(",") if id.strip()]
            if not id_list:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid ids parameter: must contain at least "
                    "one valid ID",
                )

            if len(id_list) > 100:  # Reasonable limit
                raise HTTPException(
                    status_code=400,
                    detail="Too many IDs requested: maximum 100 IDs per "
                    "request",
                )

            # Use repository's get_many method
            results = await repository.get_many(id_list)

            # Filter out None results and preserve found queries
            found_queries = [
                query for query in results.values() if query is not None
            ]

            logger.info(
                "Bulk knowledge service queries retrieved successfully",
                extra={
                    "requested_count": len(id_list),
                    "found_count": len(found_queries),
                    "missing_count": len(id_list) - len(found_queries),
                },
            )

            # Return as paginated result for consistent API response format
            return cast(Page[KnowledgeServiceQuery], paginate(found_queries))

        except HTTPException:
            # Re-raise HTTP exceptions (like 400 Bad Request)
            raise
        except Exception as e:
            logger.error(
                "Failed to retrieve bulk knowledge service queries",
                exc_info=True,
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "ids_param": ids,
                },
            )
            raise HTTPException(
                status_code=500,
                detail="Failed to retrieve queries due to an internal error.",
            )
    else:
        # List all mode (existing functionality)
        logger.info("All knowledge service queries requested")

        try:
            # Get all knowledge service queries from the repository
            queries = await repository.list_all()

            logger.info(
                "Knowledge service queries retrieved successfully",
                extra={"count": len(queries)},
            )

            # Use fastapi-pagination to paginate the results
            return cast(Page[KnowledgeServiceQuery], paginate(queries))

        except Exception as e:
            logger.error(
                "Failed to retrieve knowledge service queries",
                exc_info=True,
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
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
        KnowledgeServiceQuery: The created query with generated ID and
            timestamps
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


@router.get("/{query_id}", response_model=KnowledgeServiceQuery)
async def get_knowledge_service_query(
    query_id: str,
    repository: KnowledgeServiceQueryRepository = Depends(  # type: ignore[misc]
        get_knowledge_service_query_repository
    ),
) -> KnowledgeServiceQuery:
    """
    Get a specific knowledge service query by ID.

    Args:
        query_id: The ID of the query to retrieve
        repository: Injected repository for data access

    Returns:
        KnowledgeServiceQuery: The requested query

    Raises:
        HTTPException: 404 if query not found, 500 for internal errors
    """
    logger.info(
        "Knowledge service query detail requested",
        extra={"query_id": query_id},
    )

    try:
        query = await repository.get(query_id)

        if query is None:
            logger.warning(
                "Knowledge service query not found",
                extra={"query_id": query_id},
            )
            raise HTTPException(
                status_code=404,
                detail=f"Knowledge service query with ID '{query_id}' "
                "not found",
            )

        logger.info(
            "Knowledge service query retrieved successfully",
            extra={
                "query_id": query.query_id,
                "query_name": query.name,
            },
        )

        return query

    except HTTPException:
        # Re-raise HTTP exceptions (like 404 Not Found)
        raise
    except Exception as e:
        logger.error(
            "Failed to retrieve knowledge service query",
            exc_info=True,
            extra={
                "error_type": type(e).__name__,
                "error_message": str(e),
                "query_id": query_id,
            },
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve query due to an internal error.",
        )
