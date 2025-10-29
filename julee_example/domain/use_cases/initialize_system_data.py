"""
Initialize System Data Use Case for the julee_example CEAP system.

This module provides the use case for initializing required system data
on application startup, such as knowledge service configurations that
are needed for the system to function properly.

The use case follows clean architecture principles:
- Contains business logic for what system data is required
- Uses repository interfaces for persistence
- Is idempotent and safe to run multiple times
- Can be tested independently of infrastructure concerns
"""

import logging
import yaml
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any

from julee_example.domain.models.knowledge_service_config import (
    KnowledgeServiceConfig,
    ServiceApi,
)
from julee_example.domain.models.assembly_specification import (
    KnowledgeServiceQuery,
)
from julee_example.domain.models.assembly_specification import (
    AssemblySpecification,
    AssemblySpecificationStatus,
)
from julee_example.domain.models.document import Document, DocumentStatus
from julee_example.domain.repositories.knowledge_service_config import (
    KnowledgeServiceConfigRepository,
)
from julee_example.domain.repositories.knowledge_service_query import (
    KnowledgeServiceQueryRepository,
)
from julee_example.domain.repositories.assembly_specification import (
    AssemblySpecificationRepository,
)
from julee_example.domain.repositories.document import DocumentRepository

logger = logging.getLogger(__name__)


class InitializeSystemDataUseCase:
    """
    Use case for initializing required system data on application startup.

    This use case ensures that essential configuration data exists in the
    system, such as knowledge service configurations that are required
    for the application to function properly.

    All operations are idempotent - running this multiple times will not
    create duplicate data or cause errors.
    """

    def __init__(
        self,
        knowledge_service_config_repository: KnowledgeServiceConfigRepository,
        document_repository: DocumentRepository,
        knowledge_service_query_repository: KnowledgeServiceQueryRepository,
        assembly_specification_repository: AssemblySpecificationRepository,
    ) -> None:
        """Initialize the use case with required repositories.

        Args:
            knowledge_service_config_repository: Repository for knowledge
                service configurations
            document_repository: Repository for documents
            knowledge_service_query_repository: Repository for knowledge
                service queries
            assembly_specification_repository: Repository for assembly
                specifications
        """
        self.config_repo = knowledge_service_config_repository
        self.document_repo = document_repository
        self.query_repo = knowledge_service_query_repository
        self.assembly_spec_repo = assembly_specification_repository
        self.logger = logging.getLogger("InitializeSystemDataUseCase")

    async def execute(self) -> None:
        """
        Execute system data initialization.

        This method orchestrates the creation of all required system data.
        It's idempotent and can be safely called multiple times.

        Raises:
            Exception: If any critical system data cannot be initialized
        """
        self.logger.info("Starting system data initialization")

        try:
            await self._ensure_knowledge_service_configs_exist()
            await self._ensure_knowledge_service_queries_exist()
            await self._ensure_example_documents_exist()
            await self._ensure_assembly_specifications_exist()

            self.logger.info(
                "System data initialization completed successfully"
            )

        except Exception as e:
            self.logger.error(
                "Failed to initialize system data",
                exc_info=True,
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            raise

    def _get_demo_fixture_path(self, filename: str) -> Path:
        """
        Get path to a demo fixture file.

        Args:
            filename: Name of the fixture file

        Returns:
            Path to the fixture file
        """
        current_file = Path(__file__)
        julee_example_dir = current_file.parent.parent.parent
        return julee_example_dir / "demo_fixtures" / filename

    async def _ensure_knowledge_service_configs_exist(self) -> None:
        """
        Ensure all knowledge service configurations from fixture exist.

        This loads configurations from the YAML fixture file and creates
        any that don't already exist in the repository. The operation is
        idempotent - existing configurations are not modified.
        """
        self.logger.info(
            "Loading knowledge service configurations from fixture"
        )

        try:
            # Load configurations from YAML fixture
            fixture_configs = self._load_fixture_configurations()

            created_count = 0
            skipped_count = 0

            for config_data in fixture_configs:
                config_id = config_data["knowledge_service_id"]

                # Check if configuration already exists
                existing_config = await self.config_repo.get(config_id)
                if existing_config:
                    self.logger.debug(
                        "Knowledge service config already exists, skipping",
                        extra={
                            "config_id": config_id,
                            "config_name": existing_config.name,
                        },
                    )
                    skipped_count += 1
                    continue

                # Create new configuration from fixture data
                config = self._create_config_from_fixture_data(config_data)
                await self.config_repo.save(config)

                self.logger.info(
                    "Knowledge service config created successfully",
                    extra={
                        "config_id": config.knowledge_service_id,
                        "config_name": config.name,
                        "service_api": config.service_api.value,
                    },
                )
                created_count += 1

            self.logger.info(
                "Knowledge service configurations processed",
                extra={
                    "created_count": created_count,
                    "skipped_count": skipped_count,
                    "total_count": len(fixture_configs),
                },
            )

        except Exception as e:
            self.logger.error(
                "Failed to ensure knowledge service configurations exist",
                exc_info=True,
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            raise

    def _load_fixture_configurations(self) -> List[Dict[str, Any]]:
        """
        Load knowledge service configurations from the YAML fixture file.

        Returns:
            List of configuration dictionaries from the fixture file

        Raises:
            FileNotFoundError: If the fixture file doesn't exist
            yaml.YAMLError: If the fixture file is invalid YAML
            KeyError: If required fields are missing from the fixture
        """
        fixture_path = self._get_demo_fixture_path(
            "knowledge_service_configs.yaml"
        )

        self.logger.debug(
            "Loading fixture file",
            extra={"fixture_path": str(fixture_path)},
        )

        if not fixture_path.exists():
            raise FileNotFoundError(
                f"Knowledge services fixture file not found: {fixture_path}"
            )

        try:
            with open(fixture_path, "r", encoding="utf-8") as f:
                fixture_data = yaml.safe_load(f)

            if not fixture_data or "knowledge_services" not in fixture_data:
                raise KeyError(
                    "Fixture file must contain 'knowledge_services' key"
                )

            configs = fixture_data["knowledge_services"]
            if not isinstance(configs, list):
                raise ValueError(
                    "'knowledge_services' must be a list of configurations"
                )

            self.logger.debug(
                "Loaded fixture configurations",
                extra={"count": len(configs)},
            )

            return configs

        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Invalid YAML in fixture file: {e}")

    def _create_config_from_fixture_data(
        self, config_data: Dict[str, Any]
    ) -> KnowledgeServiceConfig:
        """
        Create a KnowledgeServiceConfig from fixture data.

        Args:
            config_data: Dictionary containing configuration data from fixture

        Returns:
            KnowledgeServiceConfig instance

        Raises:
            KeyError: If required fields are missing
            ValueError: If field values are invalid
        """
        required_fields = [
            "knowledge_service_id",
            "name",
            "description",
            "service_api",
        ]

        # Validate required fields
        for field in required_fields:
            if field not in config_data:
                raise KeyError(
                    f"Required field '{field}' missing from config"
                )

        # Parse service API enum
        try:
            service_api = ServiceApi(config_data["service_api"])
        except ValueError:
            raise ValueError(
                f"Invalid service_api '{config_data['service_api']}'. "
                f"Must be one of: {[api.value for api in ServiceApi]}"
            )

        # Create configuration
        config = KnowledgeServiceConfig(
            knowledge_service_id=config_data["knowledge_service_id"],
            name=config_data["name"],
            description=config_data["description"],
            service_api=service_api,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        self.logger.debug(
            "Created config from fixture data",
            extra={
                "config_id": config.knowledge_service_id,
                "config_name": config.name,
            },
        )

        return config

    async def _ensure_knowledge_service_queries_exist(self) -> None:
        """
        Ensure all knowledge service queries from fixture exist.

        This loads queries from the YAML fixture file and creates
        any that don't already exist in the repository. The operation is
        idempotent - existing queries are not modified.
        """
        self.logger.info("Loading knowledge service queries from fixture")

        try:
            # Load queries from YAML fixture
            fixture_queries = self._load_fixture_queries()

            created_count = 0
            skipped_count = 0

            for query_data in fixture_queries:
                query_id = query_data["query_id"]

                # Check if query already exists
                existing_query = await self.query_repo.get(query_id)
                if existing_query:
                    self.logger.debug(
                        "Knowledge service query already exists, skipping",
                        extra={
                            "query_id": query_id,
                            "query_name": existing_query.name,
                        },
                    )
                    skipped_count += 1
                    continue

                # Create new query from fixture data
                query = self._create_query_from_fixture_data(query_data)
                await self.query_repo.save(query)

                self.logger.info(
                    "Knowledge service query created successfully",
                    extra={
                        "query_id": query.query_id,
                        "query_name": query.name,
                        "knowledge_service_id": query.knowledge_service_id,
                    },
                )
                created_count += 1

            self.logger.info(
                "Knowledge service queries processed",
                extra={
                    "created_count": created_count,
                    "skipped_count": skipped_count,
                    "total_count": len(fixture_queries),
                },
            )

        except Exception as e:
            self.logger.error(
                "Failed to ensure knowledge service queries exist",
                exc_info=True,
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            raise

    def _load_fixture_queries(self) -> List[Dict[str, Any]]:
        """
        Load knowledge service queries from the YAML fixture file.

        Returns:
            List of query dictionaries from the fixture file

        Raises:
            FileNotFoundError: If the fixture file doesn't exist
            yaml.YAMLError: If the fixture file is invalid YAML
            KeyError: If required fields are missing from the fixture
        """
        fixture_path = self._get_demo_fixture_path(
            "knowledge_service_queries.yaml"
        )

        self.logger.debug(
            "Loading queries fixture file",
            extra={"fixture_path": str(fixture_path)},
        )

        if not fixture_path.exists():
            raise FileNotFoundError(
                f"Knowledge service queries fixture file not found: "
                f"{fixture_path}"
            )

        try:
            with open(fixture_path, "r", encoding="utf-8") as f:
                fixture_data = yaml.safe_load(f)

            if (
                not fixture_data
                or "knowledge_service_queries" not in fixture_data
            ):
                raise KeyError(
                    "Fixture file must contain 'knowledge_service_queries' "
                    "key"
                )

            queries = fixture_data["knowledge_service_queries"]
            if not isinstance(queries, list):
                raise ValueError(
                    "'knowledge_service_queries' must be a list of query "
                    "configurations"
                )

            self.logger.debug(
                "Loaded fixture queries",
                extra={"count": len(queries)},
            )

            return queries

        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Invalid YAML in queries fixture file: {e}")

    def _create_query_from_fixture_data(
        self, query_data: Dict[str, Any]
    ) -> KnowledgeServiceQuery:
        """
        Create a KnowledgeServiceQuery from fixture data.

        Args:
            query_data: Dictionary containing query data from fixture

        Returns:
            KnowledgeServiceQuery instance

        Raises:
            KeyError: If required fields are missing
            ValueError: If field values are invalid
        """
        required_fields = [
            "query_id",
            "name",
            "knowledge_service_id",
            "prompt",
            "assistant_prompt",
        ]

        # Validate required fields
        for field in required_fields:
            if field not in query_data:
                raise KeyError(f"Required field '{field}' missing from query")

        # Get optional fields
        query_metadata = query_data.get("query_metadata", {})

        # Create query
        query = KnowledgeServiceQuery(
            query_id=query_data["query_id"],
            name=query_data["name"],
            knowledge_service_id=query_data["knowledge_service_id"],
            prompt=query_data["prompt"],
            assistant_prompt=query_data["assistant_prompt"],
            query_metadata=query_metadata,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        self.logger.debug(
            "Created query from fixture data",
            extra={
                "query_id": query.query_id,
                "query_name": query.name,
            },
        )

        return query

    async def _ensure_assembly_specifications_exist(self) -> None:
        """
        Ensure all assembly specifications from fixture exist.

        This loads specifications from the YAML fixture file and creates
        any that don't already exist in the repository. The operation is
        idempotent - existing specifications are not modified.
        """
        self.logger.info("Loading assembly specifications from fixture")

        try:
            # Load specifications from YAML fixture
            fixture_specs = self._load_fixture_assembly_specifications()

            created_count = 0
            skipped_count = 0

            for spec_data in fixture_specs:
                spec_id = spec_data["assembly_specification_id"]

                # Check if specification already exists
                existing_spec = await self.assembly_spec_repo.get(spec_id)
                if existing_spec:
                    self.logger.debug(
                        "Assembly specification already exists, skipping",
                        extra={
                            "spec_id": spec_id,
                            "spec_name": existing_spec.name,
                        },
                    )
                    skipped_count += 1
                    continue

                # Create new specification from fixture data
                spec = self._create_assembly_spec_from_fixture_data(spec_data)
                await self.assembly_spec_repo.save(spec)

                self.logger.info(
                    "Assembly specification created successfully",
                    extra={
                        "spec_id": spec.assembly_specification_id,
                        "spec_name": spec.name,
                        "status": spec.status.value,
                    },
                )
                created_count += 1

            self.logger.info(
                "Assembly specifications processed",
                extra={
                    "created_count": created_count,
                    "skipped_count": skipped_count,
                    "total_count": len(fixture_specs),
                },
            )

        except Exception as e:
            self.logger.error(
                "Failed to ensure assembly specifications exist",
                exc_info=True,
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            raise

    def _load_fixture_assembly_specifications(self) -> List[Dict[str, Any]]:
        """
        Load assembly specifications from the YAML fixture file.

        Returns:
            List of specification dictionaries from the fixture file

        Raises:
            FileNotFoundError: If the fixture file doesn't exist
            yaml.YAMLError: If the fixture file is invalid YAML
            KeyError: If required fields are missing from the fixture
        """
        fixture_path = self._get_demo_fixture_path(
            "assembly_specifications.yaml"
        )

        self.logger.debug(
            "Loading assembly specifications fixture file",
            extra={"fixture_path": str(fixture_path)},
        )

        if not fixture_path.exists():
            raise FileNotFoundError(
                f"Assembly specifications fixture file not found: "
                f"{fixture_path}"
            )

        try:
            with open(fixture_path, "r", encoding="utf-8") as f:
                fixture_data = yaml.safe_load(f)

            if (
                not fixture_data
                or "assembly_specifications" not in fixture_data
            ):
                raise KeyError(
                    "Fixture file must contain 'assembly_specifications' key"
                )

            specs = fixture_data["assembly_specifications"]
            if not isinstance(specs, list):
                raise ValueError(
                    "'assembly_specifications' must be a list of "
                    "specification configurations"
                )

            self.logger.debug(
                "Loaded fixture assembly specifications",
                extra={"count": len(specs)},
            )

            return specs

        except yaml.YAMLError as e:
            raise yaml.YAMLError(
                f"Invalid YAML in assembly specifications fixture file: {e}"
            )

    def _create_assembly_spec_from_fixture_data(
        self, spec_data: Dict[str, Any]
    ) -> AssemblySpecification:
        """
        Create an AssemblySpecification from fixture data.

        Args:
            spec_data: Dictionary containing specification data from fixture

        Returns:
            AssemblySpecification instance

        Raises:
            KeyError: If required fields are missing
            ValueError: If field values are invalid
        """
        required_fields = [
            "assembly_specification_id",
            "name",
            "applicability",
            "jsonschema",
        ]

        # Validate required fields
        for field in required_fields:
            if field not in spec_data:
                raise KeyError(
                    f"Required field '{field}' missing from assembly "
                    "specification"
                )

        # Parse status
        status = AssemblySpecificationStatus.ACTIVE
        if "status" in spec_data:
            try:
                status = AssemblySpecificationStatus(spec_data["status"])
            except ValueError:
                self.logger.warning(
                    f"Invalid status '{spec_data['status']}', "
                    "using default 'active'"
                )

        # Get optional fields
        version = spec_data.get("version", "1.0")
        knowledge_service_queries = spec_data.get(
            "knowledge_service_queries", {}
        )

        # Create specification
        spec = AssemblySpecification(
            assembly_specification_id=spec_data["assembly_specification_id"],
            name=spec_data["name"],
            applicability=spec_data["applicability"],
            jsonschema=spec_data["jsonschema"],
            knowledge_service_queries=knowledge_service_queries,
            status=status,
            version=version,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        self.logger.debug(
            "Created assembly specification from fixture data",
            extra={
                "spec_id": spec.assembly_specification_id,
                "spec_name": spec.name,
            },
        )

        return spec

    async def _ensure_example_documents_exist(self) -> None:
        """
        Ensure all example documents from fixture exist.

        This loads documents from the YAML fixture file and creates
        any that don't already exist in the repository. The operation is
        idempotent - existing documents are not modified.
        """
        self.logger.info("Loading example documents from fixture")

        try:
            # Load documents from YAML fixture
            fixture_documents = self._load_fixture_documents()

            created_count = 0
            skipped_count = 0

            for doc_data in fixture_documents:
                doc_id = doc_data["document_id"]

                # Check if document already exists
                existing_doc = await self.document_repo.get(doc_id)
                if existing_doc:
                    self.logger.debug(
                        "Document already exists, skipping",
                        extra={
                            "document_id": doc_id,
                            "original_filename": (
                                existing_doc.original_filename
                            ),
                        },
                    )
                    skipped_count += 1
                    continue

                # Create new document from fixture data
                document = self._create_document_from_fixture_data(doc_data)
                await self.document_repo.save(document)

                self.logger.info(
                    "Example document created successfully",
                    extra={
                        "document_id": document.document_id,
                        "original_filename": document.original_filename,
                        "status": document.status.value,
                    },
                )
                created_count += 1

            self.logger.info(
                "Example documents processed",
                extra={
                    "created_count": created_count,
                    "skipped_count": skipped_count,
                    "total_count": len(fixture_documents),
                },
            )

        except Exception as e:
            self.logger.error(
                "Failed to ensure example documents exist",
                exc_info=True,
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            raise

    def _load_fixture_documents(self) -> List[Dict[str, Any]]:
        """
        Load documents from the YAML fixture file.

        Returns:
            List of document dictionaries from the fixture file

        Raises:
            FileNotFoundError: If the fixture file doesn't exist
            yaml.YAMLError: If the fixture file is invalid YAML
            KeyError: If required fields are missing from the fixture
        """
        fixture_path = self._get_demo_fixture_path("documents.yaml")

        self.logger.debug(
            "Loading documents fixture file",
            extra={"fixture_path": str(fixture_path)},
        )

        if not fixture_path.exists():
            raise FileNotFoundError(
                f"Documents fixture file not found: {fixture_path}"
            )

        try:
            with open(fixture_path, "r", encoding="utf-8") as f:
                fixture_data = yaml.safe_load(f)

            if not fixture_data or "documents" not in fixture_data:
                raise KeyError("Fixture file must contain 'documents' key")

            documents = fixture_data["documents"]
            if not isinstance(documents, list):
                raise ValueError(
                    "'documents' must be a list of document configurations"
                )

            self.logger.debug(
                "Loaded fixture documents",
                extra={"count": len(documents)},
            )

            return documents

        except yaml.YAMLError as e:
            raise yaml.YAMLError(
                f"Invalid YAML in documents fixture file: {e}"
            )

    def _create_document_from_fixture_data(
        self, doc_data: Dict[str, Any]
    ) -> Document:
        """
        Create a Document from fixture data.

        Args:
            doc_data: Dictionary containing document data from fixture

        Returns:
            Document instance

        Raises:
            KeyError: If required fields are missing
            ValueError: If field values are invalid
        """
        required_fields = [
            "document_id",
            "original_filename",
            "content_type",
            "content",
        ]

        # Validate required fields
        for field in required_fields:
            if field not in doc_data:
                raise KeyError(
                    f"Required field '{field}' missing from document"
                )

        # Get content and calculate hash
        content = doc_data["content"]
        content_bytes = content.encode("utf-8")
        size_bytes = len(content_bytes)

        # Create multihash (using SHA-256)
        sha256_hash = hashlib.sha256(content_bytes).hexdigest()
        content_multihash = f"sha256-{sha256_hash}"

        # Parse status
        status = DocumentStatus.CAPTURED
        if "status" in doc_data:
            try:
                status = DocumentStatus(doc_data["status"])
            except ValueError:
                self.logger.warning(
                    f"Invalid status '{doc_data['status']}', "
                    "using default 'captured'"
                )

        # Get optional fields
        knowledge_service_id = doc_data.get("knowledge_service_id")
        assembly_types = doc_data.get("assembly_types", [])
        additional_metadata = doc_data.get("additional_metadata", {})

        # Create document
        document = Document(
            document_id=doc_data["document_id"],
            original_filename=doc_data["original_filename"],
            content_type=doc_data["content_type"],
            size_bytes=size_bytes,
            content_multihash=content_multihash,
            status=status,
            knowledge_service_id=knowledge_service_id,
            assembly_types=assembly_types,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            additional_metadata=additional_metadata,
            content_string=content,  # Store content as string for fixtures
        )

        self.logger.debug(
            "Created document from fixture data",
            extra={
                "document_id": document.document_id,
                "original_filename": document.original_filename,
                "size_bytes": size_bytes,
            },
        )

        return document
