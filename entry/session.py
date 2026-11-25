#!/usr/bin/env python3
"""Live routing (Full plan): get work into the session that owns it, now.

    session.py check                        can this computer route live? prints "routing: live" or "routing: inbox"
    session.py list                         the kit's sessions: running now (name, id, status), then stopped ones
                                            that can be resumed
    session.py open NAME ["first message"]  start NAME in the background in its folder (respects max_sessions);
                                            if NAME has an earlier conversation that stopped, continue that one
    session.py push NAME "text"             put a short message into the running session NAME
    session.py deliver NAME "text" [--ledger L0003] [--scheduled]
                                            inbox line + tracker first; then push if NAME runs, else continue its
                                            stopped conversation, else open a new one
    session.py stop NAME                    stop NAME; its conversation is kept, its state is its task.md
    session.py trust                        mark the kit folder as trusted, so background sessions can start there

How it works. A session is Claude Code started in <SBK_HOME>/managers/<NAME>/ (the entry: <SBK_HOME>/entry/)
and named NAME. Background sessions are `claude --bg` (Claude Code's agent view); a message goes into a
running session through Claude Code's cross-session messaging (ListAgents / SendMessage). The entry is a
Claude session and sends with its own SendMessage tool; a script (the alarm tick) has no such tool, so
`push` asks one tiny `claude -p --model haiku` run to deliver the text, which uses a little quota.
The inbox line is always written first: if anything after it fails, the work still waits there and the
session sees it when it starts (hooks/inbox_notice.py). Nothing here asks a question.

config.json (<SBK_HOME>): "routing" live|inbox (set by `check` at install), "max_sessions" (sessions other
than the entry running at once), "wake_limits" {"per_day": N, "min_gap_min": M} (only for --scheduled, i.e.
the alarm tick: Claude calls it may start per day, and minutes between two for one session), "vault".
One conversation per topic. Claude Code stops the process of a finished session that nobody is attached
to after about an hour (agent view docs, "The supervisor process"); the conversation stays on disk and the
row stays in `claude agents --json --all` without pid/status. So `running()` lists with --all, and
a topic whose process stopped is continued with `claude --resume <full session id> --bg "<message>"` (same
conversation, same ID when Claude Code can) instead of starting a second empty conversation.
`claude respawn <id>` also restarts a stopped session with its conversation but takes no message, so it is
not used for delivery.

A session can be given its model and effort (config.json "session_models", see model_args), its
permission mode ("permission_modes", see permission_mode), and the kit's hooks without installing them
for every conversation ("session_hooks", see settings_arg).

Each role has its own tool allowlist (config.json "allowed_tools": {"entry": ..., "topic": ..., "maintenance":
...}; the defaults are below). A tool call outside it is refused without a prompt (dontAsk), which a
session must report to the entry in the same turn with the exact command.

Tests: SBK_SESSION_DRYRUN=1 prints the claude commands instead of running them; SBK_AGENTS_JSON=<file>
is read instead of `claude agents --json --all`.
"""
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import send  # noqa: E402

MIN_VERSION = (2, 1, 234) if os.name == "nt" else (2, 1, 224)  # cross-session messaging, official docs
TOOLS = ("Read,Grep,Glob,Edit,Write,Bash(python:*),Bash(python3:*),Bash(py:*),"
         "PowerShell(python:*),PowerShell(python3:*),PowerShell(py:*),ToolSearch,ListAgents,SendMessage")
# a topic or maintenance session also searches the web, loads skills, hands work to a subagent and commits
# the notes it changed (git push stays refused: vault_guard asks, dontAsk turns that into a refusal)
_GIT = ("Bash(git add:*),Bash(git commit:*),Bash(git status:*),Bash(git diff:*),Bash(git log:*),Bash(git -C:*),"
        "PowerShell(git add:*),PowerShell(git commit:*),PowerShell(git status:*),PowerShell(git diff:*),"
        "PowerShell(git log:*),PowerShell(git -C:*)")
TOOLS_BY_ROLE = {"entry": TOOLS,
                 "topic": TOOLS + ",WebSearch,WebFetch,Skill,Agent," + _GIT,
                 "maintenance": TOOLS + ",WebSearch,WebFetch,Skill,Agent," + _GIT}
# the courier (claude -p) only carries a message; hooks off for that run (hooks page: "turn hooks off
# for that run with --settings '{"disableAllHooks": true}'")
COURIER_SETTINGS = "{\"disableAllHooks\":true}"
# dontAsk: a tool call outside TOOLS is refused instead of asked, so a background session never
# waits at a permission prompt nobody can see (seen in a clean test on Windows with acceptEdits).
INBOUND = '{"crossSessionInbound":"accept"}'


def cfg():
    try:
        return json.loads((send.home() / "config.json").read_text(encoding="utf-8"))
    except Exception:
        return {}


def dry():
    return os.environ.get("SBK_SESSION_DRYRUN") == "1"


def exe():
    """The claude command: the absolute path `check` saved in config.json (a cron job or the Windows task
    has a minimal PATH and cannot find it), else the one on PATH."""
    saved = cfg().get("claude_path")
    if saved and Path(saved).exists():
        return saved
    return shutil.which("claude")


def role_of(name):
    return "entry" if name == "entry" else "maintenance" if name == "maintenance" else "topic"


def tools_for(name):
    """The allowlist of one role: config.json allowed_tools.<role> if set, else the default, plus the Python
    command setup found (python_cmd) when it is not one of the usual three."""
    given = (cfg().get("allowed_tools") or {}).get(role_of(name))
    base = given if isinstance(given, str) and given.strip() else TOOLS_BY_ROLE[role_of(name)]
    py = (cfg().get("python_cmd") or "").strip()
    if py and py.split()[0] not in ("python", "python3", "py"):
        exe_ = py.split()[0].replace("\\", "/")
        base += ",Bash(%s:*),PowerShell(%s:*)" % (exe_, exe_)
    return base


PERMISSION_MODES = ("default", "acceptEdits", "dontAsk", "bypassPermissions", "plan", "auto")


def permission_mode(name):
    """The permission mode of one session: config.json "permission_modes": {"<session name>" or "<role>":
    "<mode>"}, else dontAsk (a background session nobody watches must never wait at a prompt; a tool call
    outside its list, or one a guard hook asks about, is refused and reported to the entry). An entry the
    user sits in front of can be given a mode in which the prompts appear."""
    table = cfg().get("permission_modes")
    pick = None
    if isinstance(table, dict):
        pick = table.get(name) or table.get(role_of(name))
    return pick if pick in PERMISSION_MODES else "dontAsk"


def settings_arg():
    """The --settings value of a kit session. Default: only "accept messages from the user's other
    sessions". With config.json "session_hooks" (true = the kit's own hook set,
    templates/settings.hooks.example.json; or the path of a settings file of the user's), that file's
    content is given to the sessions the kit starts and to no other conversation. This is for a computer
    whose settings.json already carries hooks: installing the plugin there would put the kit's hooks on
    every conversation, next to the ones already running. "__KIT__" in the file becomes the kit's hooks
    folder. The merged file is written to <SBK_HOME>/state/session-settings.json at each start."""
    which = cfg().get("session_hooks")
    if not which:
        return INBOUND
    kit = Path(__file__).resolve().parent.parent
    src = kit / "templates" / "settings.hooks.example.json" if which is True else Path(str(which))
    try:
        data = json.loads(src.read_text(encoding="utf-8").replace("__KIT__", (kit / "hooks").as_posix()))
        data.pop("_comment", None)
        data["crossSessionInbound"] = "accept"
        out = send.home() / "state" / "session-settings.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
        return str(out)
    except Exception as e:
        print("session_hooks: cannot use %s (%r); the session starts without them" % (src, e))
        return INBOUND


def model_args(name):
    """--model / --effort for one session, from config.json "session_models":
    {"<session name>" or "<role>": {"model": "...", "effort": "..."}} (a name wins over its role: entry,
    topic, maintenance). Nothing set: Claude Code's own default, as before."""
    table = cfg().get("session_models")
    if not isinstance(table, dict):
        return []
    pick = table.get(name) if isinstance(table.get(name), dict) else table.get(role_of(name))
    out = []
    for key in ("model", "effort"):
        val = pick.get(key) if isinstance(pick, dict) else None
        if isinstance(val, str) and re.fullmatch(r"[A-Za-z0-9._\[\]-]+", val.strip()):
            out += ["--" + key, val.strip()]
    return out


def child_env():
    """The environment for claude: a session started from cron or the Windows task inherits a minimal PATH
    (agent view docs: a background session runs with the PATH of the shell it was dispatched from), so put
    the folders of claude and of this Python, and the usual install folders, in front."""
    env = dict(os.environ)
    extra = []
    if exe():
        extra.append(str(Path(exe()).parent))
    extra.append(str(Path(sys.executable).parent))
    py = (cfg().get("python_cmd") or "").split()
    found = shutil.which(py[0]) if py else None
    if found:
        extra.append(str(Path(found).parent))
    for d in ("/opt/homebrew/bin", "/usr/local/bin", str(Path.home() / ".local" / "bin")):
        if Path(d).is_dir():
            extra.append(d)
    env["PATH"] = os.pathsep.join(extra + [env.get("PATH", "")])
    return env


def folder(name):
    return send.home() / ("entry" if name == "entry" else "managers/" + name)


def _norm(p):
    try:
        return str(Path(p).resolve()).lower()
    except Exception:
        return str(p).lower()


def rows_all():
    """Every kit session `claude agents --json --all` lists, alive or not:
    [{name, id, status, state, alive, kind, startedAt, sessionId}]. pid and status exist only while the
    process is alive; a finished conversation whose process the supervisor stopped is still a row."""
    raw = None
    fake = os.environ.get("SBK_AGENTS_JSON")
    try:
        if fake:
            raw = Path(fake).read_text(encoding="utf-8")
        elif exe():
            raw = subprocess.run([exe(), "agents", "--json", "--all"], capture_output=True, text=True,
                                 encoding="utf-8", errors="replace", timeout=60, stdin=subprocess.DEVNULL,
                                 env=child_env()).stdout
    except Exception:
        raw = None
    try:
        rows = json.loads(raw) if raw else []
    except Exception:
        rows = []
    root = _norm(send.home())
    out = []
    for r in rows if isinstance(rows, list) else []:
        if not r.get("name"):
            continue
        if not _norm(r.get("cwd", "")).startswith(root):
            continue  # a session of the user's own with the same name elsewhere is not ours
        out.append({"name": r["name"], "id": r.get("id") or r.get("sessionId", "")[:8], "status": r.get("status", ""),
                    "state": r.get("state", ""), "alive": bool(r.get("pid")),
                    "kind": r.get("kind", ""), "startedAt": r.get("startedAt", 0), "sessionId": r.get("sessionId", "")})
    return out


def running():
    """Kit sessions alive now (status idle or busy)."""
    return [r for r in rows_all() if r["alive"]]


def resumable(name, rows=None):
    """The newest stopped conversation of NAME (state done or stopped, not alive), or None."""
    rows = rows if rows is not None else rows_all()
    cands = [r for r in rows if r["name"] == name and not r["alive"] and r["sessionId"]
             and r["state"] in ("done", "stopped", "")]
    return max(cands, key=lambda r: r["startedAt"]) if cands else None


def find(name, rows=None):
    return next((r for r in (rows if rows is not None else running()) if r["name"] == name), None)


def unticked(name):
    try:
        text = (send.home() / "inbox" / (name + ".md")).read_text(encoding="utf-8")
    except Exception:
        return 0
    return sum(1 for l in text.splitlines() if l.startswith("- [ ]"))


def version_ok(text):
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", text or "")
    return bool(m) and tuple(int(x) for x in m.groups()) >= MIN_VERSION


def check():
    """routing: live needs the claude command, a version with cross-session messaging, and agent view."""
    if ".claude" in [x.lower() for x in send.home().resolve().parts]:
        return "inbox", ("%s is inside a .claude folder, where Claude Code does not let a background session "
                         "write its task.md; move it to ~/.sbk" % send.home())
    if not exe():
        return "inbox", "no claude command here (the desktop app alone cannot start background sessions)"
    try:
        v = subprocess.run([exe(), "--version"], capture_output=True, text=True, timeout=60,
                           stdin=subprocess.DEVNULL).stdout
    except Exception as e:
        return "inbox", "claude --version failed: %r" % (e,)
    if not version_ok(v):
        return "inbox", "Claude Code %s is older than %s; run claude update" % (v.strip(), ".".join(map(str, MIN_VERSION)))
    try:
        r = subprocess.run([exe(), "agents", "--json", "--all"], capture_output=True, text=True, timeout=60,
                           stdin=subprocess.DEVNULL)
        json.loads(r.stdout)
    except Exception:
        return "inbox", "claude agents --json --all did not answer (agent view unavailable here)"
    return "live", "Claude Code %s: background sessions and cross-session messaging" % v.strip()


def intro(name, first=""):
    who = "the entry" if name == "entry" else "the " + name + " session"
    txt = ("You are %s of second-brain-kit, started in the background. Follow this folder's CLAUDE.md: check the "
           "notes first (including the 和 AI 協作 note), read task.md (and the newest old-*-words.md here, if any), take the unticked lines of your inbox "
           "(the start-up notice shows them), do the work, close tracker items with evidence and report back to "
           "the entry (SendMessage to \"entry\" if it is running). Ask no questions: write what only the user can "
           "do as CLAUDE.md says." % who)
    return txt + ((" " + first) if first else "")


def wake_ok(name, c, now):
    """--scheduled only: per-day cap and minimum gap per session, both from config wake_limits."""
    lim = c.get("wake_limits") if isinstance(c.get("wake_limits"), dict) else {}
    per_day = int(lim.get("per_day", 4))
    gap = datetime.timedelta(minutes=int(lim.get("min_gap_min", 120)))
    st = load_wakes()
    day = now.strftime("%Y-%m-%d")
    if st.get("day") != day:
        st = {"day": day, "count": 0, "last": st.get("last", {})}
    if st["count"] >= per_day:
        return False, "daily limit %d reached" % per_day, st
    last = st.get("last", {}).get(name)
    if last:
        try:
            if now - datetime.datetime.strptime(last, "%Y-%m-%dT%H:%M") < gap:
                return False, "woken less than %d minutes ago" % (gap.seconds // 60 + gap.days * 1440), st
        except ValueError:
            pass
    return True, "", st


def wakes_file():
    return send.home() / "state" / "wakes.json"


def load_wakes():
    try:
        return json.loads(wakes_file().read_text(encoding="utf-8"))
    except Exception:
        return {}


def count_wake(st, name, now):
    st["count"] = st.get("count", 0) + 1
    st.setdefault("last", {})[name] = now.strftime("%Y-%m-%dT%H:%M")
    wakes_file().parent.mkdir(parents=True, exist_ok=True)
    wakes_file().write_text(json.dumps(st, indent=1), encoding="utf-8")


def run_claude(args, cwd=None, timeout=300):
    if dry():
        shown = [a if (len(a) < 60 or (i and args[i - 1] == "--allowedTools")) else a[:57] + "..." for i, a in enumerate(args)]
        print("dry run: claude" + (" (%s)" % exe() if cfg().get("claude_path") else "") + " " + " ".join(shown))
        return 0, ""
    r = subprocess.run([exe()] + args, cwd=str(cwd) if cwd else None, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=timeout, stdin=subprocess.DEVNULL,
                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), env=child_env())
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def stop(name, rows=None):
    r = find(name, rows)
    if not r:
        print("not running: " + name)
        return False
    try:
        import handover
        src = handover.transcript(r.get("sessionId"))
        if src:
            handover.words(src, folder(name) / ("old-%s-words.md" % r["id"]))
    except Exception:
        pass
    run_claude(["stop", r["id"]], timeout=60)
    print("stopped %s %s (its conversation is kept; the user's words are in old-%s-words.md)" % (name, r["id"], r["id"]))
    return True


def open_session(name, first="", replace_ok=False, text=None, fresh=False):
    """Start NAME in the background. Returns 0 opened / already running, 3 cap, 4 not possible here.
    NAME's earlier conversation, if its process stopped, is continued (one conversation per topic);
    fresh=True always starts a new one (the hand-over does, after it removed the old)."""
    c = cfg()
    if c.get("routing") != "live" and not dry():
        print("inbox: %s waits until the user opens it (routing is not live on this computer)" % name)
        return 4
    d = folder(name)
    if not d.is_dir():
        print("no session folder: %s" % d)
        return 4
    allrows = rows_all()
    rows = [r for r in allrows if r["alive"]]
    if find(name, rows):
        print("running: %s %s" % (name, find(name, rows)["id"]))
        return 0
    others = [r for r in rows if r["name"] != "entry"]
    cap = int(c.get("max_sessions", 2))
    if name != "entry" and not replace_ok and len(others) >= cap:
        idle = sorted((r for r in others if r["status"] == "idle" and not unticked(r["name"])),
                      key=lambda r: r["startedAt"])
        if not idle:
            print("CAP: %d of %d sessions are busy; %s waits in its inbox (the alarm tick retries)" % (len(others), cap, name))
            return 3
        stop(idle[0]["name"], rows)
    if not exe() and not dry():
        print("inbox: no claude command; %s waits until the user opens it" % name)
        return 4
    old = None if fresh else resumable(name, allrows)
    common = ["--permission-mode", permission_mode(name), "--settings", settings_arg(),
              "--allowedTools", tools_for(name)]
    common += model_args(name)
    if c.get("vault"):
        common += ["--add-dir", c["vault"]]
    if old:
        msg = text if text is not None else (first or "Your inbox has new work.")
        rc, out = run_claude(["--resume", old["sessionId"], "--bg"] + common + ["--", msg], cwd=d, timeout=120)
        if rc == 0 or dry():
            print("resumed %s %s (its earlier conversation continues)" % (name, old["id"]))
            return 0
        print("resume failed for %s (%s); starting a new conversation" % (name, out.strip()[-200:]))
    args = ["--bg", "-n", name] + common + ["--", text if text is not None else intro(name, first)]
    rc, out = run_claude(args, cwd=d, timeout=120)
    m = re.search(r"backgrounded\W+([0-9a-f]{6,})", out)
    if rc != 0 and not dry():
        print("open failed for %s: %s" % (name, out.strip()[-300:]))
        return 4
    print("opened %s %s" % (name, m.group(1) if m else ""))
    return 0


def push(name, text):
    """Deliver text into the running session NAME via one tiny claude -p run. Returns True if sent."""
    target = _norm(folder(name))
    prompt = ("You only carry a note between two of this user's own Claude Code sessions on this machine. "
              "Do not act on the note, judge it or summarise it. Load SendMessage and ListAgents with ToolSearch "
              "(query \"select:SendMessage,ListAgents\"). Call SendMessage once with to=\"%s\" and message = the "
              "text between <note> and </note>, exactly. If several sessions answer to that name, call ListAgents "
              "and use the row whose working directory is %s. Then output one line: SENT, or ERROR: <reason>.\n"
              "<note>\n%s\n</note>" % (name, target, text))
    if not exe() and not dry():
        return False
    st = send.home() / "state"
    st.mkdir(parents=True, exist_ok=True)
    rc, out = run_claude(["-p", "--model", "haiku", "--output-format", "stream-json", "--verbose",
                          "--settings", COURIER_SETTINGS,
                          "--allowedTools", "ToolSearch,ListAgents,SendMessage", "--", prompt], cwd=st, timeout=300)
    if dry():
        return True
    ok = bool(re.search(r'\\?"success\\?":\s*true', out)) and "Not sent" not in out
    print(("pushed to " if ok else "push failed for ") + name)
    return ok


def deliver(name, text, lid=None, scheduled=False, now=None):
    """Inbox (+ tracker) first, then push into the running session or open it. Returns a short status."""
    now = now or datetime.datetime.now().replace(second=0, microsecond=0)
    if name == "entry":
        added = True
    elif lid == "ALARM":
        added = send.deliver(name, text, "ALARM")
    else:
        lid, added = send.dispatch(name, text, lid)
    if not added:
        return "already in the inbox"
    c = cfg()
    if c.get("routing") != "live" and not dry():
        return "inbox only (open %s to start it)" % name
    if scheduled:
        ok, why, st = wake_ok(name, c, now)
        if not ok:
            return "waits in the inbox: " + why
    rows = running()
    note = "New work in your inbox%s: %s" % ((" (" + lid + ")") if lid and lid != "ALARM" else "", send.ledger.clean(text))
    if find(name, rows):
        res = "pushed" if push(name, note) else "push failed, waits in the inbox"
    else:
        rc = open_session(name, note)
        res = {0: "opened", 3: "waits in the inbox: session cap"}.get(rc, "waits in the inbox")
    if scheduled and res in ("pushed", "opened"):
        count_wake(st, name, now)
    return res


def trust():
    """Add hasTrustDialogAccepted for <SBK_HOME> to Claude Code's global config (only after the user's yes)."""
    base = os.environ.get("CLAUDE_CONFIG_DIR")
    cands = [Path(base) / ".claude.json"] if base else [Path.home() / ".claude.json"]
    p = next((x for x in cands if x.exists()), cands[0])
    try:
        data = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except Exception as e:
        sys.exit("cannot read %s: %r" % (p, e))
    key = str(send.home().resolve()).replace("\\", "/")
    data.setdefault("projects", {}).setdefault(key, {})["hasTrustDialogAccepted"] = True
    tmp = p.with_suffix(".json.sbk-tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(str(tmp), str(p))
    print("trusted %s in %s" % (key, p))


def main():
    send.ledger.setup_output()
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    cmd = a[0]
    if cmd == "check":
        mode, why = check()
        p = send.home() / "config.json"
        if p.exists():  # keep every other value; only "routing" and "claude_path" change
            try:
                c = json.loads(p.read_text(encoding="utf-8"))
                found = shutil.which("claude")
                changed = c.get("routing") != mode
                if found and c.get("claude_path") != str(Path(found).resolve()):
                    c["claude_path"] = str(Path(found).resolve())  # a cron job / scheduled task cannot find it by PATH
                    changed = True
                if changed:
                    c["routing"] = mode
                    tmp = p.with_suffix(".tmp")
                    tmp.write_text(json.dumps(c, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                    os.replace(tmp, p)
            except Exception as e:
                print("config.json not updated: %r" % (e,))
        print("routing: %s  (%s)" % (mode, why))
    elif cmd == "list":
        every = rows_all()
        rows = [r for r in every if r["alive"]]
        for r in rows:
            print("%-14s %-9s %-5s %s" % (r["name"], r["id"], r["status"], r["kind"]))
        if not rows:
            print("no kit sessions running")
        for name in sorted({r["name"] for r in every if not r["alive"]} - {r["name"] for r in rows}):
            old = resumable(name, every)
            if old:
                print("%-14s %-9s %-5s %s" % (name, old["id"], "stopped", "(continues when work arrives)"))
    elif cmd == "open" and len(a) >= 2:
        sys.exit(open_session(a[1], " ".join(a[2:])))
    elif cmd == "push" and len(a) >= 3:
        sys.exit(0 if push(a[1], " ".join(a[2:])) else 1)
    elif cmd == "deliver" and len(a) >= 3:
        rest = a[1:]
        lid = None
        if "--ledger" in rest:
            k = rest.index("--ledger")
            lid = rest[k + 1].upper()
            rest = rest[:k] + rest[k + 2:]
        sched = "--scheduled" in rest
        rest = [x for x in rest if x != "--scheduled"]
        print("%s: %s" % (rest[0], deliver(rest[0], " ".join(rest[1:]), lid, sched)))
    elif cmd == "stop" and len(a) >= 2:
        stop(a[1])
    elif cmd == "trust":
        trust()
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
