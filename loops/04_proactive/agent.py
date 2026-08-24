"""
Loop Pattern 04 — Proactive (Event-driven)
===========================================
The agent waits for external events and responds autonomously.
No human at the keyboard after the initial start.

Trigger: a new .txt file appears in the `watched/` directory.
Response: Claude reads the file and writes a response to `watched/<name>.response.txt`.

This simulates real-world triggers:
  - A webhook fires (HTTP request arrives)
  - A Slack message is posted
  - A file is uploaded to S3
  - A database row is inserted

Usage:
  python agent.py
  # Then in another terminal:
  echo "What is machine learning?" > watched/my_question.txt
"""

import os
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import anthropic
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

load_dotenv()

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

WATCH_DIR = Path(__file__).parent / "watched"
WATCH_DIR.mkdir(exist_ok=True)


def handle_event(file_path: Path):
    """Called when a new .txt file appears. Claude reads and responds."""
    # Ignore response files we wrote ourselves
    if file_path.suffix != ".txt" or file_path.name.endswith(".response.txt"):
        return

    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"\n[{timestamp}] New file detected: {file_path.name}")

    try:
        question = file_path.read_text().strip()
    except Exception as e:
        print(f"  Error reading file: {e}")
        return

    if not question:
        return

    print(f"  Content: {question[:80]}{'...' if len(question) > 80 else ''}")
    print("  Calling Claude...")

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system="You are a helpful assistant. Answer questions clearly and concisely.",
        messages=[{"role": "user", "content": question}],
    )

    answer = response.content[0].text

    # Write response next to the trigger file
    response_path = file_path.with_suffix(".response.txt")
    response_path.write_text(answer)
    print(f"  Response written to: {response_path.name}")
    print(f"  Preview: {answer[:100]}...")


class NewFileHandler(FileSystemEventHandler):
    """watchdog event handler — fires on any filesystem event."""

    def on_created(self, event):
        if not event.is_directory:
            # Small delay to ensure the file is fully written before reading
            time.sleep(0.2)
            handle_event(Path(event.src_path))


# ---------------------------------------------------------------
# PROACTIVE LOOP — start and wait for events
# ---------------------------------------------------------------
print("=" * 55)
print("PROACTIVE AGENT — waiting for events")
print("=" * 55)
print(f"Watching: {WATCH_DIR}")
print("Drop a .txt file into the watched/ folder to trigger the agent.")
print("Press Ctrl+C to stop.\n")

observer = Observer()
observer.schedule(NewFileHandler(), str(WATCH_DIR), recursive=False)
observer.start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    observer.stop()
    print("\nAgent stopped.")

observer.join()
