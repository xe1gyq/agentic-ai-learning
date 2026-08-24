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

## Key testing concepts

- **Pure function tests** — no mocking needed, input → expected output
- **`requests` mocking** — use `mocker.patch("requests.get")` to avoid real HTTP calls
- **API mocking** — use `mocker.patch("anthropic.Anthropic")` to avoid real API calls
  and control exactly what Claude "returns" in each test
- **`conftest.py`** — shared fixtures available to all test files automatically
