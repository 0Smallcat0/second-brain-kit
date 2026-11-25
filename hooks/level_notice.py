#!/usr/bin/env python3
"""SessionStart hook: the weekly upgrade check (scripts/level_check.py --hook).

At most once per 7 days, and only in a session inside the notes folder (or ~/.claude/sbk), it
computes the pain-signal triggers in docs/ADVANCED.md. If one holds, it adds one line of context
asking Claude to offer that part to the user as a single yes/no question with the numbers. It
never switches anything on. Mode: config.json "modes": {"level_notice": "warn"} (default; "off"
silences it). Fails open.

level_check.py is looked for next to the kit's hooks (../scripts, plugin or clone) and then in
~/.claude/sbk/bin (where setup copies it).
"""
import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import home, log  # noqa: E402


def find():
    here = Path(__file__).resolve().parent
    for p in (here.parent / "scripts" / "level_check.py", here / "level_check.py", home() / "bin" / "level_check.py"):
        if p.exists():
            return p
    return None


def main():
    p = find()
    if not p:
        return
    spec = importlib.util.spec_from_file_location("sbk_level_check", str(p))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.main(["--hook"])


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log("level_notice", "error: %r" % (e,))
    sys.exit(0)
