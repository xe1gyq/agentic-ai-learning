"""
LangChain 02 — Chains (LCEL)
==============================
LangChain Expression Language (LCEL) lets you compose prompts and models
using the pipe operator: prompt | llm | output_parser

This is LangChain's core abstraction — "chains" link components together.

Compare with: fundamentals/02_conversation/agent.py
"""

import os

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

llm = ChatAnthropic(
    model="claude-sonnet-4-6",
    api_key=os.environ["ANTHROPIC_API_KEY"],
    max_tokens=512,
)

# --- Example 1: Simple prompt template ---
# {topic} is a placeholder filled in at call time
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are an expert teacher. Explain concepts simply."),
    ("human", "Explain {topic} in 2 sentences, like I'm 12 years old."),
])

# The pipe operator chains: prompt → llm → string parser
chain = prompt | llm | StrOutputParser()

print("=== Simple Chain ===")
result = chain.invoke({"topic": "neural networks"})
print(result)
print()

# --- Example 2: Reuse the same chain with different inputs ---
topics = ["recursion", "machine learning", "APIs"]
print("=== Reusing the chain ===")
for topic in topics:
    answer = chain.invoke({"topic": topic})
    print(f"{topic}: {answer}\n")

# --- Example 3: Streaming output ---
print("=== Streaming ===")
print("Explaining quantum computing: ", end="", flush=True)
for chunk in chain.stream({"topic": "quantum computing"}):
    print(chunk, end="", flush=True)
print()
