# Lesson 09 — Agent Evaluations

An agent saying “done” is not evidence that it succeeded. This lesson builds a small,
deterministic evaluation harness that checks the **outcome**, **trajectory**, and
**operating budget** of recorded agent runs.

No model or network call occurs during this lesson's evaluation run. That makes the
baseline fast, free, and reproducible enough to enforce in CI.

## Unit test versus agent evaluation

| Question | Unit test | Agent evaluation |
|----------|-----------|------------------|
| Subject | One deterministic function | Model + prompt + tools + loop + environment |
| Example | Does `grade_budget()` reject 501 tokens? | Does the research agent answer correctly within 1,000 tokens? |
| Input | Carefully chosen values and mocks | Representative user tasks |
| Repetition | Usually once | Multiple trials because model behavior varies |
| Evidence | Return value or side effect | Outcome, transcript, tool trajectory, cost, and latency |

The lesson uses both. `tests/test_agent_evaluations.py` unit-tests the harness, while
`run_evals.py` applies that harness to a small behavioral dataset.

## Evaluation vocabulary

```text
case (task + success criteria)
  ├── trial 1 (one agent attempt)
  ├── trial 2 (another attempt)
  └── ...

trial → graders → trial report
trial reports → per-case pass rates → suite decision
```

- **Case** — one prompt, observable requirements, and execution limits.
- **Trial** — one attempt, including final answer, sources, tool calls, turns, tokens,
  and latency.
- **Transcript/trajectory** — the steps taken during a trial. This example records the
  inspectable fields needed by its graders rather than storing hidden reasoning.
- **Outcome** — what exists or is true at the end, not what the agent claims happened.
- **Grader** — code, a model, or a human that scores one aspect of performance.
- **Harness** — loads cases and trials, invokes graders, and aggregates results.

## Files

```text
09_agent_evaluations/
├── README.md
├── evaluation.py                  # Data contracts, graders, aggregation, JSONL loading
├── run_evals.py                   # CLI and CI entry point
├── cases/
│   └── research_tasks.jsonl       # Tasks and measurable success criteria
└── fixtures/
    └── reference_trials.jsonl     # Recorded, deterministic baseline attempts
```

## Four code-based graders

| Grader | Evidence inspected | Failure example |
|--------|--------------------|-----------------|
| `outcome` | Required terms in the final answer | A key concept is absent |
| `grounding` | Source domains and citations | A source is missing, spoofed, or not cited |
| `trajectory` | Tools, turns, and tool-call count | Search was required but never called |
| `budget` | Input + output tokens | A correct answer exceeds its token budget |

A trial passes only when all four graders pass. A suite passes only when **every case**
meets the configured pass-rate threshold across its repeated trials. This prevents a
strong case from hiding a weak one in a global average.

## Run it

From the repository root:

```bash
python fundamentals/09_agent_evaluations/run_evals.py
```

Expected baseline:

```text
Evaluation suite: PASS
Trials: 4/4 passed (100%)
Mean tokens: 655.5
Mean latency: 870.0 ms
Cases:
  [PASS] agent-loop: 2/2 (100%)
  [PASS] langgraph-memory: 2/2 (100%)
```

Machine-readable output:

```bash
python fundamentals/09_agent_evaluations/run_evals.py --json
```

## Learn from the commits

This lesson follows red–green–document:

1. `test: define lesson 09 agent evaluation behavior` — tests and datasets exist, but
   `evaluation.py` does not. Checking out this commit shows the intended red state.
2. `feat: implement offline agent evaluation harness` — the smallest implementation
   makes the behavioral contract pass.
3. `docs: teach eval-driven development and gate regressions` — documentation and CI
   turn the example into a repeatable engineering practice.

Use `git log --reverse -- fundamentals/09_agent_evaluations tests/test_agent_evaluations.py`
and inspect each commit with `git show`.

## Experiments

1. Remove `observe` from an `agent-loop` answer and rerun the suite.
2. Replace `anthropic.com` with `anthropic.com.attacker.example`; notice that hostname
   parsing rejects the spoofed suffix.
3. Add a failing third trial and run with `--min-pass-rate 0.66`, then `0.67`.
4. Add a grader for answer length or forbidden claims.
5. Adapt the research agent to save real trials locally, but keep paid, non-deterministic
   model runs out of pull-request CI.

## Deliberate limitations

These graders teach evaluation mechanics; they do not prove semantic correctness.
Keyword matching can miss valid wording, and citation presence does not prove that a source
supports a claim. A production suite should combine code-based graders with calibrated
model graders and periodic human review. Start with objective checks because they are cheap,
fast, and easy to debug.

## Reference

- [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
- [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
