# Lesson 04 — Agentic Loop

**Goal:** Run a loop where Claude can call tools multiple times until it's done.

**Concepts:**
- The core agentic loop: `call model → run tools → feed results → repeat`
- `stop_reason == "end_turn"` signals the agent is finished
- Handling multiple tool calls in a single response
- Why loops are the engine of autonomous agents

**Run:**
```bash
python agent.py
```

**Key ideas:**
- Real agents rarely stop after one tool call — they chain calls to complete complex tasks
- The loop continues as long as `stop_reason == "tool_use"`
- When `stop_reason == "end_turn"`, Claude has finished reasoning and gives a final answer
- This pattern is described in Albada Ch. 3-4 as the "observe-think-act" cycle
