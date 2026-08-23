# Agentic AI Learning

Learn agentic AI step by step using the Claude API and Python.

Each numbered folder is a lesson. Follow them in order — each commit in this repo's history corresponds to one lesson being added.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env
```

## Fundamentals

| Lesson | Topic | What You Learn |
|--------|-------|----------------|
| 01_basics | Single API call | Request/response cycle |
| 02_conversation | Multi-turn chat | Message history and context |
| 03_tools | Tool use | How the model requests function calls |
| 04_tool_loop | Agentic loop | The core loop that drives agents |
| 05_research_agent | Full research agent | Planning, searching, synthesizing |

## Loop Patterns (`loops/`)

Based on Anthropic's "Startup Builds: Getting Started with Loops" (Mark Nowicki).

| Pattern | Folder | When to use |
|---------|--------|-------------|
| Turn-based | `loops/01_turn_based` | You prompt once; agent runs until it judges done |
| Goal-based | `loops/02_goal_based` | Loop until a condition is met or turn cap hit |
| Time-based | `loops/03_time_based` | Re-run on a fixed interval (cron-style) |
| Proactive | `loops/04_proactive` | Triggered by an event with no one at the keyboard |

## Reference

- [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python)
- [Claude API Docs](https://docs.anthropic.com)
- Book: *Building Applications with AI Agents* — Michael Albada
- Webinar: *Startup Builds: Getting Started with Loops* — Mark Nowicki, Anthropic
