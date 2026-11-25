---
description: Show everything still open - the tracker, task.md files, and (Full) inboxes and alarms - and run the upgrade check
allowed-tools: Bash
---

Run the status script with the user's arguments and answer from its output only (do not guess from memory):

1. `python ~/.claude/sbk/bin/status.py $ARGUMENTS`
   If that file does not exist (setup not finished, or the kit was only installed as a plugin), run `python "${CLAUDE_PLUGIN_ROOT}/entry/status.py" $ARGUMENTS` instead; if that variable is empty, find `entry/status.py` inside the second-brain-kit folder.
2. Show the user the open tracker items and each task.md's open count, in their language, short. Mark anything older than 14 days.
3. For each item older than 14 days, say what you suggest: do it now, or drop it (dropping needs the user's yes, then `ledger.py drop Lxxxx --evidence "..."`).
4. Run the upgrade check: `python ~/.claude/sbk/bin/level_check.py` (or `scripts/level_check.py` in the kit folder, found like step 1). It prints one JSON line `{"triggers": [...], "numbers": {...}}` and changes no settings. If `triggers` is not empty, end with ONE yes/no question in the user's language per the table in `docs/ADVANCED.md` ("When Claude suggests it"), quoting the numbers in plain words. Yes: follow that part's steps in ADVANCED.md. No: `python ~/.claude/sbk/bin/level_check.py --decline <trigger ids>` (not asked again for 28 days). Never switch a part on without a yes.

Arguments: `--all` lists every open task line, not just the first five per file.
