# Agentic AI Learning

Learn agentic AI step by step using the Claude API and Python.

Each numbered folder is a lesson. Follow them in order — each commit in this repo's history corresponds to one lesson being added.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env
```

## Lessons

| Lesson | Topic | What You Learn |
|--------|-------|----------------|
| 01_basics | Single API call | Request/response cycle |
| 02_conversation | Multi-turn chat | Message history and context |
| 03_tools | Tool use | How the model requests function calls |
| 04_tool_loop | Agentic loop | The core loop that drives agents |
| 05_research_agent | Full research agent | Planning, searching, synthesizing |

## Reference

- [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python)
- [Claude API Docs](https://docs.anthropic.com)
- Book: *Building Applications with AI Agents* — Michael Albada
