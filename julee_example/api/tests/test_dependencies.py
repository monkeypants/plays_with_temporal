"""
Tests for dependency injection components.

This module tests the dependency injection utilities, particularly the
StartupDependenciesProvider that provides clean access to dependencies
during application startup without exposing internal container details.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from julee_example.api.dependencies import (
    StartupDependenciesProvider,
    DependencyContainer,
    get_startup_dependencies,
)


@pytest.fixture
def mock_container() -> AsyncMock:
    """Create mock dependency container."""
    return AsyncMock(spec=DependencyContainer)


@pytest.fixture
def mock_minio_client() -> MagicMock:
    """Create mock Minio client."""
    return MagicMock()


@pytest.fixture
def startup_provider(
    mock_container: AsyncMock,
) -> StartupDependenciesProvider:
    """Create startup dependencies provider with mock container."""
    return StartupDependenciesProvider(mock_container)


class TestStartupDependenciesProvider:
    """Test the StartupDependenciesProvider."""

    def test_initialization(self, mock_container: AsyncMock) -> None:
        """Test provider initialization."""
        provider = StartupDependenciesProvider(mock_container)

        assert provider.container == mock_container
        assert provider.logger is not None

    @pytest.mark.asyncio
    async def test_get_knowledge_service_config_repository(
        self,
        startup_provider: StartupDependenciesProvider,
        mock_container: AsyncMock,
        mock_minio_client: MagicMock,
    ) -> None:
        """Test getting knowledge service config repository."""
        # Setup mock
        mock_container.get_minio_client.return_value = mock_minio_client

        # Get repository
        repo = (
            await startup_provider.get_knowledge_service_config_repository()
        )

        # Verify container was called
        mock_container.get_minio_client.assert_called_once()

        # Verify repository was created with correct client
        assert repo is not None
        # Note: We can't easily test the internal client without exposing
        # implementation details, but we can verify the method completed

    @pytest.mark.asyncio
    async def test_get_system_initialization_service(
        self,
        startup_provider: StartupDependenciesProvider,
        mock_container: AsyncMock,
        mock_minio_client: MagicMock,
    ) -> None:
        """Test getting system initialization service."""
        # Setup mock
        mock_container.get_minio_client.return_value = mock_minio_client

        # Get service
        service = await startup_provider.get_system_initialization_service()

        # Verify service was created
        assert service is not None
        assert hasattr(service, "initialize")

        # Verify container was called to create dependencies
        # The service may need multiple minio clients for different repos
        assert mock_container.get_minio_client.call_count >= 1

    @pytest.mark.asyncio
    async def test_get_system_initialization_service_creates_full_chain(
        self,
        startup_provider: StartupDependenciesProvider,
        mock_container: AsyncMock,
        mock_minio_client: MagicMock,
    ) -> None:
        """Test that service creation builds the complete dependency chain."""
        # Setup mock
        mock_container.get_minio_client.return_value = mock_minio_client

        # Get service
        service = await startup_provider.get_system_initialization_service()

        # Verify the service has the expected structure
        assert service is not None
        assert hasattr(service, "initialize_system_data_use_case")
        assert service.initialize_system_data_use_case is not None

        # Verify the use case has the repositories
        use_case = service.initialize_system_data_use_case
        assert hasattr(use_case, "config_repo")
        assert use_case.config_repo is not None
        assert hasattr(use_case, "document_repo")
        assert use_case.document_repo is not None
        assert hasattr(use_case, "query_repo")
        assert use_case.query_repo is not None
        assert hasattr(use_case, "assembly_spec_repo")
        assert use_case.assembly_spec_repo is not None

    @pytest.mark.asyncio
    async def test_container_error_propagation(
        self,
        startup_provider: StartupDependenciesProvider,
        mock_container: AsyncMock,
    ) -> None:
        """Test that container errors are properly propagated."""
        # Setup mock to raise error
        mock_container.get_minio_client.side_effect = Exception(
            "Container error"
        )

        # Verify error is propagated
        with pytest.raises(Exception, match="Container error"):
            await startup_provider.get_knowledge_service_config_repository()


class TestStartupDependenciesIntegration:
    """Integration tests for startup dependencies."""

    @pytest.mark.asyncio
    async def test_get_startup_dependencies_function(self) -> None:
        """Test the get_startup_dependencies function."""
        provider = await get_startup_dependencies()

        assert provider is not None
        assert isinstance(provider, StartupDependenciesProvider)
        assert provider.container is not None

    @pytest.mark.asyncio
    async def test_startup_dependencies_singleton_behavior(self) -> None:
        """Test that startup dependencies provider behaves as singleton."""
        provider1 = await get_startup_dependencies()
        provider2 = await get_startup_dependencies()

        # Should be the same instance
        assert provider1 is provider2
        assert provider1.container is provider2.container

    @pytest.mark.asyncio
    async def test_end_to_end_dependency_creation(self) -> None:
        """Test complete end-to-end dependency creation flow."""
        # This test verifies the complete flow works without mocking
        # the internal dependencies (integration test style)

        provider = await get_startup_dependencies()

        # This should work without throwing errors
        # (though it might fail if Minio isn't available, which is expected)
        try:
            service = await provider.get_system_initialization_service()
            assert service is not None

            # Verify the service has the expected methods
            assert hasattr(service, "initialize")
            assert hasattr(service, "get_initialization_status")
            assert hasattr(service, "reinitialize")

        except Exception as e:
            # In test environments, Minio might not be available
            # We just verify that the dependency chain is correctly structured
            # and any errors are related to infrastructure, not our code
            assert "minio" in str(e).lower() or "connection" in str(e).lower()


class TestStartupDependenciesProviderEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_multiple_repository_requests(
        self,
        startup_provider: StartupDependenciesProvider,
        mock_container: AsyncMock,
        mock_minio_client: MagicMock,
    ) -> None:
        """Test multiple requests for the same repository type."""
        # Setup mock
        mock_container.get_minio_client.return_value = mock_minio_client

        # Get repository multiple times
        repo1 = (
            await startup_provider.get_knowledge_service_config_repository()
        )
        repo2 = (
            await startup_provider.get_knowledge_service_config_repository()
        )

        # Each call should create a new repository instance
        assert repo1 is not None
        assert repo2 is not None
        # They should be different instances (no caching at provider level)
        assert repo1 is not repo2

        # But container should be called each time (container handles caching)
        assert mock_container.get_minio_client.call_count == 2

    @pytest.mark.asyncio
    async def test_service_creation_isolation(
        self,
        startup_provider: StartupDependenciesProvider,
        mock_container: AsyncMock,
        mock_minio_client: MagicMock,
    ) -> None:
        """Test that service creation doesn't interfere with operations."""
        # Setup mock
        mock_container.get_minio_client.return_value = mock_minio_client

        # Get repository first
        repo = (
            await startup_provider.get_knowledge_service_config_repository()
        )

        # Then get service
        service = await startup_provider.get_system_initialization_service()

        # Both should be valid
        assert repo is not None
        assert service is not None

        # Container should have been called multiple times:
        # 1 for direct repo call + 4 for service (config + document + query +
        # assembly spec repos)
        assert mock_container.get_minio_client.call_count == 5

    def test_provider_with_none_container(self) -> None:
        """Test provider behavior with None container."""
        # This should not happen in practice, but test defensive behavior
        with pytest.raises(AttributeError):
            provider = StartupDependenciesProvider(None)  # type: ignore
            # Any operation should fail gracefully
            provider.container.get_minio_client()  # type: ignore
