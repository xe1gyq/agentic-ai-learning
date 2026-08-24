"""
LangGraph 02 — ReAct Agent
============================
The agentic loop (fundamentals/04_tool_loop) rebuilt as a LangGraph graph.

ReAct = Reason + Act. The graph loops:
  agent_node → tool_node → agent_node → ... → END

LangGraph makes the loop structure explicit and visible as a graph,
unlike the manual while loop or LangChain's hidden AgentExecutor.

Compare with:
  fundamentals/04_tool_loop/agent.py   (manual loop)
  frameworks/langchain/03_agent/agent.py (hidden loop)
"""

import operator
import os
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langgraph.graph import START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

load_dotenv()

llm = ChatAnthropic(
    model="claude-sonnet-4-6",
    api_key=os.environ["ANTHROPIC_API_KEY"],
    max_tokens=2048,
)


# --- Tools ---
@tool
def calculate(expression: str) -> str:
    """Evaluate a basic math expression like '2 + 2 * 10'."""
    try:
        return str(eval(expression, {"__builtins__": {}}, {}))
    except Exception as e:
        return f"Error: {e}"


@tool
def word_count(text: str) -> str:
    """Count the number of words in a text."""
    return f"{len(text.split())} words"


tools = [calculate, word_count]
llm_with_tools = llm.bind_tools(tools)


# --- State ---
class AgentState(TypedDict):
    messages: Annotated[list, operator.add]


# --- Nodes ---
def agent_node(state: AgentState) -> dict:
    """Call the LLM. It may respond with text or request tool calls."""
    print(f"[agent_node] messages so far: {len(state['messages'])}")
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}


# ToolNode is a prebuilt node that:
# - finds all tool_call requests in the last message
# - runs each tool
# - returns tool results as ToolMessages
tool_node = ToolNode(tools)


# --- Graph ---
# tools_condition is a prebuilt conditional edge:
#   if last message has tool_calls → go to "tools"
#   else → go to END
graph_builder = StateGraph(AgentState)

graph_builder.add_node("agent", agent_node)
graph_builder.add_node("tools", tool_node)

graph_builder.add_edge(START, "agent")
graph_builder.add_conditional_edges("agent", tools_condition)  # loop or end
graph_builder.add_edge("tools", "agent")                       # always back to agent

graph = graph_builder.compile()

# --- Run ---
print("=" * 55)
print("LANGGRAPH — ReAct Agent")
print("=" * 55)

result = graph.invoke({
    "messages": [HumanMessage(content=(
        "Calculate 15% of 840, then count the words in "
        "'The quick brown fox jumps over the lazy dog'."
    ))]
})

print("\nFinal answer:")
print(result["messages"][-1].content)
