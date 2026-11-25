#!/usr/bin/env python3
"""The tracker (ledger.md): one line per thing the user asked for, so nothing gets lost between sessions.

    ledger.py add "text" [--to MANAGER]        new item (open, or dispatched if --to)
    ledger.py list [--all]                     open and dispatched items (--all adds closed)
    ledger.py dispatch L0003 MANAGER           hand an open item to a topic session
    ledger.py done L0003 --evidence "..."      close it; evidence = what you looked at (6+ chars)
    ledger.py drop L0003 --evidence "reason"   close it without doing it (the user decided)

File: <SBK_HOME>/ledger.md   (override with SBK_LEDGER). One line per item:
    - L0003 | dispatched:study | 2000-01-31T09:00:00 | text | ev: evidence
Closing needs evidence on purpose: "done" without something to point at is the usual lie.
"""
import os
import re
import sys
import time
from pathlib import Path

LINE = re.compile(r"^- (L\d{4}) \| ([^|]+?) \| ([^|]+?) \| (.*?) \| ev: (.*)$")
LAZY = {"done", "ok", "okay", "fine", "yes", "完成", "做完", "好了", "沒問題", "n/a", "none", "-"}
HEADER = ("# Ledger\n\nOne line per request. Statuses: open, dispatched:<manager>, done, dropped.\n"
          "Close with `ledger.py done Lxxxx --evidence \"...\"`.\n\n")


def path():
    env = os.environ.get("SBK_LEDGER")
    if env:
        return Path(env)
    base = os.environ.get("SBK_HOME")
    return (Path(base) if base else Path.home() / ".claude" / "sbk") / "ledger.md"


def load():
    p = path()
    head, items = [], []
    if p.exists():
        for raw in p.read_text(encoding="utf-8").splitlines():
            m = LINE.match(raw)
            if m:
                items.append(list(m.groups()))
            elif not items:
                head.append(raw)
    return "\n".join(head).rstrip() + "\n\n" if head else HEADER, items


def save(head, items):
    p = path()
    p.parent.mkdir(parents=True, exist_ok=True)
    body = "".join("- %s | %s | %s | %s | ev: %s\n" % tuple(i) for i in items)
    tmp = p.with_suffix(".md.tmp")
    tmp.write_text(head + body, encoding="utf-8")
    os.replace(str(tmp), str(p))


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def find(items, lid):
    for i in items:
        if i[0] == lid.upper():
            return i
    sys.exit("no such item: " + lid)


def age_days(ts):
    try:
        return int((time.time() - time.mktime(time.strptime(ts, "%Y-%m-%dT%H:%M:%S"))) // 86400)
    except Exception:
        return 0


def clean(text):
    return text.replace("|", "/").replace("\n", " ").strip()


def cmd_add(args):
    to = None
    if "--to" in args:
        k = args.index("--to")
        to = args[k + 1]
        args = args[:k] + args[k + 2:]
    text = clean(" ".join(args))
    if not text:
        sys.exit("add: text is empty")
    head, items = load()
    nxt = max([int(i[0][1:]) for i in items] + [0]) + 1
    lid = "L%04d" % nxt
    items.append([lid, ("dispatched:" + to) if to else "open", now(), text, ""])
    save(head, items)
    print(lid)


def cmd_dispatch(args):
    if len(args) != 2:
        sys.exit("usage: dispatch Lxxxx MANAGER")
    head, items = load()
    it = find(items, args[0])
    if it[1] in ("done", "dropped"):
        sys.exit("already closed")
    it[1] = "dispatched:" + args[1]
    save(head, items)
    print(it[0], "->", args[1])


def cmd_close(status, args):
    if "--evidence" not in args:
        sys.exit("close needs --evidence \"what you looked at\"")
    k = args.index("--evidence")
    ev = clean(" ".join(args[k + 1:]))
    ids = args[:k]
    if len(ids) != 1:
        sys.exit("usage: %s Lxxxx --evidence \"...\"" % status)
    if len(ev) < 6 or ev.lower() in LAZY:
        sys.exit("evidence too thin: say what you opened, ran or read, and what you saw")
    head, items = load()
    it = find(items, ids[0])
    it[1], it[4] = status, ev
    save(head, items)
    print(it[0], status)


def cmd_list(args):
    _, items = load()
    show_all = "--all" in args
    n = 0
    for lid, st, ts, text, ev in items:
        closed = st in ("done", "dropped")
        if closed and not show_all:
            continue
        n += 1
        flag = "  [STALE %dd]" % age_days(ts) if not closed and age_days(ts) >= 14 else ""
        print("%s  %-18s %s  %s%s%s" % (lid, st, ts[:10], text, ("  (ev: %s)" % ev) if closed else "", flag))
    if n == 0:
        print("nothing open")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "add":
        cmd_add(args)
    elif cmd == "list":
        cmd_list(args)
    elif cmd == "dispatch":
        cmd_dispatch(args)
    elif cmd in ("done", "drop"):
        cmd_close("done" if cmd == "done" else "dropped", args)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
