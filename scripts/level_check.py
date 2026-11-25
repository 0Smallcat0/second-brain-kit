#!/usr/bin/env python3
"""Measured "time for more?" check for second-brain-kit. Python 3 standard library only.

    level_check.py                  compute the upgrade triggers now; print one JSON line
    level_check.py --install        supporting facts for the install suggestion (run only after the
                                    user allowed reading their history); one JSON line
    level_check.py --hook           SessionStart hook (via hooks/level_notice.py): at most once per
                                    7 days, inside the notes folder only; if a trigger holds, one line
                                    of context asking Claude to offer the upgrade as one yes/no
    level_check.py --decline ID..   the user said no: do not offer these triggers again for 28 days
    --now 2026-11-25T10:00:00       pretend it is this time (tests; env SBK_NOW does the same)

Triggers (docs/ADVANCED.md, "When Claude suggests it") are pain signals, not volume:
    multi_session  in notes-folder sessions in the last 7 days the user said twice or more that
                   things got mixed up ("you mixed up the two reports", "作業搞混了")
    alarms         the user asked to be reminded twice or more in the last 7 days, or an open item
                   with "due YYYY-MM-DD" is still open 3+ days after that date
    block_mode     stop_evidence has been in log mode >= 14 days, >= 20 flagged turns could be
                   judged (small samples mislead), and < 25% of them were false alarms (false
                   alarm = the user's next message did not report a problem)
    multi_tool     the user said they have an outside resource (config outside_resources, from setup
                   or later); a mere mention of a tool in a conversation does not count
Volume (open items, topics, compactions) is still counted and reported as supporting numbers,
but never fires a trigger on its own.
A trigger whose part is already on, or that the user declined in the last 28 days, is left out.

The hook also starts the light review of the learning loop: if the 和 AI 協作 note has lines after the
last reviewed one (counted by position, not by date), one more line of context asks Claude to group
them by kind, draft preferences and any skill or hook addition, and change nothing until the user
agrees (entry/learn.py group / pref). A review counts as done only when `learn.py reviewed` (or `pref`)
wrote its mark, so an offer that was shown but never acted on comes again the next day. Basic does it
itself; Full leaves it to the maintenance session's weekly review while a "[review]" tracker item was
closed in the last 8 days, and does it itself otherwise (no scheduler, App only, a missed week).
The hook only speaks in a session in the notes folder or in the entry folder (SBK_HOME/entry): a
session that cannot ask the user (a topic session, the courier in SBK_HOME/state) must not use up
the weekly question. When the installed tools in SBK_HOME/bin are not the plugin's version it also
adds one line asking Claude to copy them again.
If config "read_history" is false the conversations are not read at all (tracker and log only).

Reads SBK_HOME (ledger.md, task.md, config.json, logs/stop_evidence.log, alarms.md, routes.md,
channels.md) and CLAUDE_CONFIG_DIR/projects (default ~/.claude/projects). Writes only
SBK_HOME/state/level_check.json. Never changes config.json. Fails open: on any error it prints
{"triggers": [], "numbers": {"error": ...}} and exits 0.

Self-contained on purpose (human_text is a copy of hooks/_common.py's): setup copies this one file
to SBK_HOME/bin, where the hooks folder is not next to it.
"""
import json
import mmap
import os
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

THROTTLE_DAYS = 7
DECLINE_DAYS = 28
OVERDUE_GRACE_DAYS = 3
MIN_JUDGED = 20
PARTS = {"multi_session": "A1", "alarms": "A2", "block_mode": "A4", "multi_tool": "A5"}
NAMES = {"multi_session": "topic sessions (one conversation per subject)",
         "alarms": "reminders", "block_mode": "the stricter done-check",
         "multi_tool": "the table for splitting work with your outside resources"}

LEDGER_LINE = re.compile(r"^- (L\d{4}) \| ([^|]+?) \| ([^|]+?) \| (.*?) \| ev: (.*)$")
TOPIC = re.compile(r"^\s*\[([^\]]{1,40})\]")
DUE = re.compile(r"(?:due|deadline|截止|期限|到期)\s*[:：]?\s*(\d{4}-\d{2}-\d{2})", re.I)
OPEN_TASK = re.compile(r"^\s*- \[ \] ?(.*)$")
REMIND = re.compile(r"remind me|set (?:a |an )?(?:reminder|alarm)|提醒我|幫我提醒|設(?:個|一個)?提醒|記得叫我|到時(?:候)?(?:叫|提醒)我", re.I)
_THINGS_ZH = r"(?:專案|主題|作業|報告|事情|工作|對話|課|件事)"
_MIX_ZH = r"(?:搞混|弄混|混在一起|搞錯|弄錯|混淆|搞亂)"
_THINGS_EN = r"(?:projects?|tasks?|topics?|subjects?|courses?|assignments?|reports?|conversations?)"
MIXUP = re.compile(_MIX_ZH + r"了?.{0,8}" + _THINGS_ZH + r"|" + _THINGS_ZH + r".{0,8}" + _MIX_ZH +
                   r"|不是(?:這|那)個(?:專案|主題|作業|報告|課)"
                   r"|mix(?:ed|ing)? up (?:the |my |two |these |those )?" + _THINGS_EN +
                   r"|" + _THINGS_EN + r" (?:got |are |were )?mixed up"
                   r"|wrong (?:project|task|topic|course|assignment|report)"
                   r"|not that (?:project|course|assignment|report)", re.I)
NO_TOOL = re.compile(r"^\s*(?:no|none|nope|n/a|-|沒有|無|沒|不用|都沒有)\s*[.。!！]?\s*$", re.I)
TOOLS = re.compile(r"\b(ChatGPT|GPT-?[45]\w*|Codex|Gemini|Antigravity|Colab|OpenRouter|Copilot|Perplexity|"
                   r"DeepSeek|Grok|Kimi|Qwen)\b|(通義|文心|豆包)", re.I)
COMPLAINT = re.compile(r"不對|錯了|有錯|沒改|沒有改|沒做|沒有做|還是(?:不|沒|一樣|錯)|失敗|壞了|跑不起來|打不開|"
                       r"不行|沒用|沒反應|doesn'?t work|does not work|didn'?t work|not working|still (?:not|broken|wrong|fails?)|"
                       r"wrong|broken|\berror\b|\bfail(?:s|ed)?\b|you didn'?t|you did not|not fixed", re.I)
LOG_LINE = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}) (\w+): turn (\d+) of (.+?\.jsonl): ")
SKIP_PREFIXES = ("<system-reminder>", "<command-", "<local-command", "<task-notification",
                 "Caveat:", "[Request interrupted", "<bash-", "<user-prompt-submit-hook>")


# ---------- small helpers ----------

def sbk_home():
    """Same rule as hooks/_common.home(): SBK_HOME, else ~/.sbk, else the pre-0.2.5 ~/.sbk."""
    env = os.environ.get("SBK_HOME")
    if env:
        return Path(env)
    new, old = Path.home() / ".sbk", Path.home() / ".claude" / "sbk"
    return old if (not new.exists() and old.exists()) else new


def projects_dir():
    base = os.environ.get("CLAUDE_CONFIG_DIR")
    return (Path(base) if base else Path.home() / ".claude") / "projects"


def read_json(p, default):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default


def parse_now(argv):
    val = None
    if "--now" in argv:
        k = argv.index("--now")
        val = argv[k + 1] if k + 1 < len(argv) else None
    val = val or os.environ.get("SBK_NOW")
    if val:
        return datetime.strptime(val[:19], "%Y-%m-%dT%H:%M:%S")
    return datetime.now().replace(microsecond=0)


def parse_ts(s):
    """ISO time from a transcript (UTC, 'Z') or a log (local) -> naive local datetime, or None."""
    try:
        s = str(s)
        if s.endswith("Z") or "+" in s[10:]:
            d = datetime.fromisoformat(s.replace("Z", "+00:00"))
            return d.astimezone().replace(tzinfo=None)
        return datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S")
    except Exception:
        return None


def day(d):
    return d.strftime("%Y-%m-%d")


def norm(p):
    try:
        return os.path.normcase(os.path.abspath(str(p))).rstrip("\\/")
    except Exception:
        return ""


def encode_dir(path):
    """Claude Code names a project folder after its path with every non-alphanumeric char as '-'."""
    return re.sub(r"[^A-Za-z0-9]", "-", str(path))


def human_text(rec):
    if rec.get("type") != "user":
        return None
    if rec.get("isMeta") or rec.get("isSidechain") or rec.get("isCompactSummary"):
        return None
    origin = rec.get("origin")
    if isinstance(origin, dict) and origin.get("kind") not in (None, "human"):
        return None
    content = (rec.get("message") or {}).get("content")
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
            return None
        text = "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    else:
        return None
    text = text.strip()
    if not text or text.startswith(SKIP_PREFIXES):
        return None
    return text


def is_compaction(rec):
    return rec.get("type") == "system" and rec.get("subtype") == "compact_boundary"


MARK = b'"compact_boundary"'
NL = bytes([10])
TS_RE = re.compile(rb'"timestamp"\s*:\s*"([^"]+)"')
CWD_RE = re.compile(rb'"cwd"\s*:\s*("(?:[^"\\]|\\.)*")')


def compaction_lines(path):
    """(timestamp, cwd) of every compaction record, found with a byte search (transcripts can be GBs)."""
    out = []
    try:
        with open(path, "rb") as fh:
            if os.fstat(fh.fileno()).st_size == 0:
                return out
            mm = mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ)
            try:
                i = mm.find(MARK)
                while i != -1:
                    a = mm.rfind(NL, 0, i) + 1
                    b = mm.find(NL, i)
                    line = mm[a:b if b != -1 else len(mm)]
                    if b'"subtype"' in line and b'"system"' in line:
                        t = TS_RE.search(line)
                        c = CWD_RE.search(line)
                        cwd = None
                        if c:
                            try:
                                cwd = json.loads(c.group(1).decode("utf-8", "replace"))
                            except Exception:
                                cwd = None
                        out.append((parse_ts(t.group(1).decode("ascii", "replace")) if t else None, cwd))
                    i = mm.find(MARK, (b if b != -1 else len(mm)))
            finally:
                mm.close()
    except Exception:
        pass
    return out


def human_records(path):
    """Records that may be a typed user message; skips tool results and everything else unparsed."""
    try:
        with open(path, "rb") as fh:
            for line in fh:
                if b'"type":"user"' not in line and b'"type": "user"' not in line:
                    continue
                if b'"tool_result"' in line:
                    continue
                try:
                    yield json.loads(line.decode("utf-8", "replace"))
                except Exception:
                    continue
    except Exception:
        return


# ---------- the facts ----------

def ledger_facts(home, now):
    items = []
    try:
        for raw in (home / "ledger.md").read_text(encoding="utf-8").splitlines():
            m = LEDGER_LINE.match(raw)
            if m:
                items.append(m.groups())
    except Exception:
        pass
    open_items, topics, overdue = 0, set(), []
    for lid, st, ts, text, ev in items:
        if st in ("done", "dropped", "verified"):
            continue
        open_items += 1
        if st.startswith("dispatched:"):
            topics.add(st.split(":", 1)[1].strip().lower())
        else:
            m = TOPIC.match(text)
            if m:
                topics.add(m.group(1).strip().lower())
        for d in DUE.findall(text):
            if d < day(now - timedelta(days=OVERDUE_GRACE_DAYS)):
                overdue.append(lid)
                break
    try:  # the Basic task.md of one large job
        for l in (home / "task.md").read_text(encoding="utf-8").splitlines():
            m = OPEN_TASK.match(l)
            if m and any(d < day(now - timedelta(days=OVERDUE_GRACE_DAYS)) for d in DUE.findall(m.group(1))):
                overdue.append("task.md")
                break
    except Exception:
        pass
    return open_items, len(topics), overdue


def vault_transcripts(vault, since_ts):
    """Transcript files of sessions started inside the notes folder, modified since since_ts."""
    root = projects_dir()
    if not vault or not root.is_dir():
        return []
    enc = encode_dir(os.path.abspath(str(vault))).lower()
    out = []
    for d in root.iterdir():
        name = d.name.lower()
        # the notes folder itself, or a folder inside it (in_vault() then checks each record's cwd)
        if not d.is_dir() or not (name == enc or name.startswith(enc + "-")):
            continue
        for f in d.glob("*.jsonl"):
            try:
                if f.stat().st_mtime >= since_ts:
                    out.append(f)
            except Exception:
                pass
    return out


def in_vault(rec, vault_n):
    cwd = rec.get("cwd")
    if not cwd:
        return True  # records without cwd belong to the file's session
    c = norm(cwd)
    return c == vault_n or c.startswith(vault_n + os.sep)


def transcript_facts(vault, now):
    """Notes-folder sessions, last 7 days: compactions, reminder requests, mix-up complaints."""
    comp, remind, mixup = 0, 0, 0
    if not vault:
        return comp, remind, mixup
    vault_n = norm(vault)
    t7 = now - timedelta(days=7)
    for f in vault_transcripts(vault, time.mktime(t7.timetuple())):
        for ts, cwd in compaction_lines(f):
            if ts and t7 <= ts <= now and in_vault({"cwd": cwd}, vault_n):
                comp += 1
        for rec in human_records(f):
            if not in_vault(rec, vault_n):
                continue
            ts = parse_ts(rec.get("timestamp"))
            if ts is None or ts > now or ts < t7:
                continue
            text = human_text(rec)
            if not text:
                continue
            if REMIND.search(text):
                remind += 1
            if MIXUP.search(text):
                mixup += 1
    return comp, remind, mixup


def stop_log_facts(home, now, state, read_history=True):
    """Days in log mode, flagged turns, judged turns, false alarms (no complaint in the next message)."""
    first = None
    flags = []
    try:
        for l in (home / "logs" / "stop_evidence.log").read_text(encoding="utf-8").splitlines():
            m = LOG_LINE.match(l)
            if not m:
                continue
            ts = parse_ts(m.group(1))
            if ts is None or ts > now:
                continue
            if m.group(2) == "log":
                first = ts if first is None or ts < first else first
                flags.append((int(m.group(3)), m.group(4)))
    except Exception:
        pass
    since = state.get("log_mode_since")
    starts = [d for d in (first, parse_ts(since + "T00:00:00") if since else None) if d]
    days = (now - min(starts)).days if starts else 0
    humans = {}
    judged = false = 0
    for turn, path in (flags if read_history else []):
        if path not in humans:
            humans[path] = [t for t in (human_text(r) for r in human_records(path)) if t]
        msgs = humans[path]
        if turn < 1 or turn >= len(msgs):
            continue  # no next message: cannot judge
        judged += 1
        if not COMPLAINT.search(msgs[turn]):
            false += 1
    return days, len(flags), judged, false


def install_facts(now, budget=30.0):
    """Before setup: project folders active in the last 14 days; is there a session compacted 2+ times
    (0 or 1: the scan stops at the first one).

    Stops after `budget` seconds and says so ("partial": true): on a heavy user's computer
    the transcripts can be many GB."""
    root = projects_dir()
    t14 = now - timedelta(days=14)
    since = time.mktime(t14.timetuple())
    start = time.time()
    active, heavy, partial = 0, 0, False
    if root.is_dir():
        recent_by_dir = []
        for d in root.iterdir():
            if not d.is_dir():
                continue
            recent = []
            for f in d.glob("*.jsonl"):
                try:
                    if f.stat().st_mtime >= since:
                        recent.append(f)
                except Exception:
                    pass
            if recent:
                active += 1
                recent_by_dir.append(recent)
        # newest first; one heavy session is enough evidence, so stop there
        files = sorted((f for r in recent_by_dir for f in r), key=lambda f: f.stat().st_mtime, reverse=True)
        for f in files:
            if time.time() - start > budget:
                partial = True
                break
            n = sum(1 for ts, _ in compaction_lines(f) if ts and t14 <= ts <= now)
            if n >= 2:
                heavy += 1
                break
    return {"active_projects_14d": active, "session_compacted_2plus_14d": heavy,
            "multi_session_evidence": active >= 3 or heavy >= 1, "partial": partial}


# ---------- the Basic light review of the learning loop ----------

# the three names of the folder/file name map this script needs (hooks/_common.NAMES_ZH has all of them;
# the selftest checks these equal that); config.json "names" overrides
NAMES_ZH = {"sys_dir": "00-09 系統與索引", "ai_dir": "03 和 AI 協作", "ai_note": "03-01 和 AI 協作.md"}
REVIEW_EVERY_DAYS = 7
REVIEW_FALLBACK_DAYS = 8
PREF_BUDGET = 25
LEARN_LINE = re.compile(r"^-\s*(\d{4}-\d{2}-\d{2})\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*(.+)$")
CORR_WORDS = {"糾正", "correction", "corrected"}
GOOD_WORDS = {"做對", "confirmed", "confirm"}


def learn_rel(cfg):
    n = dict(NAMES_ZH)
    n.update({k: v for k, v in (cfg.get("names") or {}).items() if isinstance(v, str) and v})
    return Path(n["sys_dir"]) / n["ai_dir"] / n["ai_note"]


def py(cfg):
    """The command that runs Python 3 here, found at setup (config.json python_cmd)."""
    return cfg.get("python_cmd") or "python"


def learn_cmd(home, cfg=None):
    for p in (home / "bin" / "learn.py", Path(__file__).resolve().parent.parent / "entry" / "learn.py"):
        if p.exists():
            return '%s "%s"' % (py(cfg or {}), p.as_posix())
    return "%s ~/.sbk/bin/learn.py" % py(cfg or {})


def review_closed_recently(home, now):
    """True when the maintenance session recorded its weekly review ("[review] YYYY-MM-DD ...") as a
    done/verified tracker item in the last REVIEW_FALLBACK_DAYS days."""
    try:
        lines = (home / "ledger.md").read_text(encoding="utf-8").splitlines()
    except Exception:
        return False
    for l in lines:
        m = LEDGER_LINE.match(l)
        if not m or m.group(2) not in ("done", "verified"):
            continue
        t = re.match(r"\[review\]\s*(\d{4}-\d{2}-\d{2})", m.group(4).strip())
        if t:
            try:
                if 0 <= (now - datetime.strptime(t.group(1), "%Y-%m-%d")).days <= REVIEW_FALLBACK_DAYS:
                    return True
            except Exception:
                pass
    return False


def learn_review(cfg, home, now, state):
    """One line of context for the light review of the learning loop, or None.

    Lines are chosen by position: the lines after the last one a review marked as reviewed
    (<SBK_HOME>/state/learn_review.json, written by `learn.py reviewed` and `learn.py pref`), never by
    date. Showing the line does not use the review up: it is offered again the next day until marked."""
    if cfg.get("level") == "full" and (home / "managers" / "maintenance").is_dir() \
            and review_closed_recently(home, now):
        return None  # Full: the maintenance session's weekly review is running
    vault = cfg.get("vault") or os.environ.get("SBK_VAULT")
    if not vault:
        return None
    note = Path(vault) / learn_rel(cfg)
    try:
        text = note.read_text(encoding="utf-8")
    except Exception:
        return None
    rows = []
    for l in text.splitlines():
        m = LEARN_LINE.match(l.strip())
        if not m:
            continue
        k = m.group(2).strip().lower()
        if k in CORR_WORDS or k in GOOD_WORDS:
            rows.append((m.group(1), k in CORR_WORDS, m.group(3).strip()))
    mark = read_json(home / "state" / "learn_review.json", {})
    try:
        done_n = max(0, int(mark.get("entries", 0)))
    except Exception:
        done_n = 0
    new_rows = rows[done_n:]
    if not new_rows:
        return None
    last = mark.get("date")
    try:
        if last and (now - datetime.strptime(last, "%Y-%m-%d")).days < REVIEW_EVERY_DAYS:
            return None
    except Exception:
        pass
    if state.get("last_learn_offer") == day(now):
        return None  # offered today already; if nobody acted on it, it comes again tomorrow
    state["last_learn_offer"] = day(now)
    total = {}
    for _, _, kind in rows:
        total[kind] = total.get(kind, 0) + 1
    new = {}
    for _, _, kind in new_rows:
        new[kind] = new.get(kind, 0) + 1
    nc = sum(1 for r in new_rows if r[1])
    ng = len(new_rows) - nc
    since = new_rows[0][0]
    kinds = "; ".join("%s x%d%s" % (k, n, " (came back: x%d in all)" % total[k] if total[k] > n else "")
                      for k, n in sorted(new.items(), key=lambda kv: -kv[1]))
    cmd = learn_cmd(home, cfg)
    return ("[second-brain-kit light review] The 和 AI 協作 note (%s) has %d line(s) nobody has reviewed yet, "
            "since %s: %d correction(s), %d confirmation(s). By kind: %s. In your first reply, after answering "
            "the user, do the light review as ONE short message in the user's language: run `%s group --since %s` "
            "and `%s trend`; for each kind with 2 or more lines (and any clear single preference) draft one "
            "preference sentence (what to do, not what went wrong; `pref` replaces an older line of the same "
            "kind); a kind that came back after its preference was written needs a firmer home than a sentence: "
            "propose skill text, or a hook that starts in log mode, when a program can see it at the moment of "
            "action; name any confirmed way of working worth adding to a skill or the notes folder's AGENTS.md. "
            "If the user's own preferences are over %d lines, also propose which to merge, retire (`%s retire "
            "\"<kind>\"`) or which two contradict each other. Ask one question: OK to do these? Change nothing "
            "before the user says yes. On yes, write each preference with `%s pref \"<kind>\" \"<sentence>\"` and "
            "make the other changes. Whatever the answer, finish with `%s reviewed` (that is what marks the "
            "review done; without it the review is offered again tomorrow)."
            % (note.as_posix(), len(new_rows), since, nc, ng, kinds, cmd, since, cmd, PREF_BUDGET, cmd, cmd, cmd))


# ---------- the check ----------

def state_path(home):
    return home / "state" / "level_check.json"


def save_state(home, state):
    try:
        p = state_path(home)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(str(tmp), str(p))
    except Exception:
        pass


def parts_on(home, cfg):
    modes = cfg.get("modes") or {}
    return {
        "multi_session": modes.get("inbox_notice", "off") != "off" or (home / "routes.md").exists(),
        "alarms": (home / "alarms.md").exists(),
        "block_mode": modes.get("stop_evidence", "log") == "block",
        "multi_tool": (home / "channels.md").exists(),
    }


def compute(now, state):
    home = sbk_home()
    cfg = read_json(home / "config.json", {})
    vault = cfg.get("vault") or os.environ.get("SBK_VAULT") or ""
    on = parts_on(home, cfg)
    open_items, open_topics, overdue = ledger_facts(home, now)
    read_history = cfg.get("read_history", True) is not False
    comp, remind, mixup = transcript_facts(vault, now) if read_history else (0, 0, 0)
    tools = set()
    said = str(cfg.get("outside_resources") or cfg.get("other_tools") or "").strip()
    if said and not NO_TOOL.match(said):  # the user said they have one (setup question, or told Claude later)
        for m in TOOLS.finditer(said):
            tools.add((m.group(1) or m.group(2)).lower())
        if not tools:
            tools.add("other (config)")
    mode_se = (cfg.get("modes") or {}).get("stop_evidence", "log")
    if mode_se == "log" and not state.get("log_mode_since"):
        state["log_mode_since"] = day(now)
    log_days, flags, judged, false = stop_log_facts(home, now, state, read_history)

    checks = [c for c in state.get("checks", []) if isinstance(c, dict) and c.get("date")]
    prev = None
    for c in checks:
        try:
            age = (now - datetime.strptime(c["date"], "%Y-%m-%d")).days
        except Exception:
            continue
        if 7 <= age <= 21 and (prev is None or c["date"] > prev["date"]):
            prev = c
    checks = [c for c in checks if c.get("date") != day(now)]
    checks.append({"date": day(now), "open_items": open_items, "open_topics": open_topics})
    state["checks"] = checks[-12:]

    numbers = {
        "open_items": open_items, "open_topics": open_topics,
        "prev_check": prev["date"] if prev else None,
        "prev_open_items": prev.get("open_items") if prev else None,
        "prev_open_topics": prev.get("open_topics") if prev else None,
        "compactions_7d": comp, "mixups_7d": mixup, "overdue_items": len(overdue),
        "remind_requests_7d": remind, "read_history": read_history,
        "stop_log_days": log_days, "stop_flags": flags, "stop_flags_judged": judged,
        "stop_false_alarm_pct": (round(100.0 * false / judged) if judged else None),
        "other_tools": sorted(tools), "parts_on": [k for k, v in on.items() if v],
    }
    hold = {  # pain signals only; the volume numbers above are support quoted in the question
        "multi_session": mixup >= 2,
        "alarms": bool(overdue) or remind >= 2,
        "block_mode": mode_se == "log" and log_days >= 14 and judged >= MIN_JUDGED and false * 4 < judged,
        "multi_tool": bool(tools),
    }
    declined = state.get("declined") or {}
    out = []
    for k in ("multi_session", "alarms", "block_mode", "multi_tool"):
        if not hold[k] or on[k]:
            continue
        d = declined.get(k)
        try:
            if d and (now - datetime.strptime(d, "%Y-%m-%d")).days < DECLINE_DAYS:
                continue
        except Exception:
            pass
        out.append(k)
    return out, numbers, cfg, home


def why(k, n):
    if k == "multi_session":
        bits = ["you said things got mixed up %d times in 7 days" % n["mixups_7d"],
                "supporting: %d open items in %d topics" % (n["open_items"], n["open_topics"])]
        if n["prev_check"]:
            bits[-1] += " (%d items on %s)" % (n["prev_open_items"] or 0, n["prev_check"])
        if n["compactions_7d"]:
            bits.append("the notes-folder session was summarised %d time(s) in 7 days" % n["compactions_7d"])
        return "; ".join(bits)
    if k == "alarms":
        bits = []
        if n["overdue_items"]:
            bits.append("%d open item(s) still open %d+ days after their due date" % (n["overdue_items"], OVERDUE_GRACE_DAYS))
        if n["remind_requests_7d"] >= 2:
            bits.append("asked to be reminded %d times in 7 days" % n["remind_requests_7d"])
        return "; ".join(bits)
    if k == "block_mode":
        return ("done-check logged for %d days; %d flagged turns judged, %d%% false alarms"
                % (n["stop_log_days"], n["stop_flags_judged"], n["stop_false_alarm_pct"] or 0))
    return "you said you have: " + ", ".join(n["other_tools"])


def hook_line(trigs, numbers, cmd="python ~/.sbk/bin/level_check.py"):
    parts = "; ".join("%s [%s, docs/ADVANCED.md %s]: %s" % (NAMES[k], k, PARTS[k], why(k, numbers)) for k in trigs)
    return ("[second-brain-kit weekly check] An upgrade would help: %s. In your first reply ask the user ONE "
            "yes/no question in their language whether to switch this on, quoting these numbers in plain "
            "words. Yes: follow docs/ADVANCED.md for that part and keep everything else. No: run "
            "`%s --decline %s` (it will not ask again for %d days). "
            "Never switch anything on without a yes." % (parts, cmd, " ".join(trigs), DECLINE_DAYS))


def in_scope(cwd, cfg, home):
    """Only a session where the user types: the notes folder, or the entry folder. Not SBK_HOME/state
    (the courier), not managers/* (topic sessions): they cannot ask the user, and one of them would use
    up the weekly question."""
    c = norm(cwd)
    for root in (cfg.get("vault") or os.environ.get("SBK_VAULT"), str(home / "entry")):
        if root:
            r = norm(root)
            if c == r or c.startswith(r + os.sep):
                return True
    return False


def kit_version():
    """The plugin's own version (only when this file sits in a plugin or clone, not in SBK_HOME/bin)."""
    p = Path(__file__).resolve().parent.parent / ".claude-plugin" / "plugin.json"
    try:
        return str(json.loads(p.read_text(encoding="utf-8")).get("version") or "")
    except Exception:
        return ""


def update_line(home, cfg, now, state):
    """One line when the tools copied to SBK_HOME/bin are not this kit's version, once a day."""
    v = kit_version()
    if not v or not (home / "bin").is_dir():
        return None
    try:
        have = (home / "bin" / "VERSION").read_text(encoding="utf-8").strip()
    except Exception:
        have = ""
    if have == v or state.get("last_update_notice") == day(now):
        return None
    state["last_update_notice"] = day(now)
    kit = Path(__file__).resolve().parent.parent
    return ("[second-brain-kit update] The kit is version %s but the tools in %s are %s. In your first reply "
            "tell the user in one line that the kit was updated, then copy the tools again: do docs/SETUP.md "
            "Step 1 point 2 from %s (the .py tools, the commands folder, and write the version into "
            "bin/VERSION). Do nothing else to their files."
            % (v, (home / "bin").as_posix(), have or "older (no VERSION file)", kit.as_posix()))


def run_hook(data, now):
    home = sbk_home()
    cfg = read_json(home / "config.json", {})
    m = os.environ.get("SBK_MODE_LEVEL_NOTICE") or (cfg.get("modes") or {}).get("level_notice") or "warn"
    if m == "off" or not cfg:
        return None
    if not in_scope(data.get("cwd") or os.getcwd(), cfg, home):
        return None
    state = read_json(state_path(home), {})
    last = state.get("last_hook_run")
    due = True
    try:
        if last and (now - datetime.strptime(last, "%Y-%m-%d")).days < THROTTLE_DAYS:
            due = False
    except Exception:
        pass
    trigs, numbers = [], {}
    if due:
        state["last_hook_run"] = day(now)
        trigs, numbers, _, _ = compute(now, state)
    review = learn_review(cfg, home, now, state) if m != "log" else None
    update = update_line(home, cfg, now, state) if m != "log" else None
    save_state(home, state)
    lines = [hook_line(trigs, numbers, '%s "%s"' % (py(cfg), (home / "bin" / "level_check.py").as_posix()))] \
        if trigs and m != "log" else []
    if review:
        lines.append(review)
    if update:
        lines.append(update)
    return "\n\n".join(lines) or None


def emit(obj):
    sys.stdout.buffer.write((json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8"))
    sys.stdout.flush()


def main(argv):
    now = parse_now(argv)
    if "--install" in argv:
        emit({"install": install_facts(now)})
        return
    if "--hook" in argv:
        try:
            raw = sys.stdin.buffer.read().decode("utf-8-sig", "replace")
            data = json.loads(raw) if raw.strip() else {}
        except Exception:
            data = {}
        line = run_hook(data, now)
        if line:
            emit({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": line}})
        return
    home = sbk_home()
    state = read_json(state_path(home), {})
    if "--decline" in argv:
        ids = [a for a in argv[argv.index("--decline") + 1:] if a in PARTS]
        state.setdefault("declined", {})
        for k in ids:
            state["declined"][k] = day(now)
        save_state(home, state)
        emit({"declined": ids, "until": day(now + timedelta(days=DECLINE_DAYS))})
        return
    trigs, numbers, _, _ = compute(now, state)
    save_state(home, state)
    emit({"triggers": trigs, "numbers": numbers})


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except Exception as e:  # fail open
        if "--hook" not in sys.argv:
            try:
                emit({"triggers": [], "numbers": {"error": repr(e)[:200]}})
            except Exception:
                pass
    sys.exit(0)
