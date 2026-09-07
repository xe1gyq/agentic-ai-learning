# Tests

Unit and integration tests for the agentic-ai-learning repo.

## Run all tests

```bash
source venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

## Run with coverage report

```bash
pytest --cov=. --cov-report=html
open htmlcov/index.html
```

## Test file map

| File | What it tests |
|------|---------------|
| `test_tool_functions.py` | Pure functions: calculate, word_count, run_tool dispatch |
| `test_research_tools.py` | search_web + get_page with mocked HTTP requests |
| `test_goal_logic.py` | Goal-checking logic from the goal-based loop |
| `test_mocked_agent.py` | Full agent loop with the Anthropic API mocked |
| `test_structured_outputs.py` | Task schema validation and structured-output API configuration |
| `test_context_engineering.py` | Required context, relevance, deduplication, budgets, provenance |
| `test_state_and_memory.py` | Durable memory, retrieval, corruption handling, ephemeral run state |

`lesson_loader.py` imports the actual lesson scripts by path. This lets tests exercise the
production functions even though numbered lesson folders are not valid Python package names.

## Key testing concepts

- **Pure function tests** — no mocking needed, input → expected output
- **`requests` mocking** — use `mocker.patch("requests.get")` to avoid real HTTP calls
- **API mocking** — use `mocker.patch("anthropic.Anthropic")` to avoid real API calls
  and control exactly what Claude "returns" in each test
- **Contract tests** — verify schemas and application invariants at component boundaries
- **Persistence tests** — use temporary storage to verify behavior across store instances
- **`conftest.py`** — shared fixtures available to all test files automatically

These are software tests. Agent evaluations—quality, trajectory, grounding, cost, and
regressions across non-deterministic runs—belong to the next curriculum stage.

