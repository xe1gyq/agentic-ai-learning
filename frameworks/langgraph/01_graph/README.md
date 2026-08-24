# LangGraph 01 — StateGraph Basics

**What this introduces:** The core LangGraph mental model — State, Nodes, Edges.

**Run:**
```bash
python agent.py
```

**Key concepts:**

| Concept | What it is |
|---------|------------|
| `AgentState` | A typed dict that flows through every node |
| Node | A function: `state → updates` |
| Edge | A connection: "after node A, go to node B" |
| `START` / `END` | Built-in entry and exit points |

**The pattern:**
```
START → research_node → summary_node → END
```

**Why LangGraph vs LangChain chains?**
- Chains are linear: A → B → C
- Graphs can branch, loop, and have conditional paths
- This is what makes LangGraph suitable for real agents
