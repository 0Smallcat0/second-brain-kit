#!/usr/bin/env python3
"""The learning loop's numbers: what the user corrected and confirmed, from the 和 AI 協作 note.

    learn.py add 糾正|做對 "kind of mistake / way of working" "the user's own words"
    learn.py trend [--now 2000-01-31]       this week vs last week, kinds that came back, hook candidates
    learn.py path                           where the note is

The note is <vault>/00-09 系統與索引/03 和 AI 協作/03-01 和 AI 協作.md. Claude adds one line the moment
the user corrects it or confirms a way of working (Basic and Full alike):
    - 2000-01-31 | 糾正 | 沒驗證就說做完 | 「你根本沒打開檔案看」
    - 2000-01-31 | 做對 | 先查筆記再答 | 「對，就是這樣」
"糾正" = correction, "做對" = confirmed (English "correction" / "confirmed" are read too). Before acting,
"check the notes first" reads this note: the sorted preferences at the top and the recent lines.
In Full, Maintenance's weekly review runs `trend`, groups the week's lines by kind and turns them into
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


def add(kind, what, said, today=None):
    p = note()
    if not p or not p.exists():
        sys.exit("no 和 AI 協作 note: create it from templates/和AI協作.md first (%s)" % p)
    today = today or datetime.date.today()
    kind = "糾正" if kind.lower() in CORR else "做對" if kind.lower() in GOOD else sys.exit("kind: 糾正 or 做對")
    said = said.strip().strip("「」")
    line = "- %s | %s | %s | 「%s」" % (today.isoformat(), kind, what.replace("|", "/").strip(), said.replace("\n", " "))
    text = p.read_text(encoding="utf-8")
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
    elif a[:1] == ["path"]:
        print(note())
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
