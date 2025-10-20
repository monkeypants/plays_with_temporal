"""
Assembly Specifications API router for the julee_example CEAP system.

This module provides the API endpoints for assembly specifications,
which define how to assemble documents of specific types including
JSON schemas and knowledge service query configurations.

Routes defined at root level:
- GET / - List assembly specifications (paginated)
- GET /{id} - Get a specific assembly specification by ID

These routes are mounted at /assembly_specifications in the main app.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi_pagination import Page, paginate

from julee_example.domain.models import AssemblySpecification
from julee_example.domain.repositories.assembly_specification import (
    AssemblySpecificationRepository,
)
from julee_example.api.dependencies import (
    get_assembly_specification_repository,
)

logger = logging.getLogger(__name__)

# Create the router for assembly specifications
router = APIRouter()


@router.get("/", response_model=Page[AssemblySpecification])
async def get_assembly_specifications(
    repository: AssemblySpecificationRepository = Depends(  # type: ignore[misc]
        get_assembly_specification_repository
    ),
) -> Page[AssemblySpecification]:
    """
    Get a paginated list of assembly specifications.

    This endpoint returns all assembly specifications in the system
    with pagination support. Each specification contains the configuration
    needed to define how to assemble documents of specific types.

    Returns:
        Page[AssemblySpecification]: Paginated list of specifications
    """
    logger.info("Assembly specifications requested")

    try:
        # Get all assembly specifications from the repository
        specifications = await repository.list_all()

        logger.info(
            "Assembly specifications retrieved successfully",
            extra={"count": len(specifications)},
        )

        # Use fastapi-pagination to paginate the results
        return paginate(specifications)  # type: ignore[no-any-return]

    except Exception as e:
        logger.error(
            "Failed to retrieve assembly specifications",
            exc_info=True,
            extra={"error_type": type(e).__name__, "error_message": str(e)},
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve specifications due to an internal error.",
        )


@router.get(
    "/{assembly_specification_id}", response_model=AssemblySpecification
)
async def get_assembly_specification(
    assembly_specification_id: str = Path(
        description="The ID of the assembly specification to retrieve"
    ),
    repository: AssemblySpecificationRepository = Depends(  # type: ignore[misc]
        get_assembly_specification_repository
    ),
) -> AssemblySpecification:
    """
    Get a specific assembly specification by ID.

    This endpoint retrieves a single assembly specification by its unique
    identifier. The specification contains the JSON schema and knowledge
    service query configurations needed for document assembly.

    Args:
        assembly_specification_id: The unique ID of the specification

    Returns:
        AssemblySpecification: The requested specification

    Raises:
        HTTPException: 404 if specification not found, 500 for other errors
    """
    logger.info(
        "Assembly specification requested",
        extra={"assembly_specification_id": assembly_specification_id},
    )

    try:
        # Get the specific assembly specification from the repository
        specification = await repository.get(assembly_specification_id)

        if specification is None:
            logger.warning(
                "Assembly specification not found",
                extra={
                    "assembly_specification_id": assembly_specification_id
                },
            )
            raise HTTPException(
                status_code=404,
                detail=f"Assembly specification with ID '{assembly_specification_id}' not found.",
            )

        logger.info(
            "Assembly specification retrieved successfully",
            extra={
                "assembly_specification_id": assembly_specification_id,
                "specification_name": specification.name,
            },
        )

        return specification

    except HTTPException:
        # Re-raise HTTP exceptions (like 404)
        raise
    except Exception as e:
        logger.error(
            "Failed to retrieve assembly specification",
            exc_info=True,
            extra={
                "error_type": type(e).__name__,
                "error_message": str(e),
                "assembly_specification_id": assembly_specification_id,
            },
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve specification due to an internal error.",
        )
