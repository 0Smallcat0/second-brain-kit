#!/usr/bin/env python3
"""SessionStart + UserPromptSubmit hook: show a topic session what the entry sent it.

A manager session is simply Claude started inside <SBK_HOME>/managers/<name>/. This hook
notices that folder, and tells Claude (a) the unticked lines in <SBK_HOME>/inbox/<name>.md
and (b) how many open items its task.md has. In the entry folder it shows the tracker
summary instead. At SessionStart it always shows; on later prompts only when something new
arrived. Nothing is blocked. Off by default (Basic has no topic sessions); Advanced turns it on
with config.json "modes": {"inbox_notice": "warn"}.

At SessionStart (startup, resume, clear, fork and after compaction) it also puts the notes folder's own
rule file (AGENTS.md) into the conversation, word for word. A session under <SBK_HOME> has the notes
folder only attached (--add-dir): Claude Code does not load an attached folder's CLAUDE.md unless
CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD=1 is set, and even then does not follow an import inside
it (tested on 2.1.33x: a CLAUDE.md that is only "@AGENTS.md" brings nothing). "Read its AGENTS.md
first" in the session's CLAUDE.md was only a sentence; a program does it now.
"""
import hashlib
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import add_context, config, home, log, mode, read_input  # noqa: E402

OPEN = re.compile(r"^\s*- \[ \]")
CAP = 9500          # additionalContext is limited to about 10000 characters


def vault_rules(room):
    """The notes folder's AGENTS.md, word for word, within `room` characters; "" when there is none."""
    v = os.environ.get("SBK_VAULT") or config().get("vault")
    if not v:
        return ""
    p = Path(v) / "AGENTS.md"
    try:
        text = p.read_text(encoding="utf-8-sig").strip()
    except Exception:
        return ""
    if not text:
        return ""
    head = ("[second-brain-kit] The notes folder's rules (%s), word for word. They apply to everything you "
            "read or write in the notes folder:\n" % p.as_posix())
    room -= len(head) + 160
    more = ""
    if len(text) > room:
        cut = text.rfind("\n", 0, max(room, 0))
        shown = text[:cut if cut > 0 else max(room, 0)]
        more = ("\n[cut after line %d of %d: read the rest of %s before you work in the notes folder]"
                % (shown.count("\n") + 1, text.count("\n") + 1, p.as_posix()))
        text = shown
    return head + text + more


def open_lines(path, limit=10):
    try:
        lines = [l.rstrip() for l in path.read_text(encoding="utf-8").splitlines() if OPEN.match(l)]
    except Exception:
        return []
    return lines[:limit] if limit else lines


def which(cwd):
    root = home().resolve()
    try:
        rel = Path(cwd).resolve().relative_to(root)
    except Exception:
        return None, None
    parts = rel.parts
    if len(parts) >= 2 and parts[0] == "managers":
        return "manager", parts[1]
    if parts and parts[0] == "entry":
        return "entry", "entry"
    return None, None


def main():
    if mode("inbox_notice", "off") == "off":
        return
    data = read_input()
    role, name = which(data.get("cwd") or os.getcwd())
    if not role:
        return
    event = data.get("hook_event_name") or "SessionStart"
    parts = []
    if role == "manager":
        inbox = open_lines(home() / "inbox" / (name + ".md"))
        tasks = open_lines(home() / "managers" / name / "task.md", limit=0)
        if inbox:
            parts.append("Inbox from the entry (%d new). Move each into task.md, then tick it "
                         "in the inbox file:\n%s" % (len(inbox), "\n".join(inbox)))
        parts.append("task.md has %d open items. Report results to the entry (ledger.py done ... --evidence, "
                     "and SendMessage to \"entry\" if it is running), never to the user directly." % len(tasks))
    else:
        ledger = home() / "ledger.md"
        n, done = 0, []
        try:
            for l in ledger.read_text(encoding="utf-8").splitlines():
                if re.match(r"^- L\d+ \| (open|dispatched)", l):
                    n += 1
                elif re.match(r"^- L\d+ \| done \|", l):
                    done.append(l.strip()[:200])
        except Exception:
            pass
        parts.append("Tracker (ledger.md): %d items not closed. Run ledger.py list, route each to a topic "
                     "session, and close only with evidence." % n)
        if done:
            parts.append("Done by a topic session, waiting for your check (%d). Open the evidence itself; if it "
                         "holds, ledger.py verify Lxxxx --evidence \"what you opened\" and send the user one result "
                         "message (the result itself, not a report):\n%s" % (len(done), "\n".join(done[:10])))
    text = "\n".join(parts)
    sig = hashlib.md5(text.encode("utf-8")).hexdigest()
    state = home() / "state" / ("inbox_" + role + "_" + str(name) + ".txt")
    if event != "SessionStart":
        try:
            if state.read_text(encoding="utf-8") == sig:
                return
        except Exception:
            pass
    try:
        state.parent.mkdir(parents=True, exist_ok=True)
        state.write_text(sig, encoding="utf-8")
    except Exception:
        pass
    rules = vault_rules(CAP - len(text) - 2) if event == "SessionStart" else ""
    if rules:
        text = text + "\n\n" + rules
    add_context(event if event in ("SessionStart", "UserPromptSubmit") else "SessionStart", text)
    log("inbox_notice", "%s/%s injected%s" % (role, name, " (+notes rules)" if rules else ""))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log("inbox_notice", "error: %r" % (e,))
    sys.exit(0)
