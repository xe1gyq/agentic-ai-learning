# LangGraph 02 — ReAct Agent

**Compare with:** `fundamentals/04_tool_loop/agent.py`

The agentic loop rebuilt as an explicit graph. The cycle is visible:
`agent → tools → agent → tools → ... → END`

**Run:**
```bash
python agent.py
```

**Key LangGraph prebuilts used:**

| Prebuilt | What it does |
|----------|--------------|
| `ToolNode` | Runs all tool calls from the last message |
| `tools_condition` | Routes to "tools" if tool calls exist, else END |

**Graph structure:**
```
START → agent ──[has tool calls]──→ tools → agent (loop)
              └─[no tool calls]───→ END
```

**Why explicit graphs matter:**
- You can visualize the loop: `graph.get_graph().draw_mermaid()`
- You can interrupt it at any node (lesson 03)
- You can add new nodes (memory, critique, planning) without rewriting the loop
