"""Contract tests for the dynamic orchestrator-worker research architecture."""

import asyncio
import json
from collections import Counter

import pytest

from tests.lesson_loader import load_lesson_module

system = load_lesson_module(
    "dynamic_multi_agent_system",
    "multi_agent/01_dynamic_research/system.py",
)
demo = load_lesson_module(
    "dynamic_multi_agent_demo",
    "multi_agent/01_dynamic_research/demo.py",
)


def task(task_id: str, *, depends_on: tuple[str, ...] = ()):
    return system.ResearchTask(
        id=task_id,
        objective=f"Investigate {task_id}",
        search_queries=(f"{task_id} overview", f"{task_id} evidence"),
        depends_on=depends_on,
    )


def artifact(task_id: str, *, tokens: int = 100, tool_calls: int = 1, raw_chars: int = 2_000):
    source = f"https://sources.example/{task_id}"
    return system.CompressedArtifact(
        task_id=task_id,
        summary=f"Compressed result for {task_id}.",
        findings=(
            system.Finding(
                claim=f"Verified claim for {task_id}",
                evidence="A short evidence excerpt.",
                source_url=source,
                confidence=0.9,
            ),
        ),
        sources=(source,),
        uncertainties=(),
        usage=system.Usage(tokens=tokens, tool_calls=tool_calls, wall_clock_ms=5),
        raw_chars=raw_chars,
    )


class DynamicLead:
    """Start with two branches, then add a third branch from returned evidence."""

    def __init__(self):
        self.review_snapshots = []

    async def plan(self, query, limits):
        return system.ResearchPlan(
            complexity=system.Complexity.COMPARISON,
            rationale="Two independent initial search trajectories.",
            tasks=(task("architecture"), task("economics")),
        )

    async def review(self, query, artifacts, state):
        self.review_snapshots.append(tuple(artifacts))
        completed = {item.task_id for item in artifacts}
        if "reliability" not in completed:
            return system.ReviewDecision(
                done=False,
                rationale="The first wave exposed an operational evidence gap.",
                new_tasks=(task("reliability", depends_on=("architecture",)),),
            )
        return system.ReviewDecision(done=True, rationale="Evidence is sufficient.")

    async def synthesize(self, query, artifacts):
        citations = tuple(source for item in artifacts for source in item.sources)
        answer = "Synthesis: " + " ".join(f"{item.summary} {item.sources[0]}" for item in artifacts)
        return system.ResearchReport(
            answer=answer,
            citations=citations,
            uncertainties=(),
        )


class RecordingWorker:
    def __init__(self, *, fail_once=()):
        self.calls = Counter()
        self.budgets = []
        self.fail_once = set(fail_once)
        self.active = 0
        self.max_active = 0

    async def research(self, assigned_task, budget):
        self.calls[assigned_task.id] += 1
        self.budgets.append(budget)
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        await asyncio.sleep(0.01)
        self.active -= 1

        if assigned_task.id in self.fail_once and self.calls[assigned_task.id] == 1:
            raise RuntimeError(f"temporary failure in {assigned_task.id}")
        return artifact(
            assigned_task.id,
            tokens=min(100, budget.max_tokens),
            tool_calls=min(1, budget.max_tool_calls),
        )


def build_orchestrator(lead=None, worker=None, checkpoint=None, telemetry=None):
    return system.DynamicResearchOrchestrator(
        lead=lead or DynamicLead(),
        worker=worker or RecordingWorker(),
        checkpoint_store=checkpoint or system.InMemoryCheckpointStore(),
        telemetry=telemetry or system.TelemetryRecorder(),
    )


def test_resource_policy_scales_compute_with_complexity():
    simple = system.resource_policy(system.Complexity.SIMPLE)
    comparison = system.resource_policy(system.Complexity.COMPARISON)
    complex_limits = system.resource_policy(system.Complexity.COMPLEX)

    assert simple.max_workers == 1
    assert simple.max_total_tokens < comparison.max_total_tokens < complex_limits.max_total_tokens
    assert simple.max_total_tool_calls < complex_limits.max_total_tool_calls
    assert comparison.max_workers < complex_limits.max_workers


def test_parallelism_profile_distinguishes_independent_work_from_a_serial_chain():
    independent = [task("a"), task("b"), task("c")]
    serial = [task("a"), task("b", depends_on=("a",)), task("c", depends_on=("b",))]

    broad = system.parallelism_profile(independent)
    chain = system.parallelism_profile(serial)

    assert broad.max_width == 3
    assert broad.critical_path_length == 1
    assert broad.multi_agent_recommended is True
    assert chain.max_width == 1
    assert chain.critical_path_length == 3
    assert chain.multi_agent_recommended is False


def test_dynamic_graph_adds_a_second_wave_after_reviewing_evidence():
    lead = DynamicLead()
    worker = RecordingWorker()

    result = asyncio.run(build_orchestrator(lead=lead, worker=worker).run("query", "run-1"))

    assert set(result.state.completed) == {"architecture", "economics", "reliability"}
    assert result.state.wave == 2
    assert worker.calls == Counter({"architecture": 1, "economics": 1, "reliability": 1})
    assert len(lead.review_snapshots) == 2


def test_independent_workers_execute_concurrently():
    worker = RecordingWorker()

    asyncio.run(build_orchestrator(worker=worker).run("query", "run-parallel"))

    assert worker.max_active >= 2


def test_lead_receives_compressed_artifacts_not_worker_raw_context():
    lead = DynamicLead()

    asyncio.run(build_orchestrator(lead=lead).run("query", "run-compression"))

    returned = [item for snapshot in lead.review_snapshots for item in snapshot]
    assert returned
    assert all(isinstance(item, system.CompressedArtifact) for item in returned)
    assert all(item.compression_ratio > 1 for item in returned)
    assert all(not hasattr(item, "raw_observations") for item in returned)


def test_artifact_contract_rejects_output_that_does_not_compress():
    limits = system.resource_policy(system.Complexity.SIMPLE)
    assigned_budget = system.WorkerBudget(max_tokens=500, max_tool_calls=3)
    uncompressed = artifact("a", raw_chars=10)

    with pytest.raises(system.ContractViolation, match="compress"):
        system.verify_artifact(task("a"), uncompressed, assigned_budget, limits)


def test_worker_allocations_and_total_usage_stay_inside_policy():
    worker = RecordingWorker()
    result = asyncio.run(build_orchestrator(worker=worker).run("query", "run-budget"))
    limits = result.state.limits

    assert all(budget.max_tokens <= limits.max_tokens_per_worker for budget in worker.budgets)
    assert all(
        budget.max_tool_calls <= limits.max_tool_calls_per_worker for budget in worker.budgets
    )
    assert result.state.usage.tokens <= limits.max_total_tokens
    assert result.state.usage.tool_calls <= limits.max_total_tool_calls


def test_duplicate_dynamic_tasks_are_not_scheduled_twice():
    class DuplicateLead(DynamicLead):
        async def review(self, query, artifacts, state):
            completed = {item.task_id for item in artifacts}
            if "reliability" not in completed:
                repeated = task("reliability", depends_on=("architecture",))
                return system.ReviewDecision(False, "duplicate proposal", (repeated, repeated))
            return system.ReviewDecision(True, "done")

    worker = RecordingWorker()
    asyncio.run(build_orchestrator(lead=DuplicateLead(), worker=worker).run("query", "run-dedupe"))

    assert worker.calls["reliability"] == 1


def test_checkpoint_resume_keeps_completed_work_and_retries_only_the_failure():
    checkpoint = system.InMemoryCheckpointStore()
    worker = RecordingWorker(fail_once={"economics"})
    orchestrator = build_orchestrator(worker=worker, checkpoint=checkpoint)

    with pytest.raises(system.ResearchExecutionError, match="economics"):
        asyncio.run(orchestrator.run("query", "run-resume"))

    saved = checkpoint.load("run-resume")
    assert set(saved.completed) == {"architecture"}

    result = asyncio.run(orchestrator.run("query", "run-resume"))

    assert result.state.status == "completed"
    assert worker.calls["architecture"] == 1
    assert worker.calls["economics"] == 2


def test_telemetry_contains_system_and_behavior_events_without_raw_query():
    telemetry = system.TelemetryRecorder()
    raw_query = "private research question"

    asyncio.run(build_orchestrator(telemetry=telemetry).run(raw_query, "run-telemetry"))

    categories = {event.category for event in telemetry.events}
    names = {event.name for event in telemetry.events}
    serialized = json.dumps([event.to_dict() for event in telemetry.events])
    assert categories == {"system", "behavior"}
    assert {"plan_created", "wave_started", "review_decision", "run_completed"} <= names
    assert raw_query not in serialized


def test_citation_verification_rejects_sources_outside_worker_artifacts():
    report = system.ResearchReport(
        answer="Unsupported source https://unknown.example",
        citations=("https://unknown.example",),
        uncertainties=(),
    )

    with pytest.raises(system.ContractViolation, match="citation"):
        system.verify_report(report, [artifact("a")])


def test_demo_exercises_dynamic_and_nested_parallelism(tmp_path):
    result, telemetry, search_tool = asyncio.run(demo.run_demo(tmp_path, run_id="demo-test"))

    assert result.state.wave == 2
    assert set(result.state.completed) == {"architecture", "economics", "operations"}
    assert search_tool.max_active_calls >= 4
    assert all(item.compression_ratio > 1 for item in result.state.completed.values())
    assert result.report.citations
    assert any(event.name == "tasks_spawned" for event in telemetry.events)


def test_demo_exports_an_outcome_eval_trial_not_an_exact_path(tmp_path):
    result, _, _ = asyncio.run(demo.run_demo(tmp_path, run_id="demo-eval"))

    trial = demo.result_to_evaluation_trial(result)

    assert trial["case_id"] == "dynamic-multi-agent-research"
    assert "independent" in trial["final_answer"].lower()
    assert trial["sources"] == list(result.report.citations)
    assert trial["turns"] == result.state.wave
    assert set(trial) >= {
        "id",
        "case_id",
        "final_answer",
        "sources",
        "tool_calls",
        "turns",
        "input_tokens",
        "output_tokens",
        "latency_ms",
    }
