# Loop 04 — Proactive

**Pattern:** The agent starts from an external event — no human at the keyboard.
Here it watches a directory for new `.txt` files and automatically responds to each one.

**You control:** what events trigger it, what the agent does.
**Claude controls:** the response to each event.

**Run:**
```bash
# Terminal 1 — start the agent
python agent.py

# Terminal 2 — trigger it by dropping a file
echo "What is the best way to learn Python?" > loops/04_proactive/watched/question1.txt
echo "Explain recursion simply." > loops/04_proactive/watched/question2.txt
```

**Key ideas:**
- The agent is always-on, waiting for triggers
- Real-world triggers: webhook arrives, Slack message sent, email received, database row inserted, S3 file uploaded
- This is the foundation of autonomous background agents
- Ctrl+C to stop
