# Loop Patterns

The four loop patterns from Anthropic's "Startup Builds: Getting Started with Loops"
(Mark Nowicki, Applied AI team).

## When to use each pattern

| Pattern | Trigger | Stops when | Human at keyboard? |
|---------|---------|------------|-------------------|
| Turn-based | You send a prompt | Claude says it's done | Yes |
| Goal-based | You send a prompt + goal | Goal met OR turn cap hit | Yes |
| Time-based | Timer fires | You stop it (Ctrl+C) | Optional |
| Proactive | External event (file, webhook) | You stop it | No |

## Run order

```
01_turn_based/  → simplest — just prompt and watch it run
02_goal_based/  → add a success condition and a safety cap
03_time_based/  → detach from the keyboard, run on a schedule
04_proactive/   → fully autonomous, event-driven
```
