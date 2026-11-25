# Routes: who handles what

The entry session reads this table to decide which topic session ("manager") gets a request.
A manager is Claude started inside `managers/<name>/`; its `task.md` is its to-do list.
Start with the two below. Add a row (and `managers/<name>/`) only when a topic keeps coming up
and one of the two is getting crowded; renaming keywords is free.

| keywords | manager | task.md | notes |
|---|---|---|---|
| {{manager1_keywords}} | {{manager1}} | managers/{{manager1}}/task.md | {{manager1_notes}} |
| {{manager2_keywords}} | {{manager2}} | managers/{{manager2}}/task.md | {{manager2_notes}} |

## Rules
- A request that fits no row: the entry answers it itself if it is quick, otherwise asks the user which manager.
- A request that fits two rows: split it, one ledger item each.
- Every handed-over request has a ledger item (`ledger.py add ... --to <manager>` or `send.py`). The entry closes it only after the manager shows evidence.
- Managers do not talk to each other; they report to the entry through the ledger.
