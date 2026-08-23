# Lesson 02 — Multi-turn Conversation

**Goal:** Build a CLI chat loop that maintains conversation history.

**Concepts:**
- The `messages` list as the agent's short-term memory
- Appending both user and assistant turns to maintain context
- Why order matters: alternating user/assistant roles

**Run:**
```bash
python agent.py
```
Type `quit` or `exit` to stop.

**Key ideas:**
- Each turn: append user message → call API → append assistant response
- Claude has no persistent memory — you must send the full history every time
- This is the foundation of all conversational agents
