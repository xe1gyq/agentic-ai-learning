"""
Lesson 06 - Structured Outputs
===============================
Convert a natural-language task into a schema-valid task specification.

The API constrains Claude's final text block to TASK_SPEC_SCHEMA. The application
then parses and validates the result before another component can consume it.
"""

import json
import os
import sys
from typing import Any

MODEL = "claude-sonnet-4-6"

TASK_SPEC_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "goal": {
            "type": "string",
            "description": "The outcome the agent must achieve.",
        },
        "success_criteria": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Observable conditions that demonstrate completion.",
        },
        "constraints": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Limits the agent must not violate.",
        },
        "risk_level": {
            "type": "string",
            "enum": ["low", "medium", "high"],
        },
        "requires_human_approval": {"type": "boolean"},
    },
    "required": [
        "goal",
        "success_criteria",
        "constraints",
        "risk_level",
        "requires_human_approval",
    ],
    "additionalProperties": False,
}

REQUIRED_FIELDS: set[str] = set(TASK_SPEC_SCHEMA["required"])


def validate_task_spec(value: Any) -> dict[str, Any]:
    """Apply downstream checks even though the API guarantees the JSON shape."""
    if not isinstance(value, dict):
        raise ValueError("Task specification must be a JSON object")

    if set(value) != REQUIRED_FIELDS:
        missing = REQUIRED_FIELDS - set(value)
        extra = set(value) - REQUIRED_FIELDS
        raise ValueError(f"Unexpected fields; missing={sorted(missing)}, extra={sorted(extra)}")

    if not isinstance(value["goal"], str) or not value["goal"].strip():
        raise ValueError("goal must be a non-empty string")

    for field in ("success_criteria", "constraints"):
        items = value[field]
        if not isinstance(items, list) or not all(isinstance(item, str) for item in items):
            raise ValueError(f"{field} must be a list of strings")

    if value["risk_level"] not in {"low", "medium", "high"}:
        raise ValueError("risk_level must be low, medium, or high")

    if not isinstance(value["requires_human_approval"], bool):
        raise ValueError("requires_human_approval must be a boolean")

    return value


def parse_task_spec(text: str) -> dict[str, Any]:
    """Parse Claude's JSON text block and enforce application-level invariants."""
    return validate_task_spec(json.loads(text))


def extract_task_spec(task: str, client: Any) -> dict[str, Any]:
    """Ask Claude for a structured task contract using an injected API client."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=(
            "You convert user requests into explicit agent task contracts. "
            "Success criteria must be observable. Mark approval true for external, "
            "destructive, irreversible, financial, or publication actions."
        ),
        messages=[{"role": "user", "content": task}],
        output_config={
            "format": {
                "type": "json_schema",
                "schema": TASK_SPEC_SCHEMA,
            }
        },
    )

    text_block = next(
        (block.text for block in response.content if block.type == "text"),
        None,
    )
    if text_block is None:
        raise RuntimeError("Claude returned no structured text block")
    return parse_task_spec(text_block)


def main() -> None:
    """Load configuration, call Claude, and print the validated contract."""
    import anthropic
    from dotenv import load_dotenv

    load_dotenv()
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    default_task = (
        "Research three primary sources about agent memory, write a short report, "
        "and ask me before publishing it anywhere."
    )
    task = " ".join(sys.argv[1:]).strip() or default_task
    result = extract_task_spec(task, client)

    print("Task contract:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("\nSchema valid: yes")
    print("Semantically verified: not yet")


if __name__ == "__main__":
    main()
