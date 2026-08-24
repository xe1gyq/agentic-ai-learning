# Fundamentals

Build an agent from the API boundary outward. Every lesson adds one responsibility while
keeping the previous mechanisms visible.

| Lesson | Boundary introduced | Core question |
|--------|---------------------|---------------|
| `01_basics` | Model | How does the application call the LLM? |
| `02_conversation` | History | What prior turns can the model see? |
| `03_tools` | Environment | How does the model request an action? |
| `04_tool_loop` | Execution | How do observations feed the next action? |
| `05_research_agent` | Application | How do prompt, loop, and real tools combine? |
| `06_structured_outputs` | Output contract | Can deterministic code consume the result safely? |
| `07_context_engineering` | Attention | Which information earns space in the next call? |
| `08_state_and_memory` | Time | What lives for one step, one run, or many runs? |

## System mental model

```text
Model capability
    + instructions
    + selected context
    + tools/environment
    + execution loop
    + state and memory
    = agentic system
```

The model supplies probabilistic reasoning. The surrounding application owns contracts,
context policy, storage, permissions, verification, and stop conditions.

## Why the order matters

Lessons 01–05 create capability. Lessons 06–08 introduce boundaries around that capability:

- a **schema boundary** for downstream consumers;
- an **attention boundary** for finite context;
- a **time boundary** between ephemeral state and durable memory.

The next stage adds executive control: evidence-based verification, budgets, replanning,
human approval, and durable execution.

