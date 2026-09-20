# Lesson 01 — Task Contract

An agent cannot safely decide that it is done if nobody has defined what *done* means. This lesson introduces the smallest harness boundary:

```text
incoming task → validate contract → produce output → independent checks → done / not done
```

The contract has five fields:

| Field | Purpose |
|-------|---------|
| `goal` | Desired outcome |
| `inputs` | Named information supplied to the run |
| `output` | Expected artifact key |
| `constraints` | Declared limits on execution |
| `done_when` | Named, observable completion criteria |

`parse_contract` rejects missing, unknown, blank, or duplicated fields. It copies mutable input data into an immutable runtime representation, so a caller cannot silently change the task after admission.

`check_completion` requires a non-empty output and one external verifier per criterion. Missing or broken verifiers fail closed. A model assertion such as “I finished” is not a verifier. This lesson deliberately does **not** enforce the declared constraints or grant tool permissions; those belong to later harness lessons.

Run the offline walkthrough:

```bash
python harness/01_task_contract/contract.py
pytest tests/test_harness_task_contract.py
```

Expected walkthrough result: `done=True` with both checks passing. To see the gate fail, remove the citation marker or one verifier.

The learning commits are `test → feat → docs`. Inspect them with:

```bash
git log --reverse -- harness/01_task_contract tests/test_harness_task_contract.py
```

This builds on `fundamentals/06_structured_outputs`: schema-valid model output is only an input to the application. The application still owns admission, verification, and stopping.
