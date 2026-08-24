# Frameworks

The same agentic patterns from `fundamentals/` and `loops/`, rebuilt using
popular frameworks. Compare them side by side to understand what each
framework adds (and hides).

## LangChain (`langchain/`)

LangChain wraps the raw API with higher-level abstractions:
- `ChatAnthropic` instead of `anthropic.Anthropic()`
- `ChatPromptTemplate` for reusable prompts
- `AgentExecutor` handles the tool loop for you

| Example | What it shows |
|---------|---------------|
| 01_basics | ChatAnthropic vs raw SDK |
| 02_chain | Prompt templates + LCEL chains |
| 03_agent | Tool-calling agent with AgentExecutor |

## LangGraph (`langgraph/`)

LangGraph is a lower-level graph framework for building stateful, multi-step agents.
It gives you explicit control over the loop — unlike LangChain's AgentExecutor.

| Example | What it shows |
|---------|---------------|
| 01_graph | StateGraph: nodes, edges, state |
| 02_react_agent | ReAct agent — the graph equivalent of the agentic loop |
| 03_conditional | Conditional edges — routing based on agent output |

## When to use what

| | Raw Claude API | LangChain | LangGraph |
|---|---|---|---|
| Learning | Best | OK | OK |
| Simple agents | Great | OK | Overkill |
| Complex multi-step | Verbose | OK | Great |
| Multi-agent systems | Manual | OK | Great |
| Fine-grained control | Full | Limited | Full |
