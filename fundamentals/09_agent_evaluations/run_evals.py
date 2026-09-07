"""Run the Lesson 09 offline evaluation suite from the command line."""

import argparse
import json
from pathlib import Path

from evaluation import evaluate_suite, load_cases, load_trials, render_report, report_as_dict

LESSON_DIR = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Grade recorded agent trials")
    parser.add_argument(
        "--cases",
        type=Path,
        default=LESSON_DIR / "cases/research_tasks.jsonl",
        help="JSONL evaluation cases",
    )
    parser.add_argument(
        "--trials",
        type=Path,
        default=LESSON_DIR / "fixtures/reference_trials.jsonl",
        help="JSONL recorded trials",
    )
    parser.add_argument(
        "--min-pass-rate",
        type=float,
        default=1.0,
        help="Required pass rate for every case (0.0 to 1.0)",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = evaluate_suite(
        load_cases(args.cases),
        load_trials(args.trials),
        min_pass_rate=args.min_pass_rate,
    )
    if args.json:
        print(json.dumps(report_as_dict(report), indent=2))
    else:
        print(render_report(report))
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
