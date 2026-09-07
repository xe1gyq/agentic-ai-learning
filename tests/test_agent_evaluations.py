"""Behavioral tests that define the Lesson 09 evaluation harness contract."""

from pathlib import Path

import pytest

from tests.lesson_loader import REPO_ROOT, load_lesson_module

lesson = load_lesson_module(
    "agent_evaluations_lesson",
    "fundamentals/09_agent_evaluations/evaluation.py",
)


def make_case(**overrides):
    values = {
        "id": "research-basics",
        "prompt": "Explain an agent loop using an authoritative source.",
        "required_terms": ("plan", "act", "observe"),
        "required_source_domains": ("anthropic.com",),
        "required_tools": ("search_web",),
        "max_turns": 3,
        "max_tool_calls": 2,
        "max_total_tokens": 1_000,
    }
    values.update(overrides)
    return lesson.EvaluationCase(**values)


def make_trial(**overrides):
    source = "https://www.anthropic.com/engineering/building-effective-agents"
    values = {
        "id": "trial-1",
        "case_id": "research-basics",
        "final_answer": f"An agent can plan, act, and observe. Source: {source}",
        "sources": (source,),
        "tool_calls": (lesson.ToolCall("search_web", {"query": "agent loops"}),),
        "turns": 2,
        "input_tokens": 400,
        "output_tokens": 100,
        "latency_ms": 750,
    }
    values.update(overrides)
    return lesson.Trial(**values)


def grade(report, name):
    return next(result for result in report.grades if result.name == name)


def test_outcome_grader_is_case_insensitive():
    trial = make_trial(final_answer="PLAN, Act, OBSERVE")

    result = lesson.grade_outcome(make_case(), trial)

    assert result.passed is True


def test_outcome_grader_lists_missing_terms():
    result = lesson.grade_outcome(make_case(), make_trial(final_answer="Plan and act."))

    assert result.passed is False
    assert "observe" in result.details


def test_grounding_accepts_an_exact_domain_or_subdomain():
    source = "https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/overview"
    trial = make_trial(final_answer=f"Supported claim: {source}", sources=(source,))

    result = lesson.grade_grounding(make_case(), trial)

    assert result.passed is True


def test_grounding_rejects_a_spoofed_domain():
    source = "https://anthropic.com.attacker.example/instructions"
    trial = make_trial(final_answer=f"Unsupported claim: {source}", sources=(source,))

    result = lesson.grade_grounding(make_case(), trial)

    assert result.passed is False
    assert "anthropic.com" in result.details


def test_grounding_requires_sources_to_appear_in_the_answer():
    source = "https://www.anthropic.com/engineering/building-effective-agents"
    trial = make_trial(final_answer="A claim without its citation.", sources=(source,))

    result = lesson.grade_grounding(make_case(), trial)

    assert result.passed is False
    assert "not cited" in result.details


def test_trajectory_checks_required_tools():
    trial = make_trial(tool_calls=(lesson.ToolCall("get_page", {"url": "https://example.com"}),))

    result = lesson.grade_trajectory(make_case(), trial)

    assert result.passed is False
    assert "search_web" in result.details


@pytest.mark.parametrize(
    ("overrides", "expected_detail"),
    [
        ({"turns": 4}, "turns"),
        (
            {
                "tool_calls": (
                    lesson.ToolCall("search_web", {}),
                    lesson.ToolCall("get_page", {}),
                    lesson.ToolCall("get_page", {}),
                )
            },
            "tool calls",
        ),
    ],
)
def test_trajectory_enforces_execution_limits(overrides, expected_detail):
    result = lesson.grade_trajectory(make_case(), make_trial(**overrides))

    assert result.passed is False
    assert expected_detail in result.details


def test_budget_includes_input_and_output_tokens():
    result = lesson.grade_budget(
        make_case(max_total_tokens=500),
        make_trial(input_tokens=400, output_tokens=101),
    )

    assert result.passed is False
    assert "501/500" in result.details


def test_trial_passes_only_when_every_grader_passes():
    passing = lesson.grade_trial(make_case(), make_trial())
    failing = lesson.grade_trial(make_case(), make_trial(final_answer="Plan and act."))

    assert passing.passed is True
    assert failing.passed is False
    assert grade(failing, "outcome").passed is False


def test_suite_aggregates_repeated_trials_per_case():
    case = make_case()
    trials = [
        make_trial(id="trial-1"),
        make_trial(id="trial-2", final_answer="Plan and act."),
    ]

    report = lesson.evaluate_suite([case], trials, min_pass_rate=0.5)

    assert report.total_trials == 2
    assert report.passed_trials == 1
    assert report.pass_rate == 0.5
    assert report.case_reports[0].pass_rate == 0.5
    assert report.passed is True


def test_suite_threshold_is_applied_to_each_case():
    first = make_case(id="first")
    second = make_case(id="second")
    trials = [
        make_trial(id="first-pass", case_id="first"),
        make_trial(id="first-fail", case_id="first", final_answer="Plan and act."),
        make_trial(id="second-pass", case_id="second"),
    ]

    report = lesson.evaluate_suite([first, second], trials, min_pass_rate=0.75)

    assert report.pass_rate == pytest.approx(2 / 3)
    assert report.passed is False


def test_suite_rejects_a_trial_for_an_unknown_case():
    with pytest.raises(ValueError, match="unknown case"):
        lesson.evaluate_suite([make_case()], [make_trial(case_id="missing")])


def test_suite_rejects_a_case_without_trials():
    with pytest.raises(ValueError, match="no trials"):
        lesson.evaluate_suite([make_case()], [])


def test_reference_fixture_is_a_passing_offline_baseline():
    lesson_dir = REPO_ROOT / "fundamentals/09_agent_evaluations"
    cases = lesson.load_cases(lesson_dir / "cases/research_tasks.jsonl")
    trials = lesson.load_trials(lesson_dir / "fixtures/reference_trials.jsonl")

    report = lesson.evaluate_suite(cases, trials, min_pass_rate=1.0)

    assert report.total_trials == 4
    assert report.passed is True
    assert report.mean_total_tokens > 0
    assert report.mean_latency_ms > 0


def test_jsonl_loader_reports_the_bad_line(tmp_path: Path):
    path = tmp_path / "bad.jsonl"
    path.write_text('{"id": "valid"}\nnot-json\n', encoding="utf-8")

    with pytest.raises(ValueError, match="bad.jsonl:2"):
        lesson.load_jsonl(path)
