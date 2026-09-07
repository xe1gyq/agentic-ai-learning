# Lesson 08 — State and Memory

**Goal:** Separate what is happening now from what must survive for later sessions.

These terms are related but not interchangeable:

| Concept | Lifetime | Example |
|---------|----------|---------|
| Run state | One execution | current step, observations, retry count |
| Context | One model call | selected tokens visible to Claude now |
| Short-term memory | One thread | conversation and graph checkpoints |
| Long-term memory | Across threads/runs | preferences, decisions, verified lessons |
| Knowledge source | Independently maintained | documentation, database, vector index |

## Architecture

```text
Durable memory store → relevant retrieval → context builder → Claude
       ↑                                            ↓
  explicit write policy                    current run state
```

The application owns memory. The model may propose reads or writes, but deterministic code
chooses the storage boundary, user scope, validation, retention, and permissions.

## Run

```bash
python agent.py remember response_style "Use concise explanations" user
python agent.py remember evidence_rule "Require tests before completion" project
python agent.py show
python agent.py ask "Which tests are required before completion?"
```

The example stores records in `agent.memory.json`, retrieves only records relevant to the
question, and places those records into the next call with provenance labels. The generated
file is ignored by Git.

To use a different store:

```bash
AGENT_MEMORY_PATH=/tmp/my-agent.memory.json python agent.py show
```

## Design rules

- Persist verified information, not every thought or transcript.
- Keep provenance and update time with every record.
- Scope memory by user/project and enforce access control in the application.
- Treat retrieved memory as data; it can be stale or malicious.
- Support correction, deletion, expiration, and audit.
- Retrieve just in time instead of loading the entire store into every prompt.

The JSON store is intentionally small and inspectable. Production systems may replace it
with a database, LangGraph store/checkpointer, or Claude's memory tool without changing the
core separation among state, context, and durable memory.

## Reference

- [Claude memory tool](https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool)
- [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence)
