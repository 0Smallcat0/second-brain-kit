---
description: Show everything still open - ledger items, every topic session's task.md, unread inboxes, alarms
allowed-tools: Bash
---

Run the status script and answer from its output only (do not guess from memory):

1. `python ~/.claude/sbk/bin/status.py`
   If that file does not exist (setup not finished, or the kit was only installed as a plugin), run `python "${CLAUDE_PLUGIN_ROOT}/entry/status.py"` instead; if that variable is empty, find `entry/status.py` inside the second-brain-kit folder.
2. Show the user the open ledger items and each task.md's open count, in their language, short. Mark anything older than 14 days.
3. For each item older than 14 days, say what you suggest: do it, hand it to a manager, or drop it (dropping needs the user's yes, then `ledger.py drop Lxxxx --evidence "..."`).

Arguments: $ARGUMENTS (pass `--all` to list every open task line).
