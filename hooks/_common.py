"""Shared helpers for the second-brain-kit hooks. Python 3 standard library only.

Every hook is fail-open: if anything in here raises, the hook exits 0 and Claude carries on.
"""
import json
import os
import sys
import time
from pathlib import Path

MODES = {"off", "log", "warn", "ask", "deny", "block"}


def home():
    """Runtime folder: ledger, alarms, routes, inbox, logs. Override with SBK_HOME."""
    env = os.environ.get("SBK_HOME")
    return Path(env) if env else Path.home() / ".claude" / "sbk"


def read_input():
    try:
        raw = sys.stdin.buffer.read().decode("utf-8-sig", "replace")
        return json.loads(raw) if raw.strip() else {}
    except Exception:
        return {}


def config():
    try:
        return json.loads((home() / "config.json").read_text(encoding="utf-8"))
    except Exception:
        return {}


def mode(name, default):
    """How strict a hook is. Order: env SBK_MODE_<NAME>, config.json modes.<name>, default.

    off   = do nothing
    log   = only write a line to the log (use this first when a check is new)
    warn  = tell Claude, never stop it
    ask   = ask the user to confirm (PreToolUse)
    deny  = refuse the tool call and tell Claude why (PreToolUse)
    block = stop Claude from finishing once (Stop)
    """
    val = os.environ.get("SBK_MODE_" + name.upper())
    if not val:
        val = (config().get("modes") or {}).get(name)
    return val if val in MODES else default


def log(name, message):
    try:
        d = home() / "logs"
        d.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y-%m-%dT%H:%M:%S")
        with open(d / (name + ".log"), "a", encoding="utf-8") as f:
            f.write(stamp + " " + message.replace("\n", " ")[:500] + "\n")
    except Exception:
        pass


def emit(obj):
    sys.stdout.buffer.write((json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8"))
    sys.stdout.flush()


def pretool(decision, reason):
    """Answer a PreToolUse hook. decision: ask | deny."""
    emit({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": decision,
        "permissionDecisionReason": reason}})


def add_context(event, text):
    emit({"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}})


def find_vault(start=None):
    """The vault is the folder holding a file named .sbk-vault."""
    env = os.environ.get("SBK_VAULT") or config().get("vault")
    if env and (Path(env) / ".sbk-vault").exists():
        return Path(env)
    try:
        p = Path(start or os.getcwd()).resolve()
    except Exception:
        return None
    for d in [p] + list(p.parents):
        if (d / ".sbk-vault").exists():
            return d
    return None


# ---------- transcript helpers ----------

def iter_records(path):
    try:
        with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except Exception:
                    continue
    except Exception:
        return


SKIP_PREFIXES = ("<system-reminder>", "<command-", "<local-command", "<task-notification",
                 "Caveat:", "[Request interrupted", "<bash-", "<user-prompt-submit-hook>")


def human_text(rec):
    """Return the text the person typed, or None if this record is not a human message."""
    if rec.get("type") != "user":
        return None
    if rec.get("isMeta") or rec.get("isSidechain") or rec.get("isCompactSummary"):
        return None
    origin = rec.get("origin")
    if isinstance(origin, dict) and origin.get("kind") not in (None, "human"):
        return None
    content = (rec.get("message") or {}).get("content")
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
            return None
        text = "\n".join(b.get("text", "") for b in content
                         if isinstance(b, dict) and b.get("type") == "text")
    else:
        return None
    text = text.strip()
    if not text or text.startswith(SKIP_PREFIXES):
        return None
    return text


def assistant_blocks(rec):
    if rec.get("type") != "assistant":
        return []
    content = (rec.get("message") or {}).get("content")
    return [b for b in content if isinstance(b, dict)] if isinstance(content, list) else []
