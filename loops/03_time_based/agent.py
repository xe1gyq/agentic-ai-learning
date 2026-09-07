"""
Loop Pattern 03 — Time-based
==============================
Re-run a task on a fixed interval. Uses the `schedule` library
for readability, with plain time.sleep underneath.

Task: Every N seconds, ask Claude for a short "tech tip of the moment".
Each run is independent. Ctrl+C to stop.

Usage:
  python agent.py          # every 30 seconds
  python agent.py 10       # every 10 seconds
"""

import os
import sys
import time
from datetime import datetime

import anthropic
import schedule
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

run_count = 0


def run_agent_task():
    """One scheduled execution of the agent task."""
    global run_count
    run_count += 1
    timestamp = datetime.now().strftime("%H:%M:%S")

    print(f"\n{'=' * 50}")
    print(f"[{timestamp}] Run #{run_count}")
    print("=" * 50)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=150,
        messages=[
            {
                "role": "user",
                "content": (
                    "Give me ONE practical tip for writing better Python code. "
                    "Be specific and keep it under 3 sentences. "
                    f"Make it different from previous tips (run #{run_count})."
                ),
            }
        ],
    )

    print(response.content[0].text)


# ---------------------------------------------------------------
# TIME-BASED LOOP
# ---------------------------------------------------------------
interval = int(sys.argv[1]) if len(sys.argv) > 1 else 30

print(f"Time-based agent starting. Running every {interval} seconds.")
print("Press Ctrl+C to stop.\n")

# Run once immediately, then on the schedule
run_agent_task()
schedule.every(interval).seconds.do(run_agent_task)

try:
    while True:
        schedule.run_pending()
        time.sleep(1)
except KeyboardInterrupt:
    print(f"\nStopped after {run_count} run(s).")
