"""
Lesson 04 - Agentic Loop
=========================
The core pattern of agentic AI: loop until the model says "end_turn".

Claude can call tools multiple times before giving a final answer.
This is the observe -> think -> act cycle that drives autonomous agents.
"""

import json
import os

import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# --- Tools ---
tools = [
    {
        "name": "search_web",
        "description": "Search the web for information. Returns relevant snippets.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query"}
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_page",
        "description": "Retrieve the full content of a web page by URL.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to fetch"}
            },
            "required": ["url"],
        },
    },
]

MOCK_SEARCH_RESULTS = {
    "AI agents": [
        {"title": "What is an AI Agent?", "url": "https://example.com/ai-agents", "snippet": "An AI agent perceives its environment and takes autonomous actions."},
        {"title": "Types of AI Agents", "url": "https://example.com/agent-types", "snippet": "Reactive, deliberative, and hybrid agents each have different architectures."},
    ],
    "agentic loop": [
        {"title": "The Agentic Loop Explained", "url": "https://example.com/loop", "snippet": "The observe-think-act loop is the foundation of all autonomous agents."},
    ],
}

MOCK_PAGES = {
    "https://example.com/ai-agents": "An AI agent is a system that perceives inputs, reasons about them, and takes actions to achieve goals. Agents can use tools, maintain memory, and plan multi-step tasks.",
    "https://example.com/agent-types": "Reactive agents respond directly to stimuli. Deliberative agents build internal models. Hybrid agents combine both approaches for robust behavior.",
}


def search_web(query: str) -> str:
    print(f"  [tool] search_web('{query}')")
    for key, results in MOCK_SEARCH_RESULTS.items():
        if key.lower() in query.lower():
            return json.dumps(results)
    return json.dumps([{"snippet": f"No results found for: {query}"}])


def get_page(url: str) -> str:
    print(f"  [tool] get_page('{url}')")
    return MOCK_PAGES.get(url, "Page not found.")


def run_tool(name: str, tool_input: dict) -> str:
    if name == "search_web":
        return search_web(tool_input["query"])
    if name == "get_page":
        return get_page(tool_input["url"])
    return f"Unknown tool: {name}"


# --- Agentic loop ---
def run_agent(user_task: str):
    print(f"Task: {user_task}\n")
    messages = [{"role": "user", "content": user_task}]
    step = 0

    while True:
        step += 1
        print(f"--- Step {step} ---")

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            tools=tools,
            messages=messages,
        )

        print(f"Stop reason: {response.stop_reason}")

        # Add Claude's response to message history
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            # Agent is done — extract and return final text
            final_text = next(
                (b.text for b in response.content if hasattr(b, "text")), ""
            )
            print(f"\nFinal answer:\n{final_text}")
            return final_text

        if response.stop_reason == "tool_use":
            # Run all tool calls in this response
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = run_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            # Feed all results back in one user message
            messages.append({"role": "user", "content": tool_results})


if __name__ == "__main__":
    run_agent(
        "Research AI agents: first search for 'AI agents', "
        "then get the page at https://example.com/ai-agents, "
        "then write a short summary of what you learned."
    )
