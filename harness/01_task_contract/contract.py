"""Minimal, framework-free task contract and deterministic completion gate."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any


class ContractError(ValueError):
    """An incoming task is incomplete or malformed."""


@dataclass(frozen=True)
class DoneCriterion:
    id: str
    description: str


@dataclass(frozen=True)
class TaskContract:
    goal: str
    inputs: Mapping[str, str]
    output: str
    constraints: tuple[str, ...]
    done_when: tuple[DoneCriterion, ...]


@dataclass(frozen=True)
class CompletionResult:
    done: bool
    passed: tuple[str, ...]
    failed: tuple[str, ...]
    errors: Mapping[str, str]


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{field} must be non-empty text")
    return value.strip()


def parse_contract(payload: Mapping[str, Any]) -> TaskContract:
    """Admit only a complete task; copy mutable inputs into immutable runtime state."""
    if not isinstance(payload, Mapping):
        raise ContractError("contract must be an object")
    required = {"goal", "inputs", "output", "constraints", "done_when"}
    unknown = set(payload) - required
    missing = required - set(payload)
    if unknown:
        raise ContractError(f"unknown contract fields: {sorted(unknown)}")
    if missing:
        raise ContractError(f"missing contract fields: {sorted(missing)}")

    inputs = payload["inputs"]
    if not isinstance(inputs, Mapping) or not inputs:
        raise ContractError("inputs must be a non-empty object")
    validated_inputs = {
        _text(key, "input key"): _text(value, f"input {key!r}") for key, value in inputs.items()
    }

    constraints = payload["constraints"]
    if not isinstance(constraints, list) or not constraints:
        raise ContractError("constraints must be a non-empty list")
    validated_constraints = tuple(_text(item, "constraint") for item in constraints)
    if len(set(validated_constraints)) != len(validated_constraints):
        raise ContractError("duplicate constraints are not allowed")

    done_when = payload["done_when"]
    if not isinstance(done_when, list) or not done_when:
        raise ContractError("done_when must be a non-empty list")
    criteria = []
    for item in done_when:
        if not isinstance(item, Mapping) or set(item) != {"id", "description"}:
            raise ContractError("done_when items require only id and description")
        criteria.append(
            DoneCriterion(
                id=_text(item["id"], "criterion id"),
                description=_text(item["description"], "criterion description"),
            )
        )
    if len({item.id for item in criteria}) != len(criteria):
        raise ContractError("duplicate done_when criterion IDs are not allowed")

    return TaskContract(
        goal=_text(payload["goal"], "goal"),
        inputs=MappingProxyType(validated_inputs),
        output=_text(payload["output"], "output"),
        constraints=validated_constraints,
        done_when=tuple(criteria),
    )


def check_completion(
    contract: TaskContract,
    produced_outputs: Mapping[str, str],
    checks: Mapping[str, Callable[[str], bool]],
) -> CompletionResult:
    """Require a non-empty artifact and an external check for every done criterion.

    This does not enforce constraints or authorize tools: those are later lessons.
    A missing, failed, or broken check fails closed.
    """
    output = produced_outputs.get(contract.output, "")
    passed: list[str] = []
    failed: list[str] = []
    errors: dict[str, str] = {}
    if not isinstance(output, str) or not output.strip():
        failed.append("output")

    for criterion in contract.done_when:
        verifier = checks.get(criterion.id)
        if verifier is None:
            failed.append(criterion.id)
            continue
        try:
            if verifier(output) is True:
                passed.append(criterion.id)
            else:
                failed.append(criterion.id)
        except Exception as error:
            failed.append(criterion.id)
            errors[criterion.id] = type(error).__name__

    return CompletionResult(
        done=not failed,
        passed=tuple(passed),
        failed=tuple(failed),
        errors=MappingProxyType(errors),
    )


def demo() -> CompletionResult:
    """Offline walkthrough: admission, artifact production, independent checks."""
    contract = parse_contract(
        {
            "goal": "Compare turn-based and goal-based loops",
            "inputs": {"question": "When should each pattern be used?"},
            "output": "report.md",
            "constraints": ["Do not publish"],
            "done_when": [
                {"id": "coverage", "description": "Both patterns are explained"},
                {"id": "citation", "description": "A source is cited"},
            ],
        }
    )
    report = "Turn-based loops run one requested task. Goal-based loops stop at a goal. Source: lesson notes."
    return check_completion(
        contract,
        produced_outputs={"report.md": report},
        checks={
            "coverage": lambda text: "Turn-based" in text and "Goal-based" in text,
            "citation": lambda text: "Source:" in text,
        },
    )


if __name__ == "__main__":
    print(demo())
