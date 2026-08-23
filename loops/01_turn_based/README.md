# Loop 01 — Turn-based

**Pattern:** You send one prompt. Claude runs — calling tools, thinking, retrying —
until it judges the task complete and returns `stop_reason == "end_turn"`.

**You control:** the initial prompt.
**Claude controls:** how many steps it takes.

**Run:**
```bash
python agent.py
```

**Key ideas:**
- The loop runs entirely inside one "turn" from your perspective
- Claude decides when it's done — you don't count steps
- This is the default pattern for most agentic tasks
- Risk: no budget means it could run a long time; add `max_tokens` and `max_turns` as guards
