# Lesson 01 — Task Contract

> A human request is not yet an executable specification.

A worker given only “Research Python 3.14 changes” can produce related text, but the application cannot tell what output was required or what would count as done. The first test makes that ambiguity visible: `prepare_task` rejects a bare request without explicit acceptance criteria.

This lesson adds only a frozen dataclass with five fields:

```python
@dataclass(frozen=True)
class TaskContract:
    goal: str
    inputs: tuple[str, ...]
    output: str
    constraints: tuple[str, ...]
    done_when: tuple[str, ...]
```

It checks obvious omissions such as blank fields or an empty `done_when`, then passes the contract to a tiny example worker. No inheritance, registry, model call, persistence, retry, or tracing is involved.

```text
human request → TaskContract → worker
```

Run it without an API key:

```bash
python harness/01_task_contract/contract.py
pytest tests/test_harness_task_contract.py
```

Three distinctions matter:

- Request ≠ contract: the request expresses intent; the contract makes expected output and acceptance criteria explicit.
- Contract ≠ verifier: `done_when` is data. Lesson 04 will evaluate evidence against it.
- Contract ≠ permission system: constraints are declared here; Lesson 02 will govern proposed actions.

The model proposes. The harness authorizes, records, and verifies. **Before any of that, the contract defines what the run is supposed to accomplish.**

The PR began with `test → feat → docs`. A follow-up commit narrows Lesson 01 after review; inspect the full history with `git log --reverse -- harness/01_task_contract tests/test_harness_task_contract.py`.
