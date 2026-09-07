"""
test_research_tools.py — Tests for the research agent's HTTP tools.

These test search_web() and get_page() from fundamentals/05_research_agent/tools.py.
Both functions make real HTTP requests — we mock requests.get to avoid
network calls in tests. This is the standard pattern for testing any
code that talks to external services.

Pattern:
    mocker.patch("requests.get") → returns a fake response object
    call the function → it uses the fake response instead of the real network
    assert on the output

The real DuckDuckGo HTML structure is what we're parsing, so we include
a realistic HTML fixture.
"""

# This import works because conftest.py adds the repo root to sys.path
# and tools.py has no module-level side effects (no client creation, no loops)
import importlib.util
import json
import os

# Load tools.py directly by file path — avoids issues with folder names
# starting with numbers (e.g. "05_research_agent" is not a valid Python identifier)
_tools_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "fundamentals",
    "05_research_agent",
    "tools.py",
)
_spec = importlib.util.spec_from_file_location("research_tools", _tools_path)
if _spec is None or _spec.loader is None:
    raise ImportError(f"Cannot load research tools from {_tools_path}")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

search_web = _mod.search_web
get_page = _mod.get_page
run_tool = _mod.run_tool


# ---------------------------------------------------------------------------
# Fake DuckDuckGo HTML — mimics the structure our regex parses
# ---------------------------------------------------------------------------
FAKE_DDG_HTML = """
<html><body>
  <a class="result__a" href="https://example.com">Python AI Agents</a>
  <a class="result__url">example.com</a>
  <a class="result__snippet">An AI agent perceives its environment and acts.</a>

  <a class="result__a" href="https://other.com">Agentic Patterns</a>
  <a class="result__url">other.com</a>
  <a class="result__snippet">Agents use tools and memory to complete tasks.</a>
</body></html>
"""

FAKE_PAGE_HTML = """
<html><head><title>Test Page</title></head>
<body><h1>Hello</h1><p>This is a test page with some content.</p></body>
</html>
"""


class TestSearchWeb:
    def test_returns_json_list(self, mocker):
        """search_web should return a JSON-encoded list of results."""
        mock_resp = mocker.MagicMock()
        mock_resp.text = FAKE_DDG_HTML
        mock_resp.raise_for_status = mocker.MagicMock()
        mocker.patch("requests.get", return_value=mock_resp)

        result = search_web("AI agents")
        data = json.loads(result)

        assert isinstance(data, list)
        assert len(data) >= 1

    def test_result_contains_snippet(self, mocker):
        """Each result should have a snippet key."""
        mock_resp = mocker.MagicMock()
        mock_resp.text = FAKE_DDG_HTML
        mock_resp.raise_for_status = mocker.MagicMock()
        mocker.patch("requests.get", return_value=mock_resp)

        result = search_web("AI agents")
        data = json.loads(result)

        assert "snippet" in data[0]
        assert "agent" in data[0]["snippet"].lower()

    def test_network_error_returns_error_json(self, mocker):
        """If requests raises an exception, return JSON with an error key."""
        import requests

        mocker.patch("requests.get", side_effect=requests.RequestException("timeout"))

        result = search_web("anything")
        data = json.loads(result)

        assert "error" in data
        assert data["query"] == "anything"

    def test_max_results_respected(self, mocker):
        """max_results=1 should return at most 1 result."""
        mock_resp = mocker.MagicMock()
        mock_resp.text = FAKE_DDG_HTML
        mock_resp.raise_for_status = mocker.MagicMock()
        mocker.patch("requests.get", return_value=mock_resp)

        result = search_web("AI agents", max_results=1)
        data = json.loads(result)

        assert len(data) <= 1


class TestGetPage:
    def test_strips_html_tags(self, mocker):
        """get_page should return plain text, not HTML."""
        mock_resp = mocker.MagicMock()
        mock_resp.text = FAKE_PAGE_HTML
        mock_resp.raise_for_status = mocker.MagicMock()
        mocker.patch("requests.get", return_value=mock_resp)

        result = get_page("https://example.com")

        assert "<html>" not in result
        assert "<h1>" not in result
        assert "Hello" in result
        assert "test page" in result

    def test_truncates_long_content(self, mocker):
        """Content longer than max_chars should be truncated with '...'"""
        long_html = "<p>" + ("word " * 2000) + "</p>"
        mock_resp = mocker.MagicMock()
        mock_resp.text = long_html
        mock_resp.raise_for_status = mocker.MagicMock()
        mocker.patch("requests.get", return_value=mock_resp)

        result = get_page("https://example.com", max_chars=100)

        assert len(result) <= 103  # 100 chars + "..."
        assert result.endswith("...")

    def test_network_error_returns_error_string(self, mocker):
        """If requests raises, return a human-readable error string."""
        import requests

        mocker.patch("requests.get", side_effect=requests.RequestException("refused"))

        result = get_page("https://bad.example.com")

        assert "Error fetching page" in result


class TestRunToolDispatch:
    def test_dispatches_search_web(self, mocker):
        mock_resp = mocker.MagicMock()
        mock_resp.text = FAKE_DDG_HTML
        mock_resp.raise_for_status = mocker.MagicMock()
        mocker.patch("requests.get", return_value=mock_resp)

        result = run_tool("search_web", {"query": "AI"})
        assert json.loads(result)  # valid JSON

    def test_dispatches_get_page(self, mocker):
        mock_resp = mocker.MagicMock()
        mock_resp.text = FAKE_PAGE_HTML
        mock_resp.raise_for_status = mocker.MagicMock()
        mocker.patch("requests.get", return_value=mock_resp)

        result = run_tool("get_page", {"url": "https://example.com"})
        assert isinstance(result, str)
        assert len(result) > 0

    def test_unknown_tool(self):
        result = run_tool("nonexistent_tool", {})
        data = json.loads(result)
        assert "error" in data
        assert "nonexistent_tool" in data["error"]
