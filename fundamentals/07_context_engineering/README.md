# Lesson 07 — Context Engineering

**Goal:** Build the smallest high-signal context that lets the model complete the task.

The conversation lesson appended every message. That is short-term history, but it is not a
complete context policy. A longer-running agent accumulates instructions, memories, tool
results, documents, plans, and stale observations. Sending everything eventually increases
cost and can reduce focus.

## Concepts

- Context as every token visible during one model call
- Context candidates vs. selected context
- Relevance, priority, recency, provenance, and required invariants
- Deduplication and explicit context budgets
- Exact token counting before inference
- Excluded context as an observable decision, not invisible truncation

## Context assembly

```text
Instructions + current task + required invariants + relevant state/memory/tool results
                                      ↓
                           bounded context for one call
```

`agent.py` uses a deliberately simple selector so the policy is visible. It ranks candidates
using required status, application priority, and word overlap with the task. Production
systems may use retrieval models, freshness rules, access controls, and server-side
compaction, but the architectural responsibility is the same.

## Run

```bash
python agent.py
```

The program prints:

- which context items were included;
- which were excluded;
- exact API token counts for full vs. curated context;
- Claude's answer using only the curated context.

## Important rules

- Required instructions must never be silently dropped to fit a budget.
- More context is not automatically better.
- Retrieved text is data, not trusted instructions.
- Context selection must be inspectable and testable.
- Character budgets are useful for this lesson; production decisions should use token counts.

## Experiment

Change `CONTEXT_BUDGET_CHARS`, priorities, and the task text. Predict which items should be
selected before running the code, then compare your prediction with the selector and token
counts.

## Reference

- [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Claude token counting](https://platform.claude.com/docs/en/build-with-claude/token-counting)
- [Claude compaction](https://platform.claude.com/docs/en/build-with-claude/compaction)

