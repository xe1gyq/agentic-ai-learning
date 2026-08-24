# LangChain 01 — Basics

**Compare with:** `fundamentals/01_basics/agent.py`

LangChain wraps `anthropic.Anthropic()` into `ChatAnthropic`.
The mental model is the same — messages in, response out.

**Run:**
```bash
python agent.py
```

**What changed vs raw SDK:**
- `ChatAnthropic(model=..., api_key=...)` replaces `anthropic.Anthropic()` + `client.messages.create()`
- `HumanMessage(content=...)` replaces `{"role": "user", "content": ...}`
- `.invoke()` is the universal LangChain call — works the same on any LLM
