#!/usr/bin/env python3
"""UserPromptSubmit hook: warn (never block) when weekly plan usage passes a threshold.

Warns once per session per weekly window. Silent when an API key is used, when no login
file exists (for example macOS keeps it in the keychain), or when the call fails.
The usage endpoint is the same one the /usage screen uses; it is not a documented API, so
this hook fails open and may stop working without notice.

Threshold: env SBK_USAGE_WARN_PCT or config.json "usage_warn_pct" (default 80).
Test without the network: SBK_USAGE_FAKE='{"seven_day":{"utilization":91,"resets_at":"2030-01-01T00:00:00Z"}}'
"""
import hashlib
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import add_context, config, home, log, mode, read_input  # noqa: E402

TTL = 180


def claude_dir():
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude")


def fetch():
    fake = os.environ.get("SBK_USAGE_FAKE")
    if fake:
        return json.loads(fake)
    tag = hashlib.md5(str(claude_dir()).encode("utf-8")).hexdigest()[:8]
    cache = home() / "state" / ("usage_" + tag + ".json")
    try:
        c = json.loads(cache.read_text(encoding="utf-8"))
        if time.time() - c.get("t", 0) < TTL:
            return c["data"]
    except Exception:
        pass
    creds = json.loads((claude_dir() / ".credentials.json").read_text(encoding="utf-8"))
    token = creds["claudeAiOauth"]["accessToken"]
    req = urllib.request.Request(
        "https://api.anthropic.com/api/oauth/usage",
        headers={"Authorization": "Bearer " + token, "anthropic-beta": "oauth-2025-04-20",
                 "User-Agent": "claude-code"})
    data = json.loads(urllib.request.urlopen(req, timeout=5).read().decode("utf-8"))
    try:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps({"t": time.time(), "data": data}), encoding="utf-8")
    except Exception:
        pass
    return data


def main():
    if mode("usage_warn", "warn") in ("off", "log") and not os.environ.get("SBK_USAGE_FAKE"):
        return
    if os.environ.get("ANTHROPIC_API_KEY") and not os.environ.get("SBK_USAGE_FAKE"):
        return
    event = read_input()
    limit = float(os.environ.get("SBK_USAGE_WARN_PCT") or config().get("usage_warn_pct") or 80)
    week = (fetch() or {}).get("seven_day") or {}
    pct = float(week.get("utilization"))
    if pct < limit:
        return
    key = str(week.get("resets_at"))
    sid = str(event.get("session_id") or "s")
    state = home() / "state" / "usage_warned.json"
    try:
        warned = json.loads(state.read_text(encoding="utf-8"))
    except Exception:
        warned = {}
    if warned.get(sid) == key:
        return
    warned[sid] = key
    try:
        state.parent.mkdir(parents=True, exist_ok=True)
        state.write_text(json.dumps(warned), encoding="utf-8")
    except Exception:
        pass
    add_context("UserPromptSubmit",
                "Weekly plan usage is at %d%% (resets %s). Finish what is open: save, record the "
                "next step in task.md, and do not start large new work. Mechanical work can go to "
                "another tool if the user has one." % (pct, key))
    log("usage_warn", "warned at %d%%" % pct)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log("usage_warn", "error: %r" % (e,))
    sys.exit(0)
