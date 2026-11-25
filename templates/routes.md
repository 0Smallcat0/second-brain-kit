# Routes: who handles what

The entry session reads this table to decide which session gets a request.
A session is Claude started inside `managers/<name>/`; its `task.md` is its to-do list.
The Full plan always has the first two rows (fixed sessions) plus the user's own topics.
Add a topic row (and `managers/<name>/`) only when a subject keeps coming up and an existing
topic is getting crowded; renaming keywords is free.

| keywords | session | task.md | notes |
|---|---|---|---|
| check, missed, really done?, review the week | supervisor | managers/supervisor/task.md | fixed: checks the entry and every topic for missed items and "done" claims that do not hold |
| rules, hooks, alarms, settings, update the kit, AI tools | maintenance | managers/maintenance/task.md | fixed: the kit itself, rules, hooks, alarms, the AI tool table |
| {{manager1_keywords}} | {{manager1}} | managers/{{manager1}}/task.md | {{manager1_notes}} |
| {{manager2_keywords}} | {{manager2}} | managers/{{manager2}}/task.md | {{manager2_notes}} |

## Rules
- A request that fits no row: the entry answers it itself if it is quick, otherwise asks the user which topic.
- A request that fits two rows: split it, one tracker item each.
- Every handed-over request has a tracker item (`ledger.py add ... --to <session>` or `send.py`). The entry closes it only after the session shows evidence.
- Sessions do not talk to each other; they report to the entry through the tracker (ledger.md). The supervisor reads the tracker and every task.md, opens the evidence, and sends back what does not hold.
- A session starts working when the user opens it, or when the scheduler wakes it (only if auto-wake is on for it in config.json "wake").
