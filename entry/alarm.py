#!/usr/bin/env python3
"""Alarm runner over the table in <SBK_HOME>/alarms.md.

    alarm.py --tick [--now 2000-01-31T21:05]   fire what is due (run this every 5 minutes)
    alarm.py --list                            show rows, last fired, next due
    alarm.py --fire A01                        fire one row now
    alarm.py --prune                           delete one-time rows that already fired

Table rows:   | A01 | daily 21:00 | entry | text |
              | A02 | weekly mon 09:00 | study | text |
              | A03 | monthly 1 10:00 | maintenance | text |   (day 1-31; a short month uses its last day)
              | A04 | once 2030-01-31 18:00 | entry | text |
Firing means writing, never talking: to "entry" it adds a tracker item (ledger.md), to a session
(supervisor, maintenance or a topic) it adds a line to that session's inbox. The same unfinished
alarm is never added twice, so a missed reply cannot make alarms pile up. Recurring rows that are
more than 3 hours late are skipped (you were away); one-time rows fire late, marked "(late)".

Wake-up (Full plan): <SBK_HOME>/config.json "wake" says whether sessions are started by the
scheduler. {"supervisor": "manual"|"auto", "topics": "manual"|"auto"} ("topics" covers the
maintenance session and the user's topics; the entry is never started, the user talks to it).
manual (the default): nothing starts by itself; the inbox waits until the user opens the session.
auto: on a tick, a session whose inbox has unticked lines is started in the background with
`claude -p` in its folder (this uses the user's quota), at most once per 60 minutes per session.
SBK_WAKE_DRYRUN=1 prints the command instead of running it.

Run it from the OS scheduler, for example every 5 minutes:
    Windows:  schtasks /Create /SC MINUTE /MO 5 /TN sbk-alarm /TR "python <bin>/alarm.py --tick"
    Linux/macOS crontab:  */5 * * * * python3 <bin>/alarm.py --tick
"""
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ledger  # noqa: E402
import send  # noqa: E402

DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
LATE_LIMIT = datetime.timedelta(hours=3)
MAX_ROWS = 20
WAKE_GAP = datetime.timedelta(minutes=60)
WAKE_TOOLS = "Read,Grep,Glob,Edit,Write,Bash(python:*),Bash(python3:*),Bash(py:*)"
WAKE_PROMPT = ("Scheduled wake-up: auto-wake is on for this session. Follow this folder's CLAUDE.md. "
               "Check the notes first, then take the unticked lines of your inbox, do them, and close each "
               "tracker item with evidence (ledger.py done ... --evidence). Ask no questions: write down "
               "what only the user can do as CLAUDE.md says, then stop.")


def alarms_file():
    return send.home() / "alarms.md"


def state_file():
    return send.home() / "state" / "alarms.json"


def read_rows():
    rows = []
    try:
        lines = alarms_file().read_text(encoding="utf-8").splitlines()
    except Exception:
        return rows
    for line in lines:
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 4 or not re.match(r"^[A-Za-z]\d+$", cells[0]):
            continue
        rows.append({"id": cells[0], "when": cells[1], "to": cells[2], "text": "|".join(cells[3:]).strip()})
    return rows


def load_state():
    try:
        return json.loads(state_file().read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(st):
    state_file().parent.mkdir(parents=True, exist_ok=True)
    state_file().write_text(json.dumps(st, indent=1), encoding="utf-8")


def due_time(when, now):
    """Return (scheduled datetime for the current period, kind) or None if unreadable."""
    w = when.lower().split()
    try:
        if w[0] == "daily":
            hh, mm = map(int, w[1].split(":"))
            return now.replace(hour=hh, minute=mm, second=0, microsecond=0), "daily"
        if w[0] == "weekly":
            hh, mm = map(int, w[2].split(":"))
            day = DAYS.index(w[1][:3])
            base = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
            return base - datetime.timedelta(days=(now.weekday() - day) % 7), "weekly"
        if w[0] == "monthly":
            day = int(w[1])
            hh, mm = map(int, w[2].split(":"))
            if not 1 <= day <= 31:
                return None
            nxt = (now.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
            last = (nxt - datetime.timedelta(days=1)).day
            return now.replace(day=min(day, last), hour=hh, minute=mm, second=0, microsecond=0), "monthly"
        if w[0] == "once":
            return datetime.datetime.strptime(w[1] + " " + w[2], "%Y-%m-%d %H:%M"), "once"
    except Exception:
        return None
    return None


def fire(row, late=False):
    text = row["text"] + (" (late)" if late else "")
    tag = "[alarm %s] %s" % (row["id"], text)
    if row["to"].lower() == "entry":
        head, items = ledger.load()
        if any(i[3] == ledger.clean(tag) and i[1] not in ("done", "dropped") for i in items):
            return "skipped (same alarm still open)"
        nxt = max([int(i[0][1:]) for i in items] + [0]) + 1
        items.append(["L%04d" % nxt, "open", ledger.now(), ledger.clean(tag), ""])
        ledger.save(head, items)
        return "ledger L%04d" % nxt
    if not (send.home() / "managers" / row["to"]).is_dir():
        return "no manager folder: " + row["to"]
    added = send.deliver(row["to"], tag, "ALARM")
    return "inbox of " + row["to"] if added else "skipped (same alarm still unticked)"


def config():
    try:
        return json.loads((send.home() / "config.json").read_text(encoding="utf-8"))
    except Exception:
        return {}


def wake_mode(target, cfg):
    """auto or manual for one session; anything unreadable is manual."""
    if target.lower() == "entry":
        return "manual"
    w = cfg.get("wake") if isinstance(cfg.get("wake"), dict) else {}
    val = w.get("supervisor" if target == "supervisor" else "topics", "manual")
    return "auto" if val == "auto" else "manual"


def unticked(target):
    try:
        text = (send.home() / "inbox" / (target + ".md")).read_text(encoding="utf-8")
    except Exception:
        return 0
    return sum(1 for l in text.splitlines() if l.startswith("- [ ]"))


def wake(now, st):
    """Start sessions whose wake mode is auto and whose inbox has unticked lines."""
    cfg = config()
    managers = send.home() / "managers"
    if not managers.is_dir():
        return
    for d in sorted(p for p in managers.iterdir() if p.is_dir()):
        target = d.name
        if wake_mode(target, cfg) != "auto" or not unticked(target):
            continue
        key = "wake:" + target
        try:
            last = datetime.datetime.strptime(st.get(key, ""), "%Y-%m-%dT%H:%M")
            if now - last < WAKE_GAP:
                continue
        except ValueError:
            pass
        exe = shutil.which("claude")
        cmd = [exe or "claude", "-p", "--permission-mode", "acceptEdits", "--name", target]
        if cfg.get("vault"):
            cmd += ["--add-dir", cfg["vault"]]
        cmd += ["--allowedTools", WAKE_TOOLS, "--", WAKE_PROMPT]
        if os.environ.get("SBK_WAKE_DRYRUN") == "1":
            print("wake %s (dry run): %s" % (target, " ".join(cmd[:-1]) + ' "..."'))
        elif not exe:
            print("wake %s: claude command not found, the session waits until the user opens it" % target)
            continue
        else:
            log = send.home() / "logs" / ("wake-" + target + ".log")
            log.parent.mkdir(parents=True, exist_ok=True)
            out = open(log, "ab")
            subprocess.Popen(cmd, cwd=str(d), stdout=out, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            print("wake %s: started, log %s" % (target, log))
        st[key] = now.strftime("%Y-%m-%dT%H:%M")


def tick(now):
    st = load_state()
    rows = read_rows()
    for row in rows:
        res = due_time(row["when"], now)
        if not res:
            print("%s: cannot read '%s'" % (row["id"], row["when"]))
            continue
        sched, kind = res
        key = sched.strftime("%Y-%m-%dT%H:%M")
        if now < sched or st.get(row["id"]) == key:
            continue
        late = now - sched
        if kind != "once" and late > LATE_LIMIT:
            st[row["id"]] = key  # skip this period, do not fire hours later
            print("%s: skipped, %s late" % (row["id"], late))
            continue
        print("%s: %s" % (row["id"], fire(row, late=late > datetime.timedelta(minutes=20) and kind == "once")))
        st[row["id"]] = key
    wake(now, st)
    save_state(st)
    if len(rows) > MAX_ROWS:
        print("WARNING: %d alarm rows. Alarms multiply; delete the ones nobody acts on." % len(rows))


def listing(now):
    st = load_state()
    rows = read_rows()
    for row in rows:
        res = due_time(row["when"], now)
        print("%-4s %-24s -> %-10s last=%s  %s" % (row["id"], row["when"], row["to"],
                                                 st.get(row["id"], "never"), row["text"][:50]))
        if not res:
            print("     ^ cannot read the schedule")
    print("%d rows" % len(rows))
    cfg = config()
    print("wake: supervisor=%s topics=%s" % (wake_mode("supervisor", cfg), wake_mode("topics", cfg)))
    if len(rows) > MAX_ROWS:
        print("WARNING: more than %d rows" % MAX_ROWS)


def prune(now):
    st = load_state()
    p = alarms_file()
    keep, dropped = [], 0
    for line in p.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if line.strip().startswith("|") and len(cells) >= 4 and cells[1].lower().startswith("once"):
            res = due_time(cells[1], now)
            if res and st.get(cells[0]) == res[0].strftime("%Y-%m-%dT%H:%M"):
                dropped += 1
                continue
        keep.append(line)
    p.write_text("\n".join(keep) + "\n", encoding="utf-8")
    print("removed %d fired one-time rows" % dropped)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    a = sys.argv[1:]
    now = datetime.datetime.now().replace(second=0, microsecond=0)
    if "--now" in a:
        now = datetime.datetime.strptime(a[a.index("--now") + 1], "%Y-%m-%dT%H:%M")
    if "--tick" in a:
        tick(now)
    elif "--list" in a:
        listing(now)
    elif "--prune" in a:
        prune(now)
    elif "--fire" in a:
        rid = a[a.index("--fire") + 1]
        row = next((r for r in read_rows() if r["id"] == rid), None)
        print(fire(row) if row else "no such alarm: " + rid)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
