#!/usr/bin/env python3
"""Pre-commit guard: do not let a commit silently destroy notes.

Looks at what is staged and refuses when it would
  1. delete or rename a protected file,
  2. rewrite most of an existing text file (>= 8 lines removed AND >= 50% of its old lines), or
  3. replace a committed binary file (image, pdf, ...) with different bytes.

Protected: anything listed in <repo>/.sbk-protect (one path or folder/ prefix per line) plus
AGENTS.md. Deliberate change: SBK_ALLOW_OVERWRITE=1 git commit ...  (or create the empty
file .git/SBK_UNLOCK for one commit; it is removed afterwards).
"""
import os
import subprocess
import sys
from pathlib import Path

DEL_MIN = 8
DEL_RATIO = 0.5
TEXT_EXT = {".md", ".txt", ".py", ".json", ".yml", ".yaml", ".csv", ".sh", ".ps1", ".toml"}


def git(*args):
    r = subprocess.run(["git"] + list(args), capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return r.stdout


def protected(repo):
    items = ["AGENTS.md"]
    try:
        for line in (repo / ".sbk-protect").read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                items.append(line.replace("\\", "/"))
    except Exception:
        pass
    return items


def is_protected(path, items):
    return any(path == p or (p.endswith("/") and path.startswith(p)) for p in items)


def in_head(path):
    return subprocess.run(["git", "cat-file", "-e", "HEAD:" + path],
                          capture_output=True).returncode == 0


def main():
    top = git("rev-parse", "--show-toplevel").strip()
    if not top:
        return 0
    repo = Path(top)
    unlock = repo / ".git" / "SBK_UNLOCK"
    if os.environ.get("SBK_ALLOW_OVERWRITE") == "1" or unlock.exists():
        if unlock.exists():
            try:
                unlock.unlink()
            except OSError:
                pass
        return 0
    problems = []
    items = protected(repo)
    status = git("diff", "--cached", "--name-status", "-M", "-z").split("\0")
    i = 0
    while i < len(status) - 1:
        code = status[i]
        if code.startswith("R"):
            old = status[i + 1]
            if is_protected(old, items):
                problems.append("protected file renamed: " + old)
            i += 3
            continue
        path = status[i + 1]
        if code == "D" and is_protected(path, items):
            problems.append("protected file deleted: " + path)
        i += 2
    for line in git("diff", "--cached", "--numstat", "-M").splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        added, removed, path = parts
        if "=>" in path:
            continue
        if added == "-":  # binary
            if in_head(path) and (repo / path).exists():
                problems.append("committed binary replaced: " + path)
            continue
        if Path(path).suffix.lower() not in TEXT_EXT or not in_head(path):
            continue
        old_lines = len(git("show", "HEAD:" + path).splitlines())
        rem = int(removed)
        if old_lines and rem >= DEL_MIN and rem >= old_lines * DEL_RATIO:
            problems.append("most of %s rewritten (%d of %d old lines removed)" % (path, rem, old_lines))
    if problems:
        sys.stderr.write("check_overwrite: commit refused\n  " + "\n  ".join(problems) + "\n"
                         "If this is intended: SBK_ALLOW_OVERWRITE=1 git commit ...\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
