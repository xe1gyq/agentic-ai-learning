# LangGraph 03 — Conditional Routing

**What this introduces:** Branching — the graph takes different paths at runtime
based on the agent's output.

**Run:**
```bash
python agent.py
```

**Graph structure:**
```
START → triage ──[math]────→ math_node    → END
               ├─[science]──→ science_node → END
               └─[general]──→ general_node → END
```

**Key concept — `add_conditional_edges`:**
```python
graph.add_conditional_edges(
    "triage",           # from this node
    route_question,     # call this function to decide
    {"math": "math", ...}  # map return values to node names
)
```

**Why this matters:**
- This is how real agentic systems work — dynamic routing, not fixed pipelines
- Enables: customer support routing, multi-expert agents, code review pipelines
- Combine with loops (lesson 02) for full control over agent behavior
