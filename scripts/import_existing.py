#!/usr/bin/env python3
"""Bring an existing setup into the kit's folder: for a user who already has a to-do tracker, reminders
and per-topic working files from before the kit, and does not start from nothing.

    import_existing.py PLAN.json            dry run: print what would be written, write nothing
    import_existing.py PLAN.json --apply    write it

Claude writes PLAN.json after reading the old setup (read-only), shows the dry run to the user, and
applies it after a yes. The tool writes only under <SBK_HOME> (tracker, routes.md, alarms.md,
managers/<topic>/, inbox/, state/import-map.json). It never changes or deletes an old file, never
replaces a file that exists, and can be run again: what is already imported is skipped.

PLAN.json:
{
 "expect_rows": 83,                 optional: the number of rows the old tracker has; the import stops
                                    unless "items" accounts for exactly that many (nothing dropped silently)
 "topics": [{"name": "study",       folder managers/study (letters, digits, - and _)
             "keywords": "course, exam",       the routes.md row
             "scope": "the two courses",       goes into the topic's CLAUDE.md
             "old_task": "C:/old/study.md",    optional: where this topic's state is today; the new task.md
                                               points at it, the file itself is not copied or changed
             "notes": "",                      optional: routes.md notes
             "claude_md": "C:/my/topic.md"}],  optional: the user's own text for CLAUDE.md instead of the template
 "items":  [{"old": "T12",          the old tracker's id for this row (any text; must be unique)
             "keep": true,          true: becomes a tracker item. false: a record only (finished, cancelled,
                                    a question that was answered, a consent that stays valid): kept in the map
             "text": "goal",        keep=true: the goal;   keep=false: why it is not carried over + evidence
             "done_when": "...", "said": "the user's words", "ts": "2026-11-23T21:45:00",   optional
             "to": "study"}],       optional: hand it to that topic now (tracker: dispatched, plus an inbox
                                    line, so the tick starts that session). Leave it out while the old
                                    setup still works on the topic: two sessions on one job do it twice.
 "alarms": [{"id": "A05", "when": "daily 08:10", "to": "study", "text": "[worker] check the course page"}]
}
The map <SBK_HOME>/state/import-map.json answers "where did old row X go": {"T12": {"new": "L0007"}} or
{"T13": {"record": "done 11-24, evidence ..."}}.
"""
import datetime
import json
import os
import re
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT / "entry"))
import alarm  # noqa: E402
import ledger  # noqa: E402
import send  # noqa: E402

NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,40}$")
FIXED = ("entry", "maintenance", "handover")


def load_json(p, default):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def check(plan, home):
    """Return the list of reasons the plan cannot be imported (empty: fine)."""
    bad = []
    topics = plan.get("topics") or []
    names = set()
    for t in topics:
        n = str(t.get("name", ""))
        if not NAME.match(n) or n in FIXED:
            bad.append("topic name not usable: %r" % n)
        if n in names:
            bad.append("topic twice: " + n)
        names.add(n)
        for key in ("old_task", "claude_md"):
            if t.get(key) and not Path(t[key]).is_file():
                bad.append("topic %s: %s not found: %s" % (n, key, t[key]))
    have = names | {d.name for d in (home / "managers").iterdir() if d.is_dir()} if (home / "managers").is_dir() else names
    items = plan.get("items") or []
    olds = [str(i.get("old", "")).strip() for i in items]
    for o in sorted({o for o in olds if olds.count(o) > 1}):
        bad.append("old id twice: %r" % o)
    for i in items:
        if not str(i.get("old", "")).strip() or not str(i.get("text", "")).strip():
            bad.append("item without old id or text: %r" % (i,))
        if i.get("to") and i["to"] not in have:
            bad.append("item %s: no such topic: %s" % (i.get("old"), i["to"]))
        if i.get("to") and not i.get("keep", True):
            bad.append("item %s: a record cannot be handed to a topic" % i.get("old"))
        if i.get("ts"):
            try:
                datetime.datetime.strptime(i["ts"], "%Y-%m-%dT%H:%M:%S")
            except ValueError:
                bad.append("item %s: ts must look like 2026-11-23T21:45:00" % i.get("old"))
    want = plan.get("expect_rows")
    if want is not None and int(want) != len(items):
        bad.append("the old tracker has %s rows, the plan accounts for %d" % (want, len(items)))
    now = datetime.datetime.now()
    seen = set()
    for a in plan.get("alarms") or []:
        aid = str(a.get("id", ""))
        if not re.match(r"^[A-Za-z]\d+$", aid) or aid in seen:
            bad.append("alarm id not usable or twice: %r" % aid)
        seen.add(aid)
        if alarm.due_time(str(a.get("when", "")), now) is None:
            bad.append("alarm %s: when not readable: %r (daily HH:MM, weekly mon HH:MM, monthly D HH:MM, once YYYY-MM-DD HH:MM)" % (aid, a.get("when")))
        if a.get("to") not in FIXED and a.get("to") not in have:
            bad.append("alarm %s: no such session: %r" % (aid, a.get("to")))
        if "|" in str(a.get("text", "")) or "\n" in str(a.get("text", "")) or not str(a.get("text", "")).strip():
            bad.append("alarm %s: text is empty or has a | or a line break" % aid)
    return bad


def do_topics(plan, home, apply, out):
    vault = load_json(home / "config.json", {}).get("vault") or ""
    routes = home / "routes.md"
    rtext = routes.read_text(encoding="utf-8") if routes.exists() else (KIT / "templates" / "routes.md").read_text(encoding="utf-8")
    rtext = "\n".join(l for l in rtext.splitlines() if "{{manager" not in l) + "\n"
    rows = [[c.strip() for c in l.strip().strip("|").split("|")] for l in rtext.splitlines() if l.strip().startswith("|")]
    routed = {r[1] for r in rows if len(r) >= 2}
    added = []
    for t in plan.get("topics") or []:
        n = t["name"]
        d = home / "managers" / n
        if d.is_dir():
            out.append("topic %s: folder exists, left as it is" % n)
        else:
            out.append("topic %s: new folder %s" % (n, d))
            if apply:
                d.mkdir(parents=True)
                src = Path(t["claude_md"]) if t.get("claude_md") else KIT / "templates" / "manager-CLAUDE.md"
                text = src.read_text(encoding="utf-8")
                for k, v in (("{{manager}}", n), ("{{vault}}", vault), ("{{scope}}", t.get("scope") or n)):
                    text = text.replace(k, v)
                (d / "CLAUDE.md").write_text(text, encoding="utf-8")
                task = (KIT / "templates" / "task.md").read_text(encoding="utf-8").replace("{{topic}}", n)
                if t.get("old_task"):
                    task = task.replace("## Now (", "## Before the move\n- This topic's state up to the move is in %s. Read it whole at "
                                        "your first start and carry what is still open into this file; that file is not changed "
                                        "from here.\n\n## Now (" % t["old_task"], 1)
                (d / "task.md").write_text(task, encoding="utf-8")
        if n not in routed:
            added.append("| %s | %s | managers/%s/task.md | %s |" % (
                ledger.clean(t.get("keywords") or n), n, n, ledger.clean(t.get("notes") or "")))
            out.append("routes.md: new row for %s" % n)
    if added and apply:
        lines = rtext.splitlines()
        last = max(k for k, l in enumerate(lines) if l.strip().startswith("|"))
        routes.write_text("\n".join(lines[:last + 1] + added + lines[last + 1:]) + "\n", encoding="utf-8")


def do_items(plan, home, apply, out):
    mp = home / "state" / "import-map.json"
    done = load_json(mp, {})
    kept = rec = skipped = 0
    inbox = []
    with ledger.locked():
        head, items = ledger.load()
        nxt = max([int(i[0][1:]) for i in items] + [0])
        for it in plan.get("items") or []:
            old = str(it["old"]).strip()
            if old in done:
                skipped += 1
                continue
            if not it.get("keep", True):
                done[old] = {"record": ledger.clean(str(it["text"]))}
                rec += 1
                continue
            text = ledger.clean(str(it["text"])) + " (was %s)" % old
            if it.get("done_when"):
                text += "; done when: " + ledger.clean(str(it["done_when"]))
            if it.get("said"):
                text += '; said: "' + ledger.clean(str(it["said"])) + '"'
            nxt += 1
            lid = "L%04d" % nxt
            items.append([lid, ("dispatched:" + it["to"]) if it.get("to") else "open", it.get("ts") or ledger.now(), text, ""])
            done[old] = {"new": lid}
            if it.get("to"):
                inbox.append((it["to"], text, lid))
            kept += 1
        if apply:
            ledger.save(head, items)
            mp.parent.mkdir(parents=True, exist_ok=True)
            mp.write_text(json.dumps(done, indent=1, ensure_ascii=False), encoding="utf-8")
    if apply:
        for to, text, lid in inbox:
            send.deliver(to, text, lid)
    total = len(plan.get("items") or [])
    out.append("tracker: %d old row(s) in the plan = %d new item(s) + %d record(s) + %d imported before; %d inbox line(s)"
               % (total, kept, rec, skipped, len(inbox)))
    return total == kept + rec + skipped


def do_alarms(plan, home, apply, out):
    p = home / "alarms.md"
    text = p.read_text(encoding="utf-8") if p.exists() else (KIT / "templates" / "alarms.md").read_text(encoding="utf-8")
    have = {m.group(1) for m in re.finditer(r"(?m)^\|\s*([A-Za-z]\d+)\s*\|", text)}
    new = []
    for a in plan.get("alarms") or []:
        if a["id"] in have:
            out.append("alarm %s: a row with this id exists, left as it is" % a["id"])
        else:
            new.append("| %s | %s | %s | %s |" % (a["id"], a["when"], a["to"], a["text"].strip()))
    out.append("alarms.md: %d new row(s)" % len(new))
    if new and apply:
        p.write_text(text.rstrip("\n") + "\n" + "\n".join(new) + "\n", encoding="utf-8")


def main():
    ledger.setup_output()
    a = sys.argv[1:]
    if not a or a[0].startswith("-"):
        sys.exit(__doc__)
    plan = load_json(a[0], None)
    if not isinstance(plan, dict):
        sys.exit("cannot read the plan: " + a[0])
    apply = "--apply" in a
    home = send.home()
    if apply and not home.is_dir():
        sys.exit("no kit folder at %s: run the setup first (or set SBK_HOME)" % home)
    bad = check(plan, home)
    if bad:
        print("NOT IMPORTED, the plan has %d problem(s):" % len(bad))
        for b in bad:
            print("- " + b)
        sys.exit(2)
    out = []
    do_topics(plan, home, apply, out)
    ok = do_items(plan, home, apply, out)
    do_alarms(plan, home, apply, out)
    print("\n".join(out))
    print(("IMPORTED into %s" if apply else "DRY RUN, nothing written (would go into %s); add --apply after the user's yes") % home)
    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()
