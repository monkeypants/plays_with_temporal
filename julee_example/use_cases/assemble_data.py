"""
Use case logic for data assembly within the Capture, Extract, Assemble,
Publish workflow.

This module contains use case classes that orchestrate business logic while
remaining framework-agnostic. Dependencies are injected via repository
instances following the Clean Architecture principles.
"""

import hashlib
import io
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any
import jsonpointer  # type: ignore
import multihash
import jsonschema

from julee_example.domain import (
    Assembly,
    AssemblyStatus,
    Document,
    DocumentStatus,
    ContentStream,
    AssemblySpecification,
    KnowledgeServiceQuery,
)
from julee_example.repositories import (
    DocumentRepository,
    AssemblyRepository,
    AssemblySpecificationRepository,
    KnowledgeServiceQueryRepository,
    KnowledgeServiceConfigRepository,
)
from julee_example.services import knowledge_service_factory, KnowledgeService
from sample.validation import ensure_repository_protocol
from .decorators import try_use_case_step

logger = logging.getLogger(__name__)


class AssembleDataUseCase:
    """
    Use case for assembling documents according to specifications.

    This class orchestrates the business logic for the "Assemble" phase
    of the Capture, Extract, Assemble, Publish workflow while remaining
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
    ) -> None:
        """Initialize data assembly use case.

        Args:
            document_repo: Repository for document operations
            assembly_repo: Repository for assembly operations
            assembly_specification_repo: Repository for assembly
                specification operations
            knowledge_service_query_repo: Repository for knowledge service
                query operations
            knowledge_service_config_repo: Repository for knowledge service
                configuration operations

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
            document_repo, DocumentRepository  # type: ignore[type-abstract]
        )
        self.assembly_repo = ensure_repository_protocol(
            assembly_repo, AssemblyRepository  # type: ignore[type-abstract]
        )
        self.assembly_specification_repo = ensure_repository_protocol(
            assembly_specification_repo, AssemblySpecificationRepository  # type: ignore[type-abstract]
        )
        self.knowledge_service_query_repo = ensure_repository_protocol(
            knowledge_service_query_repo, KnowledgeServiceQueryRepository  # type: ignore[type-abstract]
        )
        self.knowledge_service_config_repo = ensure_repository_protocol(
            knowledge_service_config_repo, KnowledgeServiceConfigRepository  # type: ignore[type-abstract]
        )

    async def assemble_data(
        self,
        document_id: str,
        assembly_specification_id: str,
    ) -> Assembly:
        """
        Assemble a document according to its specification and create a new
        assembly.

        This method orchestrates the core assembly workflow:
        1. Generates a unique assembly ID
        2. Retrieves the assembly specification
        3. Stores the initial assembly (without iterations) in the repository
        4. Registers the document with knowledge services
        5. Calls _assemble_iteration to perform the actual assembly work
        6. Returns the assembly with the first iteration

        Args:
            document_id: ID of the document to assemble
            assembly_specification_id: ID of the specification to use

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

        # Step 3: Store the initial assembly (without iterations)
        assembly = Assembly(
            assembly_id=assembly_id,
            assembly_specification_id=assembly_specification_id,
            input_document_id=document_id,
            status=AssemblyStatus.IN_PROGRESS,
            iterations=[],
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
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

        # Step 5: Retrieve all knowledge services once
        knowledge_services = await self._retrieve_all_knowledge_services(queries)

        # Step 6: Register the document with knowledge services
        document = await self._retrieve_document(document_id)
        document_registrations = await self._register_document_with_services(
            document, queries, knowledge_services
        )

        # Step 7: Perform the assembly iteration
        try:
            assembled_document_id = await self._assemble_iteration(
                document, assembly_specification, document_registrations, queries, knowledge_services
            )

            # Step 8: Add the iteration to the assembly and return
            assembly_with_iteration = await self.assembly_repo.add_iteration(
                assembly_id, assembled_document_id
            )

            # Update status to completed
            assembly_with_iteration.status = AssemblyStatus.COMPLETED
            assembly_with_iteration.updated_at = datetime.now(timezone.utc)
            await self.assembly_repo.save(assembly_with_iteration)

            logger.info(
                "Assembly completed successfully",
                extra={
                    "assembly_id": assembly_id,
                    "iterations_count": len(assembly_with_iteration.iterations),
                },
            )

            return assembly_with_iteration

        except Exception as e:
            # Mark assembly as failed
            assembly.status = AssemblyStatus.FAILED
            assembly.updated_at = datetime.now(timezone.utc)
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
    async def _register_document_with_services(
        self,
        document: Document,
        queries: Dict[str, KnowledgeServiceQuery],
        knowledge_services: Dict[str, KnowledgeService],
    ) -> Dict[str, str]:
        """
        Register the document with all knowledge services needed for assembly.

        This is a temporary solution - document registration will be handled
        properly in a separate process later.

        Args:
            document: The document to register
            queries: Dict of query_id to KnowledgeServiceQuery objects
            knowledge_services: Dict of service_id to KnowledgeService instances

        Returns:
            Dict mapping knowledge_service_id to service_file_id

        Raises:
            RuntimeError: If registration fails
        """
        registrations = {}
        required_service_ids = {query.knowledge_service_id for query in queries.values()}

        for knowledge_service_id in required_service_ids:
            knowledge_service = knowledge_services[knowledge_service_id]
            registration_result = await knowledge_service.register_file(
                document
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
        queries = {}
        for query_id in assembly_specification.knowledge_service_queries.values():
            query = await self.knowledge_service_query_repo.get(query_id)
            if not query:
                raise ValueError(f"Knowledge service query not found: {query_id}")
            queries[query_id] = query
        return queries

    @try_use_case_step("knowledge_services_retrieval")
    async def _retrieve_all_knowledge_services(
        self, queries: Dict[str, KnowledgeServiceQuery]
    ) -> Dict[str, KnowledgeService]:
        """Retrieve all unique knowledge services needed for this assembly."""
        knowledge_services = {}
        unique_service_ids = {query.knowledge_service_id for query in queries.values()}

        for service_id in unique_service_ids:
            knowledge_service = await self._get_knowledge_service(service_id)
            knowledge_services[service_id] = knowledge_service

        return knowledge_services

    @try_use_case_step("assembly_iteration")
    async def _assemble_iteration(
        self,
        document: Document,
        assembly_specification: AssemblySpecification,
        document_registrations: Dict[str, str],
        queries: Dict[str, KnowledgeServiceQuery],
        knowledge_services: Dict[str, KnowledgeService],
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
            knowledge_services: Dict of service_id to KnowledgeService instances

        Returns:
            ID of the newly created assembled document

        Raises:
            ValueError: If required entities are not found
            RuntimeError: If knowledge service operations fail
        """
        # Initialize the result data structure
        assembled_data: Dict[str, Any] = {}

        # Process each knowledge service query
        # TODO: This is where we may want to fan-out/fan-in to do these in parallel.
        for schema_pointer, query_id in assembly_specification.knowledge_service_queries.items():

            # Get the relevant schema section
            schema_section = self._extract_schema_section(
                assembly_specification.jsonschema, schema_pointer
            )

            # Get the query configuration
            query = queries[query_id]

            # Get the knowledge service
            knowledge_service = knowledge_services[query.knowledge_service_id]

            # Get the service file ID from our registrations
            service_file_id = document_registrations.get(
                query.knowledge_service_id
            )
            if not service_file_id:
                raise ValueError(
                    f"Document not registered with service {query.knowledge_service_id}"
                )

            # Execute the query with schema section embedded in the prompt
            query_text = self._build_query_with_schema(
                query.prompt, schema_section
            )

            query_result = await knowledge_service.execute_query(
                query_text=query_text,
                service_file_ids=[service_file_id],
                query_metadata=query.query_metadata,
                assistant_prompt=query.assistant_prompt,
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
                f"Assembly specification not found: {assembly_specification_id}"
            )
        return specification

    @try_use_case_step("document_retrieval")
    async def _retrieve_document(self, document_id: str) -> Document:
        """Retrieve document with error handling."""
        document = await self.document_repo.get(document_id)
        if not document:
            raise ValueError(f"Document not found: {document_id}")
        return document


    @try_use_case_step("knowledge_service_creation")
    async def _get_knowledge_service(
        self, knowledge_service_id: str
    ) -> KnowledgeService:
        """Get knowledge service instance with error handling."""
        config = await self.knowledge_service_config_repo.get(knowledge_service_id)
        if not config:
            raise ValueError(f"Knowledge service config not found: {knowledge_service_id}")
        return knowledge_service_factory(config)

    def _extract_schema_section(
        self, jsonschema: Dict[str, Any], schema_pointer: str
    ) -> Dict[str, Any]:
        """Extract the relevant section of the JSON schema using JSON Pointer."""
        if not schema_pointer:
            # Empty pointer refers to the entire schema
            return jsonschema

        try:
            ptr = jsonpointer.JsonPointer(schema_pointer)
            result = ptr.resolve(jsonschema)
            if not isinstance(result, dict):
                raise ValueError(f"Schema section '{schema_pointer}' is not a dictionary")
            return result
        except (jsonpointer.JsonPointerException, KeyError, TypeError) as e:
            raise ValueError(
                f"Cannot extract schema section '{schema_pointer}': {e}"
            )

    def _build_query_with_schema(
        self, base_prompt: str, schema_section: Dict[str, Any]
    ) -> str:
        """Build the query text with embedded JSON schema section."""
        schema_json = json.dumps(schema_section, indent=2)
        return f"""{base_prompt}

Please structure your response according to this JSON schema:
{schema_json}

Return only valid JSON that conforms to this schema, without any surrounding text or markdown formatting."""

    def _parse_query_result(self, result_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse the query result to extract the JSON response."""
        response_text = result_data.get("response", "")
        if not response_text:
            raise ValueError("Empty response from knowledge service")

        # Try to parse as JSON
        try:
            return json.loads(response_text.strip())
        except json.JSONDecodeError as e:
            logger.warning(
                "Failed to parse JSON response, returning as text",
                extra={"response": response_text, "error": str(e)},
            )
            # If it's not valid JSON, return as a string value
            return {"text": response_text.strip()}

    def _store_result_in_assembled_data(
        self,
        assembled_data: Dict[str, Any],
        schema_pointer: str,
        result_data: Dict[str, Any],
    ) -> None:
        """Store query result in the appropriate location in assembled data."""
        if not schema_pointer:
            # Root level - merge the entire result
            assembled_data.update(result_data)
        else:
            # Use JSON Pointer to set the data at the correct location
            try:
                # Convert pointer to path components, skipping "properties" wrapper
                path_parts = schema_pointer.strip("/").split("/") if schema_pointer.strip("/") else []

                # Remove "properties" from path if it exists (schema artifact)
                if path_parts and path_parts[0] == "properties":
                    path_parts = path_parts[1:]

                # If no path parts left, store at root level
                if not path_parts:
                    assembled_data.update(result_data)
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
                    f"Cannot store result at schema pointer '{schema_pointer}': {e}"
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
        content_bytes = assembled_content.encode('utf-8')

        # Create the assembled document with content stream at beginning
        content_stream = ContentStream(io.BytesIO(content_bytes))
        content_stream.seek(0)  # Ensure stream is at beginning

        assembled_document = Document(
            document_id=document_id,
            original_filename=f"assembled_{assembly_specification.name.replace(' ', '_')}.json",
            content_type="application/json",
            size_bytes=len(content_bytes),
            content_multihash=self._calculate_multihash_from_content(content_bytes),
            status=DocumentStatus.ASSEMBLED,
            content=content_stream,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        # Save the document
        await self.document_repo.store(assembled_document)

        return document_id

    def _validate_assembled_data(
        self, assembled_data: Dict[str, Any], assembly_specification: AssemblySpecification
    ) -> None:
        """Validate that the assembled data conforms to the JSON schema."""
        try:
            jsonschema.validate(assembled_data, assembly_specification.jsonschema)
            logger.debug(
                "Assembled data validation passed",
                extra={
                    "assembly_specification_id": assembly_specification.assembly_specification_id,
                },
            )
        except jsonschema.ValidationError as e:
            logger.error(
                "Assembled data validation failed",
                extra={
                    "assembly_specification_id": assembly_specification.assembly_specification_id,
                    "validation_error": str(e),
                    "error_path": list(e.absolute_path) if e.absolute_path else [],
                    "schema_path": list(e.schema_path) if e.schema_path else [],
                },
            )
            raise ValueError(f"Assembled data does not conform to JSON schema: {e.message}")
        except jsonschema.SchemaError as e:
            logger.error(
                "JSON schema is invalid",
                extra={
                    "assembly_specification_id": assembly_specification.assembly_specification_id,
                    "schema_error": str(e),
                },
            )
            raise ValueError(f"Invalid JSON schema in assembly specification: {e.message}")

    def _calculate_multihash_from_content(self, content_bytes: bytes) -> str:
        """Calculate multihash from content bytes."""
        # Calculate SHA-256 hash
        sha256_hash = hashlib.sha256(content_bytes).digest()

        # Create multihash with SHA-256 (code 0x12)
        mhash = multihash.encode(sha256_hash, multihash.SHA2_256)
        return str(mhash.hex())
