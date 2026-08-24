# LangChain 02 — Chains (LCEL)

**What this introduces:** LangChain Expression Language (LCEL) — composing
prompts, models, and parsers with the `|` pipe operator.

**Run:**
```bash
python agent.py
```

**Key ideas:**
- `ChatPromptTemplate` — reusable prompt with `{placeholders}`
- `chain = prompt | llm | StrOutputParser()` — the LCEL pipe syntax
- `.invoke({"key": "value"})` — fills placeholders and runs the chain
- `.stream(...)` — streams tokens as they arrive
- Same chain, different inputs — this is why templates matter at scale
