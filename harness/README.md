# Harness Engineering

The model proposes actions; the harness admits tasks, authorizes effects, preserves state, checks outcomes, and records evidence. This section teaches those mechanisms in plain Python before recreating any of them in a framework.

| Lesson | Boundary introduced |
|--------|---------------------|
| `01_task_contract` | A complete task specification and an external completion gate |
| `02_tool_permissions` | Planned: model proposal → policy decision → tool execution |
| `03_durable_state` | Planned: conversation context is not the system of record |
| `04_verification_loop` | Planned: produce → check → repair, with bounded retries |
| `05_tracing_and_receipts` | Planned: decisions, cost, artifacts, retries, and rollback points |
| `06_failure_to_infrastructure` | Planned: turn failure classes into tests, rules, or validators |

Each new abstraction must first be motivated by a visible failure and implemented at the smallest useful scale. A later comparison can rebuild one mechanism in LangGraph to expose the trade-offs in state, control flow, observability, permissions, and complexity.
