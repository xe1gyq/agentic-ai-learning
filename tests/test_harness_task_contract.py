"""A request alone cannot define successful task completion."""

import pytest

from tests.lesson_loader import load_lesson_module

lesson = load_lesson_module("harness_task_contract", "harness/01_task_contract/contract.py")


def valid_contract():
    return lesson.TaskContract(
        goal="Research Python 3.14 changes",
        inputs=("official release notes",),
        output="A short sourced report",
        constraints=("Use only supplied sources",),
        done_when=("Every claim has a source",),
    )


def test_bare_request_cannot_be_admitted_as_an_executable_task():
    with pytest.raises(lesson.ContractError, match="done_when"):
        lesson.prepare_task("Research Python 3.14 changes", None)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("goal", " "),
        ("inputs", ()),
        ("output", ""),
        ("constraints", ()),
        ("done_when", ()),
        ("done_when", (" ",)),
    ],
)
def test_obviously_incomplete_contracts_are_rejected(field, value):
    data = {
        "goal": "Research Python 3.14 changes",
        "inputs": ("official release notes",),
        "output": "A short sourced report",
        "constraints": ("Use only supplied sources",),
        "done_when": ("Every claim has a source",),
    }
    data[field] = value

    with pytest.raises(lesson.ContractError, match=field):
        lesson.TaskContract(**data)


def test_contract_is_transportable_data_not_a_verifier_or_permission_system():
    contract = lesson.prepare_task("Research Python 3.14 changes", valid_contract())
    worker_input = lesson.example_worker(contract)

    assert "official release notes" in worker_input
    assert "Use only supplied sources" in worker_input
    assert "Every claim has a source" in worker_input
    assert not hasattr(contract, "verify")
    assert not hasattr(contract, "authorize")
    with pytest.raises(AttributeError):
        contract.goal = "Different goal"
