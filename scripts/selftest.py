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
            (h / "config.json").write_text(json.dumps(dict(dict(cfg, vault=str(vault), read_history=True), **(extra_cfg or {}))), encoding="utf-8")  # read_history: a user who said yes
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

    # multi_session: pain = the user said twice in 7 days that things got mixed up; volume only supports
    many = [item(i, "thing %d" % i) for i in range(1, 13)]
    h, c = setup(many)
    check_now(h, c, ago(8))
    rc, r = check_now(h, c)
    check("level: 12 open items on two checks 8 days apart, no complaint -> no trigger (volume only supports)",
          r.get("triggers") == [] and r["numbers"]["prev_open_items"] == 12, r)
    three = [item(1, "[study] read ch 3"), item(2, "[job] shift swap"), item(3, "poster", "dispatched:club")]
    h, c = setup(three)
    check_now(h, c, ago(9))
    rc, r = check_now(h, c)
    check("level: open items in 3 topics, no complaint -> no trigger, topics counted",
          r.get("triggers") == [] and r["numbers"]["open_topics"] == 3, r)
    h, c = setup()
    transcript(c, [human("hi", 3), compact(3), compact(1)])
    rc, r = check_now(h, c)
    check("level: compacted 2 times in 7 days, no complaint -> no trigger, counted",
          r.get("triggers") == [] and r["numbers"]["compactions_7d"] == 2, r)
    h, c = setup(three)
    transcript(c, [human("你把兩個作業搞混了", 3), human("not that project, the poster one", 1)])
    rc, r = check_now(h, c)
    check("level: mixed up twice in 7 days -> multi_session",
          "multi_session" in (r.get("triggers") or []) and r["numbers"]["mixups_7d"] == 2, r)
    h, c = setup()
    transcript(c, [human("you mixed up the two reports", 2)])
    rc, r = check_now(h, c)
    check("level: mixed up once -> no trigger", r.get("triggers") == [], r)
    h, c = setup()
    transcript(c, [human("報告搞混了", 10), human("專案又弄錯了", 9)])
    rc, r = check_now(h, c)
    check("level: two mix-ups but 9+ days old -> no trigger", r.get("triggers") == [], r)
    h, c = setup()
    transcript(c, [human("我搞混了這兩個公式", 2), human("I mixed up sine and cosine", 1)])
    rc, r = check_now(h, c)
    check("level: confused about study content (not tasks) -> no trigger", r.get("triggers") == [], r)
    h, c = setup()
    other = tmp / "elsewhere"
    transcript(c, [human("作業搞混了", 2), human("wrong project again", 1)],
               folder=re.sub(r"[^A-Za-z0-9]", "-", str(other)))
    rc, r = check_now(h, c)
    check("level: mix-ups in a session outside the notes folder -> no trigger", r.get("triggers") == [], r)
    h, c = setup(extra_cfg={"read_history": False})
    transcript(c, [human("你把兩個作業搞混了", 3), human("wrong project again", 1)])
    rc, r = check_now(h, c)
    check("level: read_history false -> conversations not read, no trigger",
          r.get("triggers") == [] and r["numbers"]["mixups_7d"] == 0 and r["numbers"]["read_history"] is False, r)

    # alarms: overdue only after 3 days; reminder requests twice in 7 days
    h, c = setup([item(1, "[study] report due %s" % ago(4, "%Y-%m-%d"))])
    rc, r = check_now(h, c)
    check("level: open item 4 days past its due date -> alarms", "alarms" in (r.get("triggers") or []), r)
    h, c = setup([item(1, "[study] report due %s" % ago(2, "%Y-%m-%d"))])
    rc, r = check_now(h, c)
    check("level: only 2 days past due -> no trigger (grace 3 days)", r.get("triggers") == [], r)
    h, c = setup([item(1, "[study] report due %s" % ago(4, "%Y-%m-%d"), "done")])
    rc, r = check_now(h, c)
    check("level: past due date but item closed -> no trigger", r.get("triggers") == [], r)
    h, c = setup([item(1, "[study] report due %s" % ago(-5, "%Y-%m-%d"))])
    rc, r = check_now(h, c)
    check("level: due date still ahead -> no trigger", r.get("triggers") == [], r)
    h, c = setup()
    transcript(c, [human("週五要交報告，到時候提醒我", 2), human("remind me to email the TA", 1)])
    rc, r = check_now(h, c)
    check("level: asked to be reminded twice in 7 days -> alarms",
          "alarms" in (r.get("triggers") or []) and r["numbers"]["remind_requests_7d"] == 2, r)
    h, c = setup()
    transcript(c, [human("週五要交報告，到時候提醒我", 2)])
    rc, r = check_now(h, c)
    check("level: asked to be reminded once -> no trigger", r.get("triggers") == [], r)
    h, c = setup()
    transcript(c, [human("提醒我交報告", 12), human("remind me on Friday", 10)])
    rc, r = check_now(h, c)
    check("level: two reminder requests but 10+ days old -> no trigger", r.get("triggers") == [], r)
    h, c = setup(files={"alarms.md": "| id | when | to | text |\n"})
    transcript(c, [human("remind me on Friday", 2), human("提醒我交報告", 1)])
    rc, r = check_now(h, c)
    check("level: reminders already on -> not offered again", r.get("triggers") == [], r)

    # block_mode: stop_evidence log for 2+ weeks, >= 20 judged flags, < 25% false alarms
    def flagged(next_msgs, days_old, extra_cfg=None):
        hh, cc = setup(extra_cfg=extra_cfg)
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
    bad = ["還是不行，沒改到", "it still fails", "wrong file", "沒有改"] * 5
    h, c = flagged(bad, 20)
    rc, r = check_now(h, c)
    check("level: 20 flags, all followed by a complaint, 20 days of log -> block_mode",
          "block_mode" in (r.get("triggers") or []) and r["numbers"]["stop_flags_judged"] == 20
          and r["numbers"]["stop_false_alarm_pct"] == 0, r)
    h, c = flagged(["thanks", "great", "next please", "還是不行"] * 5, 20)
    rc, r = check_now(h, c)
    check("level: 75% false alarms -> no trigger", r.get("triggers") == [], r)
    h, c = flagged(bad, 3)
    rc, r = check_now(h, c)
    check("level: good flags but only 3 days of log -> no trigger", r.get("triggers") == [], r)
    h, c = flagged(bad[:19], 20)
    rc, r = check_now(h, c)
    check("level: only 19 judged flags -> no trigger (small sample)", r.get("triggers") == [], r)
    h, c = flagged(bad, 20, {"read_history": False})
    rc, r = check_now(h, c)
    check("level: read_history false -> flags not judged, no trigger",
          r.get("triggers") == [] and r["numbers"]["stop_flags_judged"] == 0, r)

    # multi_tool: only when the user said they have the tool
    h, c = setup(extra_cfg={"other_tools": "I also have a ChatGPT account"})
    rc, r = check_now(h, c)
    check("level: user said they have another tool -> multi_tool", r.get("triggers") == ["multi_tool"], r)
    h, c = setup()
    transcript(c, [human("Gemini 可以幫忙讀這份 PDF 嗎", 4), human("my report compares ChatGPT and Gemini", 2)])
    rc, r = check_now(h, c)
    check("level: tool only mentioned in a conversation -> no trigger", r.get("triggers") == [], r)
    h, c = setup(extra_cfg={"other_tools": "沒有"})
    rc, r = check_now(h, c)
    check("level: other_tools says 'none' -> no trigger", r.get("triggers") == [], r)
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
    check("level --install: 3 active project folders -> supporting evidence for topic sessions",
          inst.get("active_projects_14d") == 3 and inst.get("multi_session_evidence") is True, out)
    h, c = setup()
    rc, out, _ = run([LC, "--install", "--now", N], None, env(h, c))
    inst = json.loads(out)["install"] if out.strip() else {}
    check("level --install: no history -> no evidence (answer alone, default Basic)",
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

        # ---- Full plan: maintenance, monthly rows, computer off, live routing (session.py), wake limits ----
        hw = tmp / "home-wake"
        for d in ("maintenance", "study", "work"):
            (hw / "managers" / d).mkdir(parents=True)
        (hw / "alarms.md").write_text(
            "| id | when | to | text |\n|---|---|---|---|\n"
            "| M01 | weekly sun 20:00 | maintenance | weekly review: learning loop |\n"
            "| T01 | monthly 31 10:00 | maintenance | re-check the outside resources table |\n"
            "| H01 | daily 21:30 | handover | long conversations: hand over |\n", encoding="utf-8")
        tcfg = json.loads((KIT / "templates" / "config.json").read_text(encoding="utf-8"))
        (hw / "config.json").write_text(json.dumps(tcfg), encoding="utf-8")
        agents = tmp / "agents.json"
        agents.write_text("[]", encoding="utf-8")
        cdir = tmp / "cfgdir"
        (cdir / "projects" / "p").mkdir(parents=True)
        envw = {"SBK_HOME": str(hw), "SBK_VAULT": "", "ANTHROPIC_API_KEY": "", "SBK_AGENTS_JSON": str(agents),
                "CLAUDE_CONFIG_DIR": str(cdir)}
        rc, out, err = run([A, "--tick", "--now", "2026-11-29T20:01"], env=envw)  # a Sunday
        check("alarm: Sunday review row lands in the maintenance inbox (routing inbox: nothing started)",
              "M01: inbox of maintenance: inbox only" in out
              and "weekly review" in (hw / "inbox" / "maintenance.md").read_text(encoding="utf-8"), out + err)
        check("alarm: rows seen for the first time with a past time wait for their next time",
              "T01" not in out and "H01" not in out, out + err)
        rc, out, err = run([A, "--tick", "--now", "2026-11-30T10:05"], env=envw)
        check("alarm: monthly 31 fires on the last day of a 30-day month", "T01: inbox of maintenance" in out, out + err)
        check("alarm: handover row runs handover.py check", "H01: no background sessions" in out, out + err)
        rc, out, err = run([A, "--tick", "--now", "2026-12-15T10:05"], env=envw)
        check("alarm: monthly row does not fire mid-month", "T01" not in out, out + err)
        check("alarm: a missed weekly row with its line still unticked is not added again",
              "M01: skipped (same alarm still unticked" in out, out + err)
        mi = hw / "inbox" / "maintenance.md"
        mi.write_text(mi.read_text(encoding="utf-8").replace("- [ ]", "- [x]"), encoding="utf-8")
        # computer off from Tuesday 12-15 to Monday 12-21 08:00: the Sunday row fires once, late
        rc, out, err = run([A, "--tick", "--now", "2026-12-21T08:00"], env=envw)
        mtext = mi.read_text(encoding="utf-8")
        check("alarm: computer off over Sunday -> the weekly row fires once at the next tick, marked late",
              out.count("M01:") == 1 and "weekly review: learning loop (late)" in mtext
              and mtext.count("- [ ]") == 1, out + err + mtext)
        rc, out, err = run([A, "--tick", "--now", "2026-12-21T08:05"], env=envw)
        check("alarm: ... and not again on the next tick", "M01" not in out, out + err)
        # live routing, dry run: the tick starts sessions with waiting work, within the plan's limits
        S = KIT / "entry" / "session.py"
        envl = dict(envw, SBK_SESSION_DRYRUN="1")
        (hw / "config.json").write_text(json.dumps(dict(tcfg, routing="live", vault=str(vault),
                                                         wake_limits={"per_day": 2, "min_gap_min": 120})), encoding="utf-8")
        (hw / "inbox" / "study.md").write_text("- [ ] L0009 | x | read chapter 4\n", encoding="utf-8")
        rc, out, err = run([A, "--tick", "--now", "2026-12-21T09:00"], env=envl)
        check("routing: tick starts a session with waiting work in the background (claude --bg, accepts messages)",
              "claude --bg -n study" in out and "crossSessionInbound" in out and "--add-dir" in out
              and "opened study" in out and "opened maintenance" in out, out + err)
        check("routing: background sessions never wait at a permission prompt (dontAsk; python allowed in Bash and PowerShell)",
              "--permission-mode dontAsk" in out and "acceptEdits" not in out
              and "PowerShell(python:*)" in S.read_text(encoding="utf-8"), out + err)
        rc, out, err = run([A, "--tick", "--now", "2026-12-21T09:30"], env=envl)
        check("wake limits: the daily cap stops further starts; the work waits in the inbox",
              "study waits: daily limit 2 reached" in out and "claude --bg" not in out, out + err)
        rc, out, err = run([A, "--tick", "--now", "2026-12-22T09:05"], env=envl)
        check("wake limits: a new day starts again", "opened study" in out, out + err)
        (hw / "config.json").write_text(json.dumps(dict(tcfg, routing="live", vault=str(vault),
                                                         wake_limits={"per_day": 20, "min_gap_min": 120})), encoding="utf-8")
        rc, out, err = run([A, "--tick", "--now", "2026-12-22T10:00"], env=envl)
        check("wake limits: at most one start per session per minimum gap",
              "study waits: woken less than 120 minutes ago" in out and "claude --bg" not in out, out + err)
        (hw / "inbox" / "study.md").write_text("- [x] L0009 | x | read chapter 4\n", encoding="utf-8")
        mi.write_text(mi.read_text(encoding="utf-8").replace("- [ ]", "- [x]"), encoding="utf-8")
        rc, out, err = run([A, "--tick", "--now", "2026-12-22T14:00"], env=envl)
        check("routing: nothing waiting -> nothing started (the tick uses no quota)", "claude" not in out, out + err)
        rc, out, err = run([A, "--list"], env=envl)
        check("alarm --list shows routing, session cap and wake limits",
              "routing: live" in out and "sessions at once: 2" in out and "20/day, 120 min apart" in out, out + err)

        def ag(*rows):
            agents.write_text(json.dumps([{"pid": 100 + i, "id": "id%d" % i, "name": n, "status": st, "kind": "background",
                                           "cwd": str(hw / "managers" / n), "startedAt": i, "sessionId": "sess-" + n}
                                          for i, (n, st) in enumerate(rows)]), encoding="utf-8")
        ag(("study", "idle"))
        rc, out, err = run([S, "deliver", "study", "summarise chapter 5"], env=envl)
        check("routing: work for a running session is pushed into it (inbox line first)",
              "study: pushed" in out and "--model haiku" in out
              and "summarise chapter 5" in (hw / "inbox" / "study.md").read_text(encoding="utf-8"), out + err)
        ag(("study", "busy"), ("maintenance", "busy"))
        rc, out, err = run([S, "open", "work"], env=envl)
        check("session cap: Pro allows 2 at once; with both busy a third waits in its inbox (exit 3)",
              rc == 3 and "CAP: 2 of 2" in out, out + err)
        ag(("study", "busy"), ("maintenance", "idle"))
        rc, out, err = run([S, "open", "work"], env=envl)
        check("session cap: an idle session with nothing waiting is stopped to make room",
              rc == 0 and "claude stop id1" in out and "claude --bg -n work" in out, out + err)
        ag(("study", "idle"))
        agents_other = json.loads(agents.read_text(encoding="utf-8"))
        agents_other[0]["cwd"] = str(tmp)
        agents.write_text(json.dumps(agents_other), encoding="utf-8")
        rc, out, err = run([S, "list"], env=envl)
        check("session list: a session with the same name outside the kit folder is not ours",
              "no kit sessions running" in out, out + err)
        (hw / "config.json").write_text(json.dumps(tcfg), encoding="utf-8")
        rc, out, err = run([S, "deliver", "study", "outline essay"], env=envw)
        check("routing inbox (fallback): the line waits in the inbox and says which session to open",
              "inbox only (open study" in out and "outline essay" in (hw / "inbox" / "study.md").read_text(encoding="utf-8"), out + err)
        # hand-over of long background conversations (handover.py), dry run
        HO = KIT / "entry" / "handover.py"

        def usage(n):
            return {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "ok"}],
                                                     "usage": {"input_tokens": 10, "cache_read_input_tokens": n - 20,
                                                               "cache_creation_input_tokens": 5, "output_tokens": 5}}}
        ag(("study", "idle"), ("work", "idle"))
        jl(cdir / "projects" / "p" / "sess-study.jsonl", [user("plan my week, exams first"), usage(160000)])
        jl(cdir / "projects" / "p" / "sess-work.jsonl", [user("hi"), usage(40000)])
        rc, out, err = run([HO, "check"], env=envl)
        check("handover: above 150k and idle -> handed over; under it -> left alone",
              "RENEWED (dry run): study" in out and "work 40k (under 150k)" in out, out + err)
        ag(("study", "busy"))
        rc, out, err = run([HO, "check"], env=envl)
        check("handover: a busy session is not interrupted (BUSY, retried later)", "BUSY: study" in out, out + err)
        wf = tmp / "words.md"
        peer = lambda body: {"type": "user", "isMeta": True, "origin": {"kind": "peer", "name": "state-49", "body": body},
                             "message": {"role": "user", "content": "Another Claude session sent a message: <cross-session-message>"
                                         + body + "</cross-session-message>"}}
        jl(cdir / "projects" / "p" / "sess-study.jsonl", [user("You are the study session of second-brain-kit, started in the background. Follow"),
                                                          user("plan my week, exams first"),
                                                          peer("New work in your inbox (L0001): read chapter 5"),
                                                          peer("Hand-over before this conversation is replaced by a fresh one (handover.py). x"),
                                                          usage(160000)])
        rc, out, err = run([HO, "words", cdir / "projects" / "p" / "sess-study.jsonl", wf], env=envl)
        wt = wf.read_text(encoding="utf-8")
        check("handover: the user's words are copied out verbatim; messages from the entry are kept apart (real peer format)",
              "1. plan my week, exams first" in wt and "- New work in your inbox (L0001): read chapter 5" in wt
              and "2. " not in wt and "Hand-over before" not in wt
              and "- You are the study session of second-brain-kit" in wt and "1 user messages" in out, out + err + wt)
        # hand-over notice for a conversation in a window (Basic main, entry)
        tt = tmp / "long.jsonl"
        jl(tt, [user("keep the budget under 200"), usage(170000)])
        evh = {"session_id": "w1", "hook_event_name": "UserPromptSubmit", "transcript_path": str(tt)}
        rc, out, _ = run([H / "requests_reinject.py"], evh, envw)
        check("hook requests_reinject: above the threshold tells Claude to hand over and the user to say continue",
              "hand over" in out and "continue" in out and "task.md" in out, out)
        rc, out, _ = run([H / "requests_reinject.py"], evh, envw)
        check("hook requests_reinject: the hand-over notice comes once per 50k", out.strip() == "", out)
        jl(tt, [user("hi"), usage(20000)])
        rc, out, _ = run([H / "requests_reinject.py"], dict(evh, session_id="w2"), envw)
        check("hook requests_reinject: quiet below the threshold", out.strip() == "", out)
        # learning loop numbers (learn.py)
        LE = KIT / "entry" / "learn.py"
        lv = tmp / "lvault2"
        ln = lv / "00-09 系統與索引" / "03 和 AI 協作" / "03-01 和 AI 協作.md"
        ln.parent.mkdir(parents=True)
        ln.write_text((KIT / "templates" / "和AI協作.md").read_text(encoding="utf-8"), encoding="utf-8")
        envle = dict(envw, SBK_VAULT=str(lv))
        rc, out, err = run([LE, "add", "糾正", "沒驗證就說做完", "你根本沒打開檔案看", "--now", "2026-12-14"], env=envle)
        check("learn: add writes one dated line with the user's words", rc == 0 and "- 2026-12-14 | 糾正 | 沒驗證就說做完 | 「你根本沒打開檔案看」" in ln.read_text(encoding="utf-8"), out + err)
        with open(ln, "a", encoding="utf-8") as f:
            f.write("- 2026-12-16 | 糾正 | 沒驗證就說做完 | 「又沒開」\n- 2026-12-18 | 糾正 | 回太長 | 「短一點」\n"
                    "- 2026-12-19 | 糾正 | 沒驗證就說做完 | 「第三次」\n- 2026-12-19 | 做對 | 先查筆記再答 | 「對」\n")
        rc, out, err = run([LE, "trend", "--now", "2026-12-21"], env=envle)
        check("learn: trend line compares this week with last week and names kinds that came back",
              "3 corrections (last week 1, up), 1 confirmations" in out and "沒驗證就說做完 x3" in out
              and "被糾正 3 次（上週 1" in out and "hook candidates" in out, out + err)
        # tracker: the entry's processing step and its check of the evidence
        rc, out, err = run([L, "add", "summarise chapter 6", "--done-when", "one page in the notes", "--said", "幫我整理第六章"], env=env)
        lid6 = out.strip()
        lt = (home / "ledger.md").read_text(encoding="utf-8")
        check("ledger: a line keeps the goal, done-when and the user's words verbatim",
              "summarise chapter 6; done when: one page in the notes; said: \"幫我整理第六章\"" in lt, lt[-300:])
        rc, out, err = run([L, "edit", lid6, "summarise chapters 6 and 7", "--done-when", "two pages", "--said", "還有第七章"], env=env)
        lt = (home / "ledger.md").read_text(encoding="utf-8")
        check("ledger: a correction edits the old line, keeping the earlier words and adding the new ones",
              rc == 0 and "summarise chapters 6 and 7; done when: two pages; said: \"幫我整理第六章\" / \"還有第七章\"" in lt
              and "summarise chapter 6;" not in lt, out + err + lt[-300:])
        run([L, "done", lid6, "--evidence", "notes/21-06 chapter 6-7.md written, 2 pages"], env=env)
        rc, out, _ = run([H / "inbox_notice.py"], {"cwd": str(home / "entry"), "hook_event_name": "SessionStart"},
                         dict(env, SBK_MODE_INBOX_NOTICE="warn"))
        check("inbox: the entry sees items a topic closed, waiting for its own check",
              "waiting for your check (" in out and lid6 in out, out)
        rc, out, err = run([L, "verify", lid6, "--evidence", "opened 21-06, both chapters there"], env=env)
        check("ledger: verify closes it after the entry opened the evidence",
              rc == 0 and ("- %s | verified |" % lid6) in (home / "ledger.md").read_text(encoding="utf-8"), out + err)
        (home / "task.md").write_text("# big job\n- [ ] step one\n- [ ] step two\n- [x] step zero\n", encoding="utf-8")
        rc, out, err = run([KIT / "entry" / "status.py", "--all"], env=env)
        check("status: lists ledger, tasks, inbox", "== Ledger ==" in out and "study: 1 open" in out and "study: 1" in out, out + err)
        check("status: shows the Basic task.md of one large job", "main: 2 open" in out and "step two" in out, out + err)

        # ---- the Basic config that setup writes (templates/config.json) ----
        cfg = json.loads((KIT / "templates" / "config.json").read_text(encoding="utf-8"))
        check("config template: plan empty until asked; Pro starting values for sessions, wakes and hand-over",
              cfg.get("plan") == "" and "wake" not in cfg and cfg.get("routing") == "inbox" and cfg.get("max_sessions") == 2
              and cfg.get("wake_limits") == {"per_day": 4, "min_gap_min": 120} and cfg.get("handover_tokens") == 150000
              and "outside_resources" in cfg and "other_tools" not in cfg, cfg)
        check("config template: Basic level, history not read until the user says yes, modes", cfg.get("level") == "basic" and cfg.get("read_history") is False and cfg["modes"] == {
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
            learn_dir = v2 / "00-09 系統與索引" / "03 和 AI 協作"
            learn_dir.mkdir(parents=True, exist_ok=True)
            put(T / "和AI協作.md", learn_dir / "03-01 和 AI 協作.md")
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

        # ---- how the user opens the notes folder: App users get steps, no shortcut file ----
        for lang, setup, readme in (("en", KIT / "docs" / "SETUP.md", KIT / "README.md"),
                                    ("zh", KIT / "docs" / "zh-TW" / "SETUP.md", KIT / "README.zh-TW.md")):
            st = setup.read_text(encoding="utf-8")
            a = st.find("### `SURFACE` = app")
            b = st.find("### `SURFACE` = terminal")
            app = st[a:b] if 0 <= a < b else ""
            term = st[b:st.find("## Step 5b" if lang == "en" else "## 步驟 5b")] if b >= 0 else ""
            check("setup %s: surface is detected from CLAUDE_CODE_ENTRYPOINT, user answer wins" % lang,
                  "CLAUDE_CODE_ENTRYPOINT" in st and "claude-desktop" in st and "`cli`" in st)
            check("setup %s: App branch gives the Code tab / Open folder steps and makes no shortcut file" % lang,
                  "**Code**" in app and "**Open folder…**" in app and "**Local**" in app
                  and not any(w in app for w in ("chmod", "@echo off", "#!/bin/sh")))
            check("setup %s: terminal branch keeps the shortcut and the plain cd + claude way" % lang,
                  "@echo off" in term and "#!/bin/sh" in term and "claude --continue" in term and "cd \"<VAULT>\"" in term)
            check("setup %s: Step 6 and 7 do not assume a shortcut or claude -p for App users" % lang,
                  "**+ New**" in st and st.count("**Open folder…**") >= 4)
            rd = readme.read_text(encoding="utf-8")
            mm = rd[rd.find("```mermaid"):rd.find("```", rd.find("```mermaid") + 10)]
            check("readme %s: both ways in (App steps + terminal), diagram names both" % lang,
                  "**Open folder…**" in rd and "**Code**" in rd and "`claude`" in rd and ("Open folder" if lang == "en" else "選筆記資料夾") in mm and "claude" in mm
                  and "desktop launcher" not in mm)
        svg = (KIT / "docs" / "diagrams" / "00-basic.svg").read_text(encoding="utf-8")
        check("diagram 00-basic: names the App way and the terminal way, no desktop launcher",
              "Open folder" in svg and "or terminal: claude" in svg and "desktop launcher" not in svg)

        # ---- docs: plan labels, tracker wording, fixed sessions, wake choice, hook list ----
        zh_files = [KIT / "README.zh-TW.md"] + sorted((KIT / "docs" / "zh-TW").glob("*.md")) + sorted((KIT / "templates").glob("*.md")) \
            + sorted((KIT / "skills").rglob("*.md")) + sorted((KIT / "docs" / "diagrams").glob("*.svg"))
        old = [str(p.relative_to(KIT)) for p in zh_files if any(w in p.read_text(encoding="utf-8") for w in ("帳本", "工作清單"))]
        check("docs: zh text says 追蹤表, never 帳本 or 工作清單", not old, ", ".join(old))
        en_old = [str(p.relative_to(KIT)) for p in [KIT / "README.md", KIT / ".claude-plugin" / "plugin.json", KIT / ".claude-plugin" / "marketplace.json"]
                  + sorted((KIT / "docs").glob("*.md")) if "work list" in p.read_text(encoding="utf-8").lower()]
        check("docs: English text says tracker, not work list", not en_old, ", ".join(en_old))
        untitled = []
        for p in sorted((KIT / "docs" / "diagrams").glob("*.svg")):
            t = p.read_text(encoding="utf-8")
            if not any(w in t for w in ("BASIC PLAN", "FULL PLAN", "BASIC AND FULL")) or not any(w in t for w in ("基本款", "完整款")):
                untitled.append(p.name)
        check("diagrams: every drawn picture says Basic or Full (EN and zh)", not untitled, ", ".join(untitled))
        mm_untitled = []
        for p in (KIT / "README.md", KIT / "README.zh-TW.md", KIT / "docs" / "ADVANCED.md", KIT / "docs" / "zh-TW" / "進階功能.md"):
            t = p.read_text(encoding="utf-8")
            for blk in t.split("```mermaid")[1:]:
                head = blk[:200]
                if not (head.lstrip().startswith("---") and any(w in head for w in ("Basic", "Full", "基本款", "完整款"))):
                    mm_untitled.append(p.name)
        check("docs: every Mermaid picture has a Basic/Full title", not mm_untitled, ", ".join(mm_untitled))
        hooks7 = ("vault_guard", "read_whole", "requests_reinject", "stop_evidence", "level_notice", "inbox_notice", "usage_warn")
        for p in (KIT / "README.md", KIT / "README.zh-TW.md", KIT / "docs" / "ADVANCED.md", KIT / "docs" / "zh-TW" / "進階功能.md"):
            t = p.read_text(encoding="utf-8")
            listed = [h for h in hooks7 if ("- `%s`" % h) in t]
            check("docs %s: one line per hook, all 7, with Basic on/off" % p.name, len(listed) == 7 and t.count("Basic: o") + t.count("基本款：") >= 7, listed)
        check("hooks: the 7 hooks in the docs are the hooks the plugin runs",
              all((H / (h + ".py")).exists() for h in hooks7))
        adv = (KIT / "docs" / "ADVANCED.md").read_text(encoding="utf-8")
        advz = (KIT / "docs" / "zh-TW" / "進階功能.md").read_text(encoding="utf-8")
        check("advanced: Basic and Full table in both languages",
              "## Basic and Full" in adv and "| | Basic | Full |" in adv and "## 基本款和完整款" in advz and "| | 基本款 | 完整款 |" in advz)
        check("readme: short Basic and Full table, linked to the full one",
              "| | Basic | Full |" in (KIT / "README.md").read_text(encoding="utf-8") and "ADVANCED.md#basic-and-full" in (KIT / "README.md").read_text(encoding="utf-8")
              and "| | 基本款 | 完整款 |" in (KIT / "README.zh-TW.md").read_text(encoding="utf-8") and "#基本款和完整款" in (KIT / "README.zh-TW.md").read_text(encoding="utf-8"))
        check("full: two fixed sessions (entry, maintenance), no supervisor template",
              not (KIT / "templates" / "supervisor-CLAUDE.md").exists() and (KIT / "templates" / "maintenance-CLAUDE.md").exists()
              and (KIT / "templates" / "entry-CLAUDE.md").exists()
              and "maintenance" in (KIT / "templates" / "routes.md").read_text(encoding="utf-8")
              and "maintenance" in (KIT / "templates" / "entry-CLAUDE.md").read_text(encoding="utf-8"))
        every = [KIT / "README.md", KIT / "README.zh-TW.md"] + sorted((KIT / "docs").rglob("*.md")) + sorted((KIT / "templates").glob("*")) \
            + sorted((KIT / "skills").rglob("*.md")) + sorted((KIT / "commands").glob("*.md")) + sorted((KIT / "docs" / "diagrams").glob("*.svg")) \
            + [KIT / ".claude-plugin" / "plugin.json", KIT / ".claude-plugin" / "marketplace.json"]
        stale = []
        for p in every:
            t = p.read_text(encoding="utf-8").lower()
            for w in ("supervisor", "監督", "外部模型", "auto-wake", "自動喚醒", "喚醒方式", "other ai tool", "其他 ai 工具"):
                if w in t:
                    stale.append("%s: %s" % (p.relative_to(KIT), w))
        check("docs: no separate supervisor, no wake choice, 外部資源 not 外部模型", not stale, "; ".join(stale))
        check("advanced: hooks vs weekly review in one sentence, both languages",
              "hooks catch what a program can see at the moment Claude acts" in adv and "hook 擋的是 Claude 動手那一刻程式就看得出來的錯" in advz)
        check("readme: a costs section saying the 5-minute check uses no quota, limits by plan, computer off",
              "## Costs" in (KIT / "README.md").read_text(encoding="utf-8") and "uses **none** of your limit" in (KIT / "README.md").read_text(encoding="utf-8")
              and "## 費用" in (KIT / "README.zh-TW.md").read_text(encoding="utf-8") and "**完全不用**額度" in (KIT / "README.zh-TW.md").read_text(encoding="utf-8")
              and "asleep" in (KIT / "README.md").read_text(encoding="utf-8") and "睡眠" in (KIT / "README.zh-TW.md").read_text(encoding="utf-8"))
        check("learning loop: the 和 AI 協作 note is in the templates and read before acting",
              (KIT / "templates" / "和AI協作.md").exists() and "和 AI 協作" in (KIT / "templates" / "CLAUDE.md").read_text(encoding="utf-8")
              and "和 AI 協作" in (KIT / "templates" / "AGENTS.md").read_text(encoding="utf-8")
              and "learn.py trend" in (KIT / "templates" / "maintenance-CLAUDE.md").read_text(encoding="utf-8")
              and "--replay" in (KIT / "templates" / "maintenance-CLAUDE.md").read_text(encoding="utf-8"))
        check("templates: checking the notes first is step one in CLAUDE.md and AGENTS.md",
              "動手前先查第二大腦" in (KIT / "templates" / "CLAUDE.md").read_text(encoding="utf-8")
              and "動手前先查第二大腦" in (KIT / "templates" / "AGENTS.md").read_text(encoding="utf-8"))
        se = (KIT / "docs" / "SETUP.md").read_text(encoding="utf-8")
        sz = (KIT / "docs" / "zh-TW" / "SETUP.md").read_text(encoding="utf-8")
        check("setup: six questions, the plan sets starting values, outside resources are ticked (both languages)",
              "ask six things" in se and "Which Claude plan" in se and "Tick any, or none" in se and "max_sessions" in se and "可免費申請" in se
              and "問六件事" in sz and "哪種方案" in sz and "有的都勾" in sz and "max_sessions" in sz and "可免費申請" in sz)
        check("docs: the entry sends work into running sessions; inbox fallback is described",
              "straight into the running session" in adv and "直接把事送進正在跑" in advz
              and "session.py check" in se and "session.py check" in sz and "inbox" in se)
        mt = (KIT / "docs" / "MULTI-TOOL.md").read_text(encoding="utf-8")
        check("multi-tool: rules by kind of work, table filled by the user's Claude, monthly re-check",
              "## Kinds of work" in mt and "## Filling and re-checking the table" in mt
              and "Kind of work" in (KIT / "templates" / "channels.md").read_text(encoding="utf-8"))
        ver = {json.loads((KIT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"],
               json.loads((KIT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))["plugins"][0]["version"]}
        check("plugin and marketplace versions match", len(ver) == 1, ver)
        # default SBK_HOME: ~/.sbk (outside .claude, where Claude Code asks before Claude's file tools write);
        # an install from before 0.2.5 keeps ~/.claude/sbk while ~/.sbk does not exist
        with tempfile.TemporaryDirectory() as hd:
            hd = Path(hd)
            probe = ("import sys; sys.path[:0]=[%r,%r,%r]; import _common, send, ledger, level_check; "
                     "print(_common.home(), send.home(), ledger.path().parent, level_check.sbk_home(), sep='|')"
                     % (str(KIT / "hooks"), str(KIT / "entry"), str(KIT / "scripts")))
            envh = {"HOME": str(hd), "USERPROFILE": str(hd), "SBK_HOME": "", "SBK_LEDGER": ""}

            def homes():
                e = dict(os.environ, **envh)
                e.pop("SBK_HOME"); e.pop("SBK_LEDGER")
                r = subprocess.run([PY, "-c", probe], capture_output=True, text=True, env=e)
                return set(Path(x).resolve() for x in r.stdout.strip().split("|") if x) or {r.stderr}
            fresh = homes()
            (hd / ".claude" / "sbk").mkdir(parents=True)
            legacy = homes()
            (hd / ".sbk").mkdir()
            both = homes()
            check("home: new installs use ~/.sbk; an old ~/.claude/sbk is kept until ~/.sbk exists (all four readers agree)",
                  fresh == {(hd / ".sbk").resolve()} and legacy == {(hd / ".claude" / "sbk").resolve()}
                  and both == {(hd / ".sbk").resolve()}, (fresh, legacy, both))
            rc, out, err = run([KIT / "entry" / "session.py", "check"], env={"SBK_HOME": str(hd / ".claude" / "sbk")})
            check("routing: check says inbox while SBK_HOME is inside a .claude folder, and why",
                  "routing: inbox" in out and "inside a .claude folder" in out, out + err)

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
