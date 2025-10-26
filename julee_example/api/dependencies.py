"""
Dependency injection for julee_example FastAPI endpoints.

This module provides dependency injection for the julee_example API endpoints,
following the same patterns established in the sample project. It manages
singleton lifecycle for expensive resources and provides clean separation
between infrastructure concerns and business logic.

The dependencies focus on real Minio implementations for production use,
with test overrides available through FastAPI's dependency override system.
"""

import os
import logging
from typing import Any, Dict

from fastapi import Depends
from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter

from julee_example.domain.repositories.knowledge_service_query import (
    KnowledgeServiceQueryRepository,
)
from julee_example.domain.repositories.knowledge_service_config import (
    KnowledgeServiceConfigRepository,
)
from julee_example.domain.repositories.assembly_specification import (
    AssemblySpecificationRepository,
)
from julee_example.repositories.minio.knowledge_service_query import (
    MinioKnowledgeServiceQueryRepository,
)
from julee_example.repositories.minio.knowledge_service_config import (
    MinioKnowledgeServiceConfigRepository,
)
from julee_example.repositories.minio.assembly_specification import (
    MinioAssemblySpecificationRepository,
)
from julee_example.repositories.minio.client import MinioClient
from minio import Minio

logger = logging.getLogger(__name__)


class DependencyContainer:
    """
    Dependency injection container with singleton lifecycle management.
    Always creates real clients; mocks are provided by test overrides.
    """

    def __init__(self) -> None:
        self._instances: Dict[str, Any] = {}

    async def get_or_create(self, key: str, factory: Any) -> Any:
        """Get or create a singleton instance."""
        if key not in self._instances:
            self._instances[key] = await factory()
        return self._instances[key]

    async def get_temporal_client(self) -> Client:
        """Get or create Temporal client."""
        client = await self.get_or_create(
            "temporal_client", self._create_temporal_client
        )
        return client  # type: ignore[no-any-return]

    async def _create_temporal_client(self) -> Client:
        """Create Temporal client with proper configuration."""
        temporal_endpoint = os.environ.get(
            "TEMPORAL_ENDPOINT", "temporal:7233"
        )
        logger.debug(
            "Creating Temporal client",
            extra={"endpoint": temporal_endpoint, "namespace": "default"},
        )

        client = await Client.connect(
            temporal_endpoint,
            namespace="default",
            data_converter=pydantic_data_converter,
        )

        logger.debug(
            "Temporal client created",
            extra={
                "endpoint": temporal_endpoint,
                "data_converter_type": type(client.data_converter).__name__,
            },
        )
        return client

    async def get_minio_client(self) -> MinioClient:
        """Get or create Minio client."""
        client = await self.get_or_create(
            "minio_client", self._create_minio_client
        )
        return client  # type: ignore[no-any-return]

    async def _create_minio_client(self) -> MinioClient:
        """Create Minio client with proper configuration."""
        endpoint = os.environ.get("MINIO_ENDPOINT", "localhost:9000")
        access_key = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
        secret_key = os.environ.get("MINIO_SECRET_KEY", "minioadmin")
        secure = os.environ.get("MINIO_SECURE", "false").lower() == "true"

        logger.debug(
            "Creating Minio client",
            extra={
                "endpoint": endpoint,
                "secure": secure,
                "access_key": access_key[:4] + "***",  # Log partial key only
            },
        )

        # Create the actual minio client which implements MinioClient protocol
        client = Minio(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )

        logger.debug("Minio client created", extra={"endpoint": endpoint})
        return client  # type: ignore[return-value]


# Global container instance
_container = DependencyContainer()


async def get_temporal_client() -> Client:
    """FastAPI dependency for Temporal client."""
    return await _container.get_temporal_client()


async def get_minio_client() -> MinioClient:
    """FastAPI dependency for Minio client."""
    return await _container.get_minio_client()


async def get_knowledge_service_query_repository(
    minio_client: MinioClient = Depends(get_minio_client),
) -> KnowledgeServiceQueryRepository:
    """FastAPI dependency for KnowledgeServiceQueryRepository."""
    return MinioKnowledgeServiceQueryRepository(client=minio_client)


async def get_knowledge_service_config_repository(
    minio_client: MinioClient = Depends(get_minio_client),
) -> KnowledgeServiceConfigRepository:
    """FastAPI dependency for KnowledgeServiceConfigRepository."""
    return MinioKnowledgeServiceConfigRepository(client=minio_client)


async def get_assembly_specification_repository(
    minio_client: MinioClient = Depends(get_minio_client),
) -> AssemblySpecificationRepository:
    """FastAPI dependency for AssemblySpecificationRepository."""
    return MinioAssemblySpecificationRepository(client=minio_client)


# Note: Use cases and more complex dependencies can be added here as needed
# following the same pattern. For simple CRUD operations like listing
# queries, we can use the repository directly in the endpoint.
