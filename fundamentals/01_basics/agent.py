"""
Lesson 01 - Basics
==================
The simplest possible interaction with the Claude API.
Send one message, get one response.
"""

import os

import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

message = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "What is an AI agent? Answer in 3 sentences."}
    ],
)

print("Claude says:")
print(message.content[0].text)
print()
print(f"Stop reason : {message.stop_reason}")
print(f"Input tokens: {message.usage.input_tokens}")
print(f"Output tokens: {message.usage.output_tokens}")
