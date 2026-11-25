#!/usr/bin/env python3
"""Keep the user's words when a conversation gets long.

SessionStart (compact): after the conversation is summarised, put the user's own messages back,
word for word, so the original requests are never reduced to a paraphrase. The full list is also
saved to <SBK_HOME>/requests/<session>.md.

UserPromptSubmit (hand-over): when the conversation carries more than config "handover_tokens"
(default 150000) tokens, tell Claude once (and again every further 50000) to write the hand-over
into task.md, save the user's words to <SBK_HOME>/requests/<session>.md, and tell the user to start
a new conversation in the same folder and say "continue". This is for conversations in a window
(the Basic main conversation, an entry the user types into); background sessions are replaced by
entry/handover.py without the user.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (add_context, config, conversation_tokens, home, human_text,  # noqa: E402
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
    add_context("UserPromptSubmit",
                "This conversation now carries about %dk tokens (hand-over threshold %dk). After answering "
                "this message, hand over: update task.md in this folder (top section \"Now\" within 40 lines: "
                "decisions still in force with the user's words and dates, work half done, next steps; "
                "finished items one line each under \"Closed\", the long text appended to task-archive.md). "
                "The user's words are saved in %s. Then tell the user, in one line in their language, to "
                "start a new conversation in the same folder and say \"continue\"; the new one reads task.md "
                "and that file." % (n // 1000, limit // 1000, saved or "the requests folder"))
    log("requests_reinject", "hand-over notice at %d tokens" % n)


def main():
    data = read_input()
    if mode("requests_reinject", "warn") == "off":
        return
    sid = re.sub(r"[^A-Za-z0-9_-]", "", str(data.get("session_id") or "session"))[:60] or "session"
    if data.get("hook_event_name") == "UserPromptSubmit":
        return handover_notice(data, sid)
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
