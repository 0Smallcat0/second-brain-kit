#!/usr/bin/env python3
"""Hand a long conversation over to a fresh one, without losing what was asked.

    handover.py check            every kit session running in the background: hand over the ones above
                                 the threshold that are idle (the alarm row "handover" runs this)
    handover.py size NAME        how many tokens the running session NAME carries now
    handover.py run NAME         hand NAME over now, whatever its size
    handover.py words FILE.jsonl OUT.md      write the user's words of one transcript to OUT.md

A session's state lives only in two files: its task.md and its words file. So a long conversation can
be replaced by a fresh one at any time:
  a) the running session is asked to write its hand-over into task.md (Now section within 40 lines:
     decisions still in force with the user's words and dates, work half done, next steps; finished
     items one line each under Closed, the long text appended to task-archive.md);
  b) once task.md has changed and the session is idle, the user's words (and the messages it got from
     the entry) are copied out of its transcript into old-<id>-words.md in its folder;
  c) the old session is stopped and removed from the list (its transcript stays on disk);
  d) a new session with the same name starts and reads task.md and the words file first.
Results: RENEWED, BUSY (it is working; try later), NO-HANDOVER (task.md did not change in time; the
old session is kept), NOT-RUNNING.
Size = the input of the session's last reply (input + cache read + cache creation + output tokens).
config.json: "handover_tokens" (default 150000), "handover_wait_min" (default 15).
Sessions in a window (the Basic main conversation, an entry the user typed into) cannot be replaced
by a script: hooks/requests_reinject.py tells Claude there to write the hand-over and tells the user
to start a new conversation and say "continue".
"""
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "hooks"))
import send  # noqa: E402
import session  # noqa: E402
from _common import conversation_tokens, human_text, iter_records  # noqa: E402

HAND = ("Hand-over before this conversation is replaced by a fresh one (handover.py). Update task.md in "
        "this folder now (create it if missing): rewrite the top section \"Now\" in at most 40 lines with "
        "the decisions still in force and the user's words that set them (verbatim, with dates), work half "
        "done, background jobs and their output paths, next steps and dates. Every finished item becomes "
        "one line (date, result, evidence path) under \"Closed\" at the bottom; before shortening, append "
        "the long text to task-archive.md in the same folder. Do only this, then stop. Do not reply to the "
        "entry and start nothing new.")


def claude_dir():
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")


def transcript(session_id):
    if not session_id:
        return None
    hits = list((claude_dir() / "projects").glob("*/" + session_id + ".jsonl"))
    return max(hits, key=lambda p: p.stat().st_mtime) if hits else None


def size_of(path):
    """Tokens the conversation carries: the usage of its last assistant reply."""
    return conversation_tokens(path)


def words(path, out, replies=20):
    """The user's words, messages from other sessions (the entry), and the last replies, oldest first."""
    mine, other, said = [], [], []
    for rec in iter_records(path):
        t = human_text(rec)
        if t and (t.startswith("You take over from the earlier conversation")
                  or (t.startswith("You are the ") and "of second-brain-kit, started in the background" in t[:80])):
            other.append(t[:3000])  # the start prompt session.py/handover.py wrote, not the user's words
            continue
        if t:
            mine.append(t)
            continue
        o = rec.get("origin")
        if rec.get("type") == "user" and isinstance(o, dict) and o.get("kind") not in (None, "human"):
            # a message from another session: Claude Code 2.1.3xx stores it with isMeta true, origin.kind "peer"
            # and the plain text in origin.body (seen in a real transcript); the hand-over request is not kept
            c = o.get("body") or (rec.get("message") or {}).get("content")
            if isinstance(c, str) and c.strip() and not c.startswith(HAND[:40]):
                other.append(c.strip()[:3000])
        if rec.get("type") == "assistant":
            for b in (rec.get("message") or {}).get("content") or []:
                if isinstance(b, dict) and b.get("type") == "text" and b.get("text", "").strip():
                    said.append(b["text"].strip()[:1500])
    parts = ["# Words carried over from conversation %s" % Path(path).stem,
             "", "## The user's own words (verbatim, oldest first)", ""]
    parts += ["%d. %s" % (i + 1, m) for i, m in enumerate(mine)] or ["(none)"]
    parts += ["", "## Messages from other sessions and the kit's start prompts (not the user's words)", ""]
    parts += ["- " + m for m in other] or ["(none)"]
    parts += ["", "## Last replies of the old conversation", ""]
    parts += ["- " + m for m in said[-replies:]] or ["(none)"]
    Path(out).write_text("\n".join(parts) + "\n", encoding="utf-8")
    return len(mine)


def threshold():
    return int(session.cfg().get("handover_tokens", 150000))


def run(name, wait_min=None):
    rows = session.running()
    old = session.find(name, rows)
    if not old:
        return "NOT-RUNNING: " + name
    if old["status"] == "busy":
        return "BUSY: %s is working" % name
    d = session.folder(name)
    task = d / "task.md"
    before = task.stat().st_mtime if task.exists() else 0
    if session.dry():
        return "RENEWED (dry run): %s" % name
    if not session.push(name, HAND):
        return "NO-HANDOVER: could not deliver the hand-over request to %s" % name
    wait = float(wait_min if wait_min is not None else session.cfg().get("handover_wait_min", 15))
    end = time.time() + wait * 60
    ok = False
    while time.time() < end:
        time.sleep(15)
        cur = session.find(name)
        changed = task.exists() and task.stat().st_mtime > before
        if changed and cur and cur["status"] == "idle":
            ok = True
            break
    if not ok:
        return "NO-HANDOVER: task.md of %s did not change within %g minutes; the old session is kept" % (name, wait)
    src = transcript(old["sessionId"])
    out = d / ("old-%s-words.md" % old["id"])
    n = words(src, out) if src else 0
    session.run_claude(["stop", old["id"]], timeout=60)
    for _ in range(30):
        if not session.find(name):
            break
        time.sleep(2)
    session.run_claude(["rm", old["id"]], timeout=60)
    first = ("You take over from the earlier conversation %s of this session (its transcript is kept; "
             "claude --resume %s finds it). Read task.md and %s first (the user's words and the last "
             "replies), then carry on with what task.md lists as open; if nothing is open, stop and wait."
             % (old["id"], old["sessionId"], out.name))
    rc = session.open_session(name, first, replace_ok=True)
    new = None
    for _ in range(30):  # claude agents lists a new background session a few seconds after it starts
        new = session.find(name)
        if new or rc != 0:
            break
        time.sleep(2)
    if rc != 0 or not new:
        return "RENEW-FAILED: %s stopped, the new one did not start (its work waits in task.md and the inbox)" % name
    return "RENEWED: %s %s -> %s, %d user messages kept in %s" % (name, old["id"], new["id"], n, out)


def check_all():
    """Background sessions above the threshold and idle are handed over; the rest are listed."""
    out = []
    limit = threshold()
    for r in session.running():
        if r.get("kind") and r["kind"] != "background":
            continue  # a window the user types into: the hook handles it
        src = transcript(r["sessionId"])
        n = size_of(src) if src else 0
        if n < limit:
            out.append("%s %dk (under %dk)" % (r["name"], n // 1000, limit // 1000))
            continue
        out.append(run(r["name"]))
    return "; ".join(out) if out else "no background sessions"


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    a = sys.argv[1:]
    if a[:1] == ["check"]:
        print(check_all())
    elif a[:1] == ["size"] and len(a) == 2:
        r = session.find(a[1])
        src = transcript(r["sessionId"]) if r else None
        print("%s: %s tokens (threshold %d)" % (a[1], size_of(src) if src else "not running /", threshold()))
    elif a[:1] == ["run"] and len(a) >= 2:
        res = run(a[1], float(a[a.index("--wait") + 1]) if "--wait" in a else None)
        print(res)
        sys.exit(0 if res.startswith("RENEWED") else 1)
    elif a[:1] == ["words"] and len(a) == 3:
        print("%d user messages -> %s" % (words(a[1], a[2]), a[2]))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
