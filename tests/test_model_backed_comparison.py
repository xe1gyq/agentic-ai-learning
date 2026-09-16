"""Contract tests for the model-backed single-vs-multi-agent experiment."""

import asyncio
import json
from types import SimpleNamespace

import pytest

from tests.lesson_loader import load_lesson_module

comparison = load_lesson_module(
    "model_backed_comparison",
    "multi_agent/02_model_backed_comparison/comparison.py",
)


def block(block_type, **values):
    return SimpleNamespace(type=block_type, **values)


def response(*content, stop_reason="end_turn", input_tokens=20, output_tokens=10):
    return SimpleNamespace(
        content=list(content),
        stop_reason=stop_reason,
        usage=SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens),
    )


class FakeMessages:
    def __init__(self, responses, input_tokens=20):
        self.responses = list(responses)
        self.input_tokens = input_tokens
        self.create_calls = []

    async def count_tokens(self, **request):
        return SimpleNamespace(input_tokens=self.input_tokens)

    async def create(self, **request):
        self.create_calls.append(request)
        return self.responses.pop(0)


class FakeClient:
    def __init__(self, responses, input_tokens=20):
        self.messages = FakeMessages(responses, input_tokens)


class LocalCorpus:
    def __init__(self):
        self.calls = []

    async def search(self, query):
        self.calls.append(query)
        return [
            {
                "title": "Independent trajectories",
                "url": "https://example.test/independence",
                "content": "Independent searches can run concurrently and later be synthesized.",
            }
        ]


def test_budget_ledger_prevents_parallel_overallocation():
    async def reserve_twice():
        ledger = comparison.BudgetLedger(
            comparison.ExperimentLimits(max_tokens=100, max_tool_calls=2, timeout_seconds=5)
        )
        first = await ledger.reserve_model_call(input_tokens=30, requested_output_tokens=40)
        with pytest.raises(comparison.BudgetExceeded, match="token"):
            await ledger.reserve_model_call(input_tokens=40, requested_output_tokens=40)
        await ledger.settle_model_call(first, actual_input_tokens=30, actual_output_tokens=10)
        second = await ledger.reserve_model_call(input_tokens=40, requested_output_tokens=20)
        await ledger.settle_model_call(second, actual_input_tokens=40, actual_output_tokens=10)
        return ledger.snapshot()

    usage = asyncio.run(reserve_twice())

    assert usage.input_tokens == 70
    assert usage.output_tokens == 20
    assert usage.total_tokens == 90


def test_tool_loop_accounts_for_model_and_tool_usage():
    client = FakeClient(
        [
            response(
                block("tool_use", id="tool-1", name="search_corpus", input={"query": "loops"}),
                stop_reason="tool_use",
            ),
            response(block("text", text="Grounded answer https://example.test/independence")),
        ]
    )
    corpus = LocalCorpus()
    ledger = comparison.BudgetLedger(
        comparison.ExperimentLimits(max_tokens=500, max_tool_calls=3, timeout_seconds=5)
    )
    gateway = comparison.ClaudeGateway(client, "claude-test", ledger, corpus)

    result = asyncio.run(gateway.run_tool_loop("system", "research loops", max_output_tokens=80))

    assert "Grounded answer" in result.text
    assert corpus.calls == ["loops"]
    assert ledger.snapshot().tool_calls == 1
    assert ledger.snapshot().total_tokens == 60
    assert client.messages.create_calls[1]["messages"][-1]["content"][0]["type"] == "tool_result"


def test_tool_loop_stops_before_exceeding_tool_budget():
    client = FakeClient(
        [
            response(
                block("tool_use", id="one", name="search_corpus", input={"query": "a"}),
                stop_reason="tool_use",
            ),
            response(
                block("tool_use", id="two", name="search_corpus", input={"query": "b"}),
                stop_reason="tool_use",
            ),
        ]
    )
    ledger = comparison.BudgetLedger(
        comparison.ExperimentLimits(max_tokens=500, max_tool_calls=1, timeout_seconds=5)
    )
    gateway = comparison.ClaudeGateway(client, "claude-test", ledger, LocalCorpus())

    with pytest.raises(comparison.BudgetExceeded, match="tool"):
        asyncio.run(gateway.run_tool_loop("system", "query", max_output_tokens=80))


def test_failed_api_call_releases_its_token_reservation():
    class FailingMessages(FakeMessages):
        async def create(self, **request):
            raise RuntimeError("temporary API failure")

    client = FakeClient([])
    client.messages = FailingMessages([])
    ledger = comparison.BudgetLedger(
        comparison.ExperimentLimits(max_tokens=100, max_tool_calls=1, timeout_seconds=5)
    )
    gateway = comparison.ClaudeGateway(client, "claude-test", ledger, LocalCorpus())

    with pytest.raises(RuntimeError, match="temporary"):
        asyncio.run(gateway.run_tool_loop("system", "query", max_output_tokens=80))

    reservation = asyncio.run(ledger.reserve_model_call(20, 80))
    asyncio.run(ledger.cancel_model_call(reservation))


def test_fixed_corpus_and_outcome_evaluator_check_grounded_coverage():
    corpus = comparison.LearningCorpus()
    results = asyncio.run(corpus.search("independent token trajectories"))
    citation = results[0]["url"]
    answer = f"Independent trajectories improve breadth but have a token cost. {citation}"

    assert results[0]["title"] == "Independent search trajectories"
    assert comparison.evaluate_outcome(answer, (citation,), corpus) is True
    assert comparison.evaluate_outcome(answer, ("https://invented.test",), corpus) is False


def test_multi_agent_adapters_translate_structured_claude_outputs():
    plan = {
        "complexity": "comparison",
        "rationale": "Two independent trajectories.",
        "tasks": [
            {
                "id": "architecture",
                "objective": "Find architecture evidence",
                "queries": ["a"],
                "depends_on": [],
            },
            {
                "id": "economics",
                "objective": "Find cost evidence",
                "queries": ["b"],
                "depends_on": [],
            },
        ],
    }
    gateway = SimpleNamespace(json_calls=[])

    async def complete_json(system, prompt, schema, max_output_tokens):
        gateway.json_calls.append((system, prompt, schema, max_output_tokens))
        return plan

    gateway.complete_json = complete_json
    lead = comparison.ClaudeLeadResearcher(gateway)

    result = asyncio.run(lead.plan("When should multi-agent research be used?", SimpleNamespace()))

    assert result.complexity.value == "comparison"
    assert {item.id for item in result.tasks} == {"architecture", "economics"}
    assert result.tasks[0].search_queries == ("a",)


def test_benchmark_gives_both_architectures_identical_limits_and_model(tmp_path):
    seen = []

    async def runner(architecture, query, model, limits, corpus, run_id):
        seen.append((architecture, model, limits, corpus))
        return comparison.TrialResult(
            architecture=architecture,
            run_id=run_id,
            answer="Independent trajectories work. https://example.test/independence",
            citations=("https://example.test/independence",),
            usage=comparison.MeasuredUsage(100, 50, 2, 25),
            passed=True,
            failure=None,
        )

    limits = comparison.ExperimentLimits(2_000, 8, 30)
    config = comparison.BenchmarkConfig(
        query="When should multi-agent research be used?",
        model="claude-test",
        trials=2,
        limits=limits,
    )

    report = asyncio.run(comparison.run_benchmark(config, LocalCorpus(), runner=runner))
    output = tmp_path / "report.json"
    comparison.write_report(report, output)

    assert len(seen) == 4
    assert {item[0] for item in seen} == {"single_agent", "multi_agent"}
    assert {item[1] for item in seen} == {"claude-test"}
    assert all(item[2] is limits for item in seen)
    assert len({id(item[3]) for item in seen}) == 1
    assert report["comparison_policy"]["same_global_limits"] is True
    assert len(json.loads(output.read_text())["trials"]) == 4


def test_cli_requires_explicit_live_flag_before_api_calls(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    assert comparison.main([]) == 2
