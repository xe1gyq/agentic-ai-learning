"""
LangChain 03 — Tool-calling Agent
===================================
LangChain's AgentExecutor handles the tool loop for you.
Compare this with fundamentals/04_tool_loop/agent.py to see
what the framework is doing under the hood.

LangChain hides:
- The while loop
- Parsing tool_use blocks
- Building tool_result messages
- Appending to message history

You just: define tools, create the agent, call .invoke().

Compare with: fundamentals/04_tool_loop/agent.py
"""

import os
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

llm = ChatAnthropic(
    model="claude-sonnet-4-6",
    api_key=os.environ["ANTHROPIC_API_KEY"],
    max_tokens=2048,
)

# --- Define tools with the @tool decorator ---
# LangChain reads the function name, docstring, and type hints
# to build the JSON schema automatically.

@tool
def calculate(expression: str) -> str:
    """Evaluate a basic math expression. Example: '2 + 2 * 10'"""
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        return str(result)
    except Exception as e:
        return f"Error: {e}"


@tool
def get_word_count(text: str) -> str:
    """Count the number of words in a piece of text."""
    count = len(text.split())
    return f"{count} words"


tools = [calculate, get_word_count]

# --- Create the agent ---
# AgentExecutor wraps the tool loop we wrote manually in 04_tool_loop
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant. Use tools when needed."),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),  # required by LangChain agents
])

agent = create_tool_calling_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# --- Run it ---
# verbose=True shows you the tool calls — compare with our manual loop output
print("=" * 55)
result = agent_executor.invoke({
    "input": (
        "I have a text: 'The quick brown fox jumps over the lazy dog'. "
        "How many words does it have? Also calculate 15% of 240."
    )
})

print("\nFinal answer:")
print(result["output"])
