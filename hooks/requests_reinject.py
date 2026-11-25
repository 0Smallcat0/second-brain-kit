#!/usr/bin/env python3
"""SessionStart (compact) hook: after the conversation is summarised, put the user's own
messages back, word for word, so the original requests are never reduced to a paraphrase.

The full list is also saved to <SBK_HOME>/requests/<session>.md.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import add_context, home, human_text, iter_records, log, mode, read_input  # noqa: E402

CAP = 8000          # additionalContext is limited to about 10000 characters
PER_MESSAGE = 1500


def collect(path):
    out = []
    for rec in iter_records(path):
        t = human_text(rec)
        if t:
            out.append(t)
    return out


def main():
    data = read_input()
    if mode("requests_reinject", "warn") == "off":
        return
    path = data.get("transcript_path")
    if not path:
        return
    msgs = collect(path)
    if not msgs:
        return
    sid = re.sub(r"[^A-Za-z0-9_-]", "", str(data.get("session_id") or "session"))[:60] or "session"
    saved = ""
    try:
        d = home() / "requests"
        d.mkdir(parents=True, exist_ok=True)
        f = d / (sid + ".md")
        f.write_text("\n\n".join("## message %d\n\n%s" % (i + 1, m) for i, m in enumerate(msgs)),
                     encoding="utf-8")
        saved = str(f)
    except Exception:
        pass

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
