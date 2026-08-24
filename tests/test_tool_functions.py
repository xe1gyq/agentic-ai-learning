"""
test_tool_functions.py — Tests for pure tool functions.

"Pure" means: given the same input, always returns the same output.
No network calls, no API calls, no side effects.
These tests run instantly and never cost money.

Functions tested:
  - calculate()        from loops/01_turn_based and 04_tool_loop
  - word_count()       from frameworks/langchain and langgraph
  - run_tool()         dispatch logic from fundamentals/04_tool_loop
"""

import json
import pytest


# ---------------------------------------------------------------------------
# calculate() — tested independently (same logic appears in multiple files)
# We define it here to avoid importing scripts with module-level side effects.
# ---------------------------------------------------------------------------

def calculate(expression: str) -> str:
    """The calculate function used across multiple lessons."""
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        return str(result)
    except Exception as e:
        return f"Error: {e}"


class TestCalculate:
    """Tests for the calculate() tool function."""

    def test_addition(self):
        assert calculate("2 + 2") == "4"

    def test_multiplication(self):
        assert calculate("3 * 7") == "21"

    def test_division(self):
        # Python returns float for division
        assert calculate("10 / 4") == "2.5"

    def test_compound_expression(self):
        # 15% of 240: 240 * 0.15 = 36.0
        assert calculate("240 * 0.15") == "36.0"

    def test_order_of_operations(self):
        assert calculate("2 + 3 * 4") == "14"

    def test_invalid_expression_returns_error(self):
        result = calculate("not a number")
        assert result.startswith("Error:")

    def test_empty_expression_returns_error(self):
        result = calculate("")
        assert result.startswith("Error:")

    def test_no_builtins_escape(self):
        # Security: __import__ should not be accessible
        result = calculate("__import__('os').getcwd()")
        assert result.startswith("Error:")


# ---------------------------------------------------------------------------
# word_count() — the LangChain/LangGraph tool
# ---------------------------------------------------------------------------

def word_count(text: str) -> str:
    """Count words — same logic as frameworks/langchain/03_agent and langgraph/02."""
    count = len(text.split())
    return f"{count} words"


class TestWordCount:

    def test_simple_sentence(self):
        assert word_count("hello world") == "2 words"

    def test_nine_word_sentence(self):
        result = word_count("The quick brown fox jumps over the lazy dog")
        assert result == "9 words"

    def test_single_word(self):
        assert word_count("hello") == "1 words"

    def test_empty_string(self):
        # str.split() on empty string returns [], so 0 words
        assert word_count("") == "0 words"

    def test_extra_whitespace(self):
        # str.split() without args splits on any whitespace and ignores extras
        assert word_count("  hello   world  ") == "2 words"


# ---------------------------------------------------------------------------
# run_tool() dispatch — from fundamentals/04_tool_loop
# Tests the dispatcher without making any real tool calls.
# ---------------------------------------------------------------------------

# Minimal mock implementations of the tools the dispatcher calls
MOCK_SEARCH_RESULTS = {
    "AI agents": [{"title": "AI Agents", "snippet": "An AI agent..."}],
}
MOCK_PAGES = {
    "https://example.com/ai-agents": "An AI agent is a system...",
}


def search_web_mock(query: str) -> str:
    for key, results in MOCK_SEARCH_RESULTS.items():
        if key.lower() in query.lower():
            return json.dumps(results)
    return json.dumps([{"snippet": f"No results for: {query}"}])


def get_page_mock(url: str) -> str:
    return MOCK_PAGES.get(url, "Page not found.")


def run_tool(name: str, tool_input: dict) -> str:
    """Dispatcher — same logic as fundamentals/04_tool_loop/agent.py."""
    if name == "search_web":
        return search_web_mock(tool_input["query"])
    if name == "get_page":
        return get_page_mock(tool_input["url"])
    return f"Unknown tool: {name}"


class TestRunToolDispatch:

    def test_dispatches_search_web(self):
        result = run_tool("search_web", {"query": "AI agents"})
        data = json.loads(result)
        assert isinstance(data, list)
        assert data[0]["title"] == "AI Agents"

    def test_dispatches_get_page(self):
        result = run_tool("get_page", {"url": "https://example.com/ai-agents"})
        assert "AI agent" in result

    def test_get_page_missing_url(self):
        result = run_tool("get_page", {"url": "https://unknown.com"})
        assert result == "Page not found."

    def test_unknown_tool_returns_message(self):
        result = run_tool("fly_to_moon", {})
        assert "Unknown tool" in result

    def test_search_no_results(self):
        result = run_tool("search_web", {"query": "xyzzy nonsense query"})
        data = json.loads(result)
        assert "No results for" in data[0]["snippet"]
