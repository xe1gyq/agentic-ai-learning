"""
Loop Pattern 02 — Goal-based
==============================
Loop until YOUR code detects the goal is met, or a turn cap stops it.

The goal condition is external to Claude — you define it.
The turn cap is your budget — a safety net against infinite loops.

Task: Ask Claude to write a short product description that must include
the words: "reliable", "fast", and "affordable". Keep asking it to
improve until all three words appear, or we hit MAX_TURNS.
"""

import os
from dotenv import load_dotenv
import anthropic

load_dotenv()

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# ---------------------------------------------------------------
# GOAL DEFINITION — you write this, not Claude
# ---------------------------------------------------------------
REQUIRED_KEYWORDS = ["reliable", "fast", "affordable"]

def goal_met(text: str) -> bool:
    """Return True when all required keywords appear in the output."""
    text_lower = text.lower()
    missing = [kw for kw in REQUIRED_KEYWORDS if kw not in text_lower]
    if missing:
        print(f"  [goal check] missing keywords: {missing}")
        return False
    print("  [goal check] all keywords present — goal met!")
    return True


# ---------------------------------------------------------------
# TURN CAP — your safety net
# ---------------------------------------------------------------
MAX_TURNS = 6

# ---------------------------------------------------------------
# GOAL-BASED LOOP
# ---------------------------------------------------------------
TASK = (
    "Write a 2-sentence product description for a cloud storage service. "
    f"It MUST include all of these words: {', '.join(REQUIRED_KEYWORDS)}."
)

print("=" * 55)
print("GOAL-BASED LOOP")
print("=" * 55)
print(f"Goal keywords: {REQUIRED_KEYWORDS}")
print(f"Turn cap: {MAX_TURNS}")
print(f"Task: {TASK}\n")

messages = [{"role": "user", "content": TASK}]

for turn in range(1, MAX_TURNS + 1):
    print(f"\n--- Turn {turn}/{MAX_TURNS} ---")

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=messages,
    )

    output = response.content[0].text
    print(f"Claude: {output}")

    messages.append({"role": "assistant", "content": output})

    # Check the goal — YOUR code decides if we're done
    if goal_met(output):
        print(f"\nSuccess in {turn} turn(s)!")
        break

    if turn < MAX_TURNS:
        # Give Claude feedback and ask it to try again
        feedback = (
            f"Good try, but the description is missing some required words. "
            f"Revise it to include ALL of: {', '.join(REQUIRED_KEYWORDS)}."
        )
        messages.append({"role": "user", "content": feedback})
else:
    print(f"\nTurn cap reached ({MAX_TURNS} turns). Goal was not met.")
    print("In production: escalate, alert, or fall back to a default.")
