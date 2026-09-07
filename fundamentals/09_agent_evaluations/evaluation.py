"""Offline evaluation primitives for agent outcomes, trajectories, and budgets.

The harness intentionally accepts recorded trials instead of calling a model. This
keeps CI deterministic and free while preserving the data needed to evaluate an
agent run: its final answer, sources, tool trajectory, turns, tokens, and latency.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from statistics import fmean
from typing import Any
from urllib.parse import urlparse


@dataclass(frozen=True)
class EvaluationCase:
    """One task plus observable success criteria and execution limits."""

    id: str
    prompt: str
    required_terms: tuple[str, ...] = ()
    required_source_domains: tuple[str, ...] = ()
    required_tools: tuple[str, ...] = ()
    max_turns: int = 6
    max_tool_calls: int = 8
    max_total_tokens: int = 5_000


@dataclass(frozen=True)
class ToolCall:
    """The inspectable part of one tool action in an agent trajectory."""

    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Trial:
    """One recorded attempt at an evaluation case."""

    id: str
    case_id: str
    final_answer: str
    sources: tuple[str, ...]
    tool_calls: tuple[ToolCall, ...]
    turns: int
    input_tokens: int
    output_tokens: int
    latency_ms: int

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass(frozen=True)
class GradeResult:
    """The result of one deterministic grader."""

    name: str
    passed: bool
    details: str


@dataclass(frozen=True)
class TrialReport:
    """All grader results for one trial."""

    case_id: str
    trial_id: str
    passed: bool
    grades: tuple[GradeResult, ...]
    total_tokens: int
    latency_ms: int


@dataclass(frozen=True)
class CaseReport:
    """Pass-rate summary across repeated trials for one case."""

    case_id: str
    trial_count: int
    passed_trials: int
    pass_rate: float
    passed: bool


@dataclass(frozen=True)
class SuiteReport:
    """Aggregate quality and efficiency metrics for an evaluation suite."""

    case_reports: tuple[CaseReport, ...]
    trial_reports: tuple[TrialReport, ...]
    min_pass_rate: float
    total_trials: int
    passed_trials: int
    pass_rate: float
    mean_total_tokens: float
    mean_latency_ms: float
    passed: bool


def grade_outcome(case: EvaluationCase, trial: Trial) -> GradeResult:
    """Check objective answer requirements with a cheap code-based grader."""
    answer = trial.final_answer.casefold()
    missing = [term for term in case.required_terms if term.casefold() not in answer]
    if missing:
        return GradeResult("outcome", False, f"missing required terms: {missing}")
    return GradeResult("outcome", True, "all required terms are present")


def _domain_matches(url: str, required_domain: str) -> bool:
    """Match an exact hostname or subdomain without accepting spoofed suffixes."""
    hostname = (urlparse(url).hostname or "").casefold().rstrip(".")
    domain = required_domain.casefold().rstrip(".")
    return hostname == domain or hostname.endswith(f".{domain}")


def grade_grounding(case: EvaluationCase, trial: Trial) -> GradeResult:
    """Check source provenance and that recorded sources are cited in the answer."""
    missing_domains = [
        domain
        for domain in case.required_source_domains
        if not any(_domain_matches(source, domain) for source in trial.sources)
    ]
    uncited_sources = [source for source in trial.sources if source not in trial.final_answer]

    problems: list[str] = []
    if missing_domains:
        problems.append(f"missing source domains: {missing_domains}")
    if uncited_sources:
        problems.append(f"recorded sources not cited in answer: {uncited_sources}")

    if problems:
        return GradeResult("grounding", False, "; ".join(problems))
    return GradeResult("grounding", True, "required source domains are cited")


def grade_trajectory(case: EvaluationCase, trial: Trial) -> GradeResult:
    """Inspect how the result was produced, not only what the agent claimed."""
    tool_names = {call.name for call in trial.tool_calls}
    missing_tools = [tool for tool in case.required_tools if tool not in tool_names]

    problems: list[str] = []
    if missing_tools:
        problems.append(f"missing required tools: {missing_tools}")
    if trial.turns > case.max_turns:
        problems.append(f"turns exceeded: {trial.turns}/{case.max_turns}")
    if len(trial.tool_calls) > case.max_tool_calls:
        problems.append(f"tool calls exceeded: {len(trial.tool_calls)}/{case.max_tool_calls}")

    if problems:
        return GradeResult("trajectory", False, "; ".join(problems))
    return GradeResult("trajectory", True, "required tools and execution limits satisfied")


def grade_budget(case: EvaluationCase, trial: Trial) -> GradeResult:
    """Keep a separate efficiency contract so quality cannot hide runaway cost."""
    passed = trial.total_tokens <= case.max_total_tokens
    details = f"total tokens: {trial.total_tokens}/{case.max_total_tokens}"
    return GradeResult("budget", passed, details)


def grade_trial(case: EvaluationCase, trial: Trial) -> TrialReport:
    """Run every grader and require all dimensions to pass."""
    grades = (
        grade_outcome(case, trial),
        grade_grounding(case, trial),
        grade_trajectory(case, trial),
        grade_budget(case, trial),
    )
    return TrialReport(
        case_id=case.id,
        trial_id=trial.id,
        passed=all(result.passed for result in grades),
        grades=grades,
        total_tokens=trial.total_tokens,
        latency_ms=trial.latency_ms,
    )


def evaluate_suite(
    cases: list[EvaluationCase],
    trials: list[Trial],
    min_pass_rate: float = 1.0,
) -> SuiteReport:
    """Grade repeated trials and enforce the threshold for every case."""
    if not 0 <= min_pass_rate <= 1:
        raise ValueError("min_pass_rate must be between 0 and 1")

    cases_by_id = {case.id: case for case in cases}
    if len(cases_by_id) != len(cases):
        raise ValueError("evaluation case IDs must be unique")

    unknown = sorted({trial.case_id for trial in trials if trial.case_id not in cases_by_id})
    if unknown:
        raise ValueError(f"trials reference unknown case IDs: {unknown}")

    trials_by_case: dict[str, list[Trial]] = defaultdict(list)
    for trial in trials:
        trials_by_case[trial.case_id].append(trial)

    missing_trials = [case.id for case in cases if not trials_by_case[case.id]]
    if missing_trials:
        raise ValueError(f"evaluation cases have no trials: {missing_trials}")

    trial_reports: list[TrialReport] = []
    case_reports: list[CaseReport] = []
    for case in cases:
        reports = [grade_trial(case, trial) for trial in trials_by_case[case.id]]
        trial_reports.extend(reports)
        passed_trials = sum(report.passed for report in reports)
        pass_rate = passed_trials / len(reports)
        case_reports.append(
            CaseReport(
                case_id=case.id,
                trial_count=len(reports),
                passed_trials=passed_trials,
                pass_rate=pass_rate,
                passed=pass_rate >= min_pass_rate,
            )
        )

    total_trials = len(trial_reports)
    passed_trials = sum(report.passed for report in trial_reports)
    return SuiteReport(
        case_reports=tuple(case_reports),
        trial_reports=tuple(trial_reports),
        min_pass_rate=min_pass_rate,
        total_trials=total_trials,
        passed_trials=passed_trials,
        pass_rate=passed_trials / total_trials,
        mean_total_tokens=fmean(report.total_tokens for report in trial_reports),
        mean_latency_ms=fmean(report.latency_ms for report in trial_reports),
        passed=all(report.passed for report in case_reports),
    )


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load non-empty JSONL records and report malformed input with its line."""
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON at {path.name}:{line_number}: {exc.msg}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"expected an object at {path.name}:{line_number}")
        records.append(value)
    return records


def load_cases(path: Path) -> list[EvaluationCase]:
    """Load evaluation contracts from a JSONL dataset."""
    cases: list[EvaluationCase] = []
    for value in load_jsonl(path):
        cases.append(
            EvaluationCase(
                id=str(value["id"]),
                prompt=str(value["prompt"]),
                required_terms=tuple(value.get("required_terms", [])),
                required_source_domains=tuple(value.get("required_source_domains", [])),
                required_tools=tuple(value.get("required_tools", [])),
                max_turns=int(value.get("max_turns", 6)),
                max_tool_calls=int(value.get("max_tool_calls", 8)),
                max_total_tokens=int(value.get("max_total_tokens", 5_000)),
            )
        )
    return cases


def load_trials(path: Path) -> list[Trial]:
    """Load recorded agent attempts from a JSONL transcript dataset."""
    trials: list[Trial] = []
    for value in load_jsonl(path):
        tool_calls = tuple(
            ToolCall(name=str(call["name"]), arguments=dict(call.get("arguments", {})))
            for call in value.get("tool_calls", [])
        )
        trials.append(
            Trial(
                id=str(value["id"]),
                case_id=str(value["case_id"]),
                final_answer=str(value["final_answer"]),
                sources=tuple(value.get("sources", [])),
                tool_calls=tool_calls,
                turns=int(value["turns"]),
                input_tokens=int(value["input_tokens"]),
                output_tokens=int(value["output_tokens"]),
                latency_ms=int(value["latency_ms"]),
            )
        )
    return trials


def report_as_dict(report: SuiteReport) -> dict[str, Any]:
    """Convert the immutable report into JSON-serializable primitives."""
    return asdict(report)


def render_report(report: SuiteReport) -> str:
    """Render a compact report suitable for local runs and CI logs."""
    status = "PASS" if report.passed else "FAIL"
    lines = [
        f"Evaluation suite: {status}",
        f"Trials: {report.passed_trials}/{report.total_trials} passed ({report.pass_rate:.0%})",
        f"Mean tokens: {report.mean_total_tokens:.1f}",
        f"Mean latency: {report.mean_latency_ms:.1f} ms",
        "Cases:",
    ]
    for case in report.case_reports:
        case_status = "PASS" if case.passed else "FAIL"
        lines.append(
            f"  [{case_status}] {case.case_id}: "
            f"{case.passed_trials}/{case.trial_count} ({case.pass_rate:.0%})"
        )
    return "\n".join(lines)
