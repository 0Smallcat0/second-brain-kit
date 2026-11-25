#!/usr/bin/env python3
"""Generate the JDex: the index of a numbered (Johnny Decimal style) vault.

Layout it understands (see templates/筆記格式.md):
    <vault>/10-19 Area name/11 Category name/11-01 Note title.md
Writes <vault>/00-09 系統與索引/00 索引/00-01 JDex 索引.md with, per category, the note count,
the next free number and one line per note (title + its frontmatter summary).

    python gen_jdex.py [--root DIR] [--check]

--check prints nothing and exits 1 when the file on disk is out of date (used by vault_lint).
The file is only rewritten when the content changed, not merely the modified date.
"""
import argparse
import os
import re
import sys
import time
from pathlib import Path

AREA_RE = re.compile(r"^(\d{2})-(\d{2}) (.+)$")
CAT_RE = re.compile(r"^(\d{2}) (.+)$")
NOTE_RE = re.compile(r"^(\d{2})-(\d{2}) (.+)\.md$")
INDEX_REL = Path("00-09 系統與索引") / "00 索引" / "00-01 JDex 索引.md"
SKIP_DIRS = {".git", ".obsidian", "scripts", "node_modules", "__pycache__"}


def find_root(arg=None):
    if arg:
        return Path(arg).resolve()
    env = os.environ.get("SBK_VAULT")
    if env:
        return Path(env).resolve()
    p = Path.cwd().resolve()
    for d in [p] + list(p.parents):
        if (d / ".sbk-vault").exists():
            return d
    return p


def summary_of(path):
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return ""
    if not text.startswith("---"):
        return ""
    end = text.find("\n---", 3)
    if end < 0:
        return ""
    for line in text[3:end].splitlines():
        if line.startswith("summary:"):
            return line.split(":", 1)[1].strip().strip("'\"")
    return ""


def collect(root):
    areas = []
    for a in sorted(p for p in root.iterdir() if p.is_dir() and p.name not in SKIP_DIRS):
        m = AREA_RE.match(a.name)
        if not m:
            continue
        cats = []
        for c in sorted(p for p in a.iterdir() if p.is_dir()):
            cm = CAT_RE.match(c.name)
            if not cm:
                continue
            notes = []
            for n in sorted(c.rglob("*.md")):
                nm = NOTE_RE.match(n.name)
                if nm:
                    notes.append((int(nm.group(2)), n.name[:-3], summary_of(n), nm.group(1)))
            cats.append((cm.group(1), cm.group(2), notes))
        areas.append((a.name, cats))
    return areas


def build_body(root):
    out = ["# JDex 索引", "",
           "這份索引由 `scripts/gen_jdex.py` 自動產生，不要手改。新增筆記時取「下一個空號」。", ""]
    for area, cats in collect(root):
        out += ["## " + area, "", "| 類別 | 筆數 | 下一個空號 |", "|---|---|---|"]
        for cnum, cname, notes in cats:
            used = {n[0] for n in notes}
            nxt = next((i for i in range(1, 100) if i not in used), None)
            out.append("| %s %s | %d | %s |" % (
                cnum, cname, len(notes), ("%s-%02d" % (cnum, nxt)) if nxt else "已滿"))
        out.append("")
        for cnum, cname, notes in cats:
            if notes:
                out.append("### %s %s" % (cnum, cname))
                for _, base, summ, _ in notes:
                    out.append("- [[%s]]%s" % (base, (" — " + summ) if summ else ""))
                out.append("")
    return "\n".join(out).rstrip() + "\n"


def build_text(root, created=None, modified=None):
    today = time.strftime("%Y-%m-%d")
    fm = ["---", "type: moc", "status: active",
          "summary: 全庫編號索引，每類別的下一個空號（自動產生）",
          "created: %s" % (created or today), "modified: %s" % (modified or today),
          "origin: agent-drafted", "---", ""]
    return "\n".join(fm) + "\n" + build_body(root)


def strip_dates(text):
    return re.sub(r"^(created|modified): .*$", "", text, flags=re.M)


def existing_dates(path):
    try:
        t = path.read_text(encoding="utf-8")
    except Exception:
        return None, None
    c = re.search(r"^created: (.*)$", t, re.M)
    m = re.search(r"^modified: (.*)$", t, re.M)
    return (c.group(1) if c else None), (m.group(1) if m else None)


def is_stale(root):
    path = root / INDEX_REL
    if not path.exists():
        return True
    c, m = existing_dates(path)
    return strip_dates(path.read_text(encoding="utf-8")) != strip_dates(build_text(root, c, m))


def regenerate(root):
    """Write the index. Runs twice at most: the index lists itself, so the first write of a
    brand-new index changes what the second pass sees."""
    path = root / INDEX_REL
    changed = False
    for _ in range(2):
        c, _m = existing_dates(path)
        new = build_text(root, c)
        if path.exists() and strip_dates(path.read_text(encoding="utf-8")) == strip_dates(new):
            break
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".md.tmp")
        tmp.write_text(new, encoding="utf-8")
        os.replace(str(tmp), str(path))
        changed = True
    return changed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    root = find_root(a.root)
    if a.check:
        sys.exit(1 if is_stale(root) else 0)
    print("rewrote %s" % (root / INDEX_REL) if regenerate(root) else "index already up to date")


if __name__ == "__main__":
    main()
