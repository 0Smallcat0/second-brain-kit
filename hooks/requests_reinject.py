#!/usr/bin/env python3
"""Keep the user's words when a conversation gets long.

SessionStart (compact): after the conversation is summarised, put the user's own messages back,
word for word, so the original requests are never reduced to a paraphrase. The full list is also
saved to <SBK_HOME>/requests/<session>.md.

UserPromptSubmit (hand-over): when the conversation carries more than config "handover_tokens"
(default 150000) tokens, tell Claude once (and again every further 50000) to write the hand-over
into ONE fixed task.md (<SBK_HOME>/task.md for the Basic main conversation, <SBK_HOME>/entry/task.md
for the entry), save the user's words to <SBK_HOME>/requests/<session>.md, and record both in
<SBK_HOME>/state/handover.json. This is for conversations in a window (the Basic main conversation,
an entry the user types into). A kit session running in the background (the entry or a topic, live
routing) is told to write the hand-over into its own task.md and to say nothing to the user; the hook
flags it in <SBK_HOME>/state/handover_due.json and the alarm tick replaces it once that file is written
and the session is idle (entry/handover.py due). The user is never asked to open a conversation there.

SessionStart (startup, clear) in the notes folder or the entry folder: when a hand-over is waiting
in handover.json, say so and name the two files, so the new conversation continues without the user
having to say anything.
"""
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (add_context, config, conversation_tokens, find_vault, home, human_text,  # noqa: E402
                     iter_records, log, mode, read_input)

CAP = 8000          # additionalContext is limited to about 10000 characters
PER_MESSAGE = 1500
STEP = 50000


def collect(path):
    out = []
    for rec in iter_records(path):
        t = human_text(rec)
        if t:
            out.append(t)
    return out


def save(sid, msgs):
    try:
        d = home() / "requests"
        d.mkdir(parents=True, exist_ok=True)
        f = d / (sid + ".md")
        f.write_text("\n\n".join("## message %d\n\n%s" % (i + 1, m) for i, m in enumerate(msgs)),
                     encoding="utf-8")
        return str(f)
    except Exception:
        return ""


HAND_STATE = "handover.json"
HAND_DAYS = 7


def in_background():
    """True in a session Claude Code runs as a background job (it sets CLAUDE_JOB_DIR there);
    SBK_BACKGROUND=1 or 0 overrides (tests)."""
    forced = os.environ.get("SBK_BACKGROUND")
    if forced in ("0", "1"):
        return forced == "1"
    return bool(os.environ.get("CLAUDE_JOB_DIR"))


def scope_of(cwd):
    """Which conversation this is: 'entry' (the entry folder), 'topic:<name>' (a topic or the maintenance
    folder under managers/), 'main' (inside the notes folder) or None."""
    try:
        here = Path(cwd).resolve()
        entry = (home() / "entry").resolve()
        if here == entry or entry in here.parents:
            return "entry", entry / "task.md"
        managers = (home() / "managers").resolve()
        if managers in here.parents:
            name = here.relative_to(managers).parts[0]
            return "topic:" + name, managers / name / "task.md"
    except Exception:
        pass
    if find_vault(cwd):
        return "main", home() / "task.md"
    return None, None


def read_hand():
    try:
        return json.loads((home() / "state" / HAND_STATE).read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_hand(d):
    try:
        f = home() / "state" / HAND_STATE
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        pass


def handover_pickup(data):
    scope, _ = scope_of(data.get("cwd") or os.getcwd())
    if not scope or data.get("source") not in ("startup", "clear"):
        return
    hand = read_hand()
    rec = hand.get(scope)
    if not rec or rec.get("picked") or rec.get("session") == data.get("session_id"):
        return
    if time.time() - float(rec.get("ts", 0)) > HAND_DAYS * 86400:
        return
    if not Path(rec.get("task", "")).exists():
        return
    rec["picked"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    hand[scope] = rec
    write_hand(hand)
    add_context("SessionStart",
                "[second-brain-kit] A hand-over is waiting from the earlier long conversation (%s). Read %s "
                "first (what is decided, half done and next), then the user's words in %s, and carry on "
                "from there; the user does not have to say \"continue\". If the user starts something "
                "unrelated, do that instead." % (rec.get("date", ""), rec["task"], rec.get("words") or "the requests folder"))
    log("requests_reinject", "hand-over picked up (%s)" % scope)


def handover_notice(data, sid):
    path = data.get("transcript_path")
    if not path:
        return
    limit = int(config().get("handover_tokens", 150000))
    n = conversation_tokens(path)
    if n < limit:
        return
    level = (n - limit) // STEP
    state = home() / "state" / "handover_notice.json"
    try:
        seen = json.loads(state.read_text(encoding="utf-8"))
    except Exception:
        seen = {}
    if seen.get(sid, -1) >= level:
        return
    seen[sid] = level
    try:
        state.parent.mkdir(parents=True, exist_ok=True)
        state.write_text(json.dumps(seen), encoding="utf-8")
    except Exception:
        pass
    saved = save(sid, collect(path))
    scope, task = scope_of(data.get("cwd") or os.getcwd())
    if scope and scope != "main" and in_background() and config().get("routing") == "live":
        name = "entry" if scope == "entry" else scope.split(":", 1)[1]
        flag = home() / "state" / "handover_due.json"
        try:
            due = json.loads(flag.read_text(encoding="utf-8"))
        except Exception:
            due = {}
        due[name] = {"ts": time.time(), "session": str(data.get("session_id") or "")}
        try:
            flag.write_text(json.dumps(due, indent=1), encoding="utf-8")
        except Exception:
            pass
        add_context("UserPromptSubmit",
                    "This conversation now carries about %dk tokens (hand-over threshold %dk). After answering "
                    "this message, hand over: update %s (create it if missing; top section \"Now\" within 40 "
                    "lines: decisions still in force with the user's words and dates, work half done, background "
                    "jobs and their output paths, next steps and dates; finished items one line each under "
                    "\"Closed\", the long text appended to task-archive.md next to it). The user's words are "
                    "saved in %s. Say nothing about this to the user and do not ask them to open anything: once "
                    "the file is written and you are idle, the kit replaces this conversation with a fresh one "
                    "of the same name that reads it."
                    % (n // 1000, limit // 1000, task, saved or "the requests folder"))
        log("requests_reinject", "hand-over notice at %d tokens (%s, background: flagged for the tick)" % (n, name))
        return
    if scope:
        hand = read_hand()
        hand[scope] = {"task": str(task), "words": saved, "date": time.strftime("%Y-%m-%d"),
                       "ts": time.time(), "session": sid}
        write_hand(hand)
        where = "the hand-over file %s (create it if missing)" % task
        close = ("Then tell the user, in one line in their language, to start a new conversation: it picks "
                 "the hand-over up by itself, nothing has to be said.")
    else:
        where = "task.md in this folder"
        close = ("Then tell the user, in one line in their language, to start a new conversation in the "
                 "same folder and say \"continue\"; the new one reads task.md and that file.")
    add_context("UserPromptSubmit",
                "This conversation now carries about %dk tokens (hand-over threshold %dk). After answering "
                "this message, hand over: update %s (top section \"Now\" within 40 lines: "
                "decisions still in force with the user's words and dates, work half done, next steps; "
                "finished items one line each under \"Closed\", the long text appended to task-archive.md "
                "next to it). The user's words are saved in %s. %s"
                % (n // 1000, limit // 1000, where, saved or "the requests folder", close))
    log("requests_reinject", "hand-over notice at %d tokens" % n)


def main():
    data = read_input()
    if mode("requests_reinject", "warn") == "off":
        return
    sid = re.sub(r"[^A-Za-z0-9_-]", "", str(data.get("session_id") or "session"))[:60] or "session"
    if data.get("hook_event_name") == "UserPromptSubmit":
        return handover_notice(data, sid)
    if data.get("source") in ("startup", "resume", "clear", "fork"):
        return handover_pickup(data)
    path = data.get("transcript_path")
    if not path:
        return
    msgs = collect(path)
    if not msgs:
        return
    saved = save(sid, msgs)

    def clip(m):
        return m if len(m) <= PER_MESSAGE else m[:PER_MESSAGE] + " ...[cut; full text in the saved file]"

    keep = {0}
    used = len(clip(msgs[0])) + 40
    for i in range(len(msgs) - 1, 0, -1):
        n = len(clip(msgs[i])) + 40
        if used + n > CAP:
            break
        keep.add(i)
        used += n
    lines = ["[The conversation was just compacted. These are the user's own messages, verbatim, "
             "oldest first. Treat them as the source of truth for what was asked; the summary may "
             "have lost or reworded requirements. Re-read them before continuing.]"]
    for i, m in enumerate(msgs):
        if i in keep:
            lines.append("%d. %s" % (i + 1, clip(m)))
        elif i - 1 in keep:
            lines.append("... (earlier messages omitted here)")
    if saved:
        lines.append("[Full list: %s]" % saved)
    add_context("SessionStart", "\n".join(lines))
    log("requests_reinject", "reinjected %d of %d messages" % (len(keep), len(msgs)))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log("requests_reinject", "error: %r" % (e,))
    sys.exit(0)
