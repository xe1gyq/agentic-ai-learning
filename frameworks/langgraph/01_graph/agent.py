"""
LangGraph 01 — StateGraph Basics
==================================
LangGraph models agents as graphs: nodes do work, edges decide what's next.
State flows through the graph and each node can read/update it.

This is the core mental model of LangGraph — everything else builds on it.

Key concepts:
- State: a typed dict shared across all nodes
- Node: a function that receives state and returns updates
- Edge: a connection that tells the graph what node runs next
- START / END: built-in entry and exit points
"""

import operator
import os
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph

load_dotenv()

llm = ChatAnthropic(
    model="claude-sonnet-4-6",
    api_key=os.environ["ANTHROPIC_API_KEY"],
    max_tokens=512,
)


# --- 1. Define the State ---
# State is a TypedDict that flows through every node.
# `Annotated[list, operator.add]` means: append new items (don't overwrite).
class AgentState(TypedDict):
    messages: Annotated[list, operator.add]
    topic: str


# --- 2. Define Nodes ---
# Each node is a function: State → dict of updates to State

def research_node(state: AgentState) -> dict:
    """Node 1: Ask Claude a question about the topic."""
    print(f"[research_node] researching: {state['topic']}")
    response = llm.invoke([
        HumanMessage(content=f"Give me 3 key facts about: {state['topic']}")
    ])
    return {"messages": [response]}


def summary_node(state: AgentState) -> dict:
    """Node 2: Summarize what was found."""
    print("[summary_node] summarizing...")
    last_message = state["messages"][-1].content
    response = llm.invoke([
        HumanMessage(content=f"Summarize this in one sentence:\n\n{last_message}")
    ])
    return {"messages": [response]}


# --- 3. Build the Graph ---
graph_builder = StateGraph(AgentState)

# Add nodes
graph_builder.add_node("research", research_node)
graph_builder.add_node("summary", summary_node)

# Add edges: START → research → summary → END
graph_builder.add_edge(START, "research")
graph_builder.add_edge("research", "summary")
graph_builder.add_edge("summary", END)

# Compile into a runnable
graph = graph_builder.compile()

# --- 4. Run it ---
print("=" * 55)
print("LANGGRAPH — StateGraph")
print("=" * 55)

result = graph.invoke({"messages": [], "topic": "neural networks"})

print("\nAll messages:")
for i, msg in enumerate(result["messages"], 1):
    label = "Research" if i == 1 else "Summary"
    print(f"\n[{label}]\n{msg.content}")
