#!/usr/bin/env python3
"""
Example script to test AssembleDataUseCase with Anthropic knowledge services.

This script demonstrates how to:
1. Create test documents and assembly specifications
2. Set up knowledge service configurations and queries
3. Use the AssembleDataUseCase to assemble documents using Anthropic
4. View the complete assembled output

Requirements:
    - Set ANTHROPIC_API_KEY environment variable
    - Install dependencies: pip install anthropic

Usage:
    export ANTHROPIC_API_KEY="your-api-key-here"
    python -m julee_example.examples.anthropic_assemble_data_test
"""

import asyncio
import hashlib
import io
import json
import logging
import os
import traceback
from datetime import datetime, timezone
import multihash

from julee_example.domain import (
    Document,
    DocumentStatus,
    ContentStream,
    AssemblySpecification,
    AssemblySpecificationStatus,
    KnowledgeServiceConfig,
    KnowledgeServiceQuery,
)
from julee_example.domain.knowledge_service_config import ServiceApi
from julee_example.repositories.memory import (
    MemoryDocumentRepository,
    MemoryAssemblyRepository,
    MemoryAssemblySpecificationRepository,
    MemoryKnowledgeServiceConfigRepository,
    MemoryKnowledgeServiceQueryRepository,
)
from julee_example.use_cases.assemble_data import AssembleDataUseCase


def setup_logging() -> None:
    """Configure logging to see debug output."""
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()

    # Validate log level
    numeric_level = getattr(logging, log_level, None)
    if not isinstance(numeric_level, int):
        print(f"Invalid log level: {log_level}, defaulting to INFO")
        numeric_level = logging.INFO

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        force=True,  # Override any existing configuration
    )

    print(f"Logging configured at {log_level} level")


async def create_meeting_transcript_document() -> Document:
    """Create a meeting transcript document for testing."""
    # Create sample meeting transcript
    content_text = """Meeting Transcript - Q1 Planning Session
Date: March 15, 2024
Time: 2:00 PM - 3:30 PM
Attendees: Sarah Chen (Product Manager), Mike Rodriguez (Engineering Lead),
Lisa Wang (Designer)

Sarah: Thanks everyone for joining. Let's kick off our Q1 planning. Mike,
can you give us an update on the current sprint?

Mike: Sure, we're about 80% through sprint 23. We've completed the user
authentication module and are working on the data migration tool. Should be
done by Friday.

Lisa: Great! I've finished the mockups for the dashboard redesign. Sarah,
have you had a chance to review them?

Sarah: Yes, they look fantastic. I especially like the new navigation
structure. When can we start implementation?

Mike: I'd estimate 2 weeks for the frontend work, plus another week for
backend API changes.

Lisa: I can start on the component library updates while Mike works on the
APIs.

Sarah: Perfect. Let's also discuss the customer feedback integration. We had
47 responses to our survey.

Mike: The main requests were for better reporting and mobile optimization.

Sarah: Those should be our next priorities then. Lisa, can you start
sketching mobile designs?

Lisa: Absolutely. I'll have initial concepts by next Tuesday.

Sarah: Excellent. Any other items?

Mike: Just a heads up that we'll need to schedule downtime for the database
migration, probably next weekend.

Sarah: Noted. I'll coordinate with support. Meeting adjourned at 3:30 PM."""

    # Create content stream from text
    content_bytes = content_text.encode("utf-8")
    content_stream = ContentStream(io.BytesIO(content_bytes))

    # Generate document ID
    document_id = f"meeting-transcript-{int(datetime.now().timestamp())}"

    # Create document with proper multihash
    sha256_hash = hashlib.sha256(content_bytes).digest()
    mhash = multihash.encode(sha256_hash, multihash.SHA2_256)
    proper_multihash = str(mhash.hex())

    document = Document(
        document_id=document_id,
        original_filename="meeting_transcript.txt",
        content_type="text/plain",
        size_bytes=len(content_bytes),
        content_multihash=proper_multihash,
        status=DocumentStatus.CAPTURED,
        content=content_stream,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    print(f"✅ Created meeting transcript: {document.document_id}")
    print(f"   Filename: {document.original_filename}")
    print(f"   Size: {document.size_bytes} bytes")
    print(f"   Content type: {document.content_type}")

    return document


async def create_assembly_specification() -> AssemblySpecification:
    """Create an assembly specification for meeting minutes."""

    # Define JSON schema for meeting minutes
    meeting_minutes_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Meeting Minutes",
        "type": "object",
        "properties": {
            "meeting_info": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "date": {"type": "string", "format": "date"},
                    "start_time": {"type": "string"},
                    "end_time": {"type": "string"},
                    "attendees": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "role": {"type": "string"},
                            },
                            "required": ["name", "role"],
                        },
                    },
                },
                "required": ["title", "date", "attendees"],
            },
            "agenda_items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string"},
                        "discussion_points": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "decisions": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["topic"],
                },
            },
            "action_items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "task": {"type": "string"},
                        "assignee": {"type": "string"},
                        "due_date": {"type": "string"},
                        "priority": {
                            "type": "string",
                            "enum": ["low", "medium", "high"],
                        },
                    },
                    "required": ["task", "assignee"],
                },
            },
        },
        "required": ["meeting_info", "agenda_items"],
    }

    # Create assembly specification
    spec_id = f"meeting-minutes-spec-{int(datetime.now().timestamp())}"

    assembly_spec = AssemblySpecification(
        assembly_specification_id=spec_id,
        name="Meeting Minutes Assembly",
        applicability=(
            "Meeting transcripts from video conferences or in-person "
            "meetings that need to be structured into formal meeting minutes"
        ),
        jsonschema=meeting_minutes_schema,
        status=AssemblySpecificationStatus.ACTIVE,
        knowledge_service_queries={
            "/properties/meeting_info": "extract-meeting-info-query",
            "/properties/agenda_items": "extract-agenda-items-query",
            "/properties/action_items": "extract-action-items-query",
        },
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    print("✅ Created assembly specification:")
    print(f"   ID: {assembly_spec.assembly_specification_id}")
    print(f"   Name: {assembly_spec.name}")
    print(
        f"   Query mappings: {len(assembly_spec.knowledge_service_queries)}"
    )

    return assembly_spec


async def create_knowledge_service_config() -> KnowledgeServiceConfig:
    """Create Anthropic knowledge service configuration."""

    config_id = f"anthropic-ks-{int(datetime.now().timestamp())}"

    config = KnowledgeServiceConfig(
        knowledge_service_id=config_id,
        name="Anthropic Meeting Analysis Service",
        description=(
            "Anthropic Claude service for analyzing meeting transcripts and "
            "extracting structured data"
        ),
        service_api=ServiceApi.ANTHROPIC,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    print(
        f"✅ Created knowledge service config: {config.knowledge_service_id}"
    )
    print(f"   Name: {config.name}")
    print(f"   API: {config.service_api.value}")

    return config


async def create_knowledge_service_queries(
    knowledge_service_id: str,
) -> list[KnowledgeServiceQuery]:
    """Create knowledge service queries for meeting minutes parts."""

    queries = []

    # Query for meeting info extraction
    meeting_info_query = KnowledgeServiceQuery(
        query_id="extract-meeting-info-query",
        name="Extract Meeting Information",
        knowledge_service_id=knowledge_service_id,
        prompt=(
            "Extract the basic meeting information from this transcript "
            "including title, date, times, and attendees with their roles."
        ),
        query_metadata={"max_tokens": 1000, "temperature": 0.1},
        assistant_prompt=(
            "Looking at the meeting transcript, here's the extracted meeting "
            "information that conforms to the provided schema, without "
            "surrounding ```json ... ``` markers:"
        ),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    queries.append(meeting_info_query)

    # Query for agenda items extraction
    agenda_query = KnowledgeServiceQuery(
        query_id="extract-agenda-items-query",
        name="Extract Agenda Items",
        knowledge_service_id=knowledge_service_id,
        prompt=(
            "Analyze the meeting transcript and extract the main agenda "
            "items discussed, including the topic, key discussion points, "
            "and any decisions made for each item."
        ),
        query_metadata={"max_tokens": 2000, "temperature": 0.1},
        assistant_prompt=(
            "Analyzing the meeting transcript, here are the agenda items "
            "with discussion points and decisions that conform to the "
            "provided schema, without surrounding ```json ... ``` markers:"
        ),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    queries.append(agenda_query)

    # Query for action items extraction
    action_query = KnowledgeServiceQuery(
        query_id="extract-action-items-query",
        name="Extract Action Items",
        knowledge_service_id=knowledge_service_id,
        prompt=(
            "Identify and extract action items from the meeting transcript, "
            "including the specific task, who it's assigned to, any "
            "mentioned due dates, and the priority level."
        ),
        query_metadata={"max_tokens": 1500, "temperature": 0.1},
        assistant_prompt=(
            "From the meeting transcript, here are the identified action "
            "items formatted according to the provided schema, without "
            "surrounding ```json ... ``` markers:"
        ),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    queries.append(action_query)

    print(f"✅ Created {len(queries)} knowledge service queries:")
    for query in queries:
        print(f"   - {query.name} ({query.query_id})")

    return queries


async def setup_repositories_with_test_data() -> tuple:
    """Set up in-memory repositories with test data."""

    print("\n🔧 Setting up repositories with test data...")

    # Create repositories
    document_repo = MemoryDocumentRepository()
    assembly_repo = MemoryAssemblyRepository()
    assembly_spec_repo = MemoryAssemblySpecificationRepository()
    ks_config_repo = MemoryKnowledgeServiceConfigRepository()
    ks_query_repo = MemoryKnowledgeServiceQueryRepository()

    # Create test data
    document = await create_meeting_transcript_document()
    assembly_spec = await create_assembly_specification()
    ks_config = await create_knowledge_service_config()
    ks_queries = await create_knowledge_service_queries(
        ks_config.knowledge_service_id
    )

    # Store test data in repositories
    await document_repo.store(document)
    await assembly_spec_repo.save(assembly_spec)
    await ks_config_repo.save(ks_config)

    for query in ks_queries:
        await ks_query_repo.save(query)

    print("✅ Test data stored in repositories")

    return (
        document_repo,
        assembly_repo,
        assembly_spec_repo,
        ks_config_repo,
        ks_query_repo,
        document,
        assembly_spec,
    )


async def test_assemble_data_use_case() -> None:
    """Test the AssembleDataUseCase with Anthropic knowledge services."""

    # Check for API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ Error: ANTHROPIC_API_KEY environment variable not set")
        print("   Set it with: export ANTHROPIC_API_KEY='your-api-key-here'")
        return

    print("🚀 Testing AssembleDataUseCase with Anthropic knowledge services")
    print("=" * 70)

    try:
        # Set up repositories and test data
        (
            document_repo,
            assembly_repo,
            assembly_spec_repo,
            ks_config_repo,
            ks_query_repo,
            document,
            assembly_spec,
        ) = await setup_repositories_with_test_data()

        # Create the use case
        use_case = AssembleDataUseCase(
            document_repo=document_repo,
            assembly_repo=assembly_repo,
            assembly_specification_repo=assembly_spec_repo,
            knowledge_service_query_repo=ks_query_repo,
            knowledge_service_config_repo=ks_config_repo,
        )

        print("\n✅ Created AssembleDataUseCase with all repositories")

        # Execute the assembly
        print("\n🔄 Executing assembly...")
        print(f"   Document: {document.document_id}")
        print(f"   Specification: {assembly_spec.assembly_specification_id}")

        assembly_result = await use_case.assemble_data(
            document_id=document.document_id,
            assembly_specification_id=assembly_spec.assembly_specification_id,
        )

        print("\n✅ Assembly completed successfully!")
        print(f"   Assembly ID: {assembly_result.assembly_id}")
        print(f"   Status: {assembly_result.status.value}")
        print(f"   Iterations: {len(assembly_result.iterations)}")

        if assembly_result.iterations:
            iteration = assembly_result.iterations[0]
            print(f"   First iteration ID: {iteration.iteration_id}")
            print(f"   Assembled document ID: {iteration.document_id}")

            # Retrieve and display the assembled document
            assembled_doc = await document_repo.get(iteration.document_id)
            if assembled_doc:
                print("\n📄 Assembled Document Details:")
                print(f"   Document ID: {assembled_doc.document_id}")
                print(f"   Filename: {assembled_doc.original_filename}")
                print(f"   Size: {assembled_doc.size_bytes} bytes")
                print(f"   Status: {assembled_doc.status.value}")

                # Read and parse the assembled content
                assembled_doc.content.seek(0)
                content_bytes = assembled_doc.content.read()
                content_text = content_bytes.decode("utf-8")
                assembled_doc.content.seek(0)

                try:
                    assembled_data = json.loads(content_text)

                    print()
                    print("Assembled Meeting Minutes:")
                    print("=" * 50)
                    print(json.dumps(assembled_data, indent=2))

                    meeting_info = assembled_data.get("meeting_info", {})
                    agenda_items = assembled_data.get("agenda_items", [])
                    action_items = assembled_data.get("action_items", [])

                    print()
                    print("Assembly Statistics:")
                    print(
                        "   Meeting Title:", meeting_info.get("title", "N/A")
                    )
                    print(
                        "   Attendees:",
                        len(meeting_info.get("attendees", [])),
                    )
                    print("   Agenda Items:", len(agenda_items))
                    print("   Action Items:", len(action_items))

                except json.JSONDecodeError:
                    print()
                    print("Raw Assembled Content:")
                    print(content_text)

        print("\nTest completed successfully!")

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        traceback.print_exc()


async def main() -> None:
    """Main function to run the test."""
    print("Anthropic Assemble Data Use Case Test")
    print("====================================")

    # Setup logging first
    setup_logging()
    print()

    await test_assemble_data_use_case()


if __name__ == "__main__":
    # Run the async test
    asyncio.run(main())
