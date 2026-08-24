"""
Lesson 03 - Tool Use
=====================
Define a tool (mock web search) and let Claude call it.
We handle the tool_use stop reason and return a result.

This is a ONE-SHOT tool call — one user message, one tool call, one final answer.
Lesson 04 will handle multiple sequential tool calls (the agentic loop).
"""

import json
import os

import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# --- Tool definition ---
# We describe the tool to Claude using a JSON schema.
tools = [
    {
        "name": "search_web",
        "description": "Search the web for information on a topic. Returns a list of relevant snippets.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query",
                }
            },
            "required": ["query"],
        },
    }
]


def search_web(query: str) -> str:
    """Mock web search — returns fake results for demonstration."""
    print(f"  [tool] search_web called with query: '{query}'")
    return json.dumps([
        {"title": "Intro to AI Agents", "snippet": "An AI agent perceives its environment and takes actions to achieve goals."},
        {"title": "Agentic AI Overview", "snippet": "Agents use tools, memory, and planning to complete multi-step tasks autonomously."},
    ])


# --- Single interaction with tool use ---
user_message = "What are AI agents? Search the web and summarize what you find."
messages = [{"role": "user", "content": user_message}]

print(f"User: {user_message}\n")

# Step 1: Ask Claude — it will respond with a tool_use block
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    tools=tools,
    messages=messages,
)

print(f"Stop reason: {response.stop_reason}")

if response.stop_reason == "tool_use":
    # Step 2: Find the tool call in the response
    tool_use_block = next(b for b in response.content if b.type == "tool_use")
    tool_name = tool_use_block.name
    tool_input = tool_use_block.input

    print(f"Claude wants to call: {tool_name}({tool_input})\n")

    # Step 3: Execute our tool
    tool_result = search_web(tool_input["query"])

    # Step 4: Add Claude's response and the tool result to history, then call again
    messages.append({"role": "assistant", "content": response.content})
    messages.append({
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": tool_use_block.id,
                "content": tool_result,
            }
        ],
    })

    final_response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        tools=tools,
        messages=messages,
    )

    print(f"\nClaude: {final_response.content[0].text}")
