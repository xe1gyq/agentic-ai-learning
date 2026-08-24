"""
Loop Pattern 01 — Turn-based
=============================
You send ONE prompt. Claude loops (calling tools, reasoning) until
it decides the task is complete (stop_reason == "end_turn").

This is the most common agentic pattern: fire and forget one message,
let the agent run to completion on its own.
"""

import os
from typing import Any

import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# --- Mock tool: a simple calculator ---
tools = [
    {
        "name": "calculate",
        "description": "Evaluate a basic math expression and return the result.",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "A math expression like '2 + 2' or '100 / 4 * 3'",
                }
            },
            "required": ["expression"],
        },
    }
]


def calculate(expression: str) -> str:
    try:
        result = eval(expression, {"__builtins__": {}}, {})  # safe subset
        return str(result)
    except Exception as e:
        return f"Error: {e}"


def run_tool(name: str, tool_input: dict) -> str:
    if name == "calculate":
        return calculate(tool_input["expression"])
    return f"Unknown tool: {name}"


# ---------------------------------------------------------------
# TURN-BASED LOOP
# One prompt → run until end_turn → done.
# ---------------------------------------------------------------
TASK = (
    "Solve this step by step using the calculator tool:\n"
    "A store sells apples for $1.25 each. "
    "If I buy 3 dozen apples and get a 15% discount, "
    "how much do I pay in total? Show each calculation."
)

print("=" * 55)
print("TURN-BASED LOOP")
print("=" * 55)
print(f"Prompt: {TASK}\n")

messages: list[dict[str, Any]] = [{"role": "user", "content": TASK}]
step = 0

# THE LOOP — runs until Claude says "end_turn"
while True:
    step += 1
    print(f"[step {step}] calling Claude...")

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        tools=tools,
        messages=messages,
    )

    print(f"[step {step}] stop_reason = {response.stop_reason}")
    messages.append({"role": "assistant", "content": response.content})

    if response.stop_reason == "end_turn":
        # Claude decided it's done — extract the final answer
        final = next((b.text for b in response.content if hasattr(b, "text")), "")
        print(f"\nFinal answer:\n{final}")
        break

    if response.stop_reason == "tool_use":
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = run_tool(block.name, block.input)
                print(f"  tool: {block.name}({block.input}) → {result}")
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    }
                )
        messages.append({"role": "user", "content": tool_results})
