#!/usr/bin/env python3
"""EXPERIMENTAL: send one message to a stopped Claude session and let it answer in the background.

    wake_session.py SESSION_ID "message" [--name NAME] [--dry-run]

Runs `claude -p --resume SESSION_ID "message"` in the background and appends the reply to
<SBK_HOME>/logs/wake-<SESSION_ID>.log. Not exercised by scripts/selftest.py (needs a real
session and uses quota). It does not push text into a session that is open in a terminal.
Prefer entry/send.py: the inbox works whether or not the session is running.
"""
import os
import subprocess
import sys
from pathlib import Path


def main():
    a = sys.argv[1:]
    dry = "--dry-run" in a
    a = [x for x in a if x != "--dry-run"]
    if len(a) < 2:
        sys.exit(__doc__)
    sid, msg = a[0], a[1]
    home = Path(os.environ.get("SBK_HOME") or Path.home() / ".claude" / "sbk")
    log = home / "logs" / ("wake-" + sid[:12] + ".log")
    cmd = ["claude", "-p", "--resume", sid, msg]
    env = dict(os.environ)
    env.pop("CLAUDE_CODE_OAUTH_TOKEN", None)
    env.pop("ANTHROPIC_API_KEY", None)
    if dry:
        print(" ".join(cmd))
        print("log:", log)
        return
    log.parent.mkdir(parents=True, exist_ok=True)
    out = open(log, "ab")
    subprocess.Popen(cmd, stdout=out, stderr=subprocess.STDOUT, env=env,
                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    print("started; log:", log)


if __name__ == "__main__":
    main()
