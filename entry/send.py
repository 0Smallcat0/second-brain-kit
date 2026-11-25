#!/usr/bin/env python3
"""Write a piece of work into a topic session's inbox (and the tracker): the durable record.

    send.py SESSION "text"                   put the text in the session's inbox and in the tracker
    send.py SESSION "text" --ledger L0003    same, but for an existing tracker item (no new item)

A topic session is Claude started inside <SBK_HOME>/managers/<SESSION>/ ; its SessionStart and
prompt hooks (hooks/inbox_notice.py) show the unticked inbox lines, so the work cannot be
missed even if the session was not running when it was sent. Identical unticked lines are not
added twice. Getting the session to act on it now is the next step: the entry sends a short
message into the running session (its own SendMessage tool), or session.py starts the session
(session.py deliver does both). Without live routing the line waits until the user opens it.
"""
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ledger  # noqa: E402


def home():
    """Runtime folder: tracker (ledger.md), alarms, routes, inbox, logs. Override with SBK_HOME.
    Default ~/.sbk. Before 0.2.5 it was ~/.claude/sbk; that folder is still used while ~/.sbk does not
    exist. Claude Code does not let Claude's own file tools write inside a .claude folder without asking,
    so a background session there could not even write its task.md."""
    env = os.environ.get("SBK_HOME")
    if env:
        return Path(env)
    new, old = Path.home() / ".sbk", Path.home() / ".claude" / "sbk"
    return old if (not new.exists() and old.exists()) else new


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


def dispatch(manager, text, lid=None):
    """Tracker item (new, or the given one marked dispatched) + inbox line. Returns (lid, added)."""
    if not (home() / "managers" / manager).is_dir():
        sys.exit("no session folder: %s (create it from templates first)" % (home() / "managers" / manager))
    with ledger.locked():
        head, items = ledger.load()
        if lid is None:
            lid = "L%04d" % (max([int(i[0][1:]) for i in items] + [0]) + 1)
            items.append([lid, "dispatched:" + manager, ledger.now(), ledger.clean(text), ""])
        else:
            ledger.find(items, lid)[1] = "dispatched:" + manager
        ledger.save(head, items)
    return lid, deliver(manager, text, lid)


def main():
    ledger.setup_output()
    args = sys.argv[1:]
    lid = None
    if "--ledger" in args:
        k = args.index("--ledger")
        lid = args[k + 1].upper()
        args = args[:k] + args[k + 2:]
    if len(args) < 2:
        sys.exit(__doc__)
    manager, text = args[0], " ".join(args[1:])
    lid, added = dispatch(manager, text, lid)
    print("%s -> %s%s" % (lid, manager, "" if added else " (already in the inbox)"))


if __name__ == "__main__":
    main()
