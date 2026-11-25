# Routes: who handles what

The entry session reads this table to decide which session gets a request.
A session is Claude started inside `managers/<name>/`; its `task.md` is its state and to-do list.
The Full plan always has the maintenance row (fixed) plus the user's own topics.
A request that fits no row: the entry opens a new topic itself (folder from the kit's
`templates/manager-CLAUDE.md`, one row here) and tells the user in one line. Renaming keywords is free.

| keywords | session | task.md | notes |
|---|---|---|---|
| rules, hooks, alarms, settings, update the kit, outside resources, weekly review | maintenance | managers/maintenance/task.md | fixed: the kit itself, rules, hooks, alarms, the outside resources table, the weekly learning loop |
| {{manager1_keywords}} | {{manager1}} | managers/{{manager1}}/task.md | {{manager1_notes}} |
| {{manager2_keywords}} | {{manager2}} | managers/{{manager2}}/task.md | {{manager2_notes}} |

## Rules
- Before routing, the entry processes the words: a one-sentence answer is answered directly and not tracked; a correction edits the old tracker line; several jobs become several lines; each line has a goal, a done-when and the owner session, with the user's words kept verbatim.
- A request that fits two rows: split it, one tracker item each; the entry chains them (the next starts with the previous one's checked result).
- Every handed-over request has a tracker item and an inbox line (`send.py`). Then the entry sends it into the running session (SendMessage) or starts the session (`session.py open`); at most `max_sessions` topic sessions run at once (config.json).
- Topic sessions report to the entry, never to the user: `ledger.py done` with evidence and a message to `entry`. The entry opens the evidence, marks it `verified`, and sends the user one result message.
- Without live routing (config.json `"routing": "inbox"`), the line waits in the inbox and the entry tells the user which session to open.
