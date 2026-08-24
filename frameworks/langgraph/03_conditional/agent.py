"""
LangGraph 03 — Conditional Routing
=====================================
Conditional edges let the graph branch based on the agent's output.
This is what makes LangGraph powerful: the path through the graph
is decided at runtime, not at design time.

Use case: a triage agent that routes questions to the right specialist.
  - Math questions → math_node
  - Science questions → science_node
  - Anything else → general_node

This pattern models real-world systems: customer support routing,
code review pipelines, multi-expert agents.
"""

import operator
import os
from typing import Annotated, Literal, TypedDict

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


# --- State ---
class AgentState(TypedDict):
    messages: Annotated[list, operator.add]
    route: str   # set by the triage node, read by the conditional edge


# --- Triage node: decides the route ---
def triage_node(state: AgentState) -> dict:
    """Classify the question and set the route."""
    question = state["messages"][-1].content
    print(f"[triage_node] classifying: '{question[:60]}...'")

    response = llm.invoke([HumanMessage(content=(
        f"Classify this question into exactly one category: math, science, or general.\n"
        f"Reply with ONLY the category word.\n\nQuestion: {question}"
    ))])

    route = response.content.strip().lower()
    if route not in ("math", "science"):
        route = "general"

    print(f"[triage_node] routed to: {route}")
    return {"route": route}


# --- Specialist nodes ---
def math_node(state: AgentState) -> dict:
    print("[math_node] answering math question")
    response = llm.invoke([
        HumanMessage(content="You are a math tutor. " + state["messages"][-1].content)
    ])
    return {"messages": [response]}


def science_node(state: AgentState) -> dict:
    print("[science_node] answering science question")
    response = llm.invoke([
        HumanMessage(content="You are a science teacher. " + state["messages"][-1].content)
    ])
    return {"messages": [response]}


def general_node(state: AgentState) -> dict:
    print("[general_node] answering general question")
    response = llm.invoke([state["messages"][-1]])
    return {"messages": [response]}


# --- Conditional edge function ---
# Takes state, returns the name of the next node to visit.
def route_question(state: AgentState) -> Literal["math", "science", "general"]:
    return state["route"]


# --- Build the graph ---
graph_builder = StateGraph(AgentState)

graph_builder.add_node("triage", triage_node)
graph_builder.add_node("math", math_node)
graph_builder.add_node("science", science_node)
graph_builder.add_node("general", general_node)

graph_builder.add_edge(START, "triage")

# Conditional edge: after triage, branch to math / science / general
graph_builder.add_conditional_edges(
    "triage",
    route_question,
    {"math": "math", "science": "science", "general": "general"},
)

graph_builder.add_edge("math", END)
graph_builder.add_edge("science", END)
graph_builder.add_edge("general", END)

graph = graph_builder.compile()

# --- Run with different questions ---
questions = [
    "What is the derivative of x squared?",
    "Why is the sky blue?",
    "What is the best way to learn a new language?",
]

print("=" * 55)
print("LANGGRAPH — Conditional Routing")
print("=" * 55)

for question in questions:
    print(f"\nQuestion: {question}")
    result = graph.invoke({"messages": [HumanMessage(content=question)], "route": ""})
    print(f"Answer: {result['messages'][-1].content[:200]}...")
    print("-" * 40)
