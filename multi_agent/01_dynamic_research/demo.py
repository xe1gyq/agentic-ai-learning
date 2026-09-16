"""Deterministic dynamic-research demo with nested parallel search calls.

The demo uses a small local corpus instead of live APIs. Its purpose is to expose
the architecture and engineering controls without spending tokens or depending on
network state. Replace DemoLead and DemoWorker with model-backed adapters later.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import dataclass
from pathlib import Path

try:
    from system import (
        Complexity,
        CompressedArtifact,
        DynamicResearchOrchestrator,
        Finding,
        JsonCheckpointStore,
        ResearchPlan,
        ResearchReport,
        ResearchState,
        ResearchTask,
        ReviewDecision,
        RunLimits,
        RunResult,
        TelemetryRecorder,
        Usage,
        WorkerBudget,
    )
except ModuleNotFoundError:  # Loaded by the repository's path-based test helper.
    from dynamic_multi_agent_system import (  # type: ignore[no-redef]
        Complexity,
        CompressedArtifact,
        DynamicResearchOrchestrator,
        Finding,
        JsonCheckpointStore,
        ResearchPlan,
        ResearchReport,
        ResearchState,
        ResearchTask,
        ReviewDecision,
        RunLimits,
        RunResult,
        TelemetryRecorder,
        Usage,
        WorkerBudget,
    )


ANTHROPIC_ARTICLE = "https://www.anthropic.com/engineering/multi-agent-research-system"
CONTEXT_ARTICLE = (
    "https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents"
)
EVAL_ARTICLE = "https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents"


@dataclass(frozen=True)
class SourceDocument:
    """One local stand-in for a document returned by a search tool."""

    title: str
    url: str
    text: str


CORPUS = (
    SourceDocument(
        title="How Anthropic built a multi-agent research system",
        url=ANTHROPIC_ARTICLE,
        text=(
            "Research is open-ended, dynamic, and path-dependent. The lead researcher plans, "
            "delegates independent directions to parallel subagents, inspects compressed "
            "findings, and can create more subagents when evidence reveals a gap. Search is "
            "compression: workers consume large local contexts but return only important "
            "findings, sources, evidence, and uncertainty. Multi-agent systems work best for "
            "breadth-first queries with independent trajectories. Token usage explained about "
            "80 percent of BrowseComp performance variance; tokens, tool calls, and model choice "
            "together explained about 95 percent. Agents used about four times chat tokens and "
            "multi-agent systems about fifteen times. Lead agents and worker tools can both run "
            "in parallel. Anthropic reported reductions of up to 90 percent in research time for "
            "complex workloads. Stateful runs require checkpointing, resume, tracing, and "
            "behavioral observability for routing, delegation, tool selection, and stopping."
        ),
    ),
    SourceDocument(
        title="Effective context engineering for AI agents",
        url=CONTEXT_ARTICLE,
        text=(
            "Subagent architectures give focused workers clean context windows. A subagent can "
            "consume tens of thousands of tokens locally and return a distilled summary of only "
            "one or two thousand tokens. This separates detailed search context from global "
            "synthesis. Durable notes and external memory preserve plans without treating the "
            "context window as a database. The right strategy depends on whether parallel "
            "exploration or continuous shared context dominates the task."
        ),
    ),
    SourceDocument(
        title="Demystifying evals for AI agents",
        url=EVAL_ARTICLE,
        text=(
            "Agent evaluations should distinguish tasks, repeated trials, graders, transcripts, "
            "and outcomes. Research evaluations can combine groundedness, coverage, source "
            "quality, exact outcome checks, model graders, and calibrated human review. Dynamic "
            "agents may follow different valid trajectories, so outcome constraints matter more "
            "than requiring one exact sequence of tool calls."
        ),
    ),
)


class DemoSearchTool:
    """Search a local corpus while measuring concurrent tool activity."""

    def __init__(self, corpus: tuple[SourceDocument, ...] = CORPUS):
        self.corpus = corpus
        self.active_calls = 0
        self.max_active_calls = 0
        self.total_calls = 0

    async def search(self, query: str) -> tuple[SourceDocument, ...]:
        self.active_calls += 1
        self.total_calls += 1
        self.max_active_calls = max(self.max_active_calls, self.active_calls)
        try:
            await asyncio.sleep(0.01)
            terms = {word.strip(".,:;!?()[]").casefold() for word in query.split()}
            scored = []
            for document in self.corpus:
                haystack = f"{document.title} {document.text}".casefold()
                score = sum(term in haystack for term in terms if len(term) > 3)
                scored.append((score, document.title, document))
            scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
            return tuple(document for score, _, document in scored if score > 0)[:2]
        finally:
            self.active_calls -= 1


FINDING_TEMPLATES = {
    "architecture": (
        "Multi-agent research pays off when work decomposes into independent search trajectories.",
        "The lead owns global decomposition and stopping; workers own bounded local exploration.",
        "Search compresses large local contexts into small evidence-bearing artifacts.",
    ),
    "economics": (
        "Multi-agent is parallel allocation of tokens, tool calls, context windows, and time.",
        "The architecture costs substantially more tokens, so task value must justify it.",
        "Serial dependency chains expose little useful parallelism even with many agents.",
    ),
    "operations": (
        "Long-running stateful agents need checkpoints, retry, resume, and failure isolation.",
        "Observability must include delegation, routing, tool choice, stopping, cost, and latency.",
        "Outcome-based evals should allow multiple valid trajectories while enforcing quality.",
    ),
}


class DemoWorker:
    """Run parallel local searches, filter them, and return only compressed evidence."""

    def __init__(self, search_tool: DemoSearchTool):
        self.search_tool = search_tool

    async def research(
        self,
        task: ResearchTask,
        budget: WorkerBudget,
    ) -> CompressedArtifact:
        queries = task.search_queries[: budget.max_tool_calls]
        result_sets = await asyncio.gather(*(self.search_tool.search(query) for query in queries))
        documents_by_url = {
            document.url: document for results in result_sets for document in results
        }
        documents = tuple(documents_by_url.values())
        raw_chars = sum(len(document.text) for document in documents)

        claims = FINDING_TEMPLATES[task.id]
        preferred_source = EVAL_ARTICLE if task.id == "operations" else ANTHROPIC_ARTICLE
        if preferred_source not in documents_by_url:
            preferred_source = documents[0].url
        evidence = documents_by_url[preferred_source].text[:180]
        findings = tuple(
            Finding(
                claim=claim,
                evidence=evidence,
                source_url=preferred_source,
                confidence=0.9,
            )
            for claim in claims
        )
        sources = tuple(sorted({finding.source_url for finding in findings}))
        summary = " ".join(claims)
        estimated_tokens = min(
            budget.max_tokens,
            max(1, (raw_chars + len(summary)) // 4),
        )
        return CompressedArtifact(
            task_id=task.id,
            summary=summary,
            findings=findings,
            sources=sources,
            uncertainties=(
                "Reported percentages are workload-specific, not universal scaling laws.",
            ),
            usage=Usage(
                tokens=estimated_tokens,
                tool_calls=len(queries),
                wall_clock_ms=10,
            ),
            raw_chars=raw_chars,
        )


class DemoLead:
    """Deterministic executive that expands the graph after its first evidence wave."""

    async def plan(self, query: str, limits: RunLimits) -> ResearchPlan:
        return ResearchPlan(
            complexity=Complexity.COMPARISON,
            rationale="Architecture and economics are independent initial trajectories.",
            tasks=(
                ResearchTask(
                    id="architecture",
                    objective="Identify when decomposition creates real parallel value.",
                    search_queries=(
                        "multi-agent research architecture independent trajectories",
                        "search compression subagent context",
                    ),
                ),
                ResearchTask(
                    id="economics",
                    objective="Analyze test-time compute, budget, and serial anti-patterns.",
                    search_queries=(
                        "multi-agent token usage test-time compute",
                        "multi-agent serial dependencies parallelism cost",
                    ),
                ),
            ),
        )

    async def review(
        self,
        query: str,
        artifacts: tuple[CompressedArtifact, ...],
        state: ResearchState,
    ) -> ReviewDecision:
        completed = {artifact.task_id for artifact in artifacts}
        if "operations" not in completed:
            return ReviewDecision(
                done=False,
                rationale="The first wave explains value but not production reliability.",
                new_tasks=(
                    ResearchTask(
                        id="operations",
                        objective="Research checkpoints, observability, and outcome evals.",
                        search_queries=(
                            "agent checkpoint resume stateful reliability",
                            "agent behavior telemetry outcome evaluation",
                        ),
                        depends_on=("architecture", "economics"),
                    ),
                ),
            )
        return ReviewDecision(done=True, rationale="Value and operational evidence are covered.")

    async def synthesize(
        self,
        query: str,
        artifacts: tuple[CompressedArtifact, ...],
    ) -> ResearchReport:
        by_id = {artifact.task_id: artifact for artifact in artifacts}
        citations = tuple(sorted({source for artifact in artifacts for source in artifact.sources}))
        citation_text = " ".join(citations)
        answer = (
            "Use multiple agents when a hard problem can be split into independent exploratory "
            "trajectories. Workers should search with isolated local context, compress evidence, "
            "and return sources and uncertainty to a lead that owns strategy, resource policy, "
            "dynamic graph expansion, verification, and stopping. The benefit is more productive "
            "test-time compute and breadth, not automatically better truth or coordination. "
            f"Architecture evidence: {by_id['architecture'].summary} "
            f"Economics evidence: {by_id['economics'].summary} "
            f"Operations evidence: {by_id['operations'].summary} "
            f"Sources: {citation_text}"
        )
        uncertainties = tuple(
            uncertainty for artifact in artifacts for uncertainty in artifact.uncertainties
        )
        return ResearchReport(
            answer=answer,
            citations=citations,
            uncertainties=tuple(dict.fromkeys(uncertainties)),
        )


async def run_demo(
    state_directory: Path,
    run_id: str = "dynamic-research-demo",
) -> tuple[RunResult, TelemetryRecorder, DemoSearchTool]:
    """Execute the complete dynamic graph with durable state and telemetry."""
    search_tool = DemoSearchTool()
    telemetry = TelemetryRecorder(state_directory / f"{run_id}.telemetry.jsonl")
    orchestrator = DynamicResearchOrchestrator(
        lead=DemoLead(),
        worker=DemoWorker(search_tool),
        checkpoint_store=JsonCheckpointStore(state_directory / "checkpoints"),
        telemetry=telemetry,
    )
    query = "When does multi-agent research have a real architectural advantage?"
    result = await orchestrator.run(query, run_id)
    return result, telemetry, search_tool


def result_to_evaluation_trial(result: RunResult) -> dict[str, object]:
    """Export outcome and resource evidence without prescribing an exact trajectory."""
    usage = result.state.usage
    input_tokens = int(usage.tokens * 0.8)
    output_tokens = usage.tokens - input_tokens
    tool_calls = [
        {
            "name": "research_worker",
            "arguments": {"task_id": task_id},
        }
        for task_id in result.state.completed
    ]
    return {
        "id": result.state.run_id,
        "case_id": "dynamic-multi-agent-research",
        "final_answer": result.report.answer,
        "sources": list(result.report.citations),
        "tool_calls": tool_calls,
        "turns": result.state.wave,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "latency_ms": usage.wall_clock_ms,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the dynamic multi-agent research demo")
    parser.add_argument(
        "--state-dir",
        type=Path,
        default=Path(__file__).resolve().parent / ".demo_state",
        help="Directory for checkpoints and JSONL telemetry",
    )
    parser.add_argument("--run-id", default="dynamic-research-demo")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result, telemetry, search_tool = asyncio.run(run_demo(args.state_dir, args.run_id))
    print(result.report.answer)
    print("\nExecution summary:")
    print(f"  waves: {result.state.wave}")
    print(f"  tasks: {len(result.state.completed)}")
    print(f"  tokens (estimated): {result.state.usage.tokens}")
    print(f"  tool calls: {result.state.usage.tool_calls}")
    print(f"  maximum concurrent searches: {search_tool.max_active_calls}")
    print(f"  telemetry events: {len(telemetry.events)}")
    print("  compression ratios:")
    for task_id, artifact in result.state.completed.items():
        print(f"    {task_id}: {artifact.compression_ratio:.2f}x")
    print("\nEvaluation trial:")
    print(json.dumps(result_to_evaluation_trial(result), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
