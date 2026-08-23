# Lesson 03 — Tool Use (Function Calling)

**Goal:** Define a tool, let Claude decide to call it, then handle the call.

**Concepts:**
- Defining tools with a JSON schema
- The `tool_use` stop reason
- Extracting tool name and input from the response
- Returning a `tool_result` back to Claude

**Run:**
```bash
python agent.py
```

**Key ideas:**
- You define tools — Claude decides *when* and *how* to call them
- When `stop_reason == "tool_use"`, Claude is waiting for your tool's result
- You must send the tool result back as a `tool` role message to continue
- This is the mechanism behind every agentic system
