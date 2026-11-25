#!/usr/bin/env python3
"""The learning loop's numbers: what the user corrected and confirmed, from the 和 AI 協作 note.

    learn.py add 糾正|做對 "kind of mistake / way of working" "the user's own words"
    learn.py trend [--now 2000-01-31]       this week vs last week, kinds that came back, hook candidates
    learn.py group [--since 2000-01-01]     lines since a date (default: 7 days) grouped by kind, most first
    learn.py pref "kind" "one sentence"     add a sorted preference at the top (after the user agreed)
    learn.py stats                          lines recorded, corrections this week, kinds that came back
    learn.py path                           where the note is

The note is <vault>/00-09 系統與索引/03 和 AI 協作/03-01 和 AI 協作.md. Claude adds one line the moment
the user corrects it or confirms a way of working (Basic and Full alike):
    - 2000-01-31 | 糾正 | 沒驗證就說做完 | 「你根本沒打開檔案看」
    - 2000-01-31 | 做對 | 先查筆記再答 | 「對，就是這樣」
"糾正" = correction, "做對" = confirmed (English "correction" / "confirmed" are read too). Before acting,
"check the notes first" reads this note: the sorted preferences at the top and the recent lines.
The learn_notice hook reminds Claude to add the line when the user's message looks like a correction or
a confirmation. In Basic, the first session of the week in the notes folder gets a light review (level_check.py
--hook): Claude runs `group`, drafts preferences and any skill or hook addition, and writes them (`pref`) only
after the user agrees. In Full, Maintenance's weekly review runs `trend`, groups the week's lines by kind and turns them into
preferences (written at the top of the note), ways of working (added to skills) and, only for a kind
that came back a second time and that a program can see at the moment of action, a hook (started in
log mode and replayed on past conversations before it may block; see PITFALLS 9-10).
"""
import datetime
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import send  # noqa: E402

REL = Path("00-09 系統與索引") / "03 和 AI 協作" / "03-01 和 AI 協作.md"
LINE = re.compile(r"^-\s*(\d{4}-\d{2}-\d{2})\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*(.+)$")
CORR = {"糾正", "correction", "corrected"}
GOOD = {"做對", "confirmed", "confirm"}
STARTER_TAGS = ("（來自原作者，可刪）", "(from the original author; delete if you like)")


def vault():
    env = os.environ.get("SBK_VAULT")
    if env:
        return Path(env)
    try:
        v = json.loads((send.home() / "config.json").read_text(encoding="utf-8")).get("vault")
        if v:
            return Path(v)
    except Exception:
        pass
    p = Path.cwd().resolve()
    for d in [p] + list(p.parents):
        if (d / ".sbk-vault").exists():
            return d
    return None


def note():
    v = vault()
    return v / REL if v else None


def entries(text):
    out = []
    for line in text.splitlines():
        m = LINE.match(line.strip())
        if not m:
            continue
        kind = m.group(2).strip().lower()
        what = "corr" if kind in CORR else "good" if kind in GOOD else None
        if what:
            out.append((datetime.date.fromisoformat(m.group(1)), what, m.group(3).strip(), m.group(4).strip()))
    return out


def trend(text, today):
    rows = entries(text)
    wk = today - datetime.timedelta(days=6)
    lw = wk - datetime.timedelta(days=7)
    this_c = [r for r in rows if r[1] == "corr" and wk <= r[0] <= today]
    last_c = [r for r in rows if r[1] == "corr" and lw <= r[0] < wk]
    this_g = [r for r in rows if r[1] == "good" and wk <= r[0] <= today]
    count = {}
    for r in rows:
        if r[1] == "corr" and r[0] <= today:
            count[r[2]] = count.get(r[2], 0) + 1
    repeats = sorted({r[2] for r in this_c if count[r[2]] >= 2})
    return {"week_start": wk.isoformat(), "corrections": len(this_c), "last_week": len(last_c),
            "confirmations": len(this_g), "repeats": {k: count[k] for k in repeats}}


def trend_line(t):
    rep = ", ".join("%s x%d" % (k, n) for k, n in t["repeats"].items()) or "none"
    rep_zh = "、".join("%s ×%d" % (k, n) for k, n in t["repeats"].items()) or "沒有"
    arrow = "down" if t["corrections"] < t["last_week"] else "up" if t["corrections"] > t["last_week"] else "same"
    arrow_zh = {"down": "減少", "up": "增加", "same": "持平"}[arrow]
    return ("Week from %s: %d corrections (last week %d, %s), %d confirmations; kinds that came back: %s."
            % (t["week_start"], t["corrections"], t["last_week"], arrow, t["confirmations"], rep),
            "%s 起這週：被糾正 %d 次（上週 %d，%s），做對被確認 %d 次；同一類又出現：%s。"
            % (t["week_start"], t["corrections"], t["last_week"], arrow_zh, t["confirmations"], rep_zh))


def group(text, since):
    """{kind: [(date, corr|good, words), ...]} for lines on or after `since`, biggest group first."""
    out = {}
    for d, what, kind, said in entries(text):
        if d >= since:
            out.setdefault(kind, []).append((d, what, said))
    return dict(sorted(out.items(), key=lambda kv: (-len(kv[1]), kv[0])))


def prefs(text):
    """Lines of the sorted-preferences section (the first '## ' heading naming preferences)."""
    lines, on, out = text.splitlines(), False, []
    for l in lines:
        if l.startswith("## "):
            on = ("偏好" in l or "preference" in l.lower())
            continue
        if on and l.strip().startswith("- "):
            out.append(l.strip()[2:])
    return out


def starter(line):
    """A starter preference the kit ships (tagged as from the original author); the user's own are not."""
    return line.rstrip().endswith(STARTER_TAGS)


def add_pref(kind, sentence, today=None):
    p = note()
    if not p or not p.exists():
        sys.exit("no 和 AI 協作 note (%s)" % p)
    today = today or datetime.date.today()
    line = "- %s (%s; %s)" % (" ".join(sentence.split()), kind.replace("|", "/").strip(), today.isoformat())
    lines = p.read_text(encoding="utf-8").splitlines()
    head = next((i for i, l in enumerate(lines) if l.startswith("## ") and ("偏好" in l or "preference" in l.lower())), None)
    if head is None:
        sys.exit("no preferences section ('## ' heading with 偏好 or Preferences) in %s" % p)
    end = next((i for i in range(head + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    while end > head + 1 and not lines[end - 1].strip():
        end -= 1
    lines.insert(end, line)
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(line)


def stats(text, today):
    rows = entries(text)
    t = trend(text, today)
    return {"lines": len(rows), "corrections": sum(1 for r in rows if r[1] == "corr"),
            "confirmations": sum(1 for r in rows if r[1] == "good"), "corrections_this_week": t["corrections"],
            "last_week": t["last_week"], "repeats": t["repeats"],
            "preferences": sum(1 for x in prefs(text) if not starter(x)),
            "starter_preferences": sum(1 for x in prefs(text) if starter(x))}


def add(kind, what, said, today=None):
    p = note()
    if not p or not p.exists():
        sys.exit("no 和 AI 協作 note: create it from templates/和AI協作.md first (%s)" % p)
    today = today or datetime.date.today()
    text = p.read_text(encoding="utf-8")
    zh = "## 紀錄" in text  # the note is in the user's language; the kind word follows it
    k = kind.lower()
    if k not in CORR and k not in GOOD:
        sys.exit("kind: correction (糾正) or confirmed (做對)")
    kind = ("糾正" if zh else "correction") if k in CORR else ("做對" if zh else "confirmed")
    said = " ".join(said.strip().strip("「」\"").split())
    line = "- %s | %s | %s | 「%s」" % (today.isoformat(), kind, what.replace("|", "/").strip(), said)
    p.write_text(text.rstrip("\n") + "\n" + line + "\n", encoding="utf-8")
    print(line)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    a = sys.argv[1:]
    today = datetime.date.today()
    if "--now" in a:
        k = a.index("--now")
        today = datetime.date.fromisoformat(a[k + 1][:10])
        a = a[:k] + a[k + 2:]
    if a[:1] == ["add"] and len(a) == 4:
        add(a[1], a[2], a[3], today)
    elif a[:1] == ["trend"]:
        p = note()
        text = p.read_text(encoding="utf-8") if p and p.exists() else ""
        t = trend(text, today)
        en, zh = trend_line(t)
        print(en)
        print(zh)
        if t["repeats"]:
            print("Second time or more (hook candidates if a program can see them at the moment of action): "
                  + ", ".join(t["repeats"]))
    elif a[:1] == ["group"]:
        p = note()
        text = p.read_text(encoding="utf-8") if p and p.exists() else ""
        since = today - datetime.timedelta(days=6)
        if "--since" in a:
            since = datetime.date.fromisoformat(a[a.index("--since") + 1][:10])
        g = group(text, since)
        print("Lines since %s grouped by kind (%d kinds):" % (since.isoformat(), len(g)))
        for kind, rows in g.items():
            nc = sum(1 for r in rows if r[1] == "corr")
            print("- %s: %d (correction %d, confirmed %d)" % (kind, len(rows), nc, len(rows) - nc))
            for d, what, said in rows:
                print("    %s %s %s" % (d.isoformat(), "correction" if what == "corr" else "confirmed", said))
        have = [x for x in prefs(text) if not starter(x)]
        if have:
            print("Preferences already written (%d): " % len(have) + " / ".join(have))
        n_starter = sum(1 for x in prefs(text) if starter(x))
        if n_starter:
            print("Starter preferences from the kit still in the note: %d (the user may delete any)" % n_starter)
    elif a[:1] == ["pref"] and len(a) == 3:
        add_pref(a[1], a[2], today)
    elif a[:1] == ["stats"]:
        p = note()
        text = p.read_text(encoding="utf-8") if p and p.exists() else ""
        print(json.dumps(stats(text, today), ensure_ascii=False))
    elif a[:1] == ["path"]:
        print(note())
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
