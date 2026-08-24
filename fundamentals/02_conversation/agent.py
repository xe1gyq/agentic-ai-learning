"""
Lesson 02 - Multi-turn Conversation
=====================================
Maintain a message history across turns so Claude remembers
what was said earlier in the conversation.
"""

import os
from dotenv import load_dotenv
import anthropic

load_dotenv()

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# The messages list is the agent's memory.
# We grow it with each turn so Claude sees the full history.
messages = []

SYSTEM = "You are a helpful AI assistant. Be concise."

print("Chat with Claude (type 'quit' to exit)")
print("-" * 40)

while True:
    user_input = input("You: ").strip()
    if user_input.lower() in ("quit", "exit"):
        print("Goodbye!")
        break
    if not user_input:
        continue

    # 1. Add the user's message to history
    messages.append({"role": "user", "content": user_input})

    # 2. Send the full history to Claude
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM,
        messages=messages,
    )

    assistant_text = response.content[0].text

    # 3. Add Claude's reply to history so next turn has context
    messages.append({"role": "assistant", "content": assistant_text})

    print(f"Claude: {assistant_text}")
    print()
