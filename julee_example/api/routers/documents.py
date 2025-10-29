"""
Documents API router for the julee_example CEAP system.

This module provides document management API endpoints for retrieving
and managing documents in the system.

Routes defined at root level:
- GET /documents - List all documents with pagination

These routes are mounted with '/documents' prefix in the main app.
"""

import logging
from typing import cast

from fastapi import APIRouter, Depends, HTTPException
from fastapi_pagination import Page, paginate

from julee_example.domain.models.document import Document
from julee_example.domain.repositories.document import DocumentRepository
from julee_example.api.dependencies import get_document_repository

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=Page[Document])
async def list_documents(
    repository: DocumentRepository = Depends(get_document_repository),
) -> Page[Document]:
    """
    List all documents with pagination.

    Args:
        repository: Document repository dependency

    Returns:
        Paginated list of documents

    Raises:
        HTTPException: If repository operation fails
    """
    try:
        logger.info("Listing documents")

        # Get all documents from repository
        documents = await repository.list_all()

        logger.info(f"Retrieved {len(documents)} documents")

        # Return paginated result using fastapi-pagination
        return cast(Page[Document], paginate(documents))

    except Exception as e:
        logger.error(f"Failed to list documents: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve documents"
        ) from e
