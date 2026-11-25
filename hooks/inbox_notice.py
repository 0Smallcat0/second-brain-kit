#!/usr/bin/env python3
"""SessionStart + UserPromptSubmit hook: show a topic session what the entry sent it.

A manager session is simply Claude started inside <SBK_HOME>/managers/<name>/. This hook
notices that folder, and tells Claude (a) the unticked lines in <SBK_HOME>/inbox/<name>.md
and (b) how many open items its task.md has. In the entry folder it shows the ledger
summary instead. At SessionStart it always shows; on later prompts only when something new
arrived. Nothing is blocked. Off by default (Basic has no topic sessions); Advanced turns it on
with config.json "modes": {"inbox_notice": "warn"}.
"""
import hashlib
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import add_context, home, log, mode, read_input  # noqa: E402

OPEN = re.compile(r"^\s*- \[ \]")


def open_lines(path, limit=10):
    try:
        lines = [l.rstrip() for l in path.read_text(encoding="utf-8").splitlines() if OPEN.match(l)]
    except Exception:
        return []
    return lines[:limit] if limit else lines


def which(cwd):
    root = home().resolve()
    try:
        rel = Path(cwd).resolve().relative_to(root)
    except Exception:
        return None, None
    parts = rel.parts
    if len(parts) >= 2 and parts[0] == "managers":
        return "manager", parts[1]
    if parts and parts[0] == "entry":
        return "entry", "entry"
    return None, None


def main():
    if mode("inbox_notice", "off") == "off":
        return
    data = read_input()
    role, name = which(data.get("cwd") or os.getcwd())
    if not role:
        return
    event = data.get("hook_event_name") or "SessionStart"
    parts = []
    if role == "manager":
        inbox = open_lines(home() / "inbox" / (name + ".md"))
        tasks = open_lines(home() / "managers" / name / "task.md", limit=0)
        if inbox:
            parts.append("Inbox from the entry (%d new). Move each into task.md, then tick it "
                         "in the inbox file:\n%s" % (len(inbox), "\n".join(inbox)))
        parts.append("task.md has %d open items." % len(tasks))
    else:
        ledger = home() / "ledger.md"
        n = 0
        try:
            n = sum(1 for l in ledger.read_text(encoding="utf-8").splitlines()
                    if re.match(r"^- L\d+ \| (open|dispatched)", l))
        except Exception:
            pass
        parts.append("Ledger: %d items not closed. Run ledger.py list, route each to a manager, "
                     "and close only with evidence." % n)
    text = "\n".join(parts)
    sig = hashlib.md5(text.encode("utf-8")).hexdigest()
    state = home() / "state" / ("inbox_" + role + "_" + str(name) + ".txt")
    if event != "SessionStart":
        try:
            if state.read_text(encoding="utf-8") == sig:
                return
        except Exception:
            pass
    try:
        state.parent.mkdir(parents=True, exist_ok=True)
        state.write_text(sig, encoding="utf-8")
    except Exception:
        pass
    add_context(event if event in ("SessionStart", "UserPromptSubmit") else "SessionStart", text)
    log("inbox_notice", "%s/%s injected" % (role, name))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log("inbox_notice", "error: %r" % (e,))
    sys.exit(0)
