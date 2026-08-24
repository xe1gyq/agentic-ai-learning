# Agentic AI Learning

Learn agentic AI step by step using the Claude API and Python.

Each numbered folder is a lesson. Follow them in order — each commit in this repo's history corresponds to one lesson being added.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env
```

## Fundamentals (`fundamentals/`)

| Lesson | Topic | What You Learn |
|--------|-------|----------------|
| fundamentals/01_basics | Single API call | Request/response cycle |
| fundamentals/02_conversation | Multi-turn chat | Message history and context |
| fundamentals/03_tools | Tool use | How the model requests function calls |
| fundamentals/04_tool_loop | Agentic loop | The core loop that drives agents |
| fundamentals/05_research_agent | Full research agent | Planning, searching, synthesizing |
| fundamentals/06_structured_outputs | Output contracts | Schema-valid JSON and downstream validation |
| fundamentals/07_context_engineering | Context selection | Relevance, provenance, budgets, and token counting |
| fundamentals/08_state_and_memory | State and memory | Ephemeral run state vs. durable, retrieved memory |

The model supplies probabilistic reasoning. The surrounding application owns contracts,
context policy, storage, permissions, verification, and stop conditions. See the
[`fundamentals/` learning map](fundamentals/README.md) for how these responsibilities fit
together.

## Loop Patterns (`loops/`)

Based on Anthropic's "Startup Builds: Getting Started with Loops" (Mark Nowicki).

| Pattern | Folder | When to use |
|---------|--------|-------------|
| Turn-based | `loops/01_turn_based` | You prompt once; agent runs until it judges done |
| Goal-based | `loops/02_goal_based` | Loop until a condition is met or turn cap hit |
| Time-based | `loops/03_time_based` | Re-run on a fixed interval (cron-style) |
| Proactive | `loops/04_proactive` | Triggered by an event with no one at the keyboard |

## Frameworks (`frameworks/`)

Same patterns rebuilt with LangChain and LangGraph. Compare side by side.

**LangChain** — higher-level abstractions, hides the loop:

| Example | What it shows |
|---------|---------------|
| `frameworks/langchain/01_basics` | ChatAnthropic vs raw SDK |
| `frameworks/langchain/02_chain` | Prompt templates + LCEL pipe syntax |
| `frameworks/langchain/03_agent` | AgentExecutor handles the tool loop |

**LangGraph** — explicit graph structure, full control:

| Example | What it shows |
|---------|---------------|
| `frameworks/langgraph/01_graph` | StateGraph: nodes, edges, shared state |
| `frameworks/langgraph/02_react_agent` | ReAct loop as a visible graph |
| `frameworks/langgraph/03_conditional` | Conditional routing between specialist nodes |

## Reference

- [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python)
- [Claude API Docs](https://docs.anthropic.com)
- [LangChain Docs](https://python.langchain.com)
- [LangGraph Docs](https://langchain-ai.github.io/langgraph/)
- Book: *Building Applications with AI Agents* — Michael Albada
- Webinar: *Startup Builds: Getting Started with Loops* — Mark Nowicki, Anthropic

