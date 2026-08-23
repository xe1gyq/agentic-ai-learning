"""
tools.py — Tool implementations for the research agent.

Tools:
  - search_web: DuckDuckGo search (no API key required)
  - get_page: Fetch and extract text from a web page
"""

import json
import re
import requests


HEADERS = {"User-Agent": "Mozilla/5.0 (research-agent-learning/1.0)"}


def search_web(query: str, max_results: int = 5) -> str:
    """Search DuckDuckGo and return a list of results as JSON."""
    try:
        resp = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers=HEADERS,
            timeout=10,
        )
        resp.raise_for_status()

        # Parse results from DuckDuckGo HTML (no API key needed)
        results = []
        # Find result blocks using simple regex (avoids BeautifulSoup dependency)
        snippets = re.findall(
            r'class="result__snippet"[^>]*>(.*?)</a>',
            resp.text,
            re.DOTALL,
        )
        titles = re.findall(
            r'class="result__a"[^>]*>(.*?)</a>',
            resp.text,
            re.DOTALL,
        )
        urls = re.findall(
            r'class="result__url"[^>]*>(.*?)</a>',
            resp.text,
            re.DOTALL,
        )

        for i in range(min(max_results, len(snippets))):
            title = re.sub(r"<[^>]+>", "", titles[i]).strip() if i < len(titles) else ""
            snippet = re.sub(r"<[^>]+>", "", snippets[i]).strip()
            url = re.sub(r"<[^>]+>", "", urls[i]).strip() if i < len(urls) else ""
            if snippet:
                results.append({"title": title, "url": url, "snippet": snippet})

        if not results:
            return json.dumps({"error": "No results found", "query": query})
        return json.dumps(results, ensure_ascii=False)

    except requests.RequestException as e:
        return json.dumps({"error": str(e), "query": query})


def get_page(url: str, max_chars: int = 3000) -> str:
    """Fetch a web page and return its text content (truncated)."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        # Strip HTML tags
        text = re.sub(r"<[^>]+>", " ", resp.text)
        # Collapse whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text[:max_chars] + ("..." if len(text) > max_chars else "")
    except requests.RequestException as e:
        return f"Error fetching page: {e}"


# Tool schemas for the Claude API
TOOL_DEFINITIONS = [
    {
        "name": "search_web",
        "description": (
            "Search the web using DuckDuckGo. "
            "Returns a JSON list of results with title, url, and snippet. "
            "Use this to find relevant sources for a research topic."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query string",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_page",
        "description": (
            "Fetch the text content of a web page by URL. "
            "Use this to read the full content of a promising search result."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The full URL of the page to fetch",
                }
            },
            "required": ["url"],
        },
    },
]


def run_tool(name: str, tool_input: dict) -> str:
    """Dispatch a tool call by name."""
    if name == "search_web":
        return search_web(tool_input["query"])
    if name == "get_page":
        return get_page(tool_input["url"])
    return json.dumps({"error": f"Unknown tool: {name}"})
