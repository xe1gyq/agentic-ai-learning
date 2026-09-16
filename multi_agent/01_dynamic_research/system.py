"""Dynamic orchestrator-worker research graph with explicit engineering controls.

The lead owns strategy, resource allocation, graph expansion, and stopping. Workers
own bounded local exploration and return compressed evidence artifacts. The module is
model-agnostic so the orchestration, failure, and evaluation behavior remains testable.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol


class Complexity(StrEnum):
    """Query classes used by the resource scheduling policy."""

    SIMPLE = "simple"
    COMPARISON = "comparison"
    COMPLEX = "complex"


@dataclass(frozen=True)
class RunLimits:
    """Global and per-worker limits for one research run."""

    max_workers: int
    max_waves: int
    max_total_tasks: int
    max_total_tokens: int
    max_total_tool_calls: int
    max_tokens_per_worker: int
    max_tool_calls_per_worker: int
    max_artifact_chars: int


def resource_policy(complexity: Complexity) -> RunLimits:
    """Translate task complexity into an explicit test-time compute budget."""
    policies = {
        Complexity.SIMPLE: RunLimits(
            max_workers=1,
            max_waves=2,
            max_total_tasks=2,
            max_total_tokens=1_500,
            max_total_tool_calls=5,
            max_tokens_per_worker=1_000,
            max_tool_calls_per_worker=5,
            max_artifact_chars=2_000,
        ),
        Complexity.COMPARISON: RunLimits(
            max_workers=4,
            max_waves=4,
            max_total_tasks=8,
            max_total_tokens=10_000,
            max_total_tool_calls=40,
            max_tokens_per_worker=2_500,
            max_tool_calls_per_worker=10,
            max_artifact_chars=4_000,
        ),
        Complexity.COMPLEX: RunLimits(
            max_workers=8,
            max_waves=8,
            max_total_tasks=20,
            max_total_tokens=30_000,
            max_total_tool_calls=120,
            max_tokens_per_worker=5_000,
            max_tool_calls_per_worker=15,
            max_artifact_chars=6_000,
        ),
    }
    return policies[complexity]


@dataclass(frozen=True)
class ResearchTask:
    """One bounded search trajectory delegated to a worker."""

    id: str
    objective: str
    search_queries: tuple[str, ...] = ()
    depends_on: tuple[str, ...] = ()


@dataclass(frozen=True)
class ResearchPlan:
    """The lead's initial graph and its resource class."""

    complexity: Complexity
    rationale: str
    tasks: tuple[ResearchTask, ...]


@dataclass(frozen=True)
class WorkerBudget:
    """The hard allocation granted to one worker invocation."""

    max_tokens: int
    max_tool_calls: int


@dataclass(frozen=True)
class Usage:
    """System telemetry consumed by one artifact or the full run."""

    tokens: int = 0
    tool_calls: int = 0
    wall_clock_ms: int = 0

    def __add__(self, other: Usage) -> Usage:
        return Usage(
            tokens=self.tokens + other.tokens,
            tool_calls=self.tool_calls + other.tool_calls,
            wall_clock_ms=self.wall_clock_ms + other.wall_clock_ms,
        )


@dataclass(frozen=True)
class Finding:
    """A claim-evidence-source unit produced inside a worker's local context."""

    claim: str
    evidence: str
    source_url: str
    confidence: float


@dataclass(frozen=True)
class CompressedArtifact:
    """Small handoff from a large worker-local search trajectory."""

    task_id: str
    summary: str
    findings: tuple[Finding, ...]
    sources: tuple[str, ...]
    uncertainties: tuple[str, ...]
    usage: Usage
    raw_chars: int

    @property
    def artifact_chars(self) -> int:
        pieces = [self.summary, *self.sources, *self.uncertainties]
        for finding in self.findings:
            pieces.extend((finding.claim, finding.evidence, finding.source_url))
        return sum(len(piece) for piece in pieces)

    @property
    def compression_ratio(self) -> float:
        return self.raw_chars / max(self.artifact_chars, 1)


@dataclass(frozen=True)
class ReviewDecision:
    """Evidence-dependent graph update made by the lead after a wave."""

    done: bool
    rationale: str
    new_tasks: tuple[ResearchTask, ...] = ()


@dataclass(frozen=True)
class ResearchReport:
    """Final answer plus the citations and uncertainty exposed to the user."""

    answer: str
    citations: tuple[str, ...]
    uncertainties: tuple[str, ...]


@dataclass(frozen=True)
class ParallelismProfile:
    """Static evidence about independence in the currently known task graph."""

    task_count: int
    max_width: int
    critical_path_length: int
    theoretical_speedup: float
    multi_agent_recommended: bool


def parallelism_profile(tasks: list[ResearchTask] | tuple[ResearchTask, ...]) -> ParallelismProfile:
    """Measure graph width and critical path before paying for multiple agents."""
    if not tasks:
        return ParallelismProfile(0, 0, 0, 0.0, False)

    by_id = {task.id: task for task in tasks}
    if len(by_id) != len(tasks):
        raise ValueError("research task IDs must be unique")
    for item in tasks:
        unknown = sorted(set(item.depends_on) - set(by_id))
        if unknown:
            raise ValueError(f"task {item.id!r} has unknown dependencies: {unknown}")

    visiting: set[str] = set()
    depths: dict[str, int] = {}

    def depth(task_id: str) -> int:
        if task_id in depths:
            return depths[task_id]
        if task_id in visiting:
            raise ValueError("research task graph contains a cycle")
        visiting.add(task_id)
        dependencies = by_id[task_id].depends_on
        value = 1 + max((depth(dependency) for dependency in dependencies), default=0)
        visiting.remove(task_id)
        depths[task_id] = value
        return value

    for task_id in by_id:
        depth(task_id)

    widths = Counter(depths.values())
    critical_path = max(depths.values())
    theoretical_speedup = len(tasks) / critical_path
    max_width = max(widths.values())
    return ParallelismProfile(
        task_count=len(tasks),
        max_width=max_width,
        critical_path_length=critical_path,
        theoretical_speedup=theoretical_speedup,
        multi_agent_recommended=max_width > 1 and theoretical_speedup >= 1.5,
    )


@dataclass
class ResearchState:
    """Durable global run state; worker-local raw context never enters it."""

    run_id: str
    query: str
    complexity: Complexity
    limits: RunLimits
    tasks: dict[str, ResearchTask]
    completed: dict[str, CompressedArtifact] = field(default_factory=dict)
    failed_task_ids: list[str] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)
    wave: int = 0
    status: str = "running"


@dataclass(frozen=True)
class RunResult:
    """Completed report and the inspectable final execution state."""

    report: ResearchReport
    state: ResearchState


@dataclass(frozen=True)
class TelemetryEvent:
    """Privacy-conscious event containing decisions and metrics, not prompt contents."""

    timestamp: str
    category: str
    name: str
    run_id: str
    wave: int
    attributes: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TelemetryRecorder:
    """Collect system and behavior telemetry, optionally as durable JSONL."""

    def __init__(self, path: Path | None = None):
        self.path = path
        self.events: list[TelemetryEvent] = []

    def record(
        self,
        category: str,
        name: str,
        run_id: str,
        wave: int,
        **attributes: Any,
    ) -> None:
        event = TelemetryEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            category=category,
            name=name,
            run_id=run_id,
            wave=wave,
            attributes=attributes,
        )
        self.events.append(event)
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")


class CheckpointStore(Protocol):
    """Persistence boundary used by the orchestrator."""

    def load(self, run_id: str) -> ResearchState | None: ...

    def save(self, state: ResearchState) -> None: ...


def _task_from_dict(value: dict[str, Any]) -> ResearchTask:
    return ResearchTask(
        id=str(value["id"]),
        objective=str(value["objective"]),
        search_queries=tuple(value.get("search_queries", [])),
        depends_on=tuple(value.get("depends_on", [])),
    )


def _artifact_from_dict(value: dict[str, Any]) -> CompressedArtifact:
    return CompressedArtifact(
        task_id=str(value["task_id"]),
        summary=str(value["summary"]),
        findings=tuple(Finding(**finding) for finding in value["findings"]),
        sources=tuple(value["sources"]),
        uncertainties=tuple(value["uncertainties"]),
        usage=Usage(**value["usage"]),
        raw_chars=int(value["raw_chars"]),
    )


def state_to_dict(state: ResearchState) -> dict[str, Any]:
    """Serialize a checkpoint without relying on model or framework objects."""
    return {
        "version": 1,
        "run_id": state.run_id,
        "query": state.query,
        "complexity": state.complexity.value,
        "limits": asdict(state.limits),
        "tasks": {key: asdict(value) for key, value in state.tasks.items()},
        "completed": {key: asdict(value) for key, value in state.completed.items()},
        "failed_task_ids": list(state.failed_task_ids),
        "usage": asdict(state.usage),
        "wave": state.wave,
        "status": state.status,
    }


def state_from_dict(value: dict[str, Any]) -> ResearchState:
    """Restore application-owned state from a versioned checkpoint."""
    if value.get("version") != 1:
        raise ValueError("unsupported checkpoint version")
    return ResearchState(
        run_id=str(value["run_id"]),
        query=str(value["query"]),
        complexity=Complexity(value["complexity"]),
        limits=RunLimits(**value["limits"]),
        tasks={key: _task_from_dict(task) for key, task in value["tasks"].items()},
        completed={
            key: _artifact_from_dict(artifact) for key, artifact in value["completed"].items()
        },
        failed_task_ids=list(value["failed_task_ids"]),
        usage=Usage(**value["usage"]),
        wave=int(value["wave"]),
        status=str(value["status"]),
    )


class InMemoryCheckpointStore:
    """Round-tripped in-memory checkpoints for tests and short demos."""

    def __init__(self) -> None:
        self._states: dict[str, dict[str, Any]] = {}

    def load(self, run_id: str) -> ResearchState | None:
        value = self._states.get(run_id)
        return state_from_dict(json.loads(json.dumps(value))) if value is not None else None

    def save(self, state: ResearchState) -> None:
        self._states[state.run_id] = state_to_dict(state)


class JsonCheckpointStore:
    """Atomic filesystem checkpoint store suitable for local resume exercises."""

    def __init__(self, directory: Path):
        self.directory = directory

    def _path(self, run_id: str) -> Path:
        safe_name = hashlib.sha256(run_id.encode("utf-8")).hexdigest()
        return self.directory / f"{safe_name}.json"

    def load(self, run_id: str) -> ResearchState | None:
        path = self._path(run_id)
        if not path.exists():
            return None
        return state_from_dict(json.loads(path.read_text(encoding="utf-8")))

    def save(self, state: ResearchState) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self._path(state.run_id)
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(state_to_dict(state), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)


class LeadResearcher(Protocol):
    """Executive role: plan, inspect global evidence, expand, stop, synthesize."""

    async def plan(self, query: str, limits: RunLimits) -> ResearchPlan: ...

    async def review(
        self,
        query: str,
        artifacts: tuple[CompressedArtifact, ...],
        state: ResearchState,
    ) -> ReviewDecision: ...

    async def synthesize(
        self,
        query: str,
        artifacts: tuple[CompressedArtifact, ...],
    ) -> ResearchReport: ...


class ResearchWorker(Protocol):
    """Bounded local role: explore independently and compress findings."""

    async def research(
        self,
        task: ResearchTask,
        budget: WorkerBudget,
    ) -> CompressedArtifact: ...


class ContractViolation(RuntimeError):
    """Raised when an artifact or report violates a deterministic boundary."""


class BudgetExceeded(RuntimeError):
    """Raised when the executive can no longer allocate safe bounded work."""


class ResearchExecutionError(RuntimeError):
    """Raised after checkpointing a failed wave so it can later resume."""


def verify_artifact(
    task: ResearchTask,
    artifact: CompressedArtifact,
    budget: WorkerBudget,
    limits: RunLimits,
) -> None:
    """Verify identity, provenance, compression, and per-worker resource use."""
    if artifact.task_id != task.id:
        raise ContractViolation("artifact task identity does not match its assignment")
    if not artifact.summary.strip() or not artifact.findings:
        raise ContractViolation("artifact must contain a summary and at least one finding")
    if artifact.artifact_chars > limits.max_artifact_chars:
        raise ContractViolation("artifact exceeds the lead-context character budget")
    if artifact.raw_chars <= artifact.artifact_chars:
        raise ContractViolation("artifact must compress its larger local search context")
    if artifact.usage.tokens > budget.max_tokens:
        raise ContractViolation("worker exceeded its token allocation")
    if artifact.usage.tool_calls > budget.max_tool_calls:
        raise ContractViolation("worker exceeded its tool-call allocation")

    source_set = set(artifact.sources)
    if len(source_set) != len(artifact.sources):
        raise ContractViolation("artifact sources must be unique")
    for finding in artifact.findings:
        if finding.source_url not in source_set:
            raise ContractViolation("finding provenance is absent from artifact sources")
        if not 0 <= finding.confidence <= 1:
            raise ContractViolation("finding confidence must be between zero and one")


def verify_report(report: ResearchReport, artifacts: list[CompressedArtifact]) -> None:
    """Require final citations to come from verified worker evidence."""
    available_sources = {source for artifact in artifacts for source in artifact.sources}
    if not report.answer.strip() or not report.citations:
        raise ContractViolation("final report must contain an answer and citations")
    unknown = sorted(set(report.citations) - available_sources)
    if unknown:
        raise ContractViolation(f"report contains unknown citation sources: {unknown}")
    uncited = [citation for citation in report.citations if citation not in report.answer]
    if uncited:
        raise ContractViolation(f"report citations are not present in the answer: {uncited}")


class DynamicResearchOrchestrator:
    """Execute, extend, checkpoint, and verify an evidence-dependent research graph."""

    def __init__(
        self,
        lead: LeadResearcher,
        worker: ResearchWorker,
        checkpoint_store: CheckpointStore,
        telemetry: TelemetryRecorder,
    ):
        self.lead = lead
        self.worker = worker
        self.checkpoint_store = checkpoint_store
        self.telemetry = telemetry

    def _save(self, state: ResearchState) -> None:
        self.checkpoint_store.save(state)
        self.telemetry.record(
            "system",
            "checkpoint_saved",
            state.run_id,
            state.wave,
            completed_tasks=len(state.completed),
            pending_tasks=len(state.tasks) - len(state.completed),
        )

    @staticmethod
    def _ready_tasks(state: ResearchState) -> list[ResearchTask]:
        completed = set(state.completed)
        return [
            task
            for task in state.tasks.values()
            if task.id not in completed and set(task.depends_on) <= completed
        ]

    @staticmethod
    def _allocate(state: ResearchState, worker_count: int) -> WorkerBudget:
        remaining_tokens = state.limits.max_total_tokens - state.usage.tokens
        remaining_calls = state.limits.max_total_tool_calls - state.usage.tool_calls
        if remaining_tokens < worker_count or remaining_calls < worker_count:
            raise BudgetExceeded("insufficient remaining budget for the next worker wave")
        return WorkerBudget(
            max_tokens=min(
                state.limits.max_tokens_per_worker,
                remaining_tokens // worker_count,
            ),
            max_tool_calls=min(
                state.limits.max_tool_calls_per_worker,
                remaining_calls // worker_count,
            ),
        )

    async def _execute_task(
        self,
        state: ResearchState,
        task: ResearchTask,
        budget: WorkerBudget,
    ) -> CompressedArtifact:
        self.telemetry.record(
            "behavior",
            "worker_started",
            state.run_id,
            state.wave,
            task_id=task.id,
            depends_on=list(task.depends_on),
            token_budget=budget.max_tokens,
            tool_call_budget=budget.max_tool_calls,
        )
        artifact = await self.worker.research(task, budget)
        verify_artifact(task, artifact, budget, state.limits)
        self.telemetry.record(
            "system",
            "worker_completed",
            state.run_id,
            state.wave,
            task_id=task.id,
            tokens=artifact.usage.tokens,
            tool_calls=artifact.usage.tool_calls,
            compression_ratio=round(artifact.compression_ratio, 2),
        )
        return artifact

    async def run(self, query: str, run_id: str) -> RunResult:
        """Run or resume research until the lead stops or a hard boundary fires."""
        state = self.checkpoint_store.load(run_id)
        if state is None:
            planning_ceiling = resource_policy(Complexity.COMPLEX)
            plan = await self.lead.plan(query, planning_ceiling)
            limits = resource_policy(plan.complexity)
            if not plan.tasks:
                raise ContractViolation("lead plan must contain at least one task")
            if len(plan.tasks) > limits.max_total_tasks:
                raise BudgetExceeded("initial plan exceeds the task budget")
            profile = parallelism_profile(plan.tasks)
            state = ResearchState(
                run_id=run_id,
                query=query,
                complexity=plan.complexity,
                limits=limits,
                tasks={task.id: task for task in plan.tasks},
            )
            self.telemetry.record(
                "behavior",
                "plan_created",
                run_id,
                0,
                complexity=plan.complexity.value,
                task_count=len(plan.tasks),
                max_width=profile.max_width,
                critical_path=profile.critical_path_length,
                multi_agent_recommended=profile.multi_agent_recommended,
            )
            self._save(state)
        elif state.query != query:
            raise ValueError("run_id belongs to a different research query")
        elif state.status == "completed":
            raise ValueError("research run is already completed")
        else:
            state.status = "running"
            self.telemetry.record(
                "system",
                "run_resumed",
                run_id,
                state.wave,
                completed_tasks=len(state.completed),
                failed_tasks=list(state.failed_task_ids),
            )

        while True:
            if state.wave >= state.limits.max_waves:
                state.status = "budget_exceeded"
                self._save(state)
                raise BudgetExceeded("research exhausted its wave budget")

            ready = self._ready_tasks(state)
            remaining = set(state.tasks) - set(state.completed)
            if not ready and remaining:
                raise ContractViolation("research graph is blocked by unmet dependencies")

            if ready:
                selected = ready[: state.limits.max_workers]
                budget = self._allocate(state, len(selected))
                state.wave += 1
                self.telemetry.record(
                    "behavior",
                    "wave_started",
                    run_id,
                    state.wave,
                    task_ids=[task.id for task in selected],
                    worker_count=len(selected),
                )
                outcomes = await asyncio.gather(
                    *(self._execute_task(state, task, budget) for task in selected),
                    return_exceptions=True,
                )

                failures: list[str] = []
                for task, outcome in zip(selected, outcomes, strict=True):
                    if isinstance(outcome, BaseException):
                        failures.append(task.id)
                        self.telemetry.record(
                            "system",
                            "worker_failed",
                            run_id,
                            state.wave,
                            task_id=task.id,
                            error_type=type(outcome).__name__,
                        )
                        continue
                    state.completed[task.id] = outcome
                    state.usage = state.usage + outcome.usage

                state.failed_task_ids = failures
                if state.usage.tokens > state.limits.max_total_tokens:
                    raise BudgetExceeded("workers exceeded the total token budget")
                if state.usage.tool_calls > state.limits.max_total_tool_calls:
                    raise BudgetExceeded("workers exceeded the total tool-call budget")
                self._save(state)
                if failures:
                    state.status = "failed"
                    self._save(state)
                    raise ResearchExecutionError(
                        f"worker failures checkpointed for retry: {sorted(failures)}"
                    )

            artifacts = tuple(state.completed[key] for key in sorted(state.completed))
            decision = await self.lead.review(query, artifacts, state)
            self.telemetry.record(
                "behavior",
                "review_decision",
                run_id,
                state.wave,
                done=decision.done,
                proposed_tasks=[task.id for task in decision.new_tasks],
                evidence_artifacts=len(artifacts),
            )

            if decision.done:
                break

            added: list[str] = []
            for new_task in decision.new_tasks:
                if new_task.id in state.tasks:
                    continue
                if len(state.tasks) >= state.limits.max_total_tasks:
                    raise BudgetExceeded("dynamic graph expansion exceeded the task budget")
                state.tasks[new_task.id] = new_task
                added.append(new_task.id)

            parallelism_profile(tuple(state.tasks.values()))
            if added:
                self.telemetry.record(
                    "behavior",
                    "tasks_spawned",
                    run_id,
                    state.wave,
                    task_ids=added,
                    total_tasks=len(state.tasks),
                )
                self._save(state)
            elif set(state.tasks) <= set(state.completed):
                raise ContractViolation("lead requested more research without adding new tasks")

        artifacts = tuple(state.completed[key] for key in sorted(state.completed))
        report = await self.lead.synthesize(query, artifacts)
        verify_report(report, list(artifacts))
        state.status = "completed"
        state.failed_task_ids = []
        self._save(state)
        self.telemetry.record(
            "system",
            "run_completed",
            run_id,
            state.wave,
            tasks=len(state.completed),
            tokens=state.usage.tokens,
            tool_calls=state.usage.tool_calls,
            citations=len(report.citations),
        )
        return RunResult(report=report, state=state)
