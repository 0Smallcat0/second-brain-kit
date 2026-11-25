---
description: Show everything still open - the work list, task.md files, and (Advanced) inboxes and alarms
allowed-tools: Bash
---

Run the status script with the user's arguments and answer from its output only (do not guess from memory):

1. `python ~/.claude/sbk/bin/status.py $ARGUMENTS`
   If that file does not exist (setup not finished, or the kit was only installed as a plugin), run `python "${CLAUDE_PLUGIN_ROOT}/entry/status.py" $ARGUMENTS` instead; if that variable is empty, find `entry/status.py` inside the second-brain-kit folder.
2. Show the user the open work-list items and each task.md's open count, in their language, short. Mark anything older than 14 days.
3. For each item older than 14 days, say what you suggest: do it now, or drop it (dropping needs the user's yes, then `ledger.py drop Lxxxx --evidence "..."`).

Arguments: `--all` lists every open task line, not just the first five per file.
