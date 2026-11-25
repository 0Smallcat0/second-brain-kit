#!/usr/bin/env python3
"""Do not read a vault note in fragments. Two events, one hook:

PreToolUse (Bash, PowerShell): refuses head / tail / sed -n / Get-Content -TotalCount / Select-Object
-First on a note inside the vault when the command's own input is the note ("head -5 note.md",
"Get-Content note.md | Select-Object -First 20"). A listing or a search that merely mentions a .md
name ("ls 20-29*/*.md | head -5", "git log -- x.md | head") reads no note and is let through.

PostToolUse (Read): when the Read tool returned only part of a vault .md note (an offset or a limit
that stops before the last line, or more than the tool's 2000-line default), one line of context tells
Claude which lines it has and to read the rest before concluding. It works from tool_input and the file
on disk, not from the tool's output (the output's shape is not documented for hooks).

Mode (see _common.mode): deny (default) | warn | log | off. In log mode nothing is shown to Claude.
Only runs when a vault is known (.sbk-vault).
"""
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import SHELL_TOOLS, add_context, find_vault, log, mode, pretool, read_input  # noqa: E402

FRAGMENT = re.compile(
    r"(^|[\s|;&(])(head|tail)\b(?!\s+-[a-zA-Z]*f)"
    r"|(^|[\s|;&(])sed\s+(-[a-zA-Z]*\s+)*-n\b"
    r"|-(TotalCount|Tail|Head)\b|Select-Object\s+(-First|-Last)\b|\bselect\s+(-First|-Last)\b"
    r"|(^|[\s|;&(])awk\s+['\"]?\s*NR", re.I)
NOTE = re.compile(r"\.md\b", re.I)
# a command that reads the content of the file named in the same pipe stage
READER = re.compile(r"^\s*(?:[(&]\s*)?(cat|type|bat|less|more|head|tail|sed|awk|gc|get-content|"
                    r"select-string|sls)\b", re.I)
READ_DEFAULT_LINES = 2000


def norm(s):
    return s.replace("\\", "/").lower()


def reads_note_in_fragments(seg):
    """True when a stage of this pipeline reads a .md file and the pipeline cuts it short."""
    stages = seg.split("|")
    if not FRAGMENT.search(seg):
        return False
    return any(NOTE.search(st) and READER.match(st) for st in stages)


def pre_shell(data, m):
    cmd = str((data.get("tool_input") or {}).get("command", ""))
    cwd = data.get("cwd") or os.getcwd()
    vault = find_vault(cwd)
    if not vault or not NOTE.search(cmd):
        return
    inside = norm(str(Path(cwd).resolve())).startswith(norm(str(vault.resolve())))
    if not inside and norm(str(vault)) not in norm(cmd):
        return
    for seg in re.split(r"&&|\|\||;|\n", cmd):
        if reads_note_in_fragments(seg):
            log("read_whole", "%s: %s" % (m, seg.strip()[:120]))
            if m in ("deny", "block"):
                pretool("deny", "Do not read a note in fragments. Use the Read tool on the whole "
                                "file (for a long one, read consecutive chunks until the last "
                                "line) before drawing any conclusion from it.")
            return


def count_lines(path):
    n = 0
    with open(path, "rb") as f:
        for _ in f:
            n += 1
    return n


def post_read(data, m):
    inp = data.get("tool_input") or {}
    raw = inp.get("file_path")
    if not raw or not str(raw).lower().endswith(".md"):
        return
    cwd = data.get("cwd") or os.getcwd()
    path = Path(raw)
    if not path.is_absolute():
        path = Path(cwd) / path
    vault = find_vault(path.parent if path.parent.exists() else cwd)
    if not vault:
        return
    try:
        path.resolve().relative_to(vault.resolve())
        total = count_lines(path)
    except Exception:
        return
    try:
        first = max(1, int(inp.get("offset") or 1))
        limit = int(inp.get("limit") or READ_DEFAULT_LINES)
    except (TypeError, ValueError):
        return
    last = min(total, first + limit - 1)
    if last >= total:
        return
    msg = ("[second-brain-kit] You have lines %d-%d of %d of %s. Read the rest (offset %d) before "
           "you conclude anything from this note." % (first, last, total, path.name, last + 1))
    log("read_whole", "%s: partial read %s %d-%d/%d" % (m, path.name, first, last, total))
    if m in ("deny", "block", "warn"):
        add_context("PostToolUse", msg)


def main():
    m = mode("read_whole", "deny")
    if m == "off":
        return
    data = read_input()
    tool = data.get("tool_name")
    if data.get("hook_event_name") == "PostToolUse":
        if tool == "Read":
            post_read(data, m)
    elif tool in SHELL_TOOLS:
        pre_shell(data, m)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log("read_whole", "error: %r" % (e,))
    sys.exit(0)
