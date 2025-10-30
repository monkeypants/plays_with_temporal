"""
Use case logic for data assembly within the Capture, Extract, Assemble,
Publish workflow.

This module contains use case classes that orchestrate business logic while
remaining framework-agnostic. Dependencies are injected via repository
instances following the Clean Architecture principles.
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Callable
import jsonpointer  # type: ignore
import multihash
import jsonschema

from julee_example.domain.models import (
    Assembly,
    AssemblyStatus,
    Document,
    DocumentStatus,
    AssemblySpecification,
    KnowledgeServiceQuery,
)
from julee_example.domain.repositories import (
    DocumentRepository,
    AssemblyRepository,
    AssemblySpecificationRepository,
    KnowledgeServiceQueryRepository,
    KnowledgeServiceConfigRepository,
)
from julee_example.services import KnowledgeService
from sample.validation import ensure_repository_protocol
from util.validation import validate_parameter_types
from .decorators import try_use_case_step

logger = logging.getLogger(__name__)


class ExtractAssembleDataUseCase:
    """
    Use case for extracting and assembling documents according to
    specifications.

    This class orchestrates the business logic for the "Extract, Assemble"
    phases of the Capture, Extract, Assemble, Publish workflow while remaining
    framework-agnostic. It depends only on repository protocols, not
    concrete implementations.

    In workflow contexts, this use case is called from workflow code with
    repository stubs that delegate to Temporal activities for durability.
    The use case remains completely unaware of whether it's running in a
    workflow context or a simple async context - it just calls repository
    methods and expects them to work correctly.

    Architectural Notes:
    - This class contains pure business logic with no framework dependencies
    - Repository dependencies are injected via constructor
      (dependency inversion)
    - All error handling and compensation logic is contained here
    - The use case works with domain objects exclusively
    - Deterministic execution is guaranteed by avoiding
      non-deterministic operations
    """

    def __init__(
        self,
        document_repo: DocumentRepository,
        assembly_repo: AssemblyRepository,
        assembly_specification_repo: AssemblySpecificationRepository,
        knowledge_service_query_repo: KnowledgeServiceQueryRepository,
        knowledge_service_config_repo: KnowledgeServiceConfigRepository,
        knowledge_service: KnowledgeService,
        now_fn: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        """Initialize extract and assemble data use case.

        Args:
            document_repo: Repository for document operations
            assembly_repo: Repository for assembly operations
            assembly_specification_repo: Repository for assembly
                specification operations
            knowledge_service_query_repo: Repository for knowledge service
                query operations
            knowledge_service_config_repo: Repository for knowledge service
                configuration operations
            knowledge_service: Knowledge service instance for external
                operations
            now_fn: Function to get current time (for workflow compatibility)

        Note:
            The repositories passed here may be concrete implementations
            (for testing or direct execution) or workflow stubs (for
            Temporal workflow execution). The use case doesn't know or care
            which - it just calls the methods defined in the protocols.

            Repositories are validated at construction time to catch
            configuration errors early in the application lifecycle.
        """
        # Validate at construction time for early error detection
        self.document_repo = ensure_repository_protocol(
            document_repo,
            DocumentRepository,  # type: ignore[type-abstract]
        )
        self.knowledge_service = knowledge_service
        self.now_fn = now_fn
        self.assembly_repo = ensure_repository_protocol(
            assembly_repo,
            AssemblyRepository,  # type: ignore[type-abstract]
        )
        self.assembly_specification_repo = ensure_repository_protocol(
            assembly_specification_repo,
            AssemblySpecificationRepository,  # type: ignore[type-abstract]
        )
        self.knowledge_service_query_repo = ensure_repository_protocol(
            knowledge_service_query_repo,
            KnowledgeServiceQueryRepository,  # type: ignore[type-abstract]
        )
        self.knowledge_service_config_repo = ensure_repository_protocol(
            knowledge_service_config_repo,
            KnowledgeServiceConfigRepository,  # type: ignore[type-abstract]
        )

    async def assemble_data(
        self,
        document_id: str,
        assembly_specification_id: str,
        workflow_id: str,
    ) -> Assembly:
        """
        Assemble a document according to its specification and create a new
        assembly.

        This method orchestrates the core assembly workflow:
        1. Generates a unique assembly ID
        2. Retrieves the assembly specification
        3. Stores the initial assembly in the repository
        4. Retrieves all knowledge service queries needed for the assembly
        5. Retrieves all knowledge service instances needed for the assembly
        6. Retrieves the input document and registers it with knowledge
           services
        7. Performs the assembly iteration to create the assembled document
        8. Adds the iteration to the assembly and returns it

        Args:
            document_id: ID of the document to assemble
            assembly_specification_id: ID of the specification to use
            workflow_id: Temporal workflow ID that creates this assembly

        Returns:
            New Assembly with the assembled document iteration

        Raises:
            ValueError: If required entities are not found or invalid
            RuntimeError: If assembly processing fails
        """
        logger.debug(
            "Starting data assembly use case",
            extra={
                "document_id": document_id,
                "assembly_specification_id": assembly_specification_id,
                "workflow_id": workflow_id,
            },
        )

        # Step 1: Generate unique assembly ID
        assembly_id = await self._generate_assembly_id(
            document_id, assembly_specification_id
        )

        # Step 2: Retrieve the assembly specification
        assembly_specification = await self._retrieve_assembly_specification(
            assembly_specification_id
        )

        # Step 3: Store the initial assembly
        assembly = Assembly(
            assembly_id=assembly_id,
            assembly_specification_id=assembly_specification_id,
            input_document_id=document_id,
            workflow_id=workflow_id,
            status=AssemblyStatus.IN_PROGRESS,
            assembled_document_id=None,
            created_at=self.now_fn(),
            updated_at=self.now_fn(),
        )
        await self.assembly_repo.save(assembly)

        logger.debug(
            "Initial assembly stored",
            extra={
                "assembly_id": assembly_id,
                "status": assembly.status.value,
            },
        )

        # Step 4: Retrieve all knowledge service queries once
        queries = await self._retrieve_all_queries(assembly_specification)

        # Step 5: Register the document with knowledge services
        document = await self._retrieve_document(document_id)
        document_registrations = await self._register_document_with_services(
            document, queries
        )

        # Step 7: Perform the assembly iteration
        try:
            assembled_document_id = await self._assemble_iteration(
                document,
                assembly_specification,
                document_registrations,
                queries,
            )

            # Step 8: Set the assembled document and return
            assembly.assembled_document_id = assembled_document_id
            assembly.status = AssemblyStatus.COMPLETED
            await self.assembly_repo.save(assembly)

            logger.info(
                "Assembly completed successfully",
                extra={
                    "assembly_id": assembly_id,
                    "assembled_document_id": assembled_document_id,
                },
            )

            return assembly

        except Exception as e:
            # Mark assembly as failed
            assembly.status = AssemblyStatus.FAILED
            await self.assembly_repo.save(assembly)

            logger.error(
                "Assembly failed",
                extra={
                    "assembly_id": assembly_id,
                    "error": str(e),
                },
                exc_info=True,
            )
            raise

    @try_use_case_step("document_registration")
    @validate_parameter_types()
    async def _register_document_with_services(
        self,
        document: Document,
        queries: Dict[str, KnowledgeServiceQuery],
    ) -> Dict[str, str]:
        """
        Register the document with all knowledge services needed for assembly.

        This is a temporary solution - document registration will be handled
        properly in a separate process later.

        Args:
            document: The document to register
            queries: Dict of query_id to KnowledgeServiceQuery objects

        Returns:
            Dict mapping knowledge_service_id to service_file_id

        Raises:
            RuntimeError: If registration fails
        """
        registrations = {}

        required_service_ids = {
            query.knowledge_service_id for query in queries.values()
        }

        for knowledge_service_id in required_service_ids:
            # Get the config for this service
            config = await self.knowledge_service_config_repo.get(
                knowledge_service_id
            )
            if not config:
                raise ValueError(
                    f"Knowledge service config not found: "
                    f"{knowledge_service_id}"
                )

            registration_result = await self.knowledge_service.register_file(
                config, document
            )
            registrations[knowledge_service_id] = (
                registration_result.knowledge_service_file_id
            )

        return registrations

    @try_use_case_step("queries_retrieval")
    async def _retrieve_all_queries(
        self, assembly_specification: AssemblySpecification
    ) -> Dict[str, KnowledgeServiceQuery]:
        """Retrieve all knowledge service queries needed for this assembly."""
        query_ids = list(
            assembly_specification.knowledge_service_queries.values()
        )

        # TODO: TEMPORAL SERIALIZATION ISSUE - Replace with get_many when
        # fixed
        #
        # Issue: Complex return type
        # Dict[str, Optional[KnowledgeServiceQuery]] from get_many causes
        # Temporal's type system to fall back to typing.Any, resulting in
        # Pydantic models being deserialized as plain dictionaries instead of
        # model instances.
        #
        # Error: "SERIALIZATION ISSUE DETECTED: parameter
        # 'queries'['query-id'] is dict instead of KnowledgeServiceQuery!"
        #
        # Root Cause: Temporal's type resolution cannot handle the complex
        # nested generic type Dict[str, Optional[T]] and passes typing.Any to
        # the data converter, which then deserializes to plain dicts.
        #
        # Investigation: Full analysis showed:
        # - Data converter debug output confirming typing.Any fallback
        # - Repository type resolution working correctly
        # - Guard check system detecting the exact issue
        # - Evidence that simpler types (Optional[T]) work fine
        #
        # Temporary Fix: Use individual get() calls which return Optional[T]
        # that Temporal handles correctly.
        #
        # Future Solutions:
        # 1. Fix Temporal's type resolution for complex nested generics
        # 2. Create custom data converter for this specific type pattern
        # 3. Simplify repository interface to avoid Optional in batch
        #    operations
        #
        # Currently using individual get calls to avoid complex type
        # serialization issue
        queries = {}
        for query_id in query_ids:
            query = await self.knowledge_service_query_repo.get(query_id)
            if not query:
                raise ValueError(
                    f"Knowledge service query not found: {query_id}"
                )
            queries[query_id] = query
        return queries

    @try_use_case_step("assembly_iteration")
    async def _assemble_iteration(
        self,
        document: Document,
        assembly_specification: AssemblySpecification,
        document_registrations: Dict[str, str],
        queries: Dict[str, KnowledgeServiceQuery],
    ) -> str:
        """
        Perform a single assembly iteration using knowledge services.

        This method:
        1. Executes all knowledge service queries defined in the specification
        2. Stitches together the query results into a complete JSON document
        3. Creates and stores the assembled document
        4. Returns the ID of the assembled document

        Args:
            document: The input document
            assembly_specification: The specification defining how to assemble
            document_registrations: Mapping of service_id to service_file_id
            queries: Dict of query_id to KnowledgeServiceQuery objects

        Returns:
            ID of the newly created assembled document

        Raises:
            ValueError: If required entities are not found
            RuntimeError: If knowledge service operations fail
        """
        # Initialize the result data structure
        assembled_data: Dict[str, Any] = {}

        # Process each knowledge service query
        # TODO: This is where we may want to fan-out/fan-in to do these
        # in parallel.
        for (
            schema_pointer,
            query_id,
        ) in assembly_specification.knowledge_service_queries.items():
            # Get the relevant schema section
            schema_section = self._extract_schema_section(
                assembly_specification.jsonschema, schema_pointer
            )

            # Get the query configuration
            query = queries[query_id]

            # Get the config for this service
            config = await self.knowledge_service_config_repo.get(
                query.knowledge_service_id
            )

            if not config:
                raise ValueError(
                    f"Knowledge service config not found: "
                    f"{query.knowledge_service_id}"
                )

            # Get the service file ID from our registrations
            service_file_id = document_registrations.get(
                query.knowledge_service_id
            )
            if not service_file_id:
                raise ValueError(
                    f"Document not registered with service "
                    f"{query.knowledge_service_id}"
                )

            # Execute the query with schema section embedded in the prompt
            query_text = self._build_query_with_schema(
                query.prompt, schema_section
            )

            query_result = await self.knowledge_service.execute_query(
                config,
                query_text,
                [service_file_id],
                query.query_metadata,
                query.assistant_prompt,
            )

            # Parse and store the result
            result_data = self._parse_query_result(query_result.result_data)
            self._store_result_in_assembled_data(
                assembled_data, schema_pointer, result_data
            )

        # Validate the assembled data against the JSON schema
        self._validate_assembled_data(assembled_data, assembly_specification)

        # Create the assembled document
        assembled_document_id = await self._create_assembled_document(
            assembled_data, assembly_specification
        )

        return assembled_document_id

    @try_use_case_step("assembly_id_generation")
    async def _generate_assembly_id(
        self, document_id: str, assembly_specification_id: str
    ) -> str:
        """Generate a unique assembly ID with consistent error handling."""
        return await self.assembly_repo.generate_id()

    @try_use_case_step("assembly_specification_retrieval")
    async def _retrieve_assembly_specification(
        self, assembly_specification_id: str
    ) -> AssemblySpecification:
        """Retrieve assembly specification with error handling."""
        specification = await self.assembly_specification_repo.get(
            assembly_specification_id
        )
        if not specification:
            raise ValueError(
                f"Assembly specification not found: "
                f"{assembly_specification_id}"
            )
        return specification

    @try_use_case_step("document_retrieval")
    async def _retrieve_document(self, document_id: str) -> Document:
        """Retrieve document with error handling."""
        document = await self.document_repo.get(document_id)
        if not document:
            raise ValueError(f"Document not found: {document_id}")
        return document

    def _extract_schema_section(
        self, jsonschema: Dict[str, Any], schema_pointer: str
    ) -> Any:
        """Extract relevant section of JSON schema using JSON Pointer."""
        if not schema_pointer:
            # Empty pointer refers to the entire schema
            return jsonschema

        try:
            ptr = jsonpointer.JsonPointer(schema_pointer)
            result = ptr.resolve(jsonschema)
            return result
        except (jsonpointer.JsonPointerException, KeyError, TypeError) as e:
            raise ValueError(
                f"Cannot extract schema section '{schema_pointer}': {e}"
            )

    def _build_query_with_schema(
        self, base_prompt: str, schema_section: Any
    ) -> str:
        """Build the query text with embedded JSON schema section."""
        schema_json = json.dumps(schema_section, indent=2)
        return f"""{base_prompt}

Please structure your response according to this JSON schema:
{schema_json}

Return only valid JSON that conforms to this schema, without any surrounding
text or markdown formatting."""

    def _parse_query_result(self, result_data: Dict[str, Any]) -> Any:
        """Parse the query result to extract the JSON response."""
        response_text = result_data.get("response", "")
        if not response_text:
            raise ValueError("Empty response from knowledge service")

        # Response must be valid JSON
        try:
            parsed_result = json.loads(response_text.strip())
            return parsed_result
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Knowledge service response must be valid JSON. "
                f"Complete response: {response_text} "
                f"Parse error: {e}"
            )

    def _store_result_in_assembled_data(
        self,
        assembled_data: Dict[str, Any],
        schema_pointer: str,
        result_data: Any,
    ) -> None:
        """Store query result in appropriate location in assembled data."""
        if not schema_pointer:
            # Root level - merge the entire result if it's a dict,
            # otherwise store as-is
            if isinstance(result_data, dict):
                assembled_data.update(result_data)
            else:
                # Can't merge non-dict at root level, this would be an error
                raise ValueError(
                    "Cannot merge non-dict result data at root level"
                )
        else:
            # Use JSON Pointer to set the data at the correct location
            try:
                # Convert pointer to path components, skipping "properties"
                # wrapper
                path_parts = (
                    schema_pointer.strip("/").split("/")
                    if schema_pointer.strip("/")
                    else []
                )

                # Remove "properties" from path if it exists (schema artifact)
                if path_parts and path_parts[0] == "properties":
                    path_parts = path_parts[1:]

                # If no path parts left, store at root level
                if not path_parts:
                    if isinstance(result_data, dict):
                        assembled_data.update(result_data)
                    else:
                        # Can't merge non-dict at root level, this would be
                        # an error
                        raise ValueError(
                            "Cannot merge non-dict result data at root level"
                        )
                    return

                # Navigate/create the nested structure
                current = assembled_data
                for part in path_parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]

                # Set the final value
                current[path_parts[-1]] = result_data

            except (KeyError, TypeError) as e:
                raise ValueError(
                    f"Cannot store result at schema pointer "
                    f"'{schema_pointer}': {e}"
                )

    @try_use_case_step("assembled_document_creation")
    async def _create_assembled_document(
        self,
        assembled_data: Dict[str, Any],
        assembly_specification: AssemblySpecification,
    ) -> str:
        """Create and store the assembled document."""

        # Generate document ID
        document_id = await self.document_repo.generate_id()

        # Convert assembled data to JSON string
        assembled_content = json.dumps(assembled_data, indent=2)
        content_bytes = assembled_content.encode("utf-8")

        assembled_document = Document(
            document_id=document_id,
            original_filename=(
                f"assembled_"
                f"{assembly_specification.name.replace(' ', '_')}.json"
            ),
            content_type="application/json",
            size_bytes=len(content_bytes),
            content_multihash=self._calculate_multihash_from_content(
                content_bytes
            ),
            status=DocumentStatus.ASSEMBLED,
            content_string=assembled_content,  # Use content_string for small
            created_at=self.now_fn(),
            updated_at=self.now_fn(),
        )

        # Save the document
        await self.document_repo.save(assembled_document)

        return document_id

    def _validate_assembled_data(
        self,
        assembled_data: Dict[str, Any],
        assembly_specification: AssemblySpecification,
    ) -> None:
        """Validate that the assembled data conforms to the JSON schema."""
        try:
            jsonschema.validate(
                assembled_data, assembly_specification.jsonschema
            )
            logger.debug(
                "Assembled data validation passed",
                extra={
                    "assembly_specification_id": (
                        assembly_specification.assembly_specification_id
                    ),
                },
            )
        except jsonschema.ValidationError as e:
            logger.error(
                "Assembled data validation failed",
                extra={
                    "assembly_specification_id": (
                        assembly_specification.assembly_specification_id
                    ),
                    "validation_error": str(e),
                    "error_path": (
                        list(e.absolute_path) if e.absolute_path else []
                    ),
                    "schema_path": (
                        list(e.schema_path) if e.schema_path else []
                    ),
                },
            )
            raise ValueError(
                f"Assembled data does not conform to JSON schema: {e.message}"
            )
        except jsonschema.SchemaError as e:
            logger.error(
                "JSON schema is invalid",
                extra={
                    "assembly_specification_id": (
                        assembly_specification.assembly_specification_id
                    ),
                    "schema_error": str(e),
                },
            )
            raise ValueError(
                f"Invalid JSON schema in assembly specification: {e.message}"
            )

    def _calculate_multihash_from_content(self, content_bytes: bytes) -> str:
        """Calculate multihash from content bytes."""
        # Calculate SHA-256 hash
        sha256_hash = hashlib.sha256(content_bytes).digest()

        # Create multihash with SHA-256 (code 0x12)
        mhash = multihash.encode(sha256_hash, multihash.SHA2_256)
        return str(mhash.hex())
