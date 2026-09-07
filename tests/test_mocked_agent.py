"""
test_mocked_agent.py — Tests for the agent loop with a mocked Anthropic API.

This shows the most important pattern for testing agentic code:
replace the real Claude API with a fake that returns controlled responses.

Why mock the API in tests?
  1. Tests run instantly (no network latency)
  2. Tests are free (no API tokens consumed)
  3. Tests are deterministic (Claude's real output varies)
  4. You can test edge cases (what if Claude calls a tool 5 times?)

The conftest.py fixtures (make_text_response, make_tool_use_response)
build fake Message objects that look identical to real ones.
"""

from tests.conftest import make_text_response, make_tool_use_response

# ---------------------------------------------------------------------------
# Helper: a minimal agentic loop we can test directly
# (same pattern as fundamentals/04_tool_loop — extracted for testability)
# ---------------------------------------------------------------------------


def run_simple_loop(client, messages: list, tools: list, tool_fn) -> str:
    """
    A minimal agentic loop:
      call model → if tool_use → run tool → repeat → return final text

    Extracted as a standalone function so it can be unit tested without
    any module-level side effects.
    """
    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            tools=tools,
            messages=messages,
        )

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            return next((b.text for b in response.content if hasattr(b, "text")), "")

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = tool_fn(block.name, block.input)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        }
                    )
            messages.append({"role": "user", "content": tool_results})


class TestAgentLoopNoTools:
    """Test the loop when Claude answers immediately (no tool calls)."""

    def test_returns_final_text(self, mock_client):
        """If Claude returns end_turn immediately, we get its text back."""
        mock_client.messages.create.return_value = make_text_response(
            "An AI agent is a system that perceives and acts."
        )

        result = run_simple_loop(
            client=mock_client,
            messages=[{"role": "user", "content": "What is an AI agent?"}],
            tools=[],
            tool_fn=lambda name, inp: "",
        )

        assert result == "An AI agent is a system that perceives and acts."
        assert mock_client.messages.create.call_count == 1

    def test_passes_messages_to_api(self, mock_client):
        """The loop should forward the full messages list to the API."""
        mock_client.messages.create.return_value = make_text_response("Hello!")

        messages = [{"role": "user", "content": "Hi"}]
        run_simple_loop(mock_client, messages, [], lambda n, i: "")

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["messages"][0]["content"] == "Hi"


class TestAgentLoopWithTools:
    """Test the loop when Claude makes one tool call before finishing."""

    def test_calls_tool_then_returns_final_answer(self, mock_client):
        """
        Sequence:
          1st call → tool_use (calculate)
          2nd call → end_turn with final answer
        """
        tool_use_resp = make_tool_use_response(
            tool_name="calculate",
            tool_id="tool_abc123",
            tool_input={"expression": "2 + 2"},
        )
        final_resp = make_text_response("The answer is 4.")

        # Configure the mock to return different values on successive calls
        mock_client.messages.create.side_effect = [tool_use_resp, final_resp]

        tool_calls = []

        def fake_tool(name: str, inp: dict) -> str:
            tool_calls.append((name, inp))
            return "4"

        result = run_simple_loop(
            client=mock_client,
            messages=[{"role": "user", "content": "What is 2+2?"}],
            tools=[{"name": "calculate", "input_schema": {}}],
            tool_fn=fake_tool,
        )

        assert result == "The answer is 4."
        assert mock_client.messages.create.call_count == 2
        assert tool_calls == [("calculate", {"expression": "2 + 2"})]

    def test_tool_result_sent_back_to_model(self, mock_client):
        """The tool result must appear in the messages sent to the second API call."""
        tool_use_resp = make_tool_use_response("calculate", "id_001", {"expression": "3*3"})
        final_resp = make_text_response("9")

        mock_client.messages.create.side_effect = [tool_use_resp, final_resp]

        run_simple_loop(
            client=mock_client,
            messages=[{"role": "user", "content": "What is 3*3?"}],
            tools=[],
            tool_fn=lambda n, i: "9",
        )

        # The second call should include a tool_result in messages.
        # NOTE: messages is a mutable list passed by reference. By the time we
        # assert, the loop has already appended the final assistant reply too.
        # So we search for the tool_result message rather than relying on index -1.
        second_call_messages = mock_client.messages.create.call_args_list[1].kwargs["messages"]
        tool_result_msgs = [
            m
            for m in second_call_messages
            if m["role"] == "user"
            and isinstance(m.get("content"), list)
            and m["content"]
            and m["content"][0].get("type") == "tool_result"
        ]
        assert len(tool_result_msgs) == 1, "Expected exactly one tool_result message"
        assert tool_result_msgs[0]["content"][0]["content"] == "9"

    def test_multiple_tool_calls(self, mock_client):
        """The loop handles multiple sequential tool calls before end_turn."""
        tool_call_1 = make_tool_use_response("calculate", "id_1", {"expression": "10+5"})
        tool_call_2 = make_tool_use_response("calculate", "id_2", {"expression": "15*2"})
        final = make_text_response("Done: 10+5=15, 15*2=30")

        mock_client.messages.create.side_effect = [tool_call_1, tool_call_2, final]

        tool_calls = []

        def fake_tool(name, inp):
            tool_calls.append(inp["expression"])
            return str(eval(inp["expression"]))

        result = run_simple_loop(
            client=mock_client,
            messages=[{"role": "user", "content": "Calculate two things"}],
            tools=[],
            tool_fn=fake_tool,
        )

        assert mock_client.messages.create.call_count == 3
        assert len(tool_calls) == 2
        assert "Done" in result
