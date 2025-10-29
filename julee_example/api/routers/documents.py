"""
Documents API router for the julee_example CEAP system.

This module provides document management API endpoints for retrieving
and managing documents in the system.

Routes defined at root level:
- GET / - List all documents with pagination
- GET /{document_id} - Get document metadata by ID
- GET /{document_id}/content - Get document content by ID

These routes are mounted with '/documents' prefix in the main app.
"""

import logging
from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi.responses import Response
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

        logger.info("Retrieved %d documents", len(documents))

        # Return paginated result using fastapi-pagination
        return cast(Page[Document], paginate(documents))

    except Exception as e:
        logger.error("Failed to list documents: %s", e)
        raise HTTPException(
            status_code=500, detail="Failed to retrieve documents"
        ) from e


@router.get("/{document_id}", response_model=Document)
async def get_document(
    document_id: str = Path(..., description="Document ID"),
    repository: DocumentRepository = Depends(get_document_repository),
) -> Document:
    """
    Get a single document by ID with metadata only.

    Args:
        document_id: Unique document identifier
        repository: Document repository dependency

    Returns:
        Document with metadata only (no content)

    Raises:
        HTTPException: If document not found or repository operation fails
    """
    try:
        logger.info("Retrieving document metadata: %s", document_id)

        # Get document from repository
        document = await repository.get(document_id)

        if not document:
            raise HTTPException(
                status_code=404,
                detail=f"Document with ID '{document_id}' not found",
            )

        logger.info("Retrieved document metadata: %s", document_id)
        return document

    except HTTPException:
        # Re-raise HTTP exceptions (like 404) without wrapping
        raise
    except Exception as e:
        logger.error("Failed to get document %s: %s", document_id, e)
        raise HTTPException(
            status_code=500, detail="Failed to retrieve document"
        ) from e


@router.get("/{document_id}/content")
async def get_document_content(
    document_id: str = Path(..., description="Document ID"),
    repository: DocumentRepository = Depends(get_document_repository),
) -> Response:
    """
    Get the content of a document by ID.

    Args:
        document_id: Unique document identifier
        repository: Document repository dependency

    Returns:
        Raw document content with appropriate Content-Type header

    Raises:
        HTTPException: If document not found or has no content
    """
    try:
        logger.info("Retrieving document content: %s", document_id)

        # Get document from repository
        document = await repository.get(document_id)

        if not document:
            raise HTTPException(
                status_code=404,
                detail=f"Document with ID '{document_id}' not found",
            )

        if not document.content:
            raise HTTPException(
                status_code=422,
                detail=f"Document '{document_id}' has no content",
            )

        try:
            # Read content
            content_bytes = document.content.read()

            logger.info(
                "Retrieved document content: %s (%d bytes)",
                document_id,
                len(content_bytes),
            )

            # Return content with appropriate Content-Type
            return Response(
                content=content_bytes,
                media_type=document.content_type,
                headers={
                    "Content-Disposition": (
                        f'inline; filename="{document.original_filename}"'
                    )
                },
            )

        except Exception as content_error:
            logger.error(
                "Failed to read content for document %s: %s",
                document_id,
                content_error,
            )
            raise HTTPException(
                status_code=500, detail="Failed to read document content"
            ) from content_error

    except HTTPException:
        # Re-raise HTTP exceptions (like 404) without wrapping
        raise
    except Exception as e:
        logger.error("Failed to get document content %s: %s", document_id, e)
        raise HTTPException(
            status_code=500, detail="Failed to retrieve document content"
        ) from e
