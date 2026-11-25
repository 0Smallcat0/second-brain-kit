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
        check("stop: done without a check is blocked", rc == 0 and '"decision": "block"' in out, out)
        rc, out, _ = run([H / "stop_evidence.py"], {"transcript_path": str(t), "stop_hook_active": True}, env)
        check("stop: second stop passes (no trap)", rc == 0 and out.strip() == "", out)
        jl(t, [user("fix a.txt"), tool("Write", {"file_path": "a.txt", "content": "x"}), result(),
               tool("Read", {"file_path": "a.txt"}), result(), say("Done, a.txt now says x.")])
        rc, out, _ = run([H / "stop_evidence.py"], {"transcript_path": str(t)}, env)
        check("stop: done after a read-back passes", rc == 0 and out.strip() == "", out)
        jl(t, [user("fix a.txt"), tool("Write", {"file_path": "a.txt", "content": "x"}), result(),
               say("Fixed, but not verified yet.")])
        rc, out, _ = run([H / "stop_evidence.py"], {"transcript_path": str(t)}, env)
        check("stop: admitting 'not verified' passes", rc == 0 and out.strip() == "", out)
        rc, out, _ = run([H / "stop_evidence.py"], {"transcript_path": str(tmp / "missing.jsonl")}, env)
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
        check("usage: warns above the threshold", "91%" in out, out)
        rc, out, _ = run([H / "usage_warn.py"], ev, dict(env, SBK_USAGE_FAKE=fake))
        check("usage: warns only once per window", out.strip() == "", out)
        rc, out, _ = run([H / "usage_warn.py"], dict(ev, session_id="u2"),
                         dict(env, SBK_USAGE_FAKE=fake.replace("91", "10")))
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
        check("inbox: manager sees its inbox and open tasks", "summarise chapter 3" in out and "1 open" in out, out)
        rc, out, _ = run([H / "inbox_notice.py"], {"cwd": str(tmp), "hook_event_name": "SessionStart"}, env)
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
        rc, out, err = run([KIT / "entry" / "status.py"], env=env)
        check("status: lists ledger, tasks, inbox", "== Ledger ==" in out and "study: 1 open" in out and "study: 1" in out, out + err)

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

        # ---- vault built from the templates exactly as docs/SETUP.md step 3 says ----
        if shutil.which("git"):
            v2 = tmp / "vault2"
            today = __import__("time").strftime("%Y-%m-%d")
            rules = v2 / "00-09 系統與索引" / "01 規則"
            inbox = v2 / "00-09 系統與索引" / "02 收件匣"
            for d in (rules, inbox, v2 / "00-09 系統與索引" / "00 索引", v2 / "scripts", v2 / "20-29 學習與讀書" / "21 課程"):
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
