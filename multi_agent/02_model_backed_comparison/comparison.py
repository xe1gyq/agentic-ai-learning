"""Controlled Claude experiment: single agent versus dynamic multi-agent research.

The two architectures receive the same model, corpus, global token budget, tool-call
budget, timeout, query, and deterministic outcome check. Live API use is opt-in.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
from typing import Any, Protocol

LESSON_ONE = Path(__file__).resolve().parents[1] / "01_dynamic_research"
if str(LESSON_ONE) not in sys.path:
    sys.path.insert(0, str(LESSON_ONE))

from system import (  # noqa: E402
    BudgetExceeded,
    Complexity,
    CompressedArtifact,
    DynamicResearchOrchestrator,
    Finding,
    InMemoryCheckpointStore,
    ResearchPlan,
    ResearchReport,
    ResearchTask,
    ReviewDecision,
    TelemetryRecorder,
    Usage,
    WorkerBudget,
)


@dataclass(frozen=True)
class ExperimentLimits:
    """Identical global resource envelope assigned to each architecture."""

    max_tokens: int
    max_tool_calls: int
    timeout_seconds: float


@dataclass(frozen=True)
class MeasuredUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    tool_calls: int = 0
    wall_clock_ms: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass(frozen=True)
class _Reservation:
    reservation_id: int
    tokens: int


class BudgetLedger:
    """Concurrency-safe reservations prevent parallel workers overspending a budget."""

    def __init__(self, limits: ExperimentLimits):
        self.limits = limits
        self._input_tokens = 0
        self._output_tokens = 0
        self._tool_calls = 0
        self._reserved_tokens = 0
        self._next_reservation_id = 0
        self._reservations: dict[int, int] = {}
        self._lock = asyncio.Lock()
        self._started = time.perf_counter()

    async def reserve_model_call(
        self, input_tokens: int, requested_output_tokens: int
    ) -> _Reservation:
        requested = input_tokens + requested_output_tokens
        async with self._lock:
            committed = self._input_tokens + self._output_tokens
            if committed + self._reserved_tokens + requested > self.limits.max_tokens:
                raise BudgetExceeded("token budget cannot fund the next model call")
            self._next_reservation_id += 1
            reservation = _Reservation(self._next_reservation_id, requested)
            self._reservations[reservation.reservation_id] = requested
            self._reserved_tokens += requested
            return reservation

    async def settle_model_call(
        self,
        reservation: _Reservation,
        actual_input_tokens: int,
        actual_output_tokens: int,
    ) -> None:
        actual = actual_input_tokens + actual_output_tokens
        async with self._lock:
            reserved = self._reservations.pop(reservation.reservation_id)
            self._reserved_tokens -= reserved
            if actual > reserved:
                raise BudgetExceeded("model response exceeded its token reservation")
            self._input_tokens += actual_input_tokens
            self._output_tokens += actual_output_tokens

    async def cancel_model_call(self, reservation: _Reservation) -> None:
        async with self._lock:
            reserved = self._reservations.pop(reservation.reservation_id, 0)
            self._reserved_tokens -= reserved

    async def consume_tool_call(self) -> None:
        async with self._lock:
            if self._tool_calls + 1 > self.limits.max_tool_calls:
                raise BudgetExceeded("tool-call budget is exhausted")
            self._tool_calls += 1

    def snapshot(self) -> MeasuredUsage:
        return MeasuredUsage(
            input_tokens=self._input_tokens,
            output_tokens=self._output_tokens,
            tool_calls=self._tool_calls,
            wall_clock_ms=int((time.perf_counter() - self._started) * 1_000),
        )


class Corpus(Protocol):
    async def search(self, query: str) -> list[dict[str, str]]: ...


class LearningCorpus:
    """A fixed local corpus removes internet drift from architecture comparisons."""

    DOCUMENTS = (
        {
            "title": "Independent search trajectories",
            "url": "https://www.anthropic.com/engineering/multi-agent-research-system",
            "content": (
                "Multi-agent research is useful when work decomposes into independent search "
                "trajectories. Subagents compress findings before synthesis. It consumes more "
                "tokens, so breadth must justify the cost."
            ),
        },
        {
            "title": "Serial critical paths",
            "url": "https://learning.local/serial-critical-paths",
            "content": (
                "Strong dependencies form a serial critical path. More agents do not shorten "
                "work when every step needs the complete output of the previous step."
            ),
        },
        {
            "title": "Agent operations",
            "url": "https://learning.local/agent-operations",
            "content": (
                "Reliable agent systems need explicit budgets, checkpoints, citations, retries, "
                "outcome evaluations, and behavior plus system telemetry."
            ),
        },
    )

    async def search(self, query: str) -> list[dict[str, str]]:
        terms = {word.strip(".,?!").lower() for word in query.split() if len(word) > 3}
        ranked = sorted(
            self.DOCUMENTS,
            key=lambda item: sum(term in item["content"].lower() for term in terms),
            reverse=True,
        )
        return [dict(item) for item in ranked[:2]]


@dataclass(frozen=True)
class ToolLoopResult:
    text: str
    usage: MeasuredUsage
    raw_tool_chars: int


SEARCH_TOOL = {
    "name": "search_corpus",
    "description": (
        "Search the fixed learning corpus for evidence. Use it before making factual claims."
    ),
    "input_schema": {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
        "additionalProperties": False,
    },
}


def _block_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump(exclude_none=True)
    return {"type": value.type, **{key: item for key, item in vars(value).items() if key != "type"}}


def _text(response: Any) -> str:
    return "".join(block.text for block in response.content if block.type == "text")


class ClaudeGateway:
    """Small Messages API boundary with accounting and client-side tool execution."""

    def __init__(self, client: Any, model: str, ledger: BudgetLedger, corpus: Corpus):
        self.client = client
        self.model = model
        self.ledger = ledger
        self.corpus = corpus

    async def _create(self, *, max_output_tokens: int, **request: Any) -> Any:
        count = await self.client.messages.count_tokens(model=self.model, **request)
        reservation = await self.ledger.reserve_model_call(count.input_tokens, max_output_tokens)
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=max_output_tokens,
                **request,
            )
        except BaseException:
            await self.ledger.cancel_model_call(reservation)
            raise
        await self.ledger.settle_model_call(
            reservation,
            response.usage.input_tokens,
            response.usage.output_tokens,
        )
        return response

    async def complete_json(
        self,
        system: str,
        prompt: str,
        schema: dict[str, Any],
        max_output_tokens: int,
    ) -> dict[str, Any]:
        response = await self._create(
            system=system,
            messages=[{"role": "user", "content": prompt}],
            output_config={"format": {"type": "json_schema", "schema": schema}},
            max_output_tokens=max_output_tokens,
        )
        return json.loads(_text(response))

    async def run_tool_loop(
        self, system: str, prompt: str, max_output_tokens: int
    ) -> ToolLoopResult:
        started = time.perf_counter()
        input_tokens = 0
        output_tokens = 0
        tool_calls = 0
        raw_tool_chars = 0
        messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]
        while True:
            response = await self._create(
                system=system,
                messages=messages,
                tools=[SEARCH_TOOL],
                max_output_tokens=max_output_tokens,
            )
            input_tokens += response.usage.input_tokens
            output_tokens += response.usage.output_tokens
            tool_uses = [block for block in response.content if block.type == "tool_use"]
            if not tool_uses:
                return ToolLoopResult(
                    text=_text(response),
                    usage=MeasuredUsage(
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        tool_calls=tool_calls,
                        wall_clock_ms=int((time.perf_counter() - started) * 1_000),
                    ),
                    raw_tool_chars=raw_tool_chars,
                )
            messages.append(
                {"role": "assistant", "content": [_block_dict(block) for block in response.content]}
            )
            results = []
            for tool_use in tool_uses:
                if tool_use.name != "search_corpus":
                    raise ValueError(f"unknown tool: {tool_use.name}")
                await self.ledger.consume_tool_call()
                documents = await self.corpus.search(str(tool_use.input["query"]))
                serialized = json.dumps(documents)
                tool_calls += 1
                raw_tool_chars += len(serialized)
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": serialized,
                    }
                )
            messages.append({"role": "user", "content": results})


TASK_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "objective": {"type": "string"},
        "queries": {"type": "array", "items": {"type": "string"}},
        "depends_on": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["id", "objective", "queries", "depends_on"],
    "additionalProperties": False,
}

PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "complexity": {"type": "string", "enum": [item.value for item in Complexity]},
        "rationale": {"type": "string"},
        "tasks": {"type": "array", "items": TASK_SCHEMA},
    },
    "required": ["complexity", "rationale", "tasks"],
    "additionalProperties": False,
}

REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "done": {"type": "boolean"},
        "rationale": {"type": "string"},
        "new_tasks": {"type": "array", "items": TASK_SCHEMA},
    },
    "required": ["done", "rationale", "new_tasks"],
    "additionalProperties": False,
}

REPORT_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "citations": {"type": "array", "items": {"type": "string"}},
        "uncertainties": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["answer", "citations", "uncertainties"],
    "additionalProperties": False,
}


def _task(value: dict[str, Any]) -> ResearchTask:
    return ResearchTask(
        id=str(value["id"]),
        objective=str(value["objective"]),
        search_queries=tuple(value["queries"]),
        depends_on=tuple(value.get("depends_on", [])),
    )


def _artifacts_json(artifacts: tuple[CompressedArtifact, ...]) -> str:
    return json.dumps([asdict(artifact) for artifact in artifacts], ensure_ascii=False)


class ClaudeLeadResearcher:
    """Claude-backed executive: decompose, expand or stop, then synthesize."""

    def __init__(self, gateway: ClaudeGateway):
        self.gateway = gateway

    async def plan(self, query: str, limits: Any) -> ResearchPlan:
        value = await self.gateway.complete_json(
            "You plan bounded research. Create independent tasks when evidence can be searched independently.",
            f"Query: {query}\nCreate at most 3 initial tasks with short stable IDs.",
            PLAN_SCHEMA,
            700,
        )
        return ResearchPlan(
            complexity=Complexity(value["complexity"]),
            rationale=value["rationale"],
            tasks=tuple(_task(item) for item in value["tasks"]),
        )

    async def review(self, query, artifacts, state) -> ReviewDecision:
        value = await self.gateway.complete_json(
            "You decide whether verified evidence is sufficient. Add only evidence-dependent gaps.",
            (
                f"Query: {query}\nCompleted IDs: {sorted(state.completed)}\n"
                f"Artifacts: {_artifacts_json(artifacts)}\n"
                "Stop when the answer can compare benefits, limits, and operations. Add at most 2 tasks."
            ),
            REVIEW_SCHEMA,
            600,
        )
        return ReviewDecision(
            done=bool(value["done"]),
            rationale=value["rationale"],
            new_tasks=tuple(_task(item) for item in value["new_tasks"]),
        )

    async def synthesize(self, query, artifacts) -> ResearchReport:
        value = await self.gateway.complete_json(
            "Synthesize only supplied evidence. Put every cited URL verbatim in the answer.",
            f"Query: {query}\nArtifacts: {_artifacts_json(artifacts)}",
            REPORT_SCHEMA,
            900,
        )
        return ResearchReport(
            answer=value["answer"],
            citations=tuple(value["citations"]),
            uncertainties=tuple(value["uncertainties"]),
        )


class ClaudeResearchWorker:
    """Claude-backed bounded explorer that returns a compressed evidence artifact."""

    def __init__(self, gateway: ClaudeGateway):
        self.gateway = gateway

    async def research(self, task: ResearchTask, budget: WorkerBudget) -> CompressedArtifact:
        result = await self.gateway.run_tool_loop(
            (
                "You are a bounded research worker. Search the corpus, then return JSON with keys "
                "summary, findings, sources, uncertainties, and raw_chars. Each finding needs "
                "claim, evidence, source_url, confidence. Compress aggressively and cite only tool results."
            ),
            (
                f"Objective: {task.objective}\nSuggested queries: {list(task.search_queries)}\n"
                f"Use at most {budget.max_tool_calls} searches. Return only JSON."
            ),
            min(900, budget.max_tokens),
        )
        value = json.loads(result.text)
        findings = tuple(Finding(**item) for item in value["findings"])
        artifact_chars = len(result.text)
        return CompressedArtifact(
            task_id=task.id,
            summary=value["summary"],
            findings=findings,
            sources=tuple(value["sources"]),
            uncertainties=tuple(value["uncertainties"]),
            usage=Usage(
                tokens=result.usage.total_tokens,
                tool_calls=result.usage.tool_calls,
                wall_clock_ms=result.usage.wall_clock_ms,
            ),
            raw_chars=max(result.raw_tool_chars, artifact_chars + 1),
        )


@dataclass(frozen=True)
class TrialResult:
    architecture: str
    run_id: str
    answer: str
    citations: tuple[str, ...]
    usage: MeasuredUsage
    passed: bool
    failure: str | None


@dataclass(frozen=True)
class BenchmarkConfig:
    query: str
    model: str
    trials: int
    limits: ExperimentLimits


def evaluate_outcome(answer: str, citations: tuple[str, ...], corpus: Corpus) -> bool:
    documents = getattr(corpus, "DOCUMENTS", LearningCorpus.DOCUMENTS)
    available = {item["url"] for item in documents}
    grounded = bool(citations) and set(citations) <= available
    coverage = "independent" in answer.lower() and any(
        word in answer.lower() for word in ("cost", "token", "serial")
    )
    return grounded and coverage and all(source in answer for source in citations)


def _summaries(trials: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    summaries = {}
    for architecture in ("single_agent", "multi_agent"):
        group = [item for item in trials if item["architecture"] == architecture]
        summaries[architecture] = {
            "pass_rate": mean(float(item["passed"]) for item in group),
            "mean_total_tokens": mean(
                item["usage"]["input_tokens"] + item["usage"]["output_tokens"] for item in group
            ),
            "mean_tool_calls": mean(item["usage"]["tool_calls"] for item in group),
            "mean_latency_ms": mean(item["usage"]["wall_clock_ms"] for item in group),
        }
    return summaries


async def _run_architecture(
    architecture: str,
    query: str,
    model: str,
    limits: ExperimentLimits,
    corpus: Corpus,
    run_id: str,
) -> TrialResult:
    from anthropic import AsyncAnthropic

    ledger = BudgetLedger(limits)
    gateway = ClaudeGateway(AsyncAnthropic(), model, ledger, corpus)
    answer = ""
    citations: tuple[str, ...] = ()
    failure = None
    try:
        async with asyncio.timeout(limits.timeout_seconds):
            if architecture == "single_agent":
                result = await gateway.run_tool_loop(
                    (
                        "You are a research agent. Use the corpus and return JSON with answer, "
                        "citations, uncertainties. Put every cited URL verbatim in the answer."
                    ),
                    query,
                    min(1_500, limits.max_tokens),
                )
                value = json.loads(result.text)
                answer = value["answer"]
                citations = tuple(value["citations"])
            else:
                orchestrator = DynamicResearchOrchestrator(
                    lead=ClaudeLeadResearcher(gateway),
                    worker=ClaudeResearchWorker(gateway),
                    checkpoint_store=InMemoryCheckpointStore(),
                    telemetry=TelemetryRecorder(),
                )
                result = await orchestrator.run(query, run_id)
                answer = result.report.answer
                citations = result.report.citations
    except (BudgetExceeded, TimeoutError, ValueError, KeyError, json.JSONDecodeError) as error:
        failure = f"{type(error).__name__}: {error}"
    usage = ledger.snapshot()
    return TrialResult(
        architecture=architecture,
        run_id=run_id,
        answer=answer,
        citations=citations,
        usage=usage,
        passed=failure is None and evaluate_outcome(answer, citations, corpus),
        failure=failure,
    )


Runner = Callable[[str, str, str, ExperimentLimits, Corpus, str], Awaitable[TrialResult]]


async def run_benchmark(
    config: BenchmarkConfig,
    corpus: Corpus,
    runner: Runner = _run_architecture,
) -> dict[str, Any]:
    """Run paired trials sequentially to avoid cross-architecture rate interference."""
    trials = []
    for trial_number in range(1, config.trials + 1):
        for architecture in ("single_agent", "multi_agent"):
            run_id = f"trial-{trial_number}-{architecture}-{uuid.uuid4().hex[:8]}"
            result = await runner(
                architecture,
                config.query,
                config.model,
                config.limits,
                corpus,
                run_id,
            )
            trials.append(asdict(result))
    return {
        "query": config.query,
        "model": config.model,
        "limits": asdict(config.limits),
        "comparison_policy": {
            "same_model": True,
            "same_corpus": True,
            "same_global_limits": True,
            "paired_sequential_trials": True,
            "evaluation": "deterministic outcome, citation grounding, cost, and latency",
        },
        "trials": trials,
        "summary": _summaries(trials),
    }


def write_report(report: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="allow billable Claude API calls")
    parser.add_argument("--trials", type=int, default=1)
    parser.add_argument("--model", default="claude-sonnet-4-6")
    parser.add_argument("--max-tokens", type=int, default=10_000)
    parser.add_argument("--max-tool-calls", type=int, default=20)
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--output", type=Path, default=Path("benchmark-report.json"))
    parser.add_argument(
        "query",
        nargs="?",
        default="When does multi-agent research help, and when is it a poor fit?",
    )
    args = parser.parse_args(argv)
    if not args.live:
        parser.print_usage()
        print("error: pass --live to authorize billable API calls", file=sys.stderr)
        return 2
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("error: ANTHROPIC_API_KEY is required", file=sys.stderr)
        return 2

    config = BenchmarkConfig(
        query=args.query,
        model=args.model,
        trials=args.trials,
        limits=ExperimentLimits(args.max_tokens, args.max_tool_calls, args.timeout),
    )
    report = asyncio.run(run_benchmark(config, LearningCorpus()))
    write_report(report, args.output)
    print(f"Wrote {len(report['trials'])} trials to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
