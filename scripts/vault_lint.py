#!/usr/bin/env python3
"""Lint a numbered markdown vault. Python 3 standard library only.

    python vault_lint.py [--root DIR] [--errors-only] [--stale-days N]

ERROR (exit code 1):  unreadable file, unclosed frontmatter, unquoted [[link]] inside
                      frontmatter, broken [[wikilink]], missing ![[embed]], two notes with the
                      same file name, characters in a file name that break on some systems.
WARN:                 bad or missing type / status / origin / dates / summary, note number used
                      twice, note filed in the wrong category folder, active note not touched
                      for a long time, expired valid_until, archived note outside 90-99 (and
                      the reverse), oversize note, old unchecked to-do, stale JDex, stray .md in
                      the vault root.
Ignore files with glob lines in <root>/scripts/lint_ignore.txt (paths relative to the vault).
"""
import argparse
import datetime
import fnmatch
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

TYPES = {"profile", "preference", "skill", "person", "event", "area", "project", "idea",
         "daily", "moc", "log", "reference"}
STATUSES = {"active", "review", "done", "someday", "archived"}
ORIGINS = {"user", "agent-drafted", "agent-inferred", "book", "research", "mixed"}
NOTE_RE = re.compile(r"^(\d{2})-(\d{2}) (.+)\.md$")
CAT_RE = re.compile(r"^(\d{2}) ")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
LINK_RE = re.compile(r"(!?)\[\[([^\]\n]+?)\]\]")
BAD_NAME = set(':*?"<>|#^[]')
SKIP_DIRS = {".git", ".obsidian", "node_modules", "__pycache__"}
ROOT_MD_OK = {"AGENTS.md", "CLAUDE.md", "README.md"}
ARCHIVE_AREA = "90-99"
MAX_LINES = 500


def find_root(arg):
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


def load_ignore(root):
    pats = ["*/templates/*", "templates/*"]
    try:
        for line in (root / "scripts" / "lint_ignore.txt").read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                pats.append(line)
    except Exception:
        pass
    return pats


def parse_frontmatter(text):
    """Return (dict, body_start_line, closed). dict is {} when there is no frontmatter."""
    if not text.startswith("---"):
        return {}, 0, True
    lines = text.splitlines()
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            fm = {}
            for raw in lines[1:i]:
                m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", raw)
                if m:
                    fm[m.group(1)] = m.group(2).strip()
            return fm, i + 1, True
    return {}, 0, False


def strip_code(text):
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"~~~.*?~~~", "", text, flags=re.S)
    return re.sub(r"`[^`\n]*`", "", text)


def run(root, stale_days):
    ignore = load_ignore(root)
    issues = []  # (level, rule, path, message)

    def add(level, rule, rel, msg):
        issues.append((level, rule, rel, msg))

    md_files, all_names = [], set()
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for f in files:
            full = Path(dirpath) / f
            rel = full.relative_to(root).as_posix()
            all_names.add(f.lower())
            if f.endswith(".md") and not any(fnmatch.fnmatch(rel, p) for p in ignore):
                md_files.append((full, rel))

    stems, seen_stems, seen_nums = {}, {}, {}
    for full, rel in md_files:
        stem = full.stem.lower()
        stems.setdefault(stem, []).append(rel)
        if any(c in BAD_NAME for c in full.name):
            add("ERROR", "bad-filename", rel, "file name has a character that breaks links or other systems")
    for stem, rels in stems.items():
        if len(rels) > 1:
            add("ERROR", "duplicate-basename", rels[0], "same name as " + ", ".join(rels[1:]))
    rel_keys = {rel[:-3].lower() for _, rel in md_files}

    today = datetime.date.today()
    for full, rel in md_files:
        parts = rel.split("/")
        if len(parts) == 1 and full.name not in ROOT_MD_OK:
            add("WARN", "root-clutter", rel, "loose .md in the vault root; file it in a category")
        try:
            text = full.read_text(encoding="utf-8")
        except Exception as e:
            add("ERROR", "unreadable", rel, str(e))
            continue
        fm, body_at, closed = parse_frontmatter(text)
        if not closed:
            add("ERROR", "frontmatter-unclosed", rel, "frontmatter starts with --- but never closes")
            continue
        lines = text.splitlines()
        nm = NOTE_RE.match(full.name)
        is_note = bool(nm) and len(parts) >= 3

        for k, v in fm.items():
            if "[[" in v and not (v[:1] in "'\"" and v[-1:] in "'\""):
                add("ERROR", "fm-wikilink-unquoted", rel, "frontmatter '%s' holds an unquoted [[link]]" % k)
        if is_note:
            if not fm:
                add("WARN", "frontmatter-missing", rel, "note has no frontmatter")
            else:
                if fm.get("type") not in TYPES:
                    add("WARN", "type-invalid", rel, "type '%s' not in the list" % fm.get("type", ""))
                st = fm.get("status")
                if st not in STATUSES:
                    add("WARN", "status-invalid", rel, "status '%s' not in the list" % (st or ""))
                if fm.get("origin") and fm["origin"] not in ORIGINS:
                    add("WARN", "origin-invalid", rel, "origin '%s' not in the list" % fm["origin"])
                for k in ("created", "modified"):
                    if not DATE_RE.match(fm.get(k, "")):
                        add("WARN", "date-invalid", rel, "%s must look like 2000-01-31" % k)
                if not fm.get("summary"):
                    add("WARN", "summary-missing", rel, "summary is empty")
                mod = fm.get("modified", "")
                if st == "active" and DATE_RE.match(mod):
                    try:
                        age = (today - datetime.date.fromisoformat(mod)).days
                        if age > stale_days:
                            add("WARN", "stale-active", rel, "active but not modified for %d days" % age)
                    except ValueError:
                        pass
                vu = fm.get("valid_until", "")
                if DATE_RE.match(vu):
                    try:
                        if datetime.date.fromisoformat(vu) < today:
                            add("WARN", "expired-content", rel, "valid_until %s has passed" % vu)
                    except ValueError:
                        pass
                in_archive = parts[0].startswith(ARCHIVE_AREA)
                if st == "archived" and not in_archive:
                    add("WARN", "archived-not-moved", rel, "status archived: move it to the 90-99 area")
                if in_archive and st and st != "archived":
                    add("WARN", "archive-misfiled", rel, "in the archive area but status is '%s'" % st)
            num = nm.group(1) + "-" + nm.group(2)
            if num in seen_nums:
                add("WARN", "jd-number-duplicate", rel, "number %s also used by %s" % (num, seen_nums[num]))
            else:
                seen_nums[num] = rel
            cat = CAT_RE.match(parts[-2]) if len(parts) >= 3 else None
            if cat and cat.group(1) != nm.group(1):
                add("WARN", "jd-folder-mismatch", rel, "note prefix %s but folder starts with %s" % (nm.group(1), cat.group(1)))
        if len(lines) > MAX_LINES:
            add("WARN", "note-oversize", rel, "%d lines; split it" % len(lines))

        body = strip_code("\n".join(lines[body_at:]))
        for line in body.splitlines():
            m = re.match(r"^\s*- \[ \].*?(\d{4}-\d{2}-\d{2})", line)
            if m:
                try:
                    if (today - datetime.date.fromisoformat(m.group(1))).days > 30:
                        add("WARN", "todo-stale", rel, "unchecked to-do dated %s" % m.group(1))
                except ValueError:
                    pass
        for bang, raw in LINK_RE.findall(body):
            target = raw.split("|")[0].split("#")[0].strip()
            if not target:
                continue
            if bang or re.search(r"\.[A-Za-z0-9]{2,4}$", target) and not target.lower().endswith(".md"):
                if os.path.basename(target).lower() not in all_names:
                    add("ERROR", "missing-embed", rel, "![[%s]] not found" % target)
                continue
            key = target[:-3] if target.lower().endswith(".md") else target
            low = key.lower().replace("\\", "/")
            if low not in stems and not any(r == low or r.endswith("/" + low) for r in rel_keys):
                add("ERROR", "broken-wikilink", rel, "[[%s]] points to no note" % target)

    try:
        import gen_jdex
        if (root / gen_jdex.INDEX_REL).exists() and gen_jdex.is_stale(root):
            add("WARN", "jdex-stale", gen_jdex.INDEX_REL.as_posix(), "run scripts/gen_jdex.py")
    except Exception:
        pass
    return issues


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root")
    ap.add_argument("--errors-only", action="store_true")
    ap.add_argument("--stale-days", type=int, default=180)
    a = ap.parse_args()
    root = find_root(a.root)
    issues = run(root, a.stale_days)
    errors = [i for i in issues if i[0] == "ERROR"]
    shown = errors if a.errors_only else issues
    for level, rule, rel, msg in sorted(shown, key=lambda i: (i[0] != "ERROR", i[2], i[1])):
        print("%s %s %s: %s" % (level, rule, rel, msg))
    print("%d errors, %d warnings" % (len(errors), len(issues) - len(errors)))
    print("RESULT: " + ("FAIL" if errors else "PASS"))
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    if sys.stdout is not None:
        sys.stdout.reconfigure(encoding="utf-8")
    main()
