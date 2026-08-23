# Loop 03 — Time-based

**Pattern:** Re-run a task on a fixed interval. The loop lives on your machine
(or in the cloud). No human prompt is needed after the first start.

**You control:** the interval, the task, when to stop.
**Claude controls:** how it handles each individual run.

**Run:**
```bash
python agent.py          # runs every 30 seconds, Ctrl+C to stop
python agent.py 60       # run every 60 seconds
```

**Key ideas:**
- Each "tick" is an independent call — no memory between runs (by default)
- Add a log file or database if you want runs to build on each other
- In production: replace `schedule` + `time.sleep` with a cron job, AWS EventBridge, GitHub Actions schedule, etc.
- This pattern maps to: monitoring, periodic reports, polling for changes
