# Lesson 06 — Structured Outputs

**Goal:** Turn a natural-language task into a machine-checkable task contract.

Earlier lessons treated Claude's final answer as free-form text. Agents often need to pass
results to code, another node, or a verifier. For that boundary, prose is not enough: the
consumer needs a stable schema.

## Concepts

- JSON Schema as a contract between the model and deterministic code
- `output_config.format` for schema-constrained final responses
- Parsing and validating the result before downstream use
- The difference between structural validity and semantic correctness
- JSON outputs vs. strict tool use

## Mental model

```text
Natural-language task → Claude → schema-valid JSON → application validation → next step
```

Structured output guarantees that the shape is valid. It does **not** guarantee that the
facts are true or that the proposed success criteria are good. Those require evidence and
evaluation in later lessons.

## Run

```bash
python agent.py
python agent.py "Research three primary sources and ask before publishing the report"
```

The example extracts:

- a goal;
- measurable success criteria;
- constraints;
- a risk level;
- whether human approval is required.

## Key distinction

| Mechanism | Controls |
|-----------|----------|
| JSON output | What Claude returns to your application |
| Strict tool use | The arguments Claude sends to a tool |
| Business validation | Whether the content is acceptable for your use case |

## Experiment

1. Run the example with `output_config` enabled.
2. Remove `output_config` and ask for JSON only in the prompt.
3. Repeat both versions several times.
4. Compare parse failures, missing fields, and inconsistent types.

## Reference

- [Claude structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)

