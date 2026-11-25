#!/usr/bin/env python3
"""Smoke test for the whole kit. Feeds sample input to every hook and tool, in a throw-away
folder, and prints PASS / FAIL per case. Nothing outside the temp folder is touched.

    python scripts/selftest.py [--keep]        exit code 1 if any case fails
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
PY = sys.executable
results = []


def check(name, ok, detail=""):
    results.append(ok)
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else "  <- " + str(detail)[:300]))


def run(args, stdin=None, env=None, cwd=None):
    e = dict(os.environ)
    e.update(env or {})
    r = subprocess.run([PY] + [str(a) for a in args], input=(json.dumps(stdin) if stdin is not None else ""),
                       capture_output=True, text=True, encoding="utf-8", errors="replace", env=e, cwd=cwd)
    return r.returncode, r.stdout, r.stderr


def jl(path, recs):
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in recs) + "\n", encoding="utf-8")


def user(text):
    return {"type": "user", "message": {"role": "user", "content": text}}


def tool(name, inp):
    return {"type": "assistant", "message": {"role": "assistant", "content": [
        {"type": "tool_use", "id": "t1", "name": name, "input": inp}]}}


def result():
    return {"type": "user", "message": {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": "t1", "content": "ok"}]}}


def say(text):
    return {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": text}]}}


def level_tests(tmp, cfg):
    import re
    from datetime import datetime, timedelta, timezone
    LC = KIT / "scripts" / "level_check.py"
    LN = KIT / "hooks" / "level_notice.py"
    now = datetime.now().replace(microsecond=0)
    N = now.strftime("%Y-%m-%dT%H:%M:%S")

    def ago(days, fmt="%Y-%m-%dT%H:%M:%S"):
        return (now - timedelta(days=days)).strftime(fmt)

    def utc(days):  # transcript timestamps are UTC with a Z
        return datetime.fromtimestamp((now - timedelta(days=days)).timestamp(), timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    vault = tmp / "lvault"
    vault.mkdir(exist_ok=True)
    (vault / ".sbk-vault").write_text("", encoding="utf-8")
    enc = re.sub(r"[^A-Za-z0-9]", "-", os.path.abspath(str(vault)))
    count = [0]

    def setup(ledger=None, extra_cfg=None, files=None, config=True):
        count[0] += 1
        h = tmp / ("lh%d" % count[0])
        c = tmp / ("lc%d" % count[0])
        h.mkdir()
        c.mkdir()
        if config:
            (h / "config.json").write_text(json.dumps(dict(cfg, vault=str(vault), **(extra_cfg or {}))), encoding="utf-8")
        if ledger:
            (h / "ledger.md").write_text("# Ledger\n\n" + "".join(ledger), encoding="utf-8")
        for rel, text in (files or {}).items():
            p = h / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")
        return h, c

    def env(h, c, **kw):
        e = {"SBK_HOME": str(h), "SBK_VAULT": "", "CLAUDE_CONFIG_DIR": str(c), "ANTHROPIC_API_KEY": ""}
        e.update(kw)
        return e

    def check_now(h, c, when=N):
        rc, out, err = run([LC, "--now", when], None, env(h, c))
        try:
            return rc, json.loads(out.strip().splitlines()[-1])
        except Exception:
            return rc, {"triggers": None, "raw": out + err}

    def item(i, text, st="open"):
        return "- L%04d | %s | %s | %s | ev: \n" % (i, st, ago(20), text)

    def transcript(c, recs, folder=None):
        d = c / "projects" / (folder or enc)
        d.mkdir(parents=True, exist_ok=True)
        f = d / ("s%d.jsonl" % len(list(d.glob("*.jsonl"))))
        jl(f, recs)
        return f

    def compact(days, cwd=None):
        return {"type": "system", "subtype": "compact_boundary", "content": "Conversation compacted",
                "timestamp": utc(days), "cwd": str(cwd or vault)}

    def human(text, days=1):
        return {"type": "user", "message": {"role": "user", "content": text}, "timestamp": utc(days), "cwd": str(vault)}

    # no history at all
    h, c = setup(config=False)
    rc, r = check_now(h, c)
    check("level: no history at all -> no trigger", rc == 0 and r.get("triggers") == [], r)
    h, c = setup()
    rc, r = check_now(h, c)
    check("level: fresh Basic install -> no trigger", rc == 0 and r.get("triggers") == [], r)

    # multi_session: open items >= 10 on two checks a week apart
    many = [item(i, "thing %d" % i) for i in range(1, 13)]
    h, c = setup(many)
    check_now(h, c, ago(8))
    rc, r = check_now(h, c)
    check("level: 12 open items on two checks 8 days apart -> multi_session",
          "multi_session" in (r.get("triggers") or []) and r["numbers"]["prev_open_items"] == 12, r)
    h, c = setup(many)
    rc, r = check_now(h, c)
    check("level: 12 open items on one check only -> no trigger", r.get("triggers") == [], r)
    h, c = setup(many)
    check_now(h, c, ago(3))
    rc, r = check_now(h, c)
    check("level: two checks only 3 days apart -> no trigger (one busy week)", r.get("triggers") == [], r)
    h, c = setup([item(i, "thing %d" % i) for i in range(1, 10)])
    check_now(h, c, ago(8))
    rc, r = check_now(h, c)
    check("level: 9 open items -> no trigger", r.get("triggers") == [], r)

    # multi_session: items in >= 3 topics
    three = [item(1, "[study] read ch 3"), item(2, "[job] shift swap"), item(3, "poster", "dispatched:club")]
    h, c = setup(three)
    check_now(h, c, ago(9))
    rc, r = check_now(h, c)
    check("level: open items in 3 topics on two checks -> multi_session",
          "multi_session" in (r.get("triggers") or []) and r["numbers"]["open_topics"] == 3, r)
    h, c = setup(three[:2] + [item(3, "[study] ch 4")])
    check_now(h, c, ago(9))
    rc, r = check_now(h, c)
    check("level: open items in 2 topics -> no trigger", r.get("triggers") == [], r)

    # multi_session: compactions of the notes-folder session
    h, c = setup()
    transcript(c, [human("hi", 3), compact(3), compact(1)])
    rc, r = check_now(h, c)
    check("level: notes session compacted 2 times in 7 days -> multi_session",
          "multi_session" in (r.get("triggers") or []) and r["numbers"]["compactions_7d"] == 2, r)
    h, c = setup()
    transcript(c, [human("hi", 3), compact(2)])
    rc, r = check_now(h, c)
    check("level: compacted once -> no trigger", r.get("triggers") == [], r)
    h, c = setup()
    transcript(c, [human("hi", 12), compact(12), compact(10)])
    rc, r = check_now(h, c)
    check("level: 2 compactions but 10+ days old -> no trigger", r.get("triggers") == [], r)
    h, c = setup()
    other = tmp / "elsewhere"
    transcript(c, [compact(2, other), compact(1, other)], folder=re.sub(r"[^A-Za-z0-9]", "-", str(other)))
    rc, r = check_now(h, c)
    check("level: compactions in another project folder -> no trigger", r.get("triggers") == [], r)

    # alarms
    h, c = setup([item(1, "[study] report due %s" % ago(2, "%Y-%m-%d"))])
    rc, r = check_now(h, c)
    check("level: open item past its due date -> alarms", "alarms" in (r.get("triggers") or []), r)
    h, c = setup([item(1, "[study] report due %s" % ago(2, "%Y-%m-%d"), "done")])
    rc, r = check_now(h, c)
    check("level: past due date but item closed -> no trigger", r.get("triggers") == [], r)
    h, c = setup([item(1, "[study] report due %s" % ago(-5, "%Y-%m-%d"))])
    rc, r = check_now(h, c)
    check("level: due date still ahead -> no trigger", r.get("triggers") == [], r)
    h, c = setup()
    transcript(c, [human("週五要交報告，到時候提醒我", 2)])
    rc, r = check_now(h, c)
    check("level: user asked to be reminded -> alarms", "alarms" in (r.get("triggers") or []), r)
    h, c = setup(files={"alarms.md": "| id | when | to | text |\n"})
    transcript(c, [human("remind me on Friday", 2)])
    rc, r = check_now(h, c)
    check("level: reminders already on -> not offered again", r.get("triggers") == [], r)

    # block_mode: stop_evidence log for 2+ weeks, < 25% false alarms
    def flagged(next_msgs, days_old):
        hh, cc = setup()
        recs = [user("task 0")]
        for m in next_msgs:
            recs += [tool("Write", {"file_path": "a.txt", "content": "x"}), result(), say("Done."), user(m)]
        t = tmp / ("flag%d.jsonl" % count[0])
        jl(t, recs)
        log = "".join("%s log: turn %d of %s: You said the work is done\n" % (ago(days_old), i + 1, t)
                      for i in range(len(next_msgs)))
        (hh / "logs").mkdir()
        (hh / "logs" / "stop_evidence.log").write_text(log, encoding="utf-8")
        return hh, cc
    h, c = flagged(["還是不行，沒改到", "it still fails", "wrong file", "沒有改"], 20)
    rc, r = check_now(h, c)
    check("level: 4 flags, all followed by a complaint, 20 days of log -> block_mode",
          "block_mode" in (r.get("triggers") or []) and r["numbers"]["stop_false_alarm_pct"] == 0, r)
    h, c = flagged(["thanks", "great", "next please", "還是不行"], 20)
    rc, r = check_now(h, c)
    check("level: 75% false alarms -> no trigger", r.get("triggers") == [], r)
    h, c = flagged(["還是不行，沒改到", "it still fails", "wrong file", "沒有改"], 3)
    rc, r = check_now(h, c)
    check("level: good flags but only 3 days of log -> no trigger", r.get("triggers") == [], r)
    h, c = flagged(["還是不行", "wrong file"], 20)
    rc, r = check_now(h, c)
    check("level: only 2 judged flags -> no trigger", r.get("triggers") == [], r)

    # multi_tool
    h, c = setup(extra_cfg={"other_tools": "I also use ChatGPT"})
    rc, r = check_now(h, c)
    check("level: other tool named at setup -> multi_tool", r.get("triggers") == ["multi_tool"], r)
    h, c = setup()
    transcript(c, [human("Gemini 可以幫忙讀這份 PDF 嗎", 4)])
    rc, r = check_now(h, c)
    check("level: other tool mentioned in a notes session -> multi_tool", "multi_tool" in (r.get("triggers") or []), r)
    h, c = setup(extra_cfg={"other_tools": "ChatGPT"}, files={"channels.md": "| tool |\n"})
    rc, r = check_now(h, c)
    check("level: tool guide already on -> no trigger", r.get("triggers") == [], r)
    rc, out, _ = run([LC, "--decline", "multi_tool", "--now", N], None, env(*setup(extra_cfg={"other_tools": "x"})))
    hd, cd = tmp / ("lh%d" % count[0]), tmp / ("lc%d" % count[0])
    rc, r = check_now(hd, cd)
    check("level: declined trigger is not offered again for 28 days", "multi_tool" not in (r.get("triggers") or []), r)
    rc, r = check_now(hd, cd, (now + timedelta(days=29)).strftime("%Y-%m-%dT%H:%M:%S"))
    check("level: declined trigger comes back after 28 days", "multi_tool" in (r.get("triggers") or []), r)

    # the SessionStart hook: 7-day throttle, notes folder only
    h, c = setup(extra_cfg={"other_tools": "ChatGPT"})
    cfg_before = (h / "config.json").read_bytes()
    rc, out, _ = run([LN], {"cwd": str(tmp), "hook_event_name": "SessionStart"}, env(h, c, SBK_NOW=N))
    check("hook level_notice: outside the notes folder -> silent", rc == 0 and out.strip() == "", out)
    rc, out, _ = run([LN], {"cwd": str(vault), "hook_event_name": "SessionStart"}, env(h, c, SBK_NOW=N))
    ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"] if out.strip() else ""
    check("hook level_notice: trigger -> one line asking for one yes/no with the numbers",
          "multi_tool" in ctx and "yes/no" in ctx and "chatgpt" in ctx.lower() and "\n" not in ctx, out)
    rc, out, _ = run([LN], {"cwd": str(vault), "hook_event_name": "SessionStart"},
                     env(h, c, SBK_NOW=(now + timedelta(days=3)).strftime("%Y-%m-%dT%H:%M:%S")))
    check("hook level_notice: 3 days later -> throttled, silent", rc == 0 and out.strip() == "", out)
    rc, out, _ = run([LN], {"cwd": str(vault), "hook_event_name": "SessionStart"},
                     env(h, c, SBK_NOW=(now + timedelta(days=8)).strftime("%Y-%m-%dT%H:%M:%S")))
    check("hook level_notice: 8 days later -> runs again", "multi_tool" in out, out)
    check("level: config.json never changed", (h / "config.json").read_bytes() == cfg_before)
    h, c = setup(extra_cfg={"other_tools": "ChatGPT"})
    rc, out, _ = run([LN], {"cwd": str(vault)}, env(h, c, SBK_NOW=N, SBK_MODE_LEVEL_NOTICE="off"))
    check("hook level_notice: mode off -> silent", rc == 0 and out.strip() == "", out)
    h, c = setup(config=False)
    rc, out, _ = run([LN], {"cwd": str(vault)}, env(h, c, SBK_NOW=N))
    check("hook level_notice: no setup yet -> silent", rc == 0 and out.strip() == "", out)

    # fail-open
    h, c = setup()
    (h / "state").mkdir()
    (h / "state" / "level_check.json").write_text("{{{ not json", encoding="utf-8")
    rc, r = check_now(h, c)
    check("level: broken state file -> still answers, exit 0", rc == 0 and r.get("triggers") == [], r)
    r2 = subprocess.run([PY, str(LN)], input="not json at all", capture_output=True, text=True,
                        env=dict(os.environ, **env(h, c, SBK_NOW=N)))
    check("hook level_notice: garbage input -> exit 0", r2.returncode == 0, r2.stderr)

    # install facts (Step 0 of SETUP)
    h, c = setup()
    for i in range(3):
        transcript(c, [human("hi", 1)], folder="proj%d" % i)
    rc, out, _ = run([LC, "--install", "--now", N], None, env(h, c))
    inst = json.loads(out)["install"] if out.strip() else {}
    check("level --install: 3 active project folders -> evidence for Full",
          inst.get("active_projects_14d") == 3 and inst.get("multi_session_evidence") is True, out)
    h, c = setup()
    rc, out, _ = run([LC, "--install", "--now", N], None, env(h, c))
    inst = json.loads(out)["install"] if out.strip() else {}
    check("level --install: no history -> no evidence (Basic)",
          inst.get("active_projects_14d") == 0 and inst.get("multi_session_evidence") is False, out)


def main():
    keep = "--keep" in sys.argv
    tmp = Path(tempfile.mkdtemp(prefix="sbk-selftest-"))
    home = tmp / "home"
    vault = tmp / "vault"
    home.mkdir()
    env = {"SBK_HOME": str(home), "SBK_VAULT": "", "ANTHROPIC_API_KEY": ""}
    H = KIT / "hooks"
    try:
        # ---- Stop hook ----
        t = tmp / "t.jsonl"
        jl(t, [user("fix a.txt"), tool("Write", {"file_path": "a.txt", "content": "x"}), result(),
               say("Done, I fixed it.")])
        rc, out, _ = run([H / "stop_evidence.py"], {"transcript_path": str(t)}, env)
        logf = home / "logs" / "stop_evidence.log"
        check("stop: Basic default only logs, never blocks", rc == 0 and out.strip() == "" and logf.exists()
              and "log:" in logf.read_text(encoding="utf-8"), out)
        envb = dict(env, SBK_MODE_STOP_EVIDENCE="block")
        rc, out, _ = run([H / "stop_evidence.py"], {"transcript_path": str(t)}, envb)
        check("stop: block mode (Advanced) blocks done without a check", rc == 0 and '"decision": "block"' in out, out)
        rc, out, _ = run([H / "stop_evidence.py"], {"transcript_path": str(t), "stop_hook_active": True}, envb)
        check("stop: second stop passes (no trap)", rc == 0 and out.strip() == "", out)
        jl(t, [user("fix a.txt"), tool("Write", {"file_path": "a.txt", "content": "x"}), result(),
               tool("Read", {"file_path": "a.txt"}), result(), say("Done, a.txt now says x.")])
        rc, out, _ = run([H / "stop_evidence.py"], {"transcript_path": str(t)}, envb)
        check("stop: done after a read-back passes", rc == 0 and out.strip() == "", out)
        jl(t, [user("fix a.txt"), tool("Write", {"file_path": "a.txt", "content": "x"}), result(),
               say("Fixed, but not verified yet.")])
        rc, out, _ = run([H / "stop_evidence.py"], {"transcript_path": str(t)}, envb)
        check("stop: admitting 'not verified' passes", rc == 0 and out.strip() == "", out)
        rc, out, _ = run([H / "stop_evidence.py"], {"transcript_path": str(tmp / "missing.jsonl")}, envb)
        check("stop: missing transcript fails open", rc == 0 and out.strip() == "", out)
        rc, out, _ = run([H / "stop_evidence.py"], {"transcript_path": str(t)}, dict(env, SBK_MODE_STOP_EVIDENCE="log"))
        check("stop: log mode never blocks", rc == 0 and out.strip() == "", out)
        jl(t, [user("fix a.txt"), tool("Write", {"file_path": "a.txt", "content": "x"}), result(), say("Done.")])
        rc, out, _ = run([H / "stop_evidence.py", "--replay", t], None, env)
        check("stop: --replay works", rc == 0 and "BLOCK" in out, out)

        # ---- compaction re-injection ----
        t2 = tmp / "t2.jsonl"
        jl(t2, [user("first request: tidy my notes"),
                {"type": "user", "isMeta": True, "message": {"role": "user", "content": "meta noise"}},
                user("<system-reminder>injected</system-reminder>"), say("ok"),
                user("second request: also rename the folder")])
        rc, out, _ = run([H / "requests_reinject.py"], {"transcript_path": str(t2), "session_id": "s1",
                                                        "hook_event_name": "SessionStart"}, env)
        ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"] if out.strip() else ""
        check("reinject: both user messages come back", "tidy my notes" in ctx and "rename the folder" in ctx, out)
        check("reinject: meta and system text left out", "meta noise" not in ctx and "injected" not in ctx, ctx)
        check("reinject: full list saved", (home / "requests" / "s1.md").exists())

        # ---- vault + read_whole + vault_guard ----
        (vault / "20-29 學習" / "21 課程").mkdir(parents=True)
        (vault / ".sbk-vault").write_text("", encoding="utf-8")
        note = vault / "20-29 學習" / "21 課程" / "21-01 線性代數.md"
        note.write_text("---\ntype: skill\nstatus: active\nsummary: s\ncreated: 2026-01-01\nmodified: 2026-01-02\n"
                        "origin: user\n---\n\n" + "line\n" * 12, encoding="utf-8")
        rc, out, _ = run([H / "read_whole.py"], {"tool_name": "Bash", "cwd": str(vault),
                                                 "tool_input": {"command": 'head -n 5 "20-29 學習/21 課程/21-01 線性代數.md"'}}, env)
        check("read_whole: head on a note is denied", '"permissionDecision": "deny"' in out, out)
        rc, out, _ = run([H / "read_whole.py"], {"tool_name": "Bash", "cwd": str(vault),
                                                 "tool_input": {"command": "cat 21-01.md"}}, env)
        check("read_whole: cat is allowed", out.strip() == "", out)
        rc, out, _ = run([H / "read_whole.py"], {"tool_name": "Bash", "cwd": str(tmp),
                                                 "tool_input": {"command": "head -n 5 README.md"}}, env)
        check("read_whole: outside the vault is left alone", out.strip() == "", out)
        for cmd, expect in [("git push origin main", True), ("git commit --no-verify -m x", True),
                            ("git reset --hard HEAD~1", True), ("rm -rf build", True),
                            ("git status && ls", False), ("git commit -m x", False)]:
            rc, out, _ = run([H / "vault_guard.py"], {"tool_name": "Bash", "cwd": str(vault),
                                                      "tool_input": {"command": cmd}}, env)
            check("guard: '%s' %s" % (cmd, "asks" if expect else "passes"),
                  ('"permissionDecision": "ask"' in out) == expect, out)
        rc, out, _ = run([H / "vault_guard.py"], {"tool_name": "Write", "cwd": str(vault),
                         "tool_input": {"file_path": str(vault / "AGENTS.md"), "content": "x"}}, env)
        check("guard: protected AGENTS.md asks", '"permissionDecision": "ask"' in out, out)
        rc, out, _ = run([H / "vault_guard.py"], {"tool_name": "Write", "cwd": str(vault),
                         "tool_input": {"file_path": str(note), "content": "tiny\n"}}, env)
        check("guard: shrinking a note asks", '"permissionDecision": "ask"' in out, out)
        rc, out, _ = run([H / "vault_guard.py"], {"tool_name": "Edit", "cwd": str(vault),
                         "tool_input": {"file_path": str(note), "old_string": "line", "new_string": "row"}}, env)
        check("guard: a normal Edit passes", out.strip() == "", out)
        rc, out, _ = run([H / "vault_guard.py"], {"tool_name": "Bash", "cwd": str(vault),
                         "tool_input": {"command": "git push"}}, dict(env, SBK_MODE_VAULT_GUARD="log"))
        check("guard: log mode stays silent", out.strip() == "", out)

        # ---- usage warning ----
        fake = json.dumps({"seven_day": {"utilization": 91, "resets_at": "2030-01-01T00:00:00Z"}})
        ev = {"session_id": "u1", "hook_event_name": "UserPromptSubmit"}
        rc, out, _ = run([H / "usage_warn.py"], ev, dict(env, SBK_USAGE_FAKE=fake))
        check("usage: off by default (Basic), even above the threshold", rc == 0 and out.strip() == "", out)
        envu = dict(env, SBK_USAGE_FAKE=fake, SBK_MODE_USAGE_WARN="warn")
        rc, out, _ = run([H / "usage_warn.py"], ev, envu)
        check("usage: warn mode (Advanced) warns above the threshold", "91%" in out, out)
        rc, out, _ = run([H / "usage_warn.py"], ev, envu)
        check("usage: warns only once per window", out.strip() == "", out)
        rc, out, _ = run([H / "usage_warn.py"], dict(ev, session_id="u2"),
                         dict(envu, SBK_USAGE_FAKE=fake.replace("91", "10")))
        check("usage: quiet below the threshold", out.strip() == "", out)

        # ---- ledger / send / alarm / status / inbox ----
        L = KIT / "entry" / "ledger.py"
        rc, out, _ = run([L, "add", "tidy the notes"], env=env)
        check("ledger: add", rc == 0 and out.strip() == "L0001", out)
        rc, out, err = run([L, "done", "L0001", "--evidence", "ok"], env=env)
        check("ledger: thin evidence refused", rc != 0, out + err)
        rc, out, err = run([L, "done", "L0001"], env=env)
        check("ledger: no evidence refused", rc != 0, out + err)
        (home / "managers" / "study").mkdir(parents=True)
        (home / "managers" / "study" / "task.md").write_text("- [ ] read chapter 3\n- [x] old\n", encoding="utf-8")
        rc, out, err = run([KIT / "entry" / "send.py", "study", "summarise chapter 3"], env=env)
        check("send: lands in the inbox", rc == 0 and "L0002" in out and "summarise chapter 3" in (home / "inbox" / "study.md").read_text(encoding="utf-8"), out + err)
        rc, out, err = run([KIT / "entry" / "send.py", "study", "summarise chapter 3", "--ledger", "L0002"], env=env)
        check("send: same text is not added twice", "already in the inbox" in out, out + err)
        rc, out, _ = run([H / "inbox_notice.py"], {"cwd": str(home / "managers" / "study"), "hook_event_name": "SessionStart"}, env)
        check("inbox: off by default (Basic)", rc == 0 and out.strip() == "", out)
        envi = dict(env, SBK_MODE_INBOX_NOTICE="warn")
        rc, out, _ = run([H / "inbox_notice.py"], {"cwd": str(home / "managers" / "study"), "hook_event_name": "SessionStart"}, envi)
        check("inbox: warn mode (Advanced): manager sees its inbox and open tasks", "summarise chapter 3" in out and "1 open" in out, out)
        rc, out, _ = run([H / "inbox_notice.py"], {"cwd": str(tmp), "hook_event_name": "SessionStart"}, envi)
        check("inbox: other folders get nothing", out.strip() == "", out)
        rc, out, err = run([L, "done", "L0001", "--evidence", "opened notes folder, 3 files renamed"], env=env)
        check("ledger: done with evidence", rc == 0, out + err)
        rc, out, _ = run([L, "list"], env=env)
        check("ledger: list shows only open", "L0002" in out and "L0001" not in out, out)
        (home / "alarms.md").write_text(
            "| id | when | to | text |\n|---|---|---|---|\n"
            "| A01 | daily 21:00 | entry | review the ledger |\n"
            "| A02 | weekly mon 09:00 | study | weekly reading |\n"
            "| A03 | once 2020-01-01 10:00 | entry | one-time thing |\n", encoding="utf-8")
        A = KIT / "entry" / "alarm.py"
        rc, out, err = run([A, "--tick", "--now", "2026-11-23T09:05"], env=env)  # a Monday
        check("alarm: weekly row fires on its day", "A02: inbox of study" in out, out + err)
        check("alarm: one-time past row fires late", "A03: ledger" in out, out)
        check("alarm: daily row not yet due", "A01" not in out, out)
        rc, out, err = run([A, "--tick", "--now", "2026-11-23T09:10"], env=env)
        check("alarm: nothing fires twice", out.strip() == "", out + err)
        rc, out, err = run([A, "--tick", "--now", "2026-11-23T21:02"], env=env)
        check("alarm: daily row fires", "A01: ledger" in out, out + err)
        rc, out, err = run([A, "--tick", "--now", "2026-11-24T22:00"], env=env)
        check("alarm: same unfinished alarm is not added twice", "skipped (same alarm still open)" in out, out + err)
        rc, out, err = run([A, "--prune"], env=env)
        check("alarm: prune removes fired one-time rows", "removed 1" in out, out + err)
        (home / "task.md").write_text("# big job\n- [ ] step one\n- [ ] step two\n- [x] step zero\n", encoding="utf-8")
        rc, out, err = run([KIT / "entry" / "status.py", "--all"], env=env)
        check("status: lists ledger, tasks, inbox", "== Ledger ==" in out and "study: 1 open" in out and "study: 1" in out, out + err)
        check("status: shows the Basic task.md of one large job", "main: 2 open" in out and "step two" in out, out + err)

        # ---- the Basic config that setup writes (templates/config.json) ----
        cfg = json.loads((KIT / "templates" / "config.json").read_text(encoding="utf-8"))
        check("config template: Basic level and modes", cfg.get("level") == "basic" and cfg["modes"] == {
            "vault_guard": "ask", "read_whole": "deny", "requests_reinject": "warn",
            "stop_evidence": "log", "usage_warn": "off", "inbox_notice": "off", "level_notice": "warn"}, cfg)
        home2 = tmp / "home2"
        (home2 / "managers" / "study").mkdir(parents=True)
        (home2 / "inbox").mkdir()
        (home2 / "inbox" / "study.md").write_text("- [ ] L0001 | x | something sent\n", encoding="utf-8")
        (home2 / "config.json").write_text(json.dumps(dict(cfg, vault=str(vault))), encoding="utf-8")
        envc = {"SBK_HOME": str(home2), "SBK_VAULT": "", "ANTHROPIC_API_KEY": ""}
        jl(t, [user("fix a.txt"), tool("Write", {"file_path": "a.txt", "content": "x"}), result(), say("Done.")])
        rc, out, _ = run([H / "stop_evidence.py"], {"transcript_path": str(t)}, envc)
        check("config Basic: stop_evidence only logs", rc == 0 and out.strip() == "", out)
        rc, out, _ = run([H / "usage_warn.py"], {"session_id": "c1"}, dict(envc, SBK_USAGE_FAKE=fake))
        check("config Basic: usage_warn silent", rc == 0 and out.strip() == "", out)
        rc, out, _ = run([H / "inbox_notice.py"], {"cwd": str(home2 / "managers" / "study"),
                                                   "hook_event_name": "SessionStart"}, envc)
        check("config Basic: inbox_notice silent", rc == 0 and out.strip() == "", out)
        rc, out, _ = run([H / "vault_guard.py"], {"tool_name": "Bash", "cwd": str(vault),
                                                  "tool_input": {"command": "git push"}}, envc)
        check("config Basic: vault_guard asks", '"permissionDecision": "ask"' in out, out)
        adv = dict(cfg, vault=str(vault), level="full",
                   modes=dict(cfg["modes"], stop_evidence="block", inbox_notice="warn", usage_warn="warn"))
        (home2 / "config.json").write_text(json.dumps(adv), encoding="utf-8")
        rc, out, _ = run([H / "stop_evidence.py"], {"transcript_path": str(t)}, envc)
        check("config Full: stop_evidence block read from config.json", '"decision": "block"' in out, out)
        rc, out, _ = run([H / "inbox_notice.py"], {"cwd": str(home2 / "managers" / "study"),
                                                   "hook_event_name": "SessionStart"}, envc)
        check("config Full: inbox_notice read from config.json", "something sent" in out, out)
        rc, out, _ = run([H / "usage_warn.py"], {"session_id": "c2"}, dict(envc, SBK_USAGE_FAKE=fake))
        check("config Full: usage_warn read from config.json", "91%" in out, out)

        # ---- weekly level check (scripts/level_check.py, hooks/level_notice.py) ----
        level_tests(tmp, cfg)

        # ---- vault tools ----
        rc, out, _ = run([KIT / "scripts" / "gen_jdex.py", "--root", vault], env=env)
        check("jdex: writes the index", rc == 0 and "rewrote" in out, out)
        rc, out, _ = run([KIT / "scripts" / "gen_jdex.py", "--root", vault], env=env)
        check("jdex: second run changes nothing", "up to date" in out, out)
        rc, out, _ = run([KIT / "scripts" / "gen_jdex.py", "--root", vault, "--check"], env=env)
        check("jdex: --check is clean", rc == 0, out)
        rc, out, _ = run([KIT / "scripts" / "vault_lint.py", "--root", vault], env=env)
        check("lint: clean vault passes", rc == 0 and "RESULT: PASS" in out, out)
        (vault / "20-29 學習" / "21 課程" / "21-02 壞筆記.md").write_text(
            "---\ntype: weird\nstatus: active\n---\nsee [[不存在的筆記]] and ![[nope.png]]\n", encoding="utf-8")
        rc, out, _ = run([KIT / "scripts" / "vault_lint.py", "--root", vault], env=env)
        check("lint: broken link and embed are errors", rc == 1 and "broken-wikilink" in out and "missing-embed" in out, out)
        check("lint: bad type is a warning", "type-invalid" in out and "summary-missing" in out, out)
        (vault / "20-29 學習" / "21 課程" / "21-02 壞筆記.md").unlink()

        # ---- pre-commit overwrite guard ----
        if shutil.which("git"):
            repo = tmp / "repo"
            repo.mkdir()
            g = lambda *a: subprocess.run(["git", "-C", str(repo)] + list(a), capture_output=True, text=True,
                                          encoding="utf-8", errors="replace")
            g("init", "-q")
            g("config", "user.name", "t")
            g("config", "user.email", "second-brain-kit@users.noreply.github.com")
            g("config", "commit.gpgsign", "false")
            (repo / "notes.md").write_text("".join("line %d\n" % i for i in range(20)), encoding="utf-8")
            (repo / "AGENTS.md").write_text("rules\n", encoding="utf-8")
            g("add", "notes.md", "AGENTS.md")
            g("commit", "-q", "-m", "init")
            (repo / "notes.md").write_text("short\n", encoding="utf-8")
            g("add", "notes.md")
            r = subprocess.run([PY, str(KIT / "scripts" / "check_overwrite.py")], cwd=str(repo), capture_output=True, text=True)
            check("overwrite: whole-file rewrite refused", r.returncode == 1 and "rewritten" in r.stderr, r.stderr)
            r = subprocess.run([PY, str(KIT / "scripts" / "check_overwrite.py")], cwd=str(repo), capture_output=True, text=True,
                               env=dict(os.environ, SBK_ALLOW_OVERWRITE="1"))
            check("overwrite: escape hatch works", r.returncode == 0, r.stderr)
            g("reset", "-q", "--hard")
            g("rm", "-q", "AGENTS.md")
            r = subprocess.run([PY, str(KIT / "scripts" / "check_overwrite.py")], cwd=str(repo), capture_output=True, text=True)
            check("overwrite: deleting AGENTS.md refused", r.returncode == 1 and "deleted" in r.stderr, r.stderr)
        else:
            print("SKIP overwrite tests: git not found")

        # ---- Basic vault built from the templates as docs/SETUP.md step 3 says ----
        if shutil.which("git"):
            v2 = tmp / "vault2"
            today = __import__("time").strftime("%Y-%m-%d")
            rules = v2 / "00-09 系統與索引" / "01 規則"
            inbox = v2 / "00-09 系統與索引" / "02 收件匣"
            for d in (rules, inbox, v2 / "00-09 系統與索引" / "00 索引", v2 / "scripts", v2 / "20-29 學習與讀書",
                      v2 / "90-99 封存"):
                d.mkdir(parents=True, exist_ok=True)
            T = KIT / "templates"

            def put(src, dst):
                dst.write_text(src.read_text(encoding="utf-8").replace("{{date}}", today), encoding="utf-8")
            put(T / "AGENTS.md", v2 / "AGENTS.md")
            (v2 / "CLAUDE.md").write_text("@AGENTS.md\n", encoding="utf-8")
            put(T / "筆記格式.md", rules / "01-01 筆記格式.md")
            put(T / "todo-for-me.md", inbox / "02-02 我要做的事.md")
            (inbox / "02-01 收件匣.md").write_text(
                "---\ntype: log\nstatus: active\nsummary: 還沒歸位的東西先放這裡\ncreated: %s\nmodified: %s\n"
                "origin: agent-drafted\n---\n\n還沒歸位的東西先放這裡。\n" % (today, today), encoding="utf-8")
            put(T / "sbk-protect.txt", v2 / ".sbk-protect")
            (v2 / ".sbk-vault").write_text("", encoding="utf-8")
            for f in ("vault_lint.py", "gen_jdex.py", "check_overwrite.py", "pre-commit"):
                shutil.copy(str(KIT / "scripts" / f), str(v2 / "scripts" / f))
            rc, out, _ = run([v2 / "scripts" / "gen_jdex.py", "--root", v2], env=env)
            check("template vault: index generated", rc == 0, out)
            rc, out, _ = run([v2 / "scripts" / "vault_lint.py", "--root", v2], env=env)
            check("template vault: lint passes with no warnings", rc == 0 and "0 errors, 0 warnings" in out, out)
            g2 = lambda *a, **k: subprocess.run(["git", "-C", str(v2)] + list(a), capture_output=True, text=True,
                                                encoding="utf-8", errors="replace", **k)
            g2("init", "-q")
            for k, v in (("user.name", "t"), ("user.email", "second-brain-kit@users.noreply.github.com"),
                         ("commit.gpgsign", "false"), ("core.hooksPath", "scripts")):
                g2("config", k, v)
            if os.name != "nt":
                os.chmod(str(v2 / "scripts" / "pre-commit"), 0o755)
            g2("add", "-A")
            r = g2("commit", "-q", "-m", "Initial vault")
            check("template vault: first commit passes the pre-commit hook", r.returncode == 0, r.stdout + r.stderr)
            tpl = rules / "01-01 筆記格式.md"
            tpl.write_text("---\ntype: reference\n---\nx\n", encoding="utf-8")
            g2("add", str(tpl))
            r = g2("commit", "-q", "-m", "wipe the rules")
            check("template vault: wiping a note is refused by pre-commit", r.returncode != 0, r.stdout + r.stderr)
            g2("reset", "-q", "--hard")
            bad = v2 / "20-29 學習與讀書" / "21 課程" / "21-01 壞.md"
            bad.parent.mkdir(parents=True, exist_ok=True)  # categories are created when first needed
            bad.write_text("---\ntype: skill\nstatus: active\nsummary: s\ncreated: %s\nmodified: %s\norigin: user\n---\n[[沒有這張]]\n" % (today, today), encoding="utf-8")
            g2("add", str(bad))
            r = g2("commit", "-q", "-m", "broken link")
            check("template vault: a broken link is refused by pre-commit", r.returncode != 0 and "broken-wikilink" in (r.stdout + r.stderr), r.stdout + r.stderr)

        # ---- launcher wrapper ----
        sh = shutil.which("sh")
        if sh:
            r = subprocess.run([sh, str(H / "run.sh"), "usage_warn.py"], input="{}", capture_output=True, text=True,
                               env=dict(os.environ, SBK_HOME=str(home), ANTHROPIC_API_KEY="x"))
            check("run.sh: starts a hook through whichever python exists", r.returncode == 0, r.stderr)
    finally:
        if not keep:
            def _rw(func, p, _exc):  # git objects are read-only on Windows
                os.chmod(p, 0o700)
                func(p)
            shutil.rmtree(tmp, onerror=_rw)
    bad = results.count(False)
    print("\n%d passed, %d failed" % (len(results) - bad, bad))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
