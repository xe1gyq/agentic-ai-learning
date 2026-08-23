# Lesson 05 — Full Research Agent

**Goal:** A complete research agent that searches the real web and produces a report.

**Concepts:**
- Real tool implementation (DuckDuckGo search, no API key needed)
- System prompt engineering for agent behavior
- Putting everything together: loop + tools + system prompt

**Run:**
```bash
python agent.py "What is quantum computing?"
python agent.py "How do large language models work?"
```

**Files:**
- `tools.py` — Tool implementations (search, fetch page)
- `agent.py` — The agent loop with system prompt

**Key ideas:**
- The system prompt shapes *how* the agent behaves, not just *what* it can do
- Separating tool implementations from the agent loop makes code cleaner and reusable
- This is a working, real-world agentic system — the same pattern used in production

**What to explore next:**
- Add more tools: calculator, file writer, code executor
- Add memory: summarize old turns to stay within context limits
- Add multiple agents: one plans, one searches, one writes (multi-agent architecture)
