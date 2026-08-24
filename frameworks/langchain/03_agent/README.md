# LangChain 03 — Tool-calling Agent

**Compare with:** `fundamentals/04_tool_loop/agent.py`

LangChain's `AgentExecutor` runs the tool loop for you.
Set `verbose=True` to see exactly what it's doing — compare with the
manual loop you wrote in lesson 04.

**Run:**
```bash
python agent.py
```

**What LangChain hides (vs raw SDK):**
- The `while True` loop
- Parsing `tool_use` content blocks
- Building `tool_result` messages
- Appending to message history

**What you gain:**
- `@tool` decorator auto-generates the JSON schema from docstrings + type hints
- `AgentExecutor` handles retries, errors, and max iterations
- Swap `ChatAnthropic` for `ChatOpenAI` and everything else stays the same
