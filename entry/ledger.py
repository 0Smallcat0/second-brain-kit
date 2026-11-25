#!/usr/bin/env python3
"""The tracker (ledger.md): one line per thing the user asked for, so nothing gets lost between sessions.

    ledger.py add "goal" [--done-when "..."] [--said "the user's words"] [--to SESSION]
                                               new item (open, or dispatched if --to)
    ledger.py edit L0003 "goal" [--done-when ...] [--said ...]
                                               the user corrected an earlier request: change that line
    ledger.py list [--all]                     open and dispatched items (--all adds closed)
    ledger.py dispatch L0003 SESSION           hand an open item to a topic session
    ledger.py done L0003 --evidence "..."      close it; evidence = what you looked at (6+ chars)
    ledger.py verify L0003 --evidence "..."    Full: the entry opened that evidence itself and it holds
    ledger.py drop L0003 --evidence "reason"   close it without doing it (the user decided)

File: <SBK_HOME>/ledger.md   (override with SBK_LEDGER). One line per item:
    - L0003 | dispatched:study | 2000-01-31T09:00:00 | text | ev: evidence
Closing needs evidence on purpose: "done" without something to point at is the usual lie.
Several sessions write this file (a topic closing an item while the 5-minute tick adds an alarm item),
so every change runs between load and save inside `locked()`: a lock file created exclusively, retried
for two seconds. A line the pattern does not recognise is kept (written after the items), never dropped.
The text of an item is the processed request (goal; done when; the user's words verbatim), so a
line can be checked against what was really asked. In Full, a topic closes with done and the entry
marks it verified after opening the evidence; only then does the user hear the result.
"""
import os
import re
import sys
import time
from pathlib import Path

LINE = re.compile(r"^- (L\d{4}) \| ([^|]+?) \| ([^|]+?) \| (.*?) \| ev: (.*)$")
CLOSED = ("done", "dropped", "verified")
LAZY = {"done", "ok", "okay", "fine", "yes", "完成", "做完", "好了", "沒問題", "n/a", "none", "-"}
HEADER = ("# Ledger\n\nOne line per request. Statuses: open, dispatched:<session>, done, verified, dropped.\n"
          "Close with `ledger.py done Lxxxx --evidence \"...\"`.\n\n")


def path():
    env = os.environ.get("SBK_LEDGER")
    if env:
        return Path(env)
    base = os.environ.get("SBK_HOME")
    if base:
        return Path(base) / "ledger.md"
    new, old = Path.home() / ".sbk", Path.home() / ".claude" / "sbk"  # old: before 0.2.5
    return (old if (not new.exists() and old.exists()) else new) / "ledger.md"


_tail = []  # lines after the first item that are not items: load() sets them, save() writes them back


def load():
    p = path()
    head, items = [], []
    _tail.clear()
    if p.exists():
        for raw in p.read_text(encoding="utf-8").splitlines():
            m = LINE.match(raw)
            if m:
                items.append(list(m.groups()))
            elif not items:
                head.append(raw)
            elif raw.strip():
                _tail.append(raw)
    return "\n".join(head).rstrip() + "\n\n" if head else HEADER, items


def locked(wait=2.0, stale=30.0):
    """Hold the tracker's lock file from load to save. Exclusive create, retry for `wait` seconds; a lock
    older than `stale` seconds is a crashed writer's and is removed. After `wait` it goes ahead without the
    lock rather than hang a session (a lost update is rarer than a hung one)."""
    lock = path().with_suffix(".md.lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    have = False
    end = time.time() + wait
    while True:
        try:
            os.close(os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY))
            have = True
            break
        except (FileExistsError, PermissionError):
            try:
                if time.time() - lock.stat().st_mtime > stale:
                    lock.unlink()
                    continue
            except OSError:
                pass
        except OSError:
            break
        if time.time() > end:
            break
        time.sleep(0.03)
    return _Held(lock if have else None)


class _Held:
    """What locked() returns: `with locked():` releases the lock file (if it was taken) on the way out."""

    def __init__(self, lock):
        self.lock = lock

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        if self.lock is not None:
            try:
                self.lock.unlink()
            except OSError:
                pass
        return False


def save(head, items):
    p = path()
    p.parent.mkdir(parents=True, exist_ok=True)
    body = "".join("- %s | %s | %s | %s | ev: %s\n" % tuple(i) for i in items)
    body += "".join(l + "\n" for l in _tail)
    tmp = p.with_suffix(".md.%d.tmp" % os.getpid())
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


def setup_output(log_name=None):
    """UTF-8 output. Under pythonw.exe (the Windows scheduled task) sys.stdout and sys.stderr are None and
    `sys.stdout.reconfigure` raised AttributeError before 0.2.8; with log_name, everything printed is also
    appended to <SBK_HOME>/logs/<log_name>.log (the only place a scheduled run's output can be read)."""
    if sys.stdout is not None and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if log_name:
        base = os.environ.get("SBK_HOME")
        if base:
            logs = Path(base) / "logs"
        else:
            new, old = Path.home() / ".sbk", Path.home() / ".claude" / "sbk"
            logs = (old if (not new.exists() and old.exists()) else new) / "logs"
        try:
            logs.mkdir(parents=True, exist_ok=True)
        except OSError:
            return
        sys.stdout = _Tee(sys.stdout, logs / (log_name + ".log"))
        sys.stderr = _Tee(sys.stderr, logs / (log_name + ".log"))


class _Tee:
    """Passes writes on to the stream it wraps (None under pythonw.exe) and appends every non-blank one to a log."""

    def __init__(self, out, path):
        self.out, self.path, self.started = out, path, False

    def write(self, text):
        if self.out is not None:
            try:
                self.out.write(text)
            except Exception:
                pass
        if text.strip():
            try:
                with open(str(self.path), "a", encoding="utf-8") as f:
                    if not self.started:
                        f.write(time.strftime("[%Y-%m-%dT%H:%M:%S] ") + "run\n")
                        self.started = True
                    f.write(text if text.endswith("\n") else text + "\n")
            except Exception:
                pass
        return len(text)

    def flush(self):
        try:
            if self.out is not None:
                self.out.flush()
        except Exception:
            pass

    def isatty(self):
        return False


def clean(text):
    return text.replace("|", "/").replace("\n", " ").strip()


def take(args, flag):
    """Remove `flag VALUE` from args; return (value or None, args)."""
    if flag in args:
        k = args.index(flag)
        if k + 1 >= len(args):
            sys.exit(flag + " needs a value")
        return args[k + 1], args[:k] + args[k + 2:]
    return None, args


def compose(args):
    """goal; done when: ...; said: "..." -- the processed request with the user's words kept verbatim."""
    done_when, args = take(args, "--done-when")
    said, args = take(args, "--said")
    to, args = take(args, "--to")
    text = clean(" ".join(args))
    if done_when:
        text += "; done when: " + clean(done_when)
    if said:
        text += '; said: "' + clean(said) + '"'
    return text, to, args


def cmd_add(args):
    text, to, _ = compose(args)
    if not text:
        sys.exit("add: text is empty")
    with locked():
        head, items = load()
        nxt = max([int(i[0][1:]) for i in items] + [0]) + 1
        lid = "L%04d" % nxt
        items.append([lid, ("dispatched:" + to) if to else "open", now(), text, ""])
        save(head, items)
    print(lid)


def cmd_edit(args):
    if len(args) < 2:
        sys.exit('usage: edit Lxxxx "goal" [--done-when ...] [--said ...]')
    lid, rest = args[0], args[1:]
    text, _, _ = compose(rest)
    if not text:
        sys.exit("edit: text is empty")
    with locked():
        head, items = load()
        it = find(items, lid)
        if it[1] in CLOSED:
            sys.exit("already closed: add a new item instead")
        m = re.search(r'; said: "(.*)"$', it[3])
        if m:  # the user's earlier words stay; a correction's words are added after them
            n = re.search(r'; said: "(.*)"$', text)
            text = (text[:n.start()] if n else text) + '; said: "' + m.group(1) + ('" / "' + n.group(1) if n else "") + '"'
        it[3] = text
        save(head, items)
    print(it[0], "edited")


def cmd_dispatch(args):
    if len(args) != 2:
        sys.exit("usage: dispatch Lxxxx MANAGER")
    with locked():
        head, items = load()
        it = find(items, args[0])
        if it[1] in CLOSED:
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
    with locked():
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
        closed = st in CLOSED
        if closed and not show_all:
            continue
        n += 1
        flag = "  [STALE %dd]" % age_days(ts) if not closed and age_days(ts) >= 14 else ""
        print("%s  %-18s %s  %s%s%s" % (lid, st, ts[:10], text, ("  (ev: %s)" % ev) if closed else "", flag))
    if n == 0:
        print("nothing open")


def main():
    setup_output()
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "add":
        cmd_add(args)
    elif cmd == "list":
        cmd_list(args)
    elif cmd == "edit":
        cmd_edit(args)
    elif cmd == "dispatch":
        cmd_dispatch(args)
    elif cmd in ("done", "drop", "verify"):
        cmd_close({"done": "done", "drop": "dropped", "verify": "verified"}[cmd], args)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
