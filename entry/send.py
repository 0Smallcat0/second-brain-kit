#!/usr/bin/env python3
"""Hand a piece of work to a topic session (a "manager") through its inbox.

    send.py MANAGER "text"            put the text in the manager's inbox and in the ledger
    send.py MANAGER "text" --ledger L0003   same, but for an existing ledger item (no new item)

The manager is Claude started inside <SBK_HOME>/managers/<MANAGER>/ ; its SessionStart and
prompt hooks (hooks/inbox_notice.py) show the unticked inbox lines, so the work cannot be
missed even if the session was closed when it was sent. Identical unticked lines are not
added twice. Pushing text into an already running session is not supported here (see
experimental/README.md).
"""
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ledger  # noqa: E402


def home():
    env = os.environ.get("SBK_HOME")
    return Path(env) if env else Path.home() / ".claude" / "sbk"


def deliver(manager, text, lid):
    inbox = home() / "inbox" / (manager + ".md")
    inbox.parent.mkdir(parents=True, exist_ok=True)
    line = "- [ ] %s | %s | %s" % (lid, time.strftime("%Y-%m-%dT%H:%M"), ledger.clean(text))
    existing = inbox.read_text(encoding="utf-8") if inbox.exists() else "# Inbox for %s\n\n" % manager
    body = [l.split("|", 2)[-1].strip() for l in existing.splitlines() if l.startswith("- [ ]")]
    if ledger.clean(text) in body:
        return False
    inbox.write_text(existing.rstrip("\n") + "\n" + line + "\n", encoding="utf-8")
    return True


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    args = sys.argv[1:]
    lid = None
    if "--ledger" in args:
        k = args.index("--ledger")
        lid = args[k + 1].upper()
        args = args[:k] + args[k + 2:]
    if len(args) < 2:
        sys.exit(__doc__)
    manager, text = args[0], " ".join(args[1:])
    if not (home() / "managers" / manager).is_dir():
        sys.exit("no manager folder: %s (create it from templates first)" % (home() / "managers" / manager))
    head, items = ledger.load()
    if lid is None:
        lid = "L%04d" % (max([int(i[0][1:]) for i in items] + [0]) + 1)
        items.append([lid, "dispatched:" + manager, ledger.now(), ledger.clean(text), ""])
        ledger.save(head, items)
    else:
        ledger.find(items, lid)[1] = "dispatched:" + manager
        ledger.save(head, items)
    added = deliver(manager, text, lid)
    print("%s -> %s%s" % (lid, manager, "" if added else " (already in the inbox)"))


if __name__ == "__main__":
    main()
