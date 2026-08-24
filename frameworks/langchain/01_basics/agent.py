"""
LangChain 01 — Basics
======================
The same "send a message, get a response" from fundamentals/01_basics,
rewritten with LangChain's ChatAnthropic.

Compare with: fundamentals/01_basics/agent.py

What LangChain adds:
- `ChatAnthropic` wraps the client creation
- `HumanMessage` / `AIMessage` are typed message objects
- `.invoke()` is the standard LangChain call interface
"""

import os

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

load_dotenv()

# LangChain creates the client for you
llm = ChatAnthropic(
    model="claude-sonnet-4-6",
    api_key=os.environ["ANTHROPIC_API_KEY"],
    max_tokens=1024,
)

# .invoke() takes a list of messages (just like the raw SDK)
response = llm.invoke([HumanMessage(content="What is an AI agent? Answer in 3 sentences.")])

print("Claude says:")
print(response.content)
print()
print(f"Model      : {response.response_metadata.get('model')}")
print(f"Input tokens : {response.usage_metadata.get('input_tokens')}")
print(f"Output tokens: {response.usage_metadata.get('output_tokens')}")
