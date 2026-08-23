# Loop 02 — Goal-based

**Pattern:** Loop until a measurable goal is met — or a turn cap stops it.
You define both what "done" looks like AND a maximum number of attempts.

**You control:** the goal condition + the turn cap (budget).
**Claude controls:** how it gets there.

**Run:**
```bash
python agent.py
```

**Key ideas:**
- The goal is checked *by your code* after each Claude response, not by Claude
- The turn cap is your safety net — prevents infinite loops
- Define "done" as something you can test in code: keyword present, file exists, test passes, score above threshold
- This pattern maps to: "keep refining until good enough"
