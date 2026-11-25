#!/usr/bin/env python3
"""Stop hook: Claude said "done" but did not look at the result after its last edit.

Blocks ONCE (the second Stop in the same turn always passes), so it can never trap a
session. Admitting "not verified" in the reply also passes.

Replay on old transcripts before you trust a change to this file:
    python stop_evidence.py --replay path/to/transcript.jsonl
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import (assistant_blocks, emit, human_text, iter_records, log, mode,  # noqa: E402
                     read_input)

DONE = re.compile(
    r"\b(done|finished|completed|all set|fixed|implemented|is ready|are ready)\b"
    r"|已(經)?(完成|修好|修正|做完|處理好|寫好|建立|寄出|刪除)|完成了|做完了|搞定|修好了|都好了",
    re.I)
ADMIT = re.compile(r"not (yet )?(verified|checked|tested)|unverified|未驗證|沒驗證|還沒(驗|檢查|測)|尚未(驗證|檢查|測試)", re.I)
WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
READ_TOOLS = {"Read", "Grep", "Glob", "WebFetch", "WebSearch"}
BASH_WRITES = re.compile(
    r"(^|[\s;&|])(rm|mv|cp|mkdir|touch|tee|sed\s+-i|git\s+(commit|add|checkout|reset|push))\b"
    r"|>>?\s*\S|Set-Content|Out-File|Add-Content|New-Item|Remove-Item|Move-Item|Copy-Item", re.I)


def build_turns(path):
    turns = []
    for rec in iter_records(path):
        if human_text(rec) is not None:
            turns.append({"tools": [], "texts": []})
            continue
        if not turns:
            continue
        for b in assistant_blocks(rec):
            if b.get("type") == "text" and b.get("text", "").strip():
                turns[-1]["texts"].append(b["text"])
            elif b.get("type") == "tool_use":
                turns[-1]["tools"].append((b.get("name", ""), b.get("input") or {}))
    return turns


def is_write(name, inp):
    if name in WRITE_TOOLS:
        return True
    if name == "Bash":
        return bool(BASH_WRITES.search(str((inp or {}).get("command", ""))))
    return False


def is_check(name, inp):
    if name in READ_TOOLS:
        return True
    return name == "Bash" and not is_write(name, inp)


def verdict(turn, last_text=None):
    """Return None if fine, else the reason string."""
    text = last_text if last_text is not None else (turn["texts"][-1] if turn["texts"] else "")
    if not text or not DONE.search(text) or ADMIT.search(text):
        return None
    last_write = -1
    for i, (n, inp) in enumerate(turn["tools"]):
        if is_write(n, inp):
            last_write = i
    if last_write < 0:
        return None
    if any(is_check(n, inp) for n, inp in turn["tools"][last_write + 1:]):
        return None
    return ("You said the work is done, but nothing was opened, read back or run after your last "
            "edit. Check the real result now (open the file, run the test, load the page) and "
            "reply with the evidence: what you looked at and what you saw. If you cannot check "
            "something, say plainly which part is unverified.")


def replay(path):
    for i, t in enumerate(build_turns(path), 1):
        v = verdict(t)
        print("turn %3d  tools=%2d  %s" % (i, len(t["tools"]), ("BLOCK" if v else "ok")))


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--replay":
        replay(sys.argv[2])
        return
    data = read_input()
    m = mode("stop_evidence", "block")
    if m == "off" or data.get("stop_hook_active"):
        return
    path = data.get("transcript_path")
    if not path:
        return
    turns = build_turns(path)
    if not turns:
        return
    reason = verdict(turns[-1], data.get("last_assistant_message") or None)
    if not reason:
        return
    log("stop_evidence", "%s: %s" % (m, reason[:80]))
    if m == "block":
        emit({"decision": "block", "reason": reason})


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # fail open
        log("stop_evidence", "error: %r" % (e,))
    sys.exit(0)
