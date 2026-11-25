#!/usr/bin/env python3
"""Alarm runner over the table in <SBK_HOME>/alarms.md.

    alarm.py --tick [--now 2000-01-31T21:05]   fire what is due (run this every 5 minutes)
    alarm.py --list                            show rows, last fired, next due
    alarm.py --fire A01                        fire one row now
    alarm.py --prune                           delete one-time rows that already fired

Table rows:   | A01 | daily 21:00 | entry | text |
              | A02 | weekly mon 09:00 | study | text |
              | M01 | weekly sun 20:00 | maintenance | text |
              | A03 | monthly 1 10:00 | maintenance | text |   (day 1-31; a short month uses its last day)
              | A04 | once 2030-01-31 18:00 | entry | text |
              | H01 | daily 21:30 | handover | long conversations: hand over to a fresh one |
Firing first writes: to "entry" a tracker item (ledger.md), to a session (maintenance or a topic) a
line in its inbox. The same unfinished alarm is never added twice, so a missed reply cannot make
alarms pile up. Then, with live routing (config "routing": "live"), the work goes in at once: into
the running session, or the session is started in the background (session.py, same path as the
entry's routing). "handover" runs handover.py check (long conversations hand over to fresh ones).

Cost: the tick itself reads local files and uses no Claude quota. Only starting or messaging a
session does, so those are limited by config "wake_limits" {"per_day": N, "min_gap_min": M}: at most
N per day in total and M minutes between two for the same session; over the limit the work simply
waits in the inbox and a later tick (or the user opening the session) picks it up.

Report without being asked (live routing, the entry running): each tick also looks at the tracker.
(a) An item a topic closed ("done") that the entry has not checked one tick later is sent to the entry.
(b) An item handed to a topic that took it from its inbox and then stopped working for config
"report_idle_min" minutes (default 10) without closing it is sent to the entry, once per idle period.
Both are found by reading files and the session list; no model is used to find them. The entry then
opens the evidence or the topic's task.md and tells the user what they need to know.

Computer off or asleep: nothing runs then. At the next tick a recurring row that was missed fires
once, marked "(late)", however many periods were missed; a one-time row fires late too. A row seen
for the first time (just added) only fires if it is due within the last 10 minutes.

Run it from the OS scheduler every 5 minutes (docs/ADVANCED.md A2 has the exact commands):
    Windows:  Register-ScheduledTask ... -RepetitionInterval 5 minutes, with "start when available"
    macOS:    a LaunchAgent (StartInterval 300) with PATH set; Linux: crontab with PATH set:
              */5 * * * * PATH=... python3 <bin>/alarm.py --tick
The tick appends what it prints to <SBK_HOME>/logs/alarm.log (a scheduled run has no screen).
"""
import datetime
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ledger  # noqa: E402
import send  # noqa: E402
import session  # noqa: E402

DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
LATE = datetime.timedelta(minutes=20)     # fired this much after its time: marked (late)
FIRST_SIGHT = datetime.timedelta(minutes=10)
MAX_ROWS = 20


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


def _month_before(now, day):
    prev = now.replace(day=1) - datetime.timedelta(days=1)
    return prev.replace(day=min(day, prev.day))


def due_time(when, now):
    """Return (latest scheduled datetime <= now, kind), or None if unreadable. "once" returns its time."""
    w = when.lower().split()
    try:
        if w[0] == "daily":
            hh, mm = map(int, w[1].split(":"))
            t = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
            return (t if t <= now else t - datetime.timedelta(days=1)), "daily"
        if w[0] == "weekly":
            hh, mm = map(int, w[2].split(":"))
            day = DAYS.index(w[1][:3])
            base = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
            t = base - datetime.timedelta(days=(now.weekday() - day) % 7)
            return (t if t <= now else t - datetime.timedelta(days=7)), "weekly"
        if w[0] == "monthly":
            day = int(w[1])
            hh, mm = map(int, w[2].split(":"))
            if not 1 <= day <= 31:
                return None
            nxt = (now.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
            last = (nxt - datetime.timedelta(days=1)).day
            t = now.replace(day=min(day, last), hour=hh, minute=mm, second=0, microsecond=0)
            if t > now:
                t = _month_before(now, day).replace(hour=hh, minute=mm, second=0, microsecond=0)
            return t, "monthly"
        if w[0] == "once":
            return datetime.datetime.strptime(w[1] + " " + w[2], "%Y-%m-%d %H:%M"), "once"
    except Exception:
        return None
    return None


def fire(row, late=False, now=None):
    text = row["text"] + (" (late)" if late else "")
    tag = "[alarm %s] %s" % (row["id"], text)
    to = row["to"].lower()
    if to == "handover":
        import handover
        return handover.check_all()
    if to == "entry":
        mark = "[alarm %s]" % row["id"]
        with ledger.locked():
            head, items = ledger.load()
            if any(i[3].startswith(mark) and i[1] not in ledger.CLOSED for i in items):
                return "skipped (same alarm still open)"
            nxt = max([int(i[0][1:]) for i in items] + [0]) + 1
            items.append(["L%04d" % nxt, "open", ledger.now(), ledger.clean(tag), ""])
            ledger.save(head, items)
        res = "ledger L%04d" % nxt
        if session.cfg().get("routing") == "live" and session.find("entry"):
            res += ", " + session.deliver("entry", tag, "L%04d" % nxt, scheduled=True, now=now)
        return res
    if not (send.home() / "managers" / row["to"]).is_dir():
        return "no session folder: " + row["to"]
    try:
        inbox = (send.home() / "inbox" / (row["to"] + ".md")).read_text(encoding="utf-8").splitlines()
    except Exception:
        inbox = []
    if any(l.startswith("- [ ]") and ("[alarm %s]" % row["id"]) in l for l in inbox):
        return "skipped (same alarm still unticked in the inbox of %s)" % row["to"]
    return "inbox of %s: %s" % (row["to"], session.deliver(row["to"], tag, "ALARM", scheduled=True, now=now))


def drain(now):
    """Live routing: a session with unticked inbox lines that is not running is started (within limits)."""
    c = session.cfg()
    managers = send.home() / "managers"
    if (c.get("routing") != "live" and not session.dry()) or not managers.is_dir():
        return
    waiting = [d.name for d in sorted(managers.iterdir()) if d.is_dir() and session.unticked(d.name)]
    if not waiting:
        return  # nothing waits: no claude call, no quota
    rows = session.running()
    for name in waiting:
        if session.find(name, rows):
            continue
        ok, why, st = session.wake_ok(name, c, now)
        if not ok:
            print("%s waits: %s" % (name, why))
            continue
        rc = session.open_session(name, "Scheduled start: your inbox has %d unticked line(s)." % session.unticked(name))
        if rc == 0:
            session.count_wake(st, name, now)


def report_file():
    return send.home() / "state" / "report.json"


def report(now):
    """See "Report without being asked" above. Returns the text sent to the entry, or ""."""
    c = session.cfg()
    if c.get("routing") != "live" and not session.dry():
        return ""
    _, items = ledger.load()
    done = [i for i in items if i[1] == "done"]
    handed = [i for i in items if i[1].startswith("dispatched:")]
    try:
        st = json.loads(report_file().read_text(encoding="utf-8"))
    except Exception:
        st = {}
    seen = {k: v for k, v in (st.get("done") or {}).items() if k in {i[0] for i in done}}
    stale = {k: v for k, v in (st.get("stale") or {}).items() if k in {i[0] for i in handed}}
    notes, mark_done, mark_stale = [], [], {}
    for lid, _st, _ts, text, ev in done:
        if lid not in seen:
            seen[lid] = "seen"      # first sight: the topic's own message to the entry gets one tick
        elif seen[lid] == "seen":
            notes.append("Done by a topic, not checked by you yet: %s %s (ev: %s)" % (lid, text[:200], ev[:200]))
            mark_done.append(lid)
    rows = session.rows_all() if handed else []
    idle = float(c.get("report_idle_min", 10)) * 60
    if handed:
        import handover
    for lid, status, _ts, text, _ev in handed:
        name = status.split(":", 1)[1].strip()
        if session.unticked(name):
            continue                # not taken from the inbox yet: drain() starts the session
        alive = [r for r in rows if r["name"] == name and r["alive"]]
        r = alive[0] if alive else session.resumable(name, rows)
        if not r or (r["alive"] and r["status"] == "busy"):
            continue
        src = handover.transcript(r["sessionId"])
        if not src:
            continue
        last = int(src.stat().st_mtime)
        if now.timestamp() - last < idle or stale.get(lid) == last:
            continue
        notes.append("Handed to %s, which stopped working at %s without closing it: %s %s"
                     % (name, datetime.datetime.fromtimestamp(last).strftime("%m-%d %H:%M"), lid, text[:200]))
        mark_stale[lid] = last
    sent = ""
    if notes and (session.find("entry") or session.dry()):
        text = ("Report from the alarm tick (nobody asked for it). For a finished item: open the evidence itself; "
                "if it holds, ledger.py verify and give the user the result now. For a stopped one: read that "
                "topic's task.md; if the work is finished have it closed, if it waits for something tell the "
                "user only what they must do or decide.\n- " + "\n- ".join(notes))
        if session.push("entry", text):
            sent = text
            for lid in mark_done:
                seen[lid] = "pushed"
            stale.update(mark_stale)
    try:
        report_file().parent.mkdir(parents=True, exist_ok=True)
        report_file().write_text(json.dumps({"done": seen, "stale": stale}, indent=1), encoding="utf-8")
    except Exception:
        pass
    return sent


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
        if row["id"] not in st and kind != "once" and now - sched > FIRST_SIGHT:
            st[row["id"]] = key  # a row just added: start from its next time, do not fire a past one
            continue
        print("%s: %s" % (row["id"], fire(row, late=now - sched > LATE, now=now)))
        st[row["id"]] = key
    save_state(st)
    drain(now)
    told = report(now)
    if told:
        print("report: %d line(s) sent to the entry" % told.count("\n- "))
    if (send.home() / "state" / "handover_due.json").exists():
        import handover
        res = handover.due()
        if res:
            print("handover: " + res)
    if len(rows) > int(session.cfg().get("alarm_rows_warn", MAX_ROWS)):
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
    c = session.cfg()
    lim = c.get("wake_limits") or {}
    print("routing: %s  sessions at once: %s  wake limits: %s/day, %s min apart" % (
        c.get("routing", "inbox"), c.get("max_sessions", 2), lim.get("per_day", 4), lim.get("min_gap_min", 120)))
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
    a = sys.argv[1:]
    # --tick runs from the OS scheduler: its output is also kept in <SBK_HOME>/logs/alarm.log. Under
    # pythonw.exe (the Windows task) there is no stdout at all, and before 0.2.8 the next line crashed.
    ledger.setup_output("alarm" if "--tick" in a else None)
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
        print(fire(row, now=now) if row else "no such alarm: " + rid)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
