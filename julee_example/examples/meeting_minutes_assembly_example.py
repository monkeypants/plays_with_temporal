"""
Rich example of an Assembly configuration for meeting minutes extraction.

This example demonstrates a comprehensive Assembly setup for extracting
structured data from meeting transcripts, recordings, or documents.

The schema includes detailed descriptions to guide LLM extraction of:
- Meeting metadata (basic info, timing, location)
- Attendees (with roles and participation details)
- Action items (with assignments, deadlines, and priorities)
- Key decisions (with context and rationale)

This example is intended for demonstration and testing purposes.
"""

from julee_example.domain import Assembly, AssemblyStatus

# Rich meeting minutes assembly with detailed schema
meeting_minutes_assembly = Assembly(
    assembly_id="meeting-minutes-comprehensive-v1",
    name="Comprehensive Meeting Minutes",
    applicability=(
        "Corporate meetings, team standups, project reviews, board meetings, "
        "client calls, and any formal or semi-formal meeting where structured "
        "minutes need to be extracted. Applies to meeting transcripts from "
        "video calls (Zoom, Teams, etc.), audio recordings, or written notes. "
        "Best suited for meetings with clear agenda items, defined participants, "
        "and actionable outcomes."
    ),
    prompt=(
        "Extract comprehensive meeting information from this transcript or document. "
        "Focus on identifying key participants, their roles, and contributions. "
        "Capture all action items with clear ownership and deadlines. "
        "Document important decisions made during the meeting with context. "
        "Pay attention to meeting flow, timing, and any follow-up commitments. "
        "If information is unclear or missing, indicate this rather than guessing. "
        "Structure the output according to the provided JSON schema, ensuring "
        "all required fields are populated and optional fields are included when "
        "relevant information is available."
    ),
    jsonschema={
        "type": "object",
        "title": "Meeting Minutes Schema",
        "description": "Comprehensive schema for extracting structured meeting information",
        "properties": {
            "meeting_metadata": {
                "type": "object",
                "title": "Meeting Metadata",
                "description": "Basic information about the meeting context and logistics",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "The official title or subject of the meeting (e.g., 'Weekly Sprint Planning', 'Q4 Budget Review')"
                    },
                    "date": {
                        "type": "string",
                        "format": "date",
                        "description": "Meeting date in YYYY-MM-DD format"
                    },
                    "start_time": {
                        "type": "string",
                        "pattern": "^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$",
                        "description": "Meeting start time in HH:MM format (24-hour)"
                    },
                    "duration_minutes": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "Total meeting duration in minutes"
                    },
                    "meeting_type": {
                        "type": "string",
                        "enum": [
                            "standup",
                            "planning",
                            "review",
                            "retrospective",
                            "board_meeting",
                            "client_call",
                            "all_hands",
                            "one_on_one",
                            "workshop",
                            "other"
                        ],
                        "description": "Category of meeting to help with context understanding"
                    },
                    "location": {
                        "type": "string",
                        "description": "Meeting location (conference room name, video platform, or 'hybrid' for mixed)"
                    }
                },
                "required": ["title", "date"],
                "additionalProperties": False
            },
            "attendees": {
                "type": "array",
                "title": "Meeting Attendees",
                "description": "List of people who participated in the meeting",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Full name of the attendee as mentioned in the meeting"
                        },
                        "role": {
                            "type": "string",
                            "description": "Job title or role of the person (e.g., 'Product Manager', 'Senior Developer', 'CEO')"
                        },
                        "department": {
                            "type": "string",
                            "description": "Department or team the person belongs to (e.g., 'Engineering', 'Marketing', 'Executive')"
                        },
                        "attendance_type": {
                            "type": "string",
                            "enum": ["present", "late", "early_departure", "absent"],
                            "description": "How the person participated in the meeting"
                        },
                        "participation_level": {
                            "type": "string",
                            "enum": ["high", "medium", "low"],
                            "description": "How actively the person contributed to discussions (high: led discussions/made decisions, medium: regular participation, low: mostly listening)"
                        },
                        "key_contributions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Notable points, questions, or insights this person contributed during the meeting"
                        }
                    },
                    "required": ["name"],
                    "additionalProperties": False
                },
                "minItems": 1
            },
            "action_items": {
                "type": "array",
                "title": "Action Items",
                "description": "Specific tasks, commitments, or follow-up actions identified during the meeting",
                "items": {
                    "type": "object",
                    "properties": {
                        "description": {
                            "type": "string",
                            "description": "Clear, actionable description of what needs to be done (e.g., 'Update user authentication flow to support SSO', 'Schedule follow-up meeting with legal team')"
                        },
                        "assignee": {
                            "type": "string",
                            "description": "Name of the person responsible for completing this action item"
                        },
                        "due_date": {
                            "type": "string",
                            "format": "date",
                            "description": "Expected completion date in YYYY-MM-DD format"
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["urgent", "high", "medium", "low"],
                            "description": "Relative importance/urgency of this action item"
                        },
                        "category": {
                            "type": "string",
                            "description": "Type of action (e.g., 'research', 'development', 'meeting', 'documentation', 'review')"
                        },
                        "dependencies": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Other action items, people, or external factors this task depends on"
                        },
                        "estimated_effort": {
                            "type": "string",
                            "description": "Rough estimate of time/effort required (e.g., '2 hours', '1 day', '1 week')"
                        },
                        "context": {
                            "type": "string",
                            "description": "Why this action item is needed - background context from the meeting discussion"
                        }
                    },
                    "required": ["description", "assignee"],
                    "additionalProperties": False
                }
            },
            "key_decisions": {
                "type": "array",
                "title": "Key Decisions",
                "description": "Important decisions made during the meeting that affect project direction, resources, or processes",
                "items": {
                    "type": "object",
                    "properties": {
                        "decision": {
                            "type": "string",
                            "description": "Clear statement of what was decided (e.g., 'Approved budget increase for Q1 marketing campaign', 'Selected React for new frontend framework')"
                        },
                        "rationale": {
                            "type": "string",
                            "description": "Key reasons or factors that led to this decision"
                        },
                        "decision_maker": {
                            "type": "string",
                            "description": "Person who made or approved the final decision"
                        },
                        "alternatives_considered": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Other options that were discussed but not chosen"
                        },
                        "impact": {
                            "type": "string",
                            "description": "Expected effect or consequences of this decision on the team/project/organization"
                        },
                        "implementation_timeline": {
                            "type": "string",
                            "description": "When this decision will take effect or be implemented"
                        }
                    },
                    "required": ["decision"],
                    "additionalProperties": False
                }
            },
            "next_meeting": {
                "type": "object",
                "title": "Next Meeting Information",
                "description": "Details about planned follow-up meetings or recurring meeting schedules",
                "properties": {
                    "scheduled": {
                        "type": "boolean",
                        "description": "Whether a follow-up meeting was scheduled during this meeting"
                    },
                    "date": {
                        "type": "string",
                        "format": "date",
                        "description": "Date of the next meeting if scheduled"
                    },
                    "tentative_agenda": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Topics or agenda items mentioned for the next meeting"
                    },
                    "required_attendees": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "People who specifically need to attend the next meeting"
                    }
                },
                "required": ["scheduled"],
                "additionalProperties": False
            }
        },
        "required": ["meeting_metadata", "attendees", "action_items"],
        "additionalProperties": False
    },
    status=AssemblyStatus.ACTIVE,
    version="1.0.0"
)

# Example of how this would be used
if __name__ == "__main__":
    import json

    print("Meeting Minutes Assembly Example")
    print("=" * 50)
    print(f"Assembly ID: {meeting_minutes_assembly.assembly_id}")
    print(f"Name: {meeting_minutes_assembly.name}")
    print(f"Status: {meeting_minutes_assembly.status}")
    print(f"Version: {meeting_minutes_assembly.version}")
    print("\nApplicability:")
    print(meeting_minutes_assembly.applicability)
    print("\nPrompt:")
    print(meeting_minutes_assembly.prompt)
    print("\nJSON Schema Structure:")
    schema_properties = meeting_minutes_assembly.jsonschema["properties"]
    for key, value in schema_properties.items():
        print(f"- {key}: {value.get('title', key)}")
        if 'description' in value:
            print(f"  {value['description']}")

    print(f"\nFull JSON Schema: {json.dumps(meeting_minutes_assembly.jsonschema, indent=2)}")
