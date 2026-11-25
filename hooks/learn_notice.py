#!/usr/bin/env python3
"""UserPromptSubmit hook: the learning loop's trigger.

When the user's message looks like a correction ("不對", "我說過", "that's not what I asked") or a
confirmation ("就是這樣", "這樣可以", "perfect, that's it"), it adds one line of context reminding
Claude to write ONE line this turn into the 和 AI 協作 note with entry/learn.py:
    - date | correction or confirmed | kind | "the user's words"
It names the kinds already in the note so the same kind gets the same name (that is what lets the
weekly review count repeats). Claude decides whether the message really is one; the hook only reminds.

SessionStart (startup, resume, compact): puts the note's sorted preferences into the conversation, so
every new session follows them without first having to open the note.

Mode: config.json "modes": {"learn_notice": "warn"} (default, Basic and Full: remind only);
"log" = only write logs/learn_notice.log; "off" = nothing. Silent when no 和 AI 協作 note exists.
Fails open.

    learn_notice.py --replay FILE [FILE...]   (no hook) classify each message and print the hit rate.
        FILE is a .jsonl transcript (the user's typed messages are read) or a text file with one
        message per line. Use it before trusting a change to the phrase lists.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (add_context, config, find_vault, home, human_text, iter_records,  # noqa: E402
                     log, mode, read_input)

REL = Path("00-09 系統與索引") / "03 和 AI 協作" / "03-01 和 AI 協作.md"
LINE = re.compile(r"^-\s*\d{4}-\d{2}-\d{2}\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|")
HEAD = 600          # long pasted messages: only the user's own opening is read
MAX_KINDS = 12
SHORT = 200        # a confirmation is only looked for in a short message
MAX_PREFS_CHARS = 3000  # SessionStart: the preferences put into the conversation, at most

CORRECTION = [
    r"(?<!對)不對(?!稱|應|外|面)",                    # not 對不對 ("right?"), 不對稱
    r"(?<!沒)錯了|搞錯|弄錯|你錯|寫錯|改錯|看錯|做錯",
    r"(?<!是)不是這樣|不是這個意思|不是我要的|不是我說的|我不是(?:說|要)",
    r"我(?:剛剛?|已經|之前|早就)?(?:說|講)過|跟你(?:說|講)過|說了(?:幾|好幾|多少)次",
    r"(?:你|怎麼)又(?!是誰)|又(?:錯|忘|漏|犯|沒|來了)",
    r"不要再|別再|不准再",
    r"你(?:根本|都|還是|又|也)?沒(?:有)?(?:改|做|看|讀|驗|測|跑|存|記|照|打開|開|檢查|確認|給|列|放|寫|處理|附)",
    r"還是(?:錯|不對|沒(?:改|好|變)|一樣)",
    r"我(?:之前|剛剛|剛才|已經)?不是(?:有)?(?:說過|講過|讓你|叫你|要你|請你)",
    r"搞什麼|到底在(?:搞|幹|做什麼)|不夠(?:全面|仔細|完整)|(?:你|都|還|根本)沒(?:有)?做(?:好|完)(?!了?[嗎?？的])",
    r"下次(?:你)?(?:應該|要記得|記得|不要|別)|你(?:應該|要)自己|你(?:不應該|不該)|回去(?:檢查|看|改|重做)",
    r"(?i)\bthat'?s (?:wrong|not (?:it|right|what i (?:asked|said|wanted|meant)))",
    r"(?i)\bnot what i (?:asked|said|wanted|meant)\b",
    r"(?i)\bi (?:already |just )?told you\b|\bi (?:already|just) said\b|\bas i said\b",
    r"(?i)\byou (?:didn'?t|did not|forgot|missed|ignored)\b",
    r"(?i)\b(?:same|this) (?:mistake|error) again\b|\byou did it again\b|\bnot again\b",
    r"(?i)\b(?:don'?t|do not|never)\b[^.?!\n]{0,30}\bagain\b|\bstop (?:doing|adding|using|asking)\b",
    r"(?i)(?<!what )(?<!what's )\b(?:that'?s|it'?s|this is|still) (?:wrong|incorrect|broken)\b",
    r"(?i)^\s*no[,.!]\s+(?:i|you|that|it|not)\b",
]
CONFIRMED = [
    r"很好|很棒|太好了|做得好|好棒|很讚|超讚|好讚|^\s*讚|完美|沒錯(?!誤)",
    r"(?:這次|終於|現在|這樣|全部|都)對了",
    r"就是這樣|就是這個|這樣就對|這樣(?:就)?可以(?![嗎吧?？])|可以了(?![嗎吧?？])|這個好",
    r"(?i)^\s*(?:perfect|exactly)\b|\bexactly what i (?:wanted|meant|asked)\b"
    r"|\b(?:spot on|you got it|well done|nice work|nice job|good job|great job)\b",
    r"(?i)\bthat'?s (?:right|it|correct|perfect|great)\b|\bthis (?:works|is (?:right|great|perfect))\b",
    r"(?i)\b(?:works|working) now\b|\blooks (?:good|great|right)\b",
]
CORR_RE = [re.compile(p) for p in CORRECTION]
GOOD_RE = [re.compile(p) for p in CONFIRMED]
QUOTED = re.compile(r"```.*?```|`[^`\n]*`|「[^」\n]*」|\"[^\"\n]*\"|<[a-z_-]+>.*?</[a-z_-]+>", re.S)


def clean(text):
    text = text if len(text) <= HEAD * 2 else text[:HEAD]
    text = QUOTED.sub(" ", text)       # quoted words are not the user correcting this session
    return "\n".join(l for l in text.splitlines() if not l.lstrip().startswith(">"))


def classify(text):
    """('correction'|'confirmed'|None, matched phrase). A correction wins when both appear."""
    t = clean(text or "")
    for kind, pats in (("correction", CORR_RE), ("confirmed", GOOD_RE)):
        if kind == "confirmed" and len(t.strip()) > SHORT:
            continue                   # praise is short; a long message is a new request
        for p in pats:
            m = p.search(t)
            if m:
                return kind, m.group(0).strip()
    return None, ""


def note_path(data):
    v = config().get("vault")
    p = Path(v) / REL if v else None
    if p and p.exists():
        return p
    found = find_vault(data.get("cwd"))
    p = found / REL if found else None
    return p if p and p.exists() else None


def known_kinds(p):
    count = {}
    try:
        for line in p.read_text(encoding="utf-8").splitlines():
            m = LINE.match(line.strip())
            if m:
                count[m.group(2)] = count.get(m.group(2), 0) + 1
    except Exception:
        pass
    return sorted(count, key=lambda k: -count[k])[:MAX_KINDS]


def learn_cmd():
    p = home() / "bin" / "learn.py"
    if p.exists():
        return "python \"%s\"" % p.as_posix()
    kit = Path(__file__).resolve().parent.parent / "entry" / "learn.py"
    return "python \"%s\"" % kit.as_posix()


def message(kind, hit, note, kinds):
    what = "a correction" if kind == "correction" else "a confirmation of a way of working"
    names = ("Kinds already in the note (reuse one if it fits, word for word): " + "; ".join(kinds) + "."
             if kinds else "The note has no lines yet; name the kind in a few words the user would use.")
    return ("[second-brain-kit learning loop] The user's message looks like %s (matched \"%s\"). If it is one "
            "about your work in this conversation, write ONE line this turn in the 和 AI 協作 note (%s): "
            "%s add %s \"<kind: a short fixed name>\" \"<the user's words, verbatim>\". %s If it is not "
            "(a question, a quote, about someone else), write nothing. Do not mention this reminder to the user."
            % (what, hit, note.as_posix(), learn_cmd(), kind, names))


def replay(paths):
    sys.stdout.reconfigure(encoding="utf-8")
    total = 0
    hits = {"correction": [], "confirmed": []}
    for f in paths:
        msgs = []
        if f.endswith(".jsonl"):
            msgs = [t for t in (human_text(r) for r in iter_records(f)) if t]
        else:
            msgs = [l.strip() for l in Path(f).read_text(encoding="utf-8-sig").splitlines()
                    if l.strip() and not l.startswith("#")]
        for m in msgs:
            total += 1
            kind, hit = classify(m)
            if kind:
                hits[kind].append((hit, m))
    n = len(hits["correction"]) + len(hits["confirmed"])
    print("messages %d, hits %d (%.1f%%): correction %d, confirmed %d"
          % (total, n, 100.0 * n / total if total else 0, len(hits["correction"]), len(hits["confirmed"])))
    for kind in ("correction", "confirmed"):
        for hit, m in hits[kind]:
            print("  %s [%s] %s" % (kind, hit, m.replace("\n", " ")[:120]))


def preferences(p):
    """Bullet lines of the sorted-preferences section (first '## ' heading naming 偏好 or preferences)."""
    out, on = [], False
    for l in p.read_text(encoding="utf-8").splitlines():
        if l.startswith("## "):
            on = "偏好" in l or "preference" in l.lower()
            continue
        if on and l.strip().startswith("- "):
            out.append(l.strip())
    return out


def session_start(data, m):
    """At startup, resume and after compaction: put the sorted preferences into the conversation, so a
    new session follows them without having to remember to open the note (E2E 0.2.6: a fresh session
    did not open the note on its own and broke a preference written the day before)."""
    note = note_path(data)
    if not note or m == "log":
        return
    prefs = preferences(note)
    if not prefs:
        return
    text, used = [], 0
    for l in prefs:
        if used + len(l) > MAX_PREFS_CHARS:
            text.append("- (more in the note)")
            break
        text.append(l)
        used += len(l)
    add_context("SessionStart",
                "[second-brain-kit preferences] The user's sorted preferences from the 和 AI 協作 note (%s), "
                "written with their agreement. Follow them in this whole conversation; recent lines are in the "
                "note's 紀錄 section.\n%s" % (note.as_posix(), "\n".join(text)))


def main():
    if "--replay" in sys.argv:
        return replay(sys.argv[sys.argv.index("--replay") + 1:])
    data = read_input()
    m = mode("learn_notice", "warn")
    if m == "off":
        return
    if data.get("hook_event_name") == "SessionStart":
        return session_start(data, m)
    kind, hit = classify(data.get("prompt") or "")
    if not kind:
        return
    note = note_path(data)
    if not note:
        return
    log("learn_notice", "%s %s: %s" % (m, kind, hit))
    if m == "log":
        return
    add_context("UserPromptSubmit", message(kind, hit, note, known_kinds(note)))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log("learn_notice", "error: %r" % (e,))
    sys.exit(0)
