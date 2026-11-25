#!/usr/bin/env python3
"""One screen of everything still open: the work list (ledger), task.md files, unread inboxes, alarms.

    status.py [--all]     (--all also lists every open task line, not just the first 5 per file)

Reads <SBK_HOME> (default ~/.claude/sbk): <SBK_HOME>/task.md (Basic: one large job), entry/ and
managers/*/task.md (Advanced). Extra task.md files can be listed in
<SBK_HOME>/config.json as  {"task_files": ["/path/to/task.md"]}.
"""
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ledger  # noqa: E402
import send  # noqa: E402

OPEN = re.compile(r"^\s*- \[ \] ?(.*)$")


def open_lines(p):
    try:
        return [m.group(1) for m in (OPEN.match(l) for l in p.read_text(encoding="utf-8").splitlines()) if m]
    except Exception:
        return None


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    show_all = "--all" in sys.argv
    home = send.home()
    print("== Ledger ==")
    _, items = ledger.load()
    live = [i for i in items if i[1] not in ("done", "dropped")]
    if not live:
        print("  nothing open")
    for lid, st, ts, text, _ in live:
        old = ledger.age_days(ts)
        print("  %s %-16s %s%s" % (lid, st, text[:90], "  [%dd old]" % old if old >= 14 else ""))

    files = sorted((home / "managers").glob("*/task.md")) if (home / "managers").is_dir() else []
    try:
        extra = json.loads((home / "config.json").read_text(encoding="utf-8")).get("task_files", [])
        files += [Path(x) for x in extra]
    except Exception:
        pass
    if (home / "entry" / "task.md").exists():
        files.insert(0, home / "entry" / "task.md")
    if (home / "task.md").exists():  # Basic: the one large job, if there is one
        files.insert(0, home / "task.md")
    print("\n== task.md files ==")
    if not files:
        print("  none found")
    for f in files:
        lines = open_lines(f)
        name = "main" if f.parent == home else f.parent.name
        if lines is None:
            print("  %s: cannot read %s" % (name, f))
            continue
        print("  %s: %d open  (%s)" % (name, len(lines), f))
        for l in lines if show_all else lines[:5]:
            print("     - " + l[:100])

    print("\n== Inboxes (sent, not yet ticked) ==")
    inbox = home / "inbox"
    any_in = False
    if inbox.is_dir():
        for f in sorted(inbox.glob("*.md")):
            n = open_lines(f) or []
            if n:
                any_in = True
                print("  %s: %d" % (f.stem, len(n)))
    if not any_in:
        print("  empty")

    alarms = home / "alarms.md"
    n = 0
    if alarms.exists():
        n = sum(1 for l in alarms.read_text(encoding="utf-8").splitlines() if re.match(r"^\|\s*[A-Za-z]\d+\s*\|", l))
    print("\n== Alarms: %d rows ==" % n)


if __name__ == "__main__":
    main()
