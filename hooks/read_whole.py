#!/usr/bin/env python3
"""PreToolUse (Bash) hook: do not read a vault note in fragments.

Reading the first 20 lines of a note and then concluding is a common source of wrong
answers. This refuses head / tail / sed -n / Get-Content -TotalCount on notes inside the
vault and tells Claude to read the whole file with the Read tool (long files in
consecutive chunks, to the last line). Only runs when a vault is known (.sbk-vault).
"""
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import find_vault, log, mode, pretool, read_input  # noqa: E402

FRAGMENT = re.compile(
    r"(^|[\s|;&(])(head|tail)\b(?!\s+-[a-zA-Z]*f)"
    r"|(^|[\s|;&(])sed\s+(-[a-zA-Z]*\s+)*-n\b"
    r"|-(TotalCount|Tail|Head)\b|Select-Object\s+(-First|-Last)\b"
    r"|(^|[\s|;&(])awk\s+['\"]?\s*NR", re.I)
NOTE = re.compile(r"\.md\b", re.I)


def norm(s):
    return s.replace("\\", "/").lower()


def main():
    m = mode("read_whole", "deny")
    if m == "off":
        return
    data = read_input()
    if data.get("tool_name") != "Bash":
        return
    cmd = str((data.get("tool_input") or {}).get("command", ""))
    cwd = data.get("cwd") or os.getcwd()
    vault = find_vault(cwd)
    if not vault or not NOTE.search(cmd):
        return
    inside = norm(str(Path(cwd).resolve())).startswith(norm(str(vault.resolve())))
    if not inside and norm(str(vault)) not in norm(cmd):
        return
    for seg in re.split(r"&&|\|\||;|\n", cmd):
        if NOTE.search(seg) and FRAGMENT.search(seg):
            log("read_whole", "%s: %s" % (m, seg.strip()[:120]))
            if m in ("deny", "block"):
                pretool("deny", "Do not read a note in fragments. Use the Read tool on the whole "
                                "file (for a long one, read consecutive chunks until the last "
                                "line) before drawing any conclusion from it.")
            return


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log("read_whole", "error: %r" % (e,))
    sys.exit(0)
