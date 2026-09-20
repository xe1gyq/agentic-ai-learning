"""Lesson 01: represent a human request as a minimal task contract."""

from dataclasses import dataclass


class ContractError(ValueError):
    """A request lacks the information needed to specify the task."""


@dataclass(frozen=True)
class TaskContract:
    goal: str
    inputs: tuple[str, ...]
    output: str
    constraints: tuple[str, ...]
    done_when: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.goal, str) or not self.goal.strip():
            raise ContractError("goal must be non-empty")
        if not isinstance(self.output, str) or not self.output.strip():
            raise ContractError("output must be non-empty")
        for name in ("inputs", "constraints", "done_when"):
            items = getattr(self, name)
            if (
                not isinstance(items, tuple)
                or not items
                or any(not isinstance(item, str) or not item.strip() for item in items)
            ):
                raise ContractError(f"{name} must be a non-empty tuple of text")


def prepare_task(request: str, contract: TaskContract | None) -> TaskContract:
    """Refuse execution when a request has no explicit acceptance criteria.

    A contract makes success criteria explicit; it does not verify them.
    """
    if not isinstance(request, str) or not request.strip():
        raise ContractError("request must be non-empty")
    if contract is None:
        raise ContractError("request needs a TaskContract with done_when before execution")
    return contract


def example_worker(contract: TaskContract) -> str:
    """Illustrate what a worker receives; this is not a completion check."""
    return (
        f"Goal: {contract.goal}\n"
        f"Inputs: {', '.join(contract.inputs)}\n"
        f"Output: {contract.output}\n"
        f"Constraints: {'; '.join(contract.constraints)}\n"
        f"Done when: {'; '.join(contract.done_when)}"
    )


if __name__ == "__main__":
    task = TaskContract(
        goal="Summarize Python 3.14 changes",
        inputs=("official release notes",),
        output="A short sourced report",
        constraints=("Use only supplied sources",),
        done_when=("Every claim has a source",),
    )
    print(example_worker(prepare_task("Research Python 3.14 changes", task)))
