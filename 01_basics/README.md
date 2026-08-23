# Lesson 01 — Basics

**Goal:** Send a single message to Claude and print the response.

**Concepts:**
- Importing and configuring the Anthropic client
- The `messages.create()` call
- The `Message` response object and how to extract text

**Run:**
```bash
python agent.py
```

**Key ideas:**
- `model` — which Claude model to use
- `max_tokens` — maximum length of the response
- `messages` — a list of `{"role": ..., "content": ...}` dicts
- `message.content[0].text` — where the response text lives
