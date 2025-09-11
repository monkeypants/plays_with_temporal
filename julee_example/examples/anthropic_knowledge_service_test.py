#!/usr/bin/env python3
"""
Example script to test AnthropicKnowledgeService with Document objects.

This script demonstrates how to:
1. Create a document directly
2. Register it with Anthropic using the beta Files API
3. Test the query execution functionality with assistant prompt constraints

Requirements:
    - Set ANTHROPIC_API_KEY environment variable
    - Install dependencies: pip install anthropic

Usage:
    export ANTHROPIC_API_KEY="your-api-key-here"
    python -m julee_example.examples.anthropic_knowledge_service_test
"""

import asyncio
import io
import logging
import os
from datetime import datetime, timezone

from julee_example.domain import (
    Document,
    DocumentStatus,
    KnowledgeServiceConfig,
)
from julee_example.domain.knowledge_service_config import ServiceApi
from julee_example.domain.custom_fields.content_stream import ContentStream
from julee_example.services.knowledge_service.anthropic import (
    AnthropicKnowledgeService,
)


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
    """Create a meeting transcript document for testing.

    Returns:
        The Document domain object
    """
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

    # Create document
    document = Document(
        document_id=document_id,
        original_filename="meeting_transcript.txt",
        content_type="text/plain",
        size_bytes=len(content_bytes),
        content_multihash="test-transcript-hash-12345",
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


async def create_json_schema_document() -> Document:
    """Create a JSON schema document for meeting minutes structure.

    Returns:
        The Document domain object
    """
    # Create JSON schema for meeting minutes
    schema_content = """{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Meeting Minutes",
  "type": "object",
  "properties": {
    "meeting_info": {
      "type": "object",
      "properties": {
        "title": {"type": "string"},
        "date": {"type": "string", "format": "date"},
        "start_time": {"type": "string", "format": "time"},
        "end_time": {"type": "string", "format": "time"},
        "attendees": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "name": {"type": "string"},
              "role": {"type": "string"}
            },
            "required": ["name"]
          }
        }
      },
      "required": ["title", "date", "attendees"]
    },
    "agenda_items": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "topic": {"type": "string"},
          "discussion_points": {
            "type": "array",
            "items": {"type": "string"}
          },
          "decisions": {
            "type": "array",
            "items": {"type": "string"}
          }
        },
        "required": ["topic"]
      }
    },
    "action_items": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "task": {"type": "string"},
          "assignee": {"type": "string"},
          "due_date": {"type": "string", "format": "date"},
          "priority": {"type": "string", "enum": ["low", "medium", "high"]}
        },
        "required": ["task", "assignee"]
      }
    },
    "next_steps": {
      "type": "array",
      "items": {"type": "string"}
    }
  },
  "required": ["meeting_info", "agenda_items"]
}"""

    # Create content stream from schema
    content_bytes = schema_content.encode("utf-8")
    content_stream = ContentStream(io.BytesIO(content_bytes))

    # Generate document ID
    document_id = f"schema-{int(datetime.now().timestamp())}"

    # Create document
    document = Document(
        document_id=document_id,
        original_filename="meeting_minutes_schema.json",
        content_type="text/plain",
        size_bytes=len(content_bytes),
        content_multihash="test-schema-hash-12345",
        status=DocumentStatus.CAPTURED,
        content=content_stream,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    print(f"✅ Created JSON schema: {document.document_id}")
    print(f"   Filename: {document.original_filename}")
    print(f"   Size: {document.size_bytes} bytes")
    print(f"   Content type: {document.content_type}")

    return document


async def test_anthropic_knowledge_service() -> None:
    """Test the AnthropicKnowledgeService with transcript and JSON schema."""

    # Check for API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("❌ Error: ANTHROPIC_API_KEY environment variable not set")
        print("   Set it with: export ANTHROPIC_API_KEY='your-api-key-here'")
        return

    print(
        "🚀 Testing AnthropicKnowledgeService with meeting transcript and "
        "JSON schema"
    )
    print("=" * 80)

    try:
        # Create meeting transcript document
        transcript_doc = await create_meeting_transcript_document()

        # Create JSON schema document
        schema_doc = await create_json_schema_document()

        # Create knowledge service configuration
        config = KnowledgeServiceConfig(
            knowledge_service_id="test-anthropic-meeting-ks",
            name="Test Anthropic Meeting Knowledge Service",
            description="Testing meeting transcript summarization with JSON "
            "schema",
            service_api=ServiceApi.ANTHROPIC,
        )
        print("✅ Created KnowledgeServiceConfig")

        # Create Anthropic knowledge service
        knowledge_service = AnthropicKnowledgeService(config)
        print("✅ Created AnthropicKnowledgeService")

        # Register both files with Anthropic
        print("\n📤 Registering meeting transcript with Anthropic...")
        transcript_result = await knowledge_service.register_file(
            transcript_doc
        )
        transcript_file_id = transcript_result.knowledge_service_file_id
        print(f"✅ Transcript registered - File ID: {transcript_file_id}")

        print("\n📤 Registering JSON schema with Anthropic...")
        schema_result = await knowledge_service.register_file(schema_doc)
        schema_file_id = schema_result.knowledge_service_file_id
        print(f"✅ Schema registered - File ID: {schema_file_id}")

        # Execute query with both files
        print("\n🔍 Executing query with both files...")
        query_text = (
            "Please summarise the following meeting transcript into a json "
            "file that satisfies the attached json schema"
        )
        print(f"   Query: {query_text}")

        # Use default model and settings with assistant prompt
        query_result = await knowledge_service.execute_query(
            query_text=query_text,
            service_file_ids=[
                transcript_result.knowledge_service_file_id,
                schema_result.knowledge_service_file_id,
            ],
            assistant_prompt=(
                "Looking at the meeting transcript, here's the formatted "
                "JSON summary that satisfies the provided schema, without "
                "surrounding ```json ... ``` markers:"
            ),
        )

        print("✅ Query executed successfully!")
        print(f"   Query ID: {query_result.query_id}")
        print(f"   Execution time: {query_result.execution_time_ms}ms")
        print(f"   Model: {query_result.result_data.get('model')}")
        usage = query_result.result_data.get("usage", {})
        print(f"   Input tokens: {usage.get('input_tokens')}")
        print(f"   Output tokens: {usage.get('output_tokens')}")
        file_count = len(query_result.result_data.get("sources", []))
        print(f"   Files provided: {file_count}")
        print("   Response:")
        print(f"   {query_result.result_data.get('response')}")

        response_text = query_result.result_data.get("response", "")
        print(f"\n📄 Response text ({len(response_text)} characters)")

        print("\n🎉 Test completed successfully!")

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()


async def main() -> None:
    """Main function to run the test."""
    print("Anthropic Knowledge Service Test")
    print("================================")

    # Setup logging first
    setup_logging()
    print()

    await test_anthropic_knowledge_service()


if __name__ == "__main__":
    # Run the async test
    asyncio.run(main())
