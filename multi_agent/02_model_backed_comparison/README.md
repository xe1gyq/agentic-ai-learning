# Lesson 02 — Model-backed comparison

This lesson connects the dynamic graph from Lesson 01 to the real Claude Messages API and asks a narrower engineering question:

> Under the same global resource envelope, when does a multi-agent architecture outperform one agent?

It does **not** assume that multi-agent is better. Both sides receive the same:

- Claude model;
- research question;
- fixed local corpus and `search_corpus` tool;
- total token limit;
- total tool-call limit;
- wall-clock timeout;
- deterministic outcome and citation checks.

Trials run sequentially in pairs so one architecture does not create concurrent rate-limit pressure for the other. Multiple trials are still necessary because model trajectories vary.

## Architecture

```text
                         SAME EXPERIMENT ENVELOPE
                  model + corpus + tokens + tools + time
                                /          \
                               /            \
                    SINGLE AGENT         MULTI-AGENT
                     tool loop         lead plans graph
                         |              /      |      \
                         |          worker  worker  worker
                         |              \      |      /
                         |              compressed evidence
                         |                     |
                         +--------- outcome evaluator --------+
                                      |
                         quality + citations + cost + latency
```

The multi-agent side reuses Lesson 01's dynamic orchestrator. `ClaudeLeadResearcher` owns planning, graph expansion, stopping, and synthesis. `ClaudeResearchWorker` owns one bounded search trajectory. Workers run concurrently, but all model and tool calls reserve capacity from one concurrency-safe `BudgetLedger`.

The single-agent side uses the same `ClaudeGateway`, corpus, and ledger. This isolates architecture as much as a small learning experiment can.

## Why token reservations matter

Checking the budget only after parallel calls finish is too late: three workers could each observe the same remaining budget and overspend it. Before each Messages API call, the gateway:

1. calls the token-counting endpoint;
2. atomically reserves input tokens plus the requested maximum output;
3. executes the model call;
4. settles the reservation with actual usage and releases unused capacity.

Tool calls are also charged atomically. This is resource scheduling, not just bookkeeping.

## Run the tests first

The tests use a fake asynchronous Claude client. They make no network requests and incur no API charges.

```bash
pytest tests/test_model_backed_comparison.py
```

They cover concurrent budget allocation, model/tool accounting, tool-loop messages, adapter translation, comparison fairness, and the live-execution safety gate.

## Run a live benchmark

Live execution requires both an API key and the explicit `--live` flag:

```bash
export ANTHROPIC_API_KEY="your-key"
python multi_agent/02_model_backed_comparison/comparison.py \
  --live \
  --trials 3 \
  --max-tokens 10000 \
  --max-tool-calls 20 \
  --timeout 120 \
  --output benchmark-report.json
```

Without `--live`, the command exits before constructing the Anthropic client. CI therefore tests behavior with fakes but never spends API credits.

The JSON report contains every trial plus per-architecture pass rate, mean input and output tokens, mean tool calls, and mean latency.

Do not infer much from one run. A useful experiment needs repeated paired trials, confidence intervals, and more than one outcome case.

## What this controls—and what it does not

Controlled:

- model identity and model parameters;
- available evidence and tool interface;
- global resource limits;
- evaluation rule;
- execution ordering.

Not controlled:

- nondeterministic model trajectories;
- prompt differences required by the two architectures;
- API load outside the process;
- the generality of one small local corpus.

This lesson demonstrates experimental mechanics. It does not prove that either architecture is universally superior.

## Expected hypotheses

- Breadth-first questions with independent evidence paths may gain coverage from workers.
- Serial tasks should gain little and may lose efficiency to orchestration overhead.
- Multi-agent should normally consume more test-time compute unless the shared cap stops it.
- Correct citations and sufficient coverage matter more than reproducing an exact trajectory.

## Source notes

The adapter follows Anthropic's Messages API conventions: client tools produce `tool_use` blocks; the application returns matching `tool_result` blocks; structured outputs constrain lead decisions; and token counting happens before generation. The architectural hypothesis comes from Anthropic's multi-agent research engineering article.
