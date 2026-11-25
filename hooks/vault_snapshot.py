#!/usr/bin/env python3
"""Stop hook: commit the notes Claude changed, so git really records every change (a program does it,
not a rule Claude may forget).

Runs when a reply ends and the session's folder is inside a vault (.sbk-vault) that is a git repository:
`git add` of the files git reports as changed or new, then one commit "snapshot ...". Nothing is
pushed. The vault's own pre-commit check (scripts/check_overwrite.py) still runs, so a commit that
shrinks a note is refused and only logged. Files git ignores stay out.

Mode (see _common.mode): warn (default: commit quietly) | log (only write the log line) | off.
"""
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import find_vault, log, mode, read_input  # noqa: E402

SKIP = (".sbk-setup-test/", "__pycache__/", ".sbk-vault")


def git(vault, *args, timeout=20):
    return subprocess.run(["git", "-C", str(vault), "-c", "core.quotepath=off"] + list(args),
                          capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)


def changed_files(vault):
    out = git(vault, "status", "--porcelain", "-z", "--untracked-files=all").stdout
    files = []
    parts = out.split("\0")
    i = 0
    while i < len(parts):
        e = parts[i]
        i += 1
        if len(e) < 4:
            continue
        status, name = e[:2], e[3:]
        if "R" in status or "C" in status:
            i += 1  # the old name follows
        if not any(s in name for s in SKIP):
            files.append(name)
    return files


def main():
    m = mode("vault_snapshot", "warn")
    if m == "off":
        return
    data = read_input()
    if data.get("stop_hook_active"):
        return
    vault = find_vault(data.get("cwd") or os.getcwd())
    if not vault or not (vault / ".git").exists():
        return
    files = changed_files(vault)
    if not files:
        return
    if m != "warn":
        log("vault_snapshot", "%s: would commit %d file(s)" % (m, len(files)))
        return
    r = git(vault, "add", "--", *files)
    if r.returncode != 0:
        log("vault_snapshot", "add failed: %s" % r.stderr.strip()[:200])
        return
    msg = "snapshot %s: %d file(s)" % (time.strftime("%Y-%m-%d %H:%M"), len(files))
    r = git(vault, "commit", "-q", "-m", msg, "--", *files, timeout=40)
    if r.returncode == 0:
        log("vault_snapshot", "committed %d file(s)" % len(files))
    else:
        log("vault_snapshot", "commit refused or failed: %s" % (r.stdout + r.stderr).strip()[:300])


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # fail open
        log("vault_snapshot", "error: %r" % (e,))
    sys.exit(0)
