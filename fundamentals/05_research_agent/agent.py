"""
Lesson 05 - Full Research Agent
=================================
A complete research agent that:
  1. Receives a research question from the command line
  2. Searches the web (real DuckDuckGo, no API key)
  3. Reads relevant pages
  4. Synthesizes a structured report

Usage:
  python agent.py "What is quantum computing?"
  python agent.py "How do large language models work?"
"""

import os
import sys
from dotenv import load_dotenv
import anthropic

from tools import TOOL_DEFINITIONS, run_tool

load_dotenv()

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

SYSTEM_PROMPT = """You are a research assistant. Your job is to answer research questions
by searching the web and reading relevant pages.

Follow this process:
1. Search for the topic using 1-3 targeted queries
2. Read the most promising pages using get_page
3. Synthesize what you learned into a clear, structured report

Format your final report with:
- A brief summary (2-3 sentences)
- Key concepts (bullet points)
- Sources you used

Be thorough but concise. Cite your sources."""


def run_research_agent(question: str) -> str:
    print(f"Research question: {question}\n")
    print("=" * 50)

    messages = [{"role": "user", "content": question}]
    step = 0

    while True:
        step += 1
        print(f"\n[Step {step}]")

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOL_DEFINITIONS,
            messages=messages,
        )

        print(f"Stop reason: {response.stop_reason}")

        # Add Claude's full response to history
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            final_text = next(
                (b.text for b in response.content if hasattr(b, "text")), ""
            )
            print("\n" + "=" * 50)
            print("RESEARCH REPORT")
            print("=" * 50)
            print(final_text)
            return final_text

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"  Calling: {block.name}({list(block.input.values())[0]!r})")
                    result = run_tool(block.name, block.input)
                    # Show a preview of the result
                    preview = result[:120] + "..." if len(result) > 120 else result
                    print(f"  Result preview: {preview}")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            messages.append({"role": "user", "content": tool_results})


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python agent.py \"Your research question here\"")
        sys.exit(1)

    question = " ".join(sys.argv[1:])
    run_research_agent(question)
