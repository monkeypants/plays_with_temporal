"""
Knowledge Service Configs API router for the julee_example CEAP system.

This module provides the API endpoints for knowledge service configurations,
which define the available knowledge services that can be used for extracting
data during the assembly process.

Routes defined at root level:
- GET / - List all knowledge service configurations (paginated)

These routes are mounted at /knowledge_service_configs in the main app.
"""

import logging
from typing import cast
from fastapi import APIRouter, Depends, HTTPException
from fastapi_pagination import Page, paginate

from julee_example.domain.models.knowledge_service_config import (
    KnowledgeServiceConfig,
)
from julee_example.domain.repositories.knowledge_service_config import (
    KnowledgeServiceConfigRepository,
)
from julee_example.api.dependencies import (
    get_knowledge_service_config_repository,
)

logger = logging.getLogger(__name__)

# Create the router for knowledge service configurations
router = APIRouter()


@router.get("/", response_model=Page[KnowledgeServiceConfig])
async def get_knowledge_service_configs(
    repository: KnowledgeServiceConfigRepository = Depends(  # type: ignore[misc]
        get_knowledge_service_config_repository
    ),
) -> Page[KnowledgeServiceConfig]:
    """
    Get all knowledge service configurations with pagination.

    This endpoint returns all available knowledge service configurations
    that can be used when creating knowledge service queries. Each
    configuration contains the metadata needed to interact with a specific
    external knowledge service.

    Returns:
        Page[KnowledgeServiceConfig]: Paginated list of all knowledge
            service configurations
    """
    logger.info("All knowledge service configurations requested")

    try:
        # Get all knowledge service configurations from the repository
        configs = await repository.list_all()

        logger.info(
            "Knowledge service configurations retrieved successfully",
            extra={"count": len(configs)},
        )

        # Use fastapi-pagination to paginate the results
        return cast(Page[KnowledgeServiceConfig], paginate(configs))

    except Exception as e:
        logger.error(
            "Failed to retrieve knowledge service configurations",
            exc_info=True,
            extra={
                "error_type": type(e).__name__,
                "error_message": str(e),
            },
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve configurations due to an "
            "internal error.",
        )
