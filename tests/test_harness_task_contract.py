"""Lesson 01: a task contract is an admission and completion boundary."""

import pytest

from tests.lesson_loader import load_lesson_module

lesson = load_lesson_module("harness_task_contract", "harness/01_task_contract/contract.py")


def valid_payload():
    return {
        "goal": "Write a sourced comparison of two loop patterns",
        "inputs": {"question": "When should each loop be used?"},
        "output": "report.md",
        "constraints": ["Use only the supplied sources", "Do not publish the report"],
        "done_when": [
            {"id": "coverage", "description": "Both patterns are compared"},
            {"id": "citations", "description": "Every claim has a source"},
        ],
    }


def test_valid_contract_is_immutable_and_normalized():
    payload = valid_payload()
    contract = lesson.parse_contract(payload)
    payload["inputs"]["question"] = "changed later"

    assert contract.goal == "Write a sourced comparison of two loop patterns"
    assert contract.inputs["question"] == "When should each loop be used?"
    assert contract.done_when[0].id == "coverage"
    with pytest.raises(TypeError):
        contract.inputs["question"] = "mutated"


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"goal": "  "}, "goal"),
        ({"inputs": {}}, "inputs"),
        ({"output": ""}, "output"),
        ({"constraints": []}, "constraints"),
        ({"done_when": []}, "done_when"),
    ],
)
def test_missing_or_empty_contract_fields_are_rejected(change, message):
    payload = valid_payload()
    payload.update(change)

    with pytest.raises(lesson.ContractError, match=message):
        lesson.parse_contract(payload)


def test_unknown_fields_and_duplicate_criterion_ids_are_rejected():
    payload = valid_payload()
    payload["permission_to_publish"] = True
    with pytest.raises(lesson.ContractError, match="unknown"):
        lesson.parse_contract(payload)

    payload = valid_payload()
    payload["done_when"][1]["id"] = "coverage"
    with pytest.raises(lesson.ContractError, match="duplicate"):
        lesson.parse_contract(payload)


def test_completion_requires_output_and_external_checks_not_model_claims():
    contract = lesson.parse_contract(valid_payload())
    result = lesson.check_completion(
        contract,
        produced_outputs={"report.md": "# Comparison"},
        checks={"coverage": lambda _: True, "citations": lambda _: False},
    )

    assert result.done is False
    assert result.passed == ("coverage",)
    assert result.failed == ("citations",)


def test_completion_fails_closed_on_missing_output_or_verifier():
    contract = lesson.parse_contract(valid_payload())

    missing_output = lesson.check_completion(
        contract,
        produced_outputs={},
        checks={"coverage": lambda _: True, "citations": lambda _: True},
    )
    missing_check = lesson.check_completion(
        contract,
        produced_outputs={"report.md": "report"},
        checks={"coverage": lambda _: True},
    )

    assert missing_output.done is False
    assert "output" in missing_output.failed
    assert missing_check.done is False
    assert "citations" in missing_check.failed


def test_verifier_failure_is_reported_and_cannot_mark_task_done():
    contract = lesson.parse_contract(valid_payload())

    def broken(_):
        raise RuntimeError("validator unavailable")

    result = lesson.check_completion(
        contract,
        produced_outputs={"report.md": "report"},
        checks={"coverage": broken, "citations": lambda _: True},
    )

    assert result.done is False
    assert result.failed == ("coverage",)
    assert result.errors == {"coverage": "RuntimeError"}
