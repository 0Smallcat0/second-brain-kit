#!/usr/bin/env python3
"""PreToolUse hook (Bash, Write, Edit, MultiEdit): ask before things that are hard to undo.

Bash:   git push, skipping git hooks (--no-verify), destructive git (reset --hard, clean -f,
        checkout -- ., restore ., branch -D, stash drop/clear), recursive deletes.
Files:  the vault's protected files (AGENTS.md, CLAUDE.md, the rules folder 01 規則, scripts/,
        .sbk-vault, .git/ and any prefix listed in <vault>/.sbk-protect), Claude's own settings / CLAUDE.md, and a Write
        that would replace most of an existing vault note with something much shorter.

Mode (see _common.mode): ask (default) | deny | log | off.
"""
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import find_vault, log, mode, pretool, read_input  # noqa: E402

BASH_RULES = [
    (re.compile(r"\bgit\s+(-\S+\s+\S+\s+)*push\b"), "git push publishes work outside this machine."),
    (re.compile(r"--no-verify\b|--no-gpg-sign\b|commit\.gpgsign\s*=\s*false"),
     "This skips the git safety hooks."),
    (re.compile(r"\bgit\s+reset\s+--hard\b|\bgit\s+clean\s+-\S*f|\bgit\s+checkout\s+(--\s+)?\.(\s|$)"
                r"|\bgit\s+restore\s+(?!--staged)\S*\.(\s|$)|\bgit\s+branch\s+-D\b"
                r"|\bgit\s+stash\s+(drop|clear)\b"),
     "This git command throws work away."),
    (re.compile(r"\brm\s+-\S*[rR]|\bRemove-Item\b[^\n]*-Recurse|\brmdir\s+/s\b|\bdel\s+/s\b", re.I),
     "This deletes a whole folder tree."),
]
DEFAULT_PROTECTED = ("AGENTS.md", "CLAUDE.md", "scripts/", ".sbk-vault", ".git/", "00-09 系統與索引/01 規則/")
CLAUDE_FILES = {"settings.json", "settings.local.json", "CLAUDE.md"}


def norm(p):
    return str(p).replace("\\", "/")


def decide(reason):
    m = mode("vault_guard", "ask")
    log("vault_guard", "%s: %s" % (m, reason))
    if m in ("ask", "deny"):
        pretool(m, reason)


def check_bash(cmd):
    for seg in re.split(r"&&|\|\||;|\n", cmd):
        for rx, why in BASH_RULES:
            if rx.search(seg):
                return decide(why + " Command: " + seg.strip()[:160])


def protected_list(vault):
    items = list(DEFAULT_PROTECTED)
    try:
        for line in (vault / ".sbk-protect").read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                items.append(norm(line))
    except Exception:
        pass
    return items


def check_file(tool, inp, cwd):
    raw = inp.get("file_path") or inp.get("notebook_path")
    if not raw:
        return
    path = Path(raw)
    if not path.is_absolute():
        path = Path(cwd) / path
    try:
        path = path.resolve()
    except Exception:
        return
    claude_home = Path(os.environ.get("CLAUDE_CONFIG_DIR") or Path.home() / ".claude").resolve()
    if path.name in CLAUDE_FILES and norm(path).startswith(norm(claude_home)):
        return decide("This changes how every Claude session behaves: " + path.name)
    vault = find_vault(path.parent if path.parent.exists() else cwd)
    if not vault:
        return
    try:
        rel = norm(path.relative_to(vault.resolve()))
    except ValueError:
        return
    for p in protected_list(vault):
        if rel == p or (p.endswith("/") and rel.startswith(p)):
            return decide("Protected vault file: " + rel)
    if tool == "Write" and path.suffix == ".md" and path.exists():
        try:
            old = path.read_text(encoding="utf-8").splitlines()
        except Exception:
            return
        new = str(inp.get("content", "")).splitlines()
        if len(old) >= 8 and len(new) < len(old) * 0.5:
            return decide("Writing this would replace %d lines of %s with %d. Edit the parts that "
                          "change instead of rewriting the note." % (len(old), rel, len(new)))


def main():
    if mode("vault_guard", "ask") == "off":
        return
    data = read_input()
    tool = data.get("tool_name", "")
    inp = data.get("tool_input") or {}
    cwd = data.get("cwd") or os.getcwd()
    if tool == "Bash":
        check_bash(str(inp.get("command", "")))
    elif tool in ("Write", "Edit", "MultiEdit", "NotebookEdit"):
        check_file(tool, inp, cwd)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log("vault_guard", "error: %r" % (e,))
    sys.exit(0)
