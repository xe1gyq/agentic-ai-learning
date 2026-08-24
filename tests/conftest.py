"""
conftest.py — Shared pytest fixtures.

Fixtures defined here are automatically available to every test file
without needing to import them. pytest discovers conftest.py automatically.

Key fixtures:
  - mock_env: sets ANTHROPIC_API_KEY so imports don't fail
  - mock_anthropic_client: returns a fully mocked Anthropic client
  - fake_claude_response: builds a fake Claude Message object
"""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch

# Make the repo root importable from tests/
# This lets us do: from fundamentals.five_research_agent.tools import search_web
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(autouse=True)
def mock_env(monkeypatch):
    """
    Set a fake API key so every test can import modules that read
    os.environ["ANTHROPIC_API_KEY"] at import time without failing.

    autouse=True means this runs automatically for every test.
    """
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-fake-key-for-testing")


def make_text_response(text: str) -> MagicMock:
    """
    Build a fake anthropic.Message object that looks like a real text response.

    Real Claude response structure:
        message.content = [ContentBlock(type="text", text="...")]
        message.stop_reason = "end_turn"
        message.usage.input_tokens = N
        message.usage.output_tokens = N
    """
    content_block = MagicMock()
    content_block.type = "text"
    content_block.text = text

    response = MagicMock()
    response.content = [content_block]
    response.stop_reason = "end_turn"
    response.usage.input_tokens = 10
    response.usage.output_tokens = 20
    return response


def make_tool_use_response(tool_name: str, tool_id: str, tool_input: dict) -> MagicMock:
    """
    Build a fake anthropic.Message object that looks like a tool_use response.

    Real tool_use structure:
        message.content = [ContentBlock(type="tool_use", name=..., id=..., input=...)]
        message.stop_reason = "tool_use"
    """
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = tool_name
    tool_block.id = tool_id
    tool_block.input = tool_input

    response = MagicMock()
    response.content = [tool_block]
    response.stop_reason = "tool_use"
    return response


@pytest.fixture
def mock_client(mocker):
    """
    A mocked Anthropic client. Patch it before the module creates its own client.

    Usage in tests:
        def test_something(mock_client):
            mock_client.messages.create.return_value = make_text_response("Hello!")
    """
    client = MagicMock()
    mocker.patch("anthropic.Anthropic", return_value=client)
    return client
