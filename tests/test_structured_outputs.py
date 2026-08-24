"""Tests for the structured-output task contract lesson."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from tests.lesson_loader import load_lesson_module


lesson = load_lesson_module(
    "structured_outputs_lesson",
    "fundamentals/06_structured_outputs/agent.py",
)


VALID_SPEC = {
    "goal": "Produce a verified report",
    "success_criteria": ["Three primary sources are cited"],
    "constraints": ["Do not publish without approval"],
    "risk_level": "medium",
    "requires_human_approval": True,
}


def test_parse_valid_task_spec():
    assert lesson.parse_task_spec(json.dumps(VALID_SPEC)) == VALID_SPEC


def test_rejects_missing_field():
    invalid = dict(VALID_SPEC)
    invalid.pop("goal")

    with pytest.raises(ValueError, match="missing"):
        lesson.validate_task_spec(invalid)


def test_rejects_wrong_business_type():
    invalid = dict(VALID_SPEC)
    invalid["requires_human_approval"] = "yes"

    with pytest.raises(ValueError, match="boolean"):
        lesson.validate_task_spec(invalid)


def test_api_call_uses_json_schema_and_parses_result():
    client = MagicMock()
    client.messages.create.return_value = SimpleNamespace(
        content=[SimpleNamespace(type="text", text=json.dumps(VALID_SPEC))]
    )

    result = lesson.extract_task_spec("Create a report", client)

    assert result == VALID_SPEC
    kwargs = client.messages.create.call_args.kwargs
    output_format = kwargs["output_config"]["format"]
    assert output_format["type"] == "json_schema"
    assert output_format["schema"] == lesson.TASK_SPEC_SCHEMA

