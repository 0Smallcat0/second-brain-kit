#!/usr/bin/env python3
"""Smoke test for the whole kit. Feeds sample input to every hook and tool, in a throw-away
folder, and prints PASS / FAIL per case. Nothing outside the temp folder is touched.

    python scripts/selftest.py [--keep]        exit code 1 if any case fails
"""
import datetime
import json
import os
import re
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
    e.pop("CLAUDE_JOB_DIR", None)   # the tests must not depend on being run from a background session
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


# ---- learning loop: messages for learn_notice (normal ones must not fire; replayed in the selftest) ----
LEARN_NORMAL = [
    '幫我整理這週的筆記',
    '我明天要交報告，先幫我列大綱',
    '找我之前記的線性代數筆記',
    '還有什麼沒做完？',
    '接著上次的專案報告繼續',
    '記住：我這週要讀完第三章',
    '對了，下週三要考期中考，幫我記一下',
    '這樣可以嗎？',
    '這個對不對？',
    '你覺得是不是這樣比較好？',
    '幫我查一下 Python 的 list comprehension 怎麼寫',
    '把這份 PDF 讀完，整理重點',
    "這段程式碼有錯誤訊息，幫我看看：TypeError: 'NoneType' object is not subscriptable",
    '幫我寫一封信給教授問期末考範圍',
    '我想討論一下這個專案要用哪個資料庫',
    '可以幫我把這三個檔案合併嗎',
    '今天的會議記錄幫我存起來',
    '下個月要搬家，幫我列一下要做的事',
    '我需要一份履歷的範本',
    '幫我翻譯這段英文',
    '我又多了一個作業，要寫實驗報告',
    '這題的答案是不是錯的？',
    '課本上說這個公式是錯的，為什麼？',
    '不要用太難的字，寫給小學生看的',
    '請用表格整理',
    '幫我把筆記裡的錯字找出來',
    '這個 bug 為什麼會發生',
    '幫我想三個專題題目',
    '開一個新的筆記放讀書計畫',
    '把上週的會議紀錄移到封存',
    '幫我算一下這個月的開銷',
    '提醒我週五交作業',
    '我說的是第二版的檔案，在桌面上',
    '這個字怎麼念',
    '再跑一次測試',
    '執行看看',
    '你可以再解釋一次嗎',
    '我剛剛上傳了一個檔案，幫我看',
    '今天天氣好嗎',
    '幫我把這個網頁存成筆記',
    'Can you summarise this article for me?',
    'What is still open?',
    'Find my notes about chapter 3',
    'Remember this: the meeting is on Friday',
    'Can you run the tests again?',
    "What's wrong with this code? It throws an error.",
    'Please write a cover letter for this job',
    'I want to discuss the database design first',
    'Is this right?',
    'Is that correct?',
    'Draft an email to my landlord about the heater',
    'Make a table of the expenses',
    'Translate this into Spanish',
    'Read the whole PDF and list the key points',
    'Help me plan my week',
    'Show me how to use git rebase',
    'Why does this fail with a 404?',
    'Can you do it again with a different color?',
    'Open the notes folder',
    'Add a reminder for Monday',
    'I said in the meeting that we would ship on Friday, draft the follow-up',
    'The error message says permission denied',
    'Make it shorter',
    "Let's continue where we stopped yesterday",
    'Tell me the difference between TCP and UDP',
    'How do I fix a broken pipe error in Python?',
    'List my open tasks',
    'Write a short story about a cat',
    'Could you check if the link works?',
    'Explain recursion simply',
    'Rename the file to report-final',
    'What did we decide last week about the logo?',
    'Give me three options for the title',
    'Look up the deadline for the scholarship',
    'Merge these two notes',
    'Delete the test file you created',
    'Start a new note for the trip',
    '這份報告第二段幫我改得口語一點',
    '幫我把這個連結的影片摘要一下',
    '幫我做一張比較表：Notion 和 Obsidian',
    '我需要練習英文口說，給我幾個題目',
    '把待辦依照截止日排序',
    '幫我查最近的颱風消息',
    '期末考考哪些範圍',
    '我想學 SQL，從哪裡開始',
    '幫我寫一個 Python 腳本把 CSV 轉成 Excel',
    '這張圖幫我看一下有什麼問題',
    '檢查一下我的程式有沒有漏掉的地方',
    '我要買筆電，預算三萬，推薦一下',
    '寫一段自我介紹，一百字',
    '幫我把行程排進行事曆',
    '這週的讀書進度做到哪了',
    '上次說的那個網站叫什麼',
    '你可以幫我把這份文件轉成 PDF 嗎',
    '今天先到這裡，幫我記下進度',
    '今天作業太多了，幫我排順序',
    '這篇文章太長了，幫我摘要',
    '這個函式為什麼沒有回傳值',
    '說到底這門課要考什麼',
    '好了嗎？',
    '為什麼天空是藍的',
    'Why is the sky blue?',
]
LEARN_CORRECTIONS = [
    '不對，我要的是第三章不是第二章',
    '錯了，日期是週五',
    '不是這樣，筆記標題要用英文',
    '我說過筆記標題要用英文',
    '你又沒看檔案就說做完',
    '不要再把兩份報告搞混了',
    '你根本沒打開檔案看',
    '還是錯的',
    "That's not what I asked for",
    'I told you to use English titles',
    "You didn't check the file",
    "Don't add a summary at the end again",
    'No, I meant the second version',
    "That's wrong, the deadline is Friday",
    '到底為什麼表格只放三列？',
    '做完了沒？都沒有回報',
    '為什麼你每次都漏掉附件',
    '說明文字寫太多了',
    '應該要放圖比較直接，而不是全用文字',
    '這筆紀錄根本就沒有出現在清單裡',
    '這個做法我忍很久了',
    '明明就有範本了，為什麼還要重寫',
    "Why didn't you check the file first?",
    'How many times do I have to say it',
]
LEARN_CONFIRMED = [
    '很好，就是這樣',
    '這樣可以',
    '對，就是這樣',
    '這次對了',
    '完美',
    "Perfect, that's it",
    'Exactly what I wanted',
    'Good job, this works',
    'Looks good',
    "That's right",
]


def learn_loop_tests(tmp, cfg):
    """learn_notice (UserPromptSubmit), learn.py group/pref/stats, the Basic light review, /sbk-status."""
    from datetime import datetime, timedelta
    H = KIT / "hooks"
    LE = KIT / "entry" / "learn.py"
    LNH = H / "learn_notice.py"
    # 1. phrase lists: replay the three sets
    for name, msgs, want in (("normal", LEARN_NORMAL, None), ("corrections", LEARN_CORRECTIONS, "correction"),
                             ("confirmations", LEARN_CONFIRMED, "confirmed")):
        f = tmp / ("learn-%s.txt" % name)
        f.write_text("\n".join(msgs) + "\n", encoding="utf-8")
        rc, out, err = run([LNH, "--replay", f], env={"SBK_HOME": str(tmp / "nohome")})
        hit_lines = [l for l in out.splitlines() if l.startswith("  ")]
        if want is None:
            check("learn_notice: %d ordinary messages (requests, questions, 對不對/是不是這樣 as questions) fire 0 times"
                  % len(msgs), rc == 0 and "hits 0 " in out and not hit_lines, out + err)
        else:
            ok = len(hit_lines) == len(msgs) and all(l.strip().startswith(want + " ") for l in hit_lines)
            check("learn_notice: all %d %s are recognised as %s" % (len(msgs), name, want), rc == 0 and ok, out + err)
    # 2. the hook: a vault with the note, Basic config
    v = tmp / "learnvault"
    note = v / "00-09 系統與索引" / "03 和 AI 協作" / "03-01 和 AI 協作.md"
    note.parent.mkdir(parents=True)
    (v / ".sbk-vault").write_text("", encoding="utf-8")
    note.write_text((KIT / "templates" / "和AI協作.md").read_text(encoding="utf-8").replace("{{date}}", "2026-12-01"),
                    encoding="utf-8")
    h = tmp / "learnhome"
    h.mkdir()
    (h / "config.json").write_text(json.dumps(dict(cfg, vault=str(v))), encoding="utf-8")
    env = {"SBK_HOME": str(h), "SBK_VAULT": "", "ANTHROPIC_API_KEY": "", "CLAUDE_CONFIG_DIR": str(tmp / "learncc")}
    ev = {"cwd": str(v), "hook_event_name": "UserPromptSubmit"}
    rc, out, err = run([LNH], dict(ev, prompt="你又沒看檔案就說做完"), env)
    check("learn_notice: a correction adds a reminder to write one line with learn.py add correction",
          rc == 0 and "learning loop" in out and "add correction" in out and "03-01" in out, out + err)
    rc, out, err = run([LNH], dict(ev, prompt="對，就是這樣"), env)
    check("learn_notice: a confirmation reminds with learn.py add confirmed", rc == 0 and "add confirmed" in out, out + err)
    rc, out, err = run([LNH], dict(ev, prompt="幫我整理這週的筆記"), env)
    check("learn_notice: an ordinary request adds nothing", rc == 0 and out.strip() == "", out + err)
    rc, out, err = run([LNH], dict(ev, prompt="他說「你又錯了」是什麼意思？"), env)
    check("learn_notice: words inside quotes do not count", rc == 0 and out.strip() == "", out + err)
    rc, out, err = run([LNH], dict(ev, prompt="你又沒看檔案就說做完"), dict(env, SBK_MODE_LEARN_NOTICE="log"))
    lg = (h / "logs" / "learn_notice.log")
    check("learn_notice: log mode only writes logs/learn_notice.log",
          rc == 0 and out.strip() == "" and lg.exists() and "correction" in lg.read_text(encoding="utf-8"), out + err)
    rc, out, err = run([LNH], dict(ev, prompt="你又沒看檔案就說做完"), dict(env, SBK_MODE_LEARN_NOTICE="off"))
    check("learn_notice: off says nothing", rc == 0 and out.strip() == "", out + err)
    h2 = tmp / "learnhome2"
    h2.mkdir()
    (h2 / "config.json").write_text(json.dumps(dict(cfg, vault=str(tmp / "no-such-vault"))), encoding="utf-8")
    rc, out, err = run([LNH], {"cwd": str(tmp), "prompt": "你又沒看檔案就說做完"}, dict(env, SBK_HOME=str(h2)))
    check("learn_notice: silent when there is no 和 AI 協作 note", rc == 0 and out.strip() == "", out + err)
    # 3. three corrections of the same kind -> three lines -> grouped -> a preference after the yes
    envl = dict(env, SBK_VAULT=str(v))
    for d, said in (("2026-12-07", "你又沒看檔案就說做完"), ("2026-12-08", "你根本沒打開檔案看"), ("2026-12-09", "還是沒打開就說好了")):
        run([LE, "add", "correction", "沒驗證就說做完", said, "--now", d], env=envl)
    run([LE, "add", "confirmed", "先查筆記再答", "對，就是這樣", "--now", "2026-12-09"], env=envl)
    t = note.read_text(encoding="utf-8")
    check("learn: three corrections of one kind are three lines in the note's language (糾正), words verbatim",
          t.count("| 糾正 | 沒驗證就說做完 |") == 3 and "「你根本沒打開檔案看」" in t and "| 做對 | 先查筆記再答 |" in t, t[-400:])
    rc, out, err = run([LE, "group", "--since", "2026-12-07", "--now", "2026-12-10"], env=envl)
    check("learn: group puts the three lines of one kind together, biggest first",
          rc == 0 and "- 沒驗證就說做完: 3 (correction 3, confirmed 0)" in out
          and out.find("沒驗證就說做完") < out.find("先查筆記再答"), out + err)
    rc, out, err = run([LE, "pref", "沒驗證就說做完", "Open the result and look at it before saying done.", "--now", "2026-12-10"], env=envl)
    t = note.read_text(encoding="utf-8")
    pa, pb = t.find("## 已整理的偏好"), t.find("## 紀錄")
    check("learn: pref writes the preference under the preferences heading, not among the lines",
          rc == 0 and 0 <= pa < t.find("- Open the result and look at it before saying done. (沒驗證就說做完; 2026-12-10)") < pb, t)
    rc, out, err = run([LE, "group", "--since", "2026-12-07", "--now", "2026-12-10"], env=envl)
    check("learn: group shows the preferences already written", "Preferences already written (1)" in out, out + err)
    ss = {"cwd": str(v), "hook_event_name": "SessionStart", "source": "startup"}
    rc, out, err = run([LNH], ss, env)
    check("learn_notice: at session start the sorted preferences are put into the conversation (E2E: a new session did not open the note)",
          rc == 0 and "Open the result and look at it before saying done." in out and '"hookEventName": "SessionStart"' in out
          and "沒驗證就說做完 | 「" not in out, out + err)
    rc, out, err = run([LNH], ss, dict(env, SBK_MODE_LEARN_NOTICE="log"))
    check("learn_notice: session start in log mode adds nothing", rc == 0 and out.strip() == "", out + err)
    rc, out, err = run([LNH], {"cwd": str(tmp), "hook_event_name": "SessionStart"}, dict(env, SBK_HOME=str(h2)))
    check("learn_notice: session start with no note adds nothing", rc == 0 and out.strip() == "", out + err)
    rc, out, err = run([LE, "stats", "--now", "2026-12-10"], env=envl)
    try:
        st = json.loads(out)
    except Exception:
        st = {}
    check("learn: stats counts lines, corrections this week, kinds that came back, preferences",
          st.get("lines") == 4 and st.get("corrections") == 3 and st.get("confirmations") == 1
          and st.get("corrections_this_week") == 3 and st.get("preferences") == 1 and "沒驗證就說做完" in str(st.get("repeats")),
          out + err)
    # 4. the light review through level_notice: by position, used up only when marked done (v8 item 4)
    LC = KIT / "scripts" / "level_check.py"
    (h / "state" / "learn_review.json").unlink()  # the pref above marked those lines reviewed; this case is a user who has not reviewed
    note2 = note.read_text(encoding="utf-8")
    cc = tmp / "learncc"
    cc.mkdir(exist_ok=True)
    hook = {"cwd": str(v), "hook_event_name": "SessionStart"}
    rc, out, err = run([LC, "--hook", "--now", "2026-12-10T09:00:00"], hook, dict(env, CLAUDE_CONFIG_DIR=str(cc)))
    check("light review (Basic): the first session gets the review with the new lines by kind",
          rc == 0 and "light review" in out and "沒驗證就說做完 x3" in out and "group --since" in out
          and "learn.py" in out and "reviewed" in out and note.read_text(encoding="utf-8") == note2, out + err)
    rc, out, err = run([LC, "--hook", "--now", "2026-12-10T15:00:00"], hook, dict(env, CLAUDE_CONFIG_DIR=str(cc)))
    check("light review: offered once a day, not on every session start", rc == 0 and "light review" not in out, out + err)
    rc, out, err = run([LC, "--hook", "--now", "2026-12-11T09:00:00"], hook, dict(env, CLAUDE_CONFIG_DIR=str(cc)))
    check("light review: a review that was shown but never marked done is offered again the next day (v8 item 4)",
          rc == 0 and "light review" in out and "沒驗證就說做完 x3" in out, out + err)
    rc, out, err = run([LE, "reviewed", "--now", "2026-12-11"], env=envl)
    rc, out, err = run([LC, "--hook", "--now", "2026-12-12T09:00:00"], hook, dict(env, CLAUDE_CONFIG_DIR=str(cc)))
    check("light review: marked done (learn.py reviewed) it does not come again", rc == 0 and "light review" not in out, out + err)
    # lines written after the mark, on the day of the mark itself, are not lost (the old date test dropped them)
    run([LE, "add", "correction", "太長", "回答太長了，不對", "--now", "2026-12-11"], env=envl)
    run([LE, "add", "correction", "太長", "還是太長", "--now", "2026-12-12"], env=envl)
    rc, out, err = run([LC, "--hook", "--now", "2026-12-13T09:00:00"], hook, dict(env, CLAUDE_CONFIG_DIR=str(cc)))
    check("light review: within 7 days of the last review nothing new is offered", rc == 0 and "light review" not in out, out + err)
    rc, out, err = run([LC, "--hook", "--now", "2026-12-19T09:00:00"], hook, dict(env, CLAUDE_CONFIG_DIR=str(cc)))
    check("light review: a week after the last one, only the lines written since (by position, same day as the mark included)",
          rc == 0 and "light review" in out and "太長 x2" in out and "沒驗證就說做完 x" not in out
          and "2 line(s)" in out, out + err)
    rc, out, err = run([LE, "pref", "太長", "Keep answers short.", "--now", "2026-12-19"], env=envl)
    rc, out, err = run([LC, "--hook", "--now", "2026-12-20T09:00:00"], hook, dict(env, CLAUDE_CONFIG_DIR=str(cc)))
    check("light review: writing a preference (learn.py pref) marks the review done", rc == 0 and "light review" not in out, out + err)
    hf = tmp / "learnhome-full"
    (hf / "managers" / "maintenance").mkdir(parents=True)
    (hf / "config.json").write_text(json.dumps(dict(cfg, vault=str(v), level="full")), encoding="utf-8")
    rc, out, err = run([LC, "--hook", "--now", "2026-12-10T09:00:00"], hook, dict(env, SBK_HOME=str(hf), CLAUDE_CONFIG_DIR=str(cc)))
    check("light review (Full, no [review] item closed in 8 days: App only / no scheduler): the entry gets it (v8 item 8)",
          rc == 0 and "light review" in out, out + err)
    (hf / "state").mkdir(exist_ok=True)
    (hf / "state" / "level_check.json").unlink()
    (hf / "ledger.md").write_text("# Ledger\n\n- L0001 | done | 2026-12-07T20:00:00 | [review] 2026-12-07: trend lines | ev: opened the result\n", encoding="utf-8")
    rc, out, err = run([LC, "--hook", "--now", "2026-12-10T09:00:00"], hook, dict(env, SBK_HOME=str(hf), CLAUDE_CONFIG_DIR=str(cc)))
    check("light review (Full): none while a [review] tracker item was closed in the last 8 days (maintenance does it)",
          rc == 0 and "light review" not in out, out + err)
    # 5. /sbk-status shows the learning numbers
    (h / "bin").mkdir(exist_ok=True)
    rc, out, err = run([KIT / "entry" / "status.py", "--all"], env=envl)
    check("status: a learning section with lines recorded, preferences, corrections this week, same kind again",
          "== Learning" in out and "lines recorded: 6 (corrections 5, confirmations 1)" in out
          and "preferences written: 2" in out and "corrections this week:" in out and "same kind again" in out, out + err)


def v8_tests(tmp, cfg):
    """One or more cases per item of the 0.2.8 review (L0612 review-v8). Each would have failed on 0.2.7."""
    import time
    H = KIT / "hooks"
    E = KIT / "entry"
    LE = E / "learn.py"
    LC = KIT / "scripts" / "level_check.py"
    base = tmp / "v8"
    base.mkdir()
    v = base / "vault"
    (v / "20-29 學習" / "21 課程").mkdir(parents=True)
    (v / ".sbk-vault").write_text("", encoding="utf-8")
    (v / ".sbk-protect").write_text("AGENTS.md\nCLAUDE.md\n00-09 System and index/01 Rules/\nscripts/\n", encoding="utf-8")
    nt = v / "20-29 學習" / "21 課程" / "21-01 Linear algebra.md"
    nt.write_text("---\ntype: skill\nstatus: active\nsummary: s\ncreated: 2026-01-01\nmodified: 2026-01-02\norigin: user\n---\n\n"
                  + "".join("line %d\n" % i for i in range(1, 401)), encoding="utf-8")
    hm = base / "home"
    hm.mkdir()
    env = {"SBK_HOME": str(hm), "SBK_VAULT": "", "ANTHROPIC_API_KEY": "", "CLAUDE_CONFIG_DIR": str(base / "cc")}

    def put_cfg(**kw):
        (hm / "config.json").write_text(json.dumps(dict(cfg, vault=str(v), **kw)), encoding="utf-8")
    put_cfg()

    # ---- item 1: the hooks see the PowerShell tool ----
    hj = json.loads((H / "hooks.json").read_text(encoding="utf-8"))
    pre = hj["hooks"]["PreToolUse"]
    check("v8 item 1: hooks.json and the manual example match Bash|PowerShell (the shell Claude uses on Windows)",
          any(m["matcher"] == "Bash|PowerShell" for m in pre)
          and "Bash|PowerShell" in (KIT / "templates" / "settings.hooks.example.json").read_text(encoding="utf-8"),
          [m["matcher"] for m in pre])
    for cmd, expect in [("git push origin main", True), ("Remove-Item -Recurse -Force .\\20-29", True),
                        ("ri -r build", True), ("rd /s /q build", True), ("Get-ChildItem", False)]:
        rc, out, _ = run([H / "vault_guard.py"], {"tool_name": "PowerShell", "cwd": str(v), "tool_input": {"command": cmd}}, env)
        check("v8 item 1: vault_guard on the PowerShell tool: '%s' %s" % (cmd, "asks" if expect else "passes"),
              ('"permissionDecision": "ask"' in out) == expect, out)
    rc, out, _ = run([H / "read_whole.py"], {"tool_name": "PowerShell", "cwd": str(v), "tool_input": {
        "command": 'Get-Content "20-29 學習/21 課程/21-01 Linear algebra.md" -TotalCount 20'}}, env)
    check("v8 item 1: read_whole refuses Get-Content -TotalCount on a note (PowerShell tool)", '"permissionDecision": "deny"' in out, out)
    t = base / "t.jsonl"
    envb = dict(env, SBK_MODE_STOP_EVIDENCE="block")
    jl(t, [user("fix a.txt"), tool("PowerShell", {"command": "Set-Content a.txt x"}), result(),
           tool("PowerShell", {"command": "Get-Content a.txt"}), result(), say("Done, a.txt now says x.")])
    rc, out, _ = run([H / "stop_evidence.py"], {"transcript_path": str(t)}, envb)
    check("v8 item 1: stop_evidence counts a PowerShell read-back as the check (no false 'done without looking')",
          rc == 0 and out.strip() == "", out)
    jl(t, [user("fix a.txt"), tool("PowerShell", {"command": "Set-Content a.txt x"}), result(), say("Done.")])
    rc, out, _ = run([H / "stop_evidence.py"], {"transcript_path": str(t)}, envb)
    check("v8 item 1: ... and a PowerShell write with no read-back is a write", '"decision": "block"' in out, out)

    # ---- item 2: heartbeat, onFailure, status ----
    check("v8 item 2: every hook is registered with onFailure continue (a failing hook cannot block a tool call on Windows without Git Bash)",
          all(h.get("onFailure") == "continue" for evs in hj["hooks"].values() for m in evs for h in m["hooks"])
          and "onFailure" in (KIT / "templates" / "settings.hooks.example.json").read_text(encoding="utf-8"), hj["hooks"].keys())
    rc, out, err = run([E / "status.py"], env=env)
    check("v8 item 2: /sbk-status says NO STAMP when no hook ever ran", "== Hooks ==" in out and "NO STAMP" in out, out + err)
    sh = shutil.which("sh")
    if sh:
        r = subprocess.run([sh, str(H / "run.sh"), "usage_warn.py"], input="{}", capture_output=True, text=True,
                           env=dict(os.environ, SBK_HOME=str(hm), ANTHROPIC_API_KEY="x"))
        hb = hm / "state" / "hooks-heartbeat.json"
        check("v8 item 2: run.sh stamps state/hooks-heartbeat.json each time it starts a hook",
              r.returncode == 0 and hb.exists() and json.loads(hb.read_text(encoding="utf-8")).get("hook") == "usage_warn.py", r.stderr)
        rc, out, err = run([E / "status.py"], env=env)
        check("v8 item 2: status.py then says 'hooks: last ran'", "hooks: last ran" in out and "NO STAMP" not in out, out + err)
    se = (KIT / "docs" / "SETUP.md").read_text(encoding="utf-8")
    check("v8 item 2: SETUP has the quit-and-reopen step before Step 4, 'not enabled' without Git Bash, and no 'never trap'",
          "Quit the Claude app completely and reopen it" in se and "Windows without Git Bash" in se
          and "hooks never trap a session" not in se and "hooks-heartbeat.json" in se, "")

    # ---- item 3: python_cmd ----
    put_cfg(python_cmd="python3-sbk")
    ev = {"cwd": str(v), "hook_event_name": "UserPromptSubmit", "prompt": "你又沒看檔案就說做完"}
    note = v / "00-09 系統與索引" / "03 和 AI 協作" / "03-01 和 AI 協作.md"
    note.parent.mkdir(parents=True)
    note.write_text((KIT / "templates" / "和AI協作.md").read_text(encoding="utf-8").replace("{{date}}", "2026-12-01"), encoding="utf-8")
    rc, out, err = run([H / "learn_notice.py"], ev, env)
    check("v8 item 3: learn_notice prints the command with python_cmd from config.json, not a hard-coded python",
          "python3-sbk" in out and "learn.py" in out and " python " not in out.replace("python3-sbk", ""), out + err)
    check("v8 item 3: the templates use no python the setup cannot rewrite (only `python <path>` commands) and config has python_cmd",
          "python_cmd" in (KIT / "templates" / "config.json").read_text(encoding="utf-8")
          and all(re.fullmatch(r"(~|\.\./|scripts/|\.\./\.\./|SBK_HOME/|KIT/).*", m)
                  for n in ("AGENTS.md", "CLAUDE.md", "entry-CLAUDE.md", "manager-CLAUDE.md", "maintenance-CLAUDE.md")
                  for m in re.findall(r"`python ([^ `]+)", (KIT / "templates" / n).read_text(encoding="utf-8"))), "")
    check("v8 item 3: Step 6's end-to-end allowlist has python3, py and the PowerShell tool",
          "Bash(python3:*),Bash(py:*),PowerShell(python:*)" in se, "")

    # ---- item 4: the review is used up only when it was done ----
    LCe = dict(env)
    put_cfg()
    for d in ("2026-12-07", "2026-12-08", "2026-12-09"):
        run([LE, "add", "correction", "kind-one", "不對，重做", "--now", d], env=dict(env, SBK_VAULT=str(v)))
    hook = {"cwd": str(v), "hook_event_name": "SessionStart"}
    rc, o1, err = run([LC, "--hook", "--now", "2026-12-10T09:00:00"], hook, LCe)
    rc, o2, err = run([LC, "--hook", "--now", "2026-12-11T09:00:00"], hook, LCe)
    check("v8 item 4: a review that was shown and not done is offered again the next day (0.2.7 used it up when shown)",
          "light review" in o1 and "light review" in o2 and "kind-one x3" in o2, o1 + o2 + err)
    run([LE, "reviewed", "--now", "2026-12-11"], env=dict(env, SBK_VAULT=str(v)))
    run([LE, "add", "correction", "kind-two", "again, wrong", "--now", "2026-12-11"], env=dict(env, SBK_VAULT=str(v)))
    rc, o3, err = run([LC, "--hook", "--now", "2026-12-19T09:00:00"], hook, LCe)
    check("v8 item 4: lines are chosen by position after the last review, so a line written on the day of the review is not lost",
          "kind-two" in o3 and "kind-one" not in o3, o3 + err)

    # ---- item 5: the hand-over is picked up by the next conversation ----
    big = base / "big.jsonl"
    jl(big, [user("plan my week"), {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "ok"}],
                                                                        "usage": {"input_tokens": 10, "cache_read_input_tokens": 160000,
                                                                                  "cache_creation_input_tokens": 5, "output_tokens": 5}}}])
    put_cfg(handover_tokens=150000)
    rc, out, err = run([H / "requests_reinject.py"], {"cwd": str(v), "hook_event_name": "UserPromptSubmit", "session_id": "old1",
                                                      "transcript_path": str(big), "prompt": "next"}, env)
    hf = hm / "state" / "handover.json"
    check("v8 item 5: the hand-over notice names the fixed task.md (not 'this folder') and writes state/handover.json",
          "task.md" in out and "this folder" not in out and hf.exists()
          and json.loads(hf.read_text(encoding="utf-8")).get("main", {}).get("task", "").endswith("task.md"), out + err)
    (hm / "task.md").write_text("# task\n- [ ] x\n", encoding="utf-8")
    rc, out, err = run([H / "requests_reinject.py"], {"cwd": str(v), "hook_event_name": "SessionStart", "source": "startup",
                                                      "session_id": "new1"}, env)
    check("v8 item 5: a new conversation in the notes folder is told 'A hand-over is waiting' and which files to read",
          "A hand-over is waiting" in out and "task.md" in out, out + err)
    rc, out, err = run([E / "status.py"], env=env)
    rc2, out2, err2 = run([H / "requests_reinject.py"], {"cwd": str(v), "hook_event_name": "SessionStart", "source": "startup",
                                                         "session_id": "new2"}, env)
    check("v8 item 5: picked up once only", "A hand-over is waiting" not in out2, out2 + err2)
    (hm / "entry").mkdir()
    (hm / "entry" / "task.md").write_text("# entry task\n", encoding="utf-8")
    hand = json.loads(hf.read_text(encoding="utf-8"))
    hand["entry"] = {"task": str(hm / "entry" / "task.md"), "words": "", "date": "2026-12-10", "ts": time.time(), "session": "e0"}
    hf.write_text(json.dumps(hand), encoding="utf-8")
    rc, out, err = run([E / "status.py"], env=env)
    check("v8 item 5: /sbk-status lists a waiting hand-over", "== Hand-over ==" in out and "WAITING" in out, out + err)
    rc, out, err = run([H / "requests_reinject.py"], {"cwd": str(hm / "entry"), "hook_event_name": "SessionStart", "source": "clear",
                                                      "session_id": "e1"}, env)
    check("v8 item 5: the entry picks up its own hand-over after /clear",
          "A hand-over is waiting" in out and "entry" in out and "task.md" in out, out + err)
    ag = (KIT / "templates" / "AGENTS.md").read_text(encoding="utf-8")
    check("v8 item 5: AGENTS.md has the 'A hand-over is waiting' rule and the fixed place",
          "A hand-over waiting" in ag and "`~/.sbk/task.md`" in ag and "never write a `task.md` into the notes folder" in ag, "")

    # ---- item 6 and 7: the Windows tick under pythonw.exe; cron PATH and claude_path ----
    pyw = Path(PY).with_name("pythonw.exe")
    if os.name == "nt" and pyw.exists():
        hw = base / "homew"
        (hw / "inbox").mkdir(parents=True)
        (hw / "config.json").write_text(json.dumps(dict(cfg, vault=str(v))), encoding="utf-8")
        (hw / "alarms.md").write_text((KIT / "templates" / "alarms.md").read_text(encoding="utf-8"), encoding="utf-8")
        r = subprocess.run([str(pyw), str(E / "alarm.py"), "--tick", "--now", "2026-12-20T20:05"], capture_output=True, text=True,
                           env=dict(os.environ, SBK_HOME=str(hw), SBK_SESSION_DRYRUN="1"), timeout=60)
        check("v8 item 6: the tick runs to the end under pythonw.exe (sys.stdout is None there; 0.2.7 crashed, exit 1)",
              r.returncode == 0 and (hw / "state" / "alarms.json").exists(), (r.returncode, r.stderr))
        lg = hw / "logs" / "alarm.log"
        check("v8 item 6: the tick's output is kept in logs/alarm.log (the only place a scheduled run can be read)",
              lg.exists() and "M01" in lg.read_text(encoding="utf-8"), lg.exists())
    else:
        print("SKIP v8 item 6: the pythonw.exe tick runs on Windows only")
    adv = (KIT / "docs" / "ADVANCED.md").read_text(encoding="utf-8")
    check("v8 item 6: A2's check waits for one real scheduled run (LastTaskResult 0, state/alarms.json time)",
          "LastTaskResult" in adv and "Get-ScheduledTaskInfo" in adv, "")
    check("v8 item 7: the cron line sets PATH, installs without an editor, macOS gets a LaunchAgent, the tick logs to alarm.log",
          "crontab -l 2>/dev/null; echo" in adv and "LaunchAgent" in adv and "logs/alarm.log" in adv and "PATH=" in adv, "")
    fake = base / "claude-fake.cmd"
    fake.write_text("@echo off\n", encoding="utf-8")
    (hm / "managers" / "study").mkdir(parents=True, exist_ok=True)
    put_cfg(claude_path=str(fake), routing="live")
    rc, out, err = run([E / "session.py", "open", "study", "hello"], env=dict(env, SBK_SESSION_DRYRUN="1", SBK_AGENTS_JSON=str(base / "none.json")))
    check("v8 item 7: session.py uses the absolute claude_path saved in config.json first (cron has no PATH to find claude)",
          str(fake) in out or fake.name in out, out + err)
    put_cfg()

    # ---- items 8: Full without a review item gets the light review (covered in learn_loop_tests) ----
    # ---- item 9: app-only users are not offered topic sessions ----
    check("v8 item 9: SETUP offers no topic sessions to App-only users and says what they click; the entry template does the work itself on routing inbox",
          "App only, no `claude` command: not offered" in se
          and "do not open topic sessions and do not ask the user to open one by hand"
          in (KIT / "templates" / "entry-CLAUDE.md").read_text(encoding="utf-8"), "")

    # ---- item 10: one conversation per topic ----
    hs = base / "homes"
    (hs / "managers" / "study").mkdir(parents=True)
    (hs / "inbox").mkdir()
    (hs / "config.json").write_text(json.dumps(dict(cfg, vault=str(v), routing="live", wake_limits={"per_day": 20, "min_gap_min": 1})), encoding="utf-8")
    agents = base / "agents.json"
    agents.write_text(json.dumps([{"id": "id1", "name": "study", "kind": "background", "cwd": str(hs / "managers" / "study"),
                                   "startedAt": 5, "sessionId": "11111111-aaaa-bbbb-cccc-000000000001", "state": "done"}]), encoding="utf-8")
    envs = dict(env, SBK_HOME=str(hs), SBK_SESSION_DRYRUN="1", SBK_AGENTS_JSON=str(agents))
    rc, out, err = run([E / "session.py", "list"], env=envs)
    check("v8 item 10: session list shows a stopped conversation that can be resumed (0.2.7 listed only rows with a pid)",
          "study" in out and "stopped" in out, out + err)
    rc, out, err = run([E / "session.py", "deliver", "study", "new work"], env=envs)
    check("v8 item 10: delivering to a stopped topic resumes the SAME conversation (claude --resume <id> --bg), not a second empty one",
          "--resume 11111111-aaaa-bbbb-cccc-000000000001" in out and "--bg" in out and "-n study" not in out.split("--resume")[0], out + err)
    jl(base / "ps.jsonl", [user("hi"), {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "ok"}],
                                                                           "usage": {"input_tokens": 10, "cache_read_input_tokens": 160000,
                                                                                     "cache_creation_input_tokens": 5, "output_tokens": 5}}}])
    cdir = base / "cc"
    (cdir / "projects" / "p").mkdir(parents=True)
    shutil.copy(base / "ps.jsonl", cdir / "projects" / "p" / "11111111-aaaa-bbbb-cccc-000000000001.jsonl")
    rc, out, err = run([E / "handover.py", "check"], env=dict(envs, CLAUDE_CONFIG_DIR=str(cdir)))
    check("v8 item 10: the 150k hand-over check sees a stopped row (it was invisible before: the long conversation is the stopped one)",
          "study" in out and "no sessions" not in out.lower(), out + err)
    entry_t = (KIT / "templates" / "entry-CLAUDE.md").read_text(encoding="utf-8")
    check("v8 item 10: the entry template says one conversation per topic and never a second one", "one conversation per topic" in entry_t.lower()
          and "Never start a second conversation" in entry_t, "")

    # ---- item 11: maintenance checks read_history and does not Read raw jsonl ----
    mt = (KIT / "templates" / "maintenance-CLAUDE.md").read_text(encoding="utf-8")
    check("v8 item 11: maintenance checks read_history first, is limited to the vault and ~/.sbk projects, uses handover.py words (no raw jsonl)",
          "`read_history`" in mt and "handover.py words" in mt and "never other projects" in mt and "never a raw `.jsonl`" in mt, "")

    # ---- item 12: allowlist per role ----
    sess = (E / "session.py").read_text(encoding="utf-8")
    rc, out, err = run([E / "session.py", "open", "study", "go"], env=dict(envs, SBK_AGENTS_JSON=str(base / "none.json")))
    check("v8 item 12: a topic session may search the web, load skills, use subagents and commit its notes (WebSearch, Agent, git commit)",
          "WebSearch" in out and "Agent" in out and "git commit" in out and "--permission-mode dontAsk" in out, out + err)
    check("v8 item 12: the manager and maintenance templates say a refused tool call is reported to the entry the same turn",
          "refused" in (KIT / "templates" / "manager-CLAUDE.md").read_text(encoding="utf-8")
          and "refused" in mt, "")

    # ---- item 13: the Stop hook commits changed notes ----
    if shutil.which("git"):
        g = lambda *a: subprocess.run(["git", "-C", str(v)] + list(a), capture_output=True, text=True, encoding="utf-8")
        g("init", "-q")
        g("config", "user.name", "t")
        g("config", "user.email", "t@localhost")
        g("add", ".")
        g("commit", "-q", "-m", "init", "--no-verify")
        nt.write_text(nt.read_text(encoding="utf-8") + "an addition\n", encoding="utf-8")
        before = g("rev-list", "--count", "HEAD").stdout.strip()
        rc, out, err = run([H / "vault_snapshot.py"], {"cwd": str(v), "hook_event_name": "Stop"}, env)
        after = g("rev-list", "--count", "HEAD").stdout.strip()
        check("v8 item 13: the Stop hook vault_snapshot commits the changed note (git now records every change)",
              rc == 0 and int(after) == int(before) + 1 and "snapshot" in g("log", "-1", "--format=%s").stdout
              and g("status", "--short").stdout.strip() == "", (before, after, err))
        rc, out, err = run([H / "vault_snapshot.py"], {"cwd": str(v), "hook_event_name": "Stop"}, env)
        check("v8 item 13: nothing changed -> no empty commit", g("rev-list", "--count", "HEAD").stdout.strip() == after, err)
        nt.write_text(nt.read_text(encoding="utf-8") + "another\n", encoding="utf-8")
        rc, out, err = run([H / "vault_snapshot.py"], {"cwd": str(v), "hook_event_name": "Stop"}, dict(env, SBK_MODE_VAULT_SNAPSHOT="off"))
        check("v8 item 13: mode off commits nothing", g("rev-list", "--count", "HEAD").stdout.strip() == after, err)
        g("checkout", "--", ".")
    check("v8 item 13: it never pushes, and AGENTS.md's 'Before you stop' names it",
          "push" not in re.sub(r"never pushes|no push|nothing is pushed", "", (H / "vault_snapshot.py").read_text(encoding="utf-8")).lower().split("def ")[1]
          and "`vault_snapshot`" in ag, "")

    # ---- item 14: README and diagram say what the guard does ----
    rd = "\n".join((KIT / n).read_text(encoding="utf-8") for n in ("README.md", "docs/SAFETY.md", "docs/GUIDE.md", "docs/FAQ.md", "docs/HOW-IT-WORKS.md"))
    rz = "\n".join((KIT / n).read_text(encoding="utf-8") for n in ("README.zh-TW.md", "docs/zh-TW/安全與資料.md", "docs/zh-TW/指南.md", "docs/zh-TW/常見問題.md", "docs/zh-TW/運作原理.md"))
    sv = (KIT / "docs" / "diagrams" / "00-basic.svg").read_text(encoding="utf-8")
    check("v8 item 14: README (both), the Basic diagram no longer promise 'asks before deleting, uploading or overwriting'",
          "asks before deleting, uploading or overwriting" not in rd.lower() and "刪除、上傳、覆寫之前先問你" not in rz
          and "刪除、上傳前先問你" not in sv and "before Claude uploads or deletes anything" not in rd, "")

    # ---- item 15: partial Read context; narrowed shell rule ----
    rp = lambda **kw: run([H / "read_whole.py"], {"hook_event_name": "PostToolUse", "tool_name": "Read", "cwd": str(v),
                                                  "tool_input": dict({"file_path": str(nt)}, **kw)}, env)
    rc, out, err = rp(limit=80)
    check("v8 item 15: a Read of a note that stops before the end gets 'You have lines 1-80 of N ... read the rest'",
          "You have lines 1-80 of" in out and "offset 81" in out and "PostToolUse" in out, out + err)
    rc, out, err = rp()
    check("v8 item 15: a Read that reaches the end adds nothing", out.strip() == "", out + err)
    for cmd, expect in [("ls 20-29*/*.md | head -5", False), ("git log -- x.md | head -3", False), ("cat x.md | head -5", True)]:
        rc, out, _ = run([H / "read_whole.py"], {"tool_name": "Bash", "cwd": str(v), "tool_input": {"command": cmd}}, env)
        check("v8 item 15: shell rule is about the note itself: '%s' %s" % (cmd, "denied" if expect else "allowed"),
              ('"permissionDecision": "deny"' in out) == expect, out)

    # ---- item 16: the block names the vault by absolute path and shows Core stance before the yes ----
    cl = (KIT / "templates" / "CLAUDE.md").read_text(encoding="utf-8")
    check("v8 item 16: the global block uses {{vault}} (absolute path), says the preferences are already in the conversation, "
          "and SETUP shows the block with Core stance before the yes",
          "{{vault}}" in cl and "already in this conversation" in cl and "Core stance" in se and "show the block before the yes" in se, "")

    # ---- item 17: kit sessions that cannot ask the user do not use the weekly check ----
    h17 = base / "home17"
    (h17 / "managers" / "x").mkdir(parents=True)
    (h17 / "config.json").write_text(json.dumps(dict(cfg, vault=str(v), level="full")), encoding="utf-8")
    env17 = dict(env, SBK_HOME=str(h17))
    for sub in ("state", "managers/x"):
        d = h17 / sub
        d.mkdir(parents=True, exist_ok=True)
        rc, out, err = run([LC, "--hook", "--now", "2026-12-30T09:00:00"], {"cwd": str(d), "hook_event_name": "SessionStart"}, env17)
        st = h17 / "state" / "level_check.json"
        check("v8 item 17: level_notice is silent in SBK_HOME/%s and does not use up the week" % sub,
              out.strip() == "" and (not st.exists() or "last_hook_run" not in json.loads(st.read_text(encoding="utf-8"))), out + err)
        rc, out, err = run([H / "learn_notice.py"], {"cwd": str(d), "hook_event_name": "SessionStart", "source": "startup"}, env17)
        if sub == "state":
            check("v8 item 17: learn_notice does not load the preferences into the haiku courier's run (SBK_HOME/state)", out.strip() == "", out + err)
    rc, out, err = run([E / "session.py", "push", "study", "hi"], env=dict(envs, SBK_AGENTS_JSON=str(base / "none2.json")))
    agents.write_text(json.dumps([{"pid": 9, "id": "id1", "name": "study", "status": "idle", "kind": "background",
                                   "cwd": str(hs / "managers" / "study"), "startedAt": 5, "sessionId": "s1"}]), encoding="utf-8")
    rc, out, err = run([E / "session.py", "push", "study", "hi"], env=envs)
    check("v8 item 17: the courier run has all hooks off for that run (--settings disableAllHooks, documented)",
          "disableAllHooks" in out, out + err)
    put_cfg()

    # ---- item 18: preferences merge, retire, trend, budget ----
    envl = dict(env, SBK_VAULT=str(v))
    run([LE, "pref", "short", "Keep answers to three lines.", "--now", "2026-11-01"], env=envl)
    rc, out, err = run([LE, "pref", "short", "Keep answers to five lines.", "--now", "2026-11-20"], env=envl)
    nt_text = note.read_text(encoding="utf-8")
    check("v8 item 18a: pref of the same kind REPLACES the older line (0.2.7 only appended)",
          "replaced" in out and nt_text.count("(short;") == 1 and "five lines" in nt_text and "three lines" not in nt_text, out + err + nt_text[-500:])
    rc, out, err = run([LE, "retire", "short", "--now", "2026-12-01"], env=envl)
    check("v8 item 18b: learn.py retire removes a preference of a kind", rc == 0 and "(short;" not in note.read_text(encoding="utf-8"), out + err)
    check("v8 item 18b: the maintenance template has the merge / retire / resolve step with the 25-line budget",
          "pref_budget" in mt and "25 lines" in mt and "learn.py retire" in mt and "learn.py reviewed" in mt, "")
    run([LE, "pref", "repeat", "Check twice.", "--now", "2026-11-10"], env=envl)
    run([LE, "add", "correction", "repeat", "again", "--now", "2026-11-03"], env=envl)
    run([LE, "add", "correction", "repeat", "again2", "--now", "2026-11-04"], env=envl)
    run([LE, "add", "correction", "repeat", "still", "--now", "2026-11-15"], env=envl)
    rc, out, err = run([LE, "trend", "--now", "2026-11-25"], env=envl)
    check("v8 item 18c: trend prints, per preference, the corrections of its kind before and after it was written (2 before, 1 after)",
          "repeat" in out and "2" in out and "came back" in out.lower() and "after" in out.lower(), out + err)
    check("v8 item 18d: a kind that returns after its preference is escalated (maintenance template; trend line)",
          "came back after its preference" in out.lower() or "Came back after its preference" in out, out)
    # newest never cut
    sys.path.insert(0, str(H))
    import importlib
    ln = importlib.import_module("learn_notice")
    starters = ["- starter line %d %s" % (i, ln.STARTER_TAGS[0]) for i in range(5)]
    own = ["- own %d %s" % (i, "x" * 400) + " (k%d; 2026-12-%02d)" % (i, i + 1) for i in range(1, 15)]
    out_p = ln.fit(starters + own) if hasattr(ln, "fit") else []
    joined = "\n".join(out_p)
    check("v8 item 18: when the preferences exceed the cap the starter lines go first and the user's newest line is kept",
          "own 14" in joined and "starter line 4" not in joined, joined[-300:])

    # ---- item 19: the starter lines the block already says are gone, identically in both languages ----
    zh = (KIT / "templates" / "和AI協作.md").read_text(encoding="utf-8")
    en = (KIT / "templates" / "和AI協作.en.md").read_text(encoding="utf-8")
    gone_en = ["Prepare everything up to the user's last step", "When editing the user's document, change only what was asked",
               "Decide small, reversible things yourself"]
    gone_zh = ["把事情準備到只剩使用者的最後一步", "改使用者的文件時只動要改的地方", "可挽回的小事自己決定"]
    check("v8 item 19: the same three starter lines were removed from the EN and zh files (12 left each), and the block covers each",
          not any(x in en for x in gone_en) and not any(x in zh for x in gone_zh)
          and "Keep going until only the user's own step is left" in cl and "When editing the user's document, change only what must change" in cl
          and "Ask for permission as" in cl, "")

    # ---- item 20: one name map ----
    sys.path.insert(0, str(H))
    cm = importlib.import_module("_common")
    nj = json.loads((KIT / "templates" / "names.json").read_text(encoding="utf-8"))
    cfgt = json.loads((KIT / "templates" / "config.json").read_text(encoding="utf-8"))
    check("v8 item 20: templates/names.json ships zh-TW and en, equal to _common; config template carries the zh-TW map",
          nj["zh-TW"] == cm.NAMES_ZH and nj["en"] == cm.NAMES_EN and cfgt["names"] == cm.NAMES_ZH, "")
    sys.path.insert(0, str(KIT / "scripts"))
    gj = importlib.import_module("gen_jdex")
    lc = importlib.import_module("level_check")
    check("v8 item 20: the default-name copies in gen_jdex and level_check equal _common.NAMES_ZH",
          all(cm.NAMES_ZH[k] == vv for k, vv in gj.NAMES_ZH.items()) and all(cm.NAMES_ZH[k] == vv for k, vv in lc.NAMES_ZH.items()), "")
    ve = base / "vault-en"
    en_names = nj["en"]
    (ve / en_names["sys_dir"] / en_names["ai_dir"]).mkdir(parents=True)
    (ve / en_names["sys_dir"] / en_names["rules_dir"]).mkdir(parents=True)
    (ve / ".sbk-vault").write_text("", encoding="utf-8")
    (ve / "AGENTS.md").write_text("x", encoding="utf-8")
    ne = ve / en_names["sys_dir"] / en_names["ai_dir"] / en_names["ai_note"]
    ne.write_text(en.replace("{{date}}", "2026-12-01"), encoding="utf-8")
    he = base / "home-en"
    he.mkdir()
    (he / "config.json").write_text(json.dumps(dict(cfg, vault=str(ve), language="English", names=en_names)), encoding="utf-8")
    ene = dict(env, SBK_HOME=str(he), SBK_VAULT=str(ve))
    rc, out, err = run([LE, "add", "correction", "too-long", "that is too long", "--now", "2026-12-05"], env=ene)
    check("v8 item 20: with the en name map learn.py finds and writes the English-named note", rc == 0 and "too-long" in ne.read_text(encoding="utf-8"), out + err)
    run([LE, "pref", "too-long", "Keep answers short.", "--now", "2026-12-06"], env=ene)
    rc, out, err = run([H / "learn_notice.py"], {"cwd": str(ve), "hook_event_name": "SessionStart", "source": "startup"}, ene)
    check("v8 item 20: learn_notice puts the preferences of the English-named note into the conversation", "Keep answers short." in out, out + err)
    rc, out, err = run([KIT / "scripts" / "gen_jdex.py", "--root", ve], env=ene)
    idx = ve / en_names["sys_dir"] / en_names["index_dir"] / en_names["index_note"]
    check("v8 item 20: gen_jdex writes the index under the English names, in English text (no 'JDex 索引' / '下一個空號')",
          idx.exists() and "Next free number" in idx.read_text(encoding="utf-8") and "下一個空號" not in idx.read_text(encoding="utf-8"), out + err)
    rc, out, _ = run([H / "vault_guard.py"], {"tool_name": "Write", "cwd": str(ve), "tool_input": {
        "file_path": str(ve / en_names["sys_dir"] / en_names["rules_dir"] / "x.md"), "content": "x"}}, ene)
    check("v8 item 20: vault_guard protects the English-named rules folder (0.2.7 knew only the Chinese name)",
          '"permissionDecision": "ask"' in out, out)
    (he / "config.json").write_text(json.dumps(dict(cfg, vault=str(ve), language="English")), encoding="utf-8")
    rc, out, err = run([H / "vault_guard.py"], {"tool_name": "Write", "cwd": str(ve), "tool_input": {
        "file_path": str(ve / en_names["sys_dir"] / en_names["rules_dir"] / "x.md"), "content": "x"}}, ene)
    check("v8 item 20: with no names in config.json (an install from before 0.2.8) the old Chinese defaults still apply",
          cm.names().get("rules_dir") == "01 規則" if False else cm.NAMES_ZH["rules_dir"] == "01 規則", "")
    check("v8 item 20: SETUP no longer contradicts itself (the 'translate' vs 'names stay as they are' sentences are one rule: the map)",
          "Folder and file names stay as they are." not in se and "translate the words only if the user wants another language" not in se, "")

    # ---- item 21: Basic records a processed item ----
    check("v8 item 21: AGENTS.md uses ledger.py add with --done-when and --said (Basic records goal, done-when and the words)",
          'ledger.py add "[topic] goal in one line" --done-when' in ag and "--said" in ag, "")

    # ---- item 22: version notice, commands on the clone route ----
    hv = base / "homev"
    (hv / "bin").mkdir(parents=True)
    (hv / "bin" / "VERSION").write_text("0.2.7\n", encoding="utf-8")
    (hv / "config.json").write_text(json.dumps(dict(cfg, vault=str(v))), encoding="utf-8")
    rc, out, err = run([LC, "--hook", "--now", "2026-12-30T09:00:00"], {"cwd": str(v), "hook_event_name": "SessionStart"},
                       dict(env, SBK_HOME=str(hv)))
    check("v8 item 22: bin/VERSION differs from the plugin's -> 'kit updated: copy the tools again' (0.2.7 had no such notice)",
          "second-brain-kit update" in out and "copy the tools again" in out, out + err)
    pv = json.loads((KIT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
    (hv / "bin" / "VERSION").write_text(pv + "\n", encoding="utf-8")
    (hv / "state" / "level_check.json").unlink() if (hv / "state" / "level_check.json").exists() else None
    rc, out, err = run([LC, "--hook", "--now", "2026-12-31T09:00:00"], {"cwd": str(v), "hook_event_name": "SessionStart"},
                       dict(env, SBK_HOME=str(hv)))
    check("v8 item 22: ... and silent when the versions match", "second-brain-kit update" not in out, out + err)
    check("v8 item 22: SETUP writes bin/VERSION and copies commands/ on the clone route; plugin and marketplace say 0.2.9",
          "bin/VERSION" in se and "KIT/commands/*.md" in se and pv == "0.2.9"
          and json.loads((KIT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))["plugins"][0]["version"] == "0.2.9", pv)

    # ---- item 23: SessionStart covers /clear and forks ----
    ss = hj["hooks"]["SessionStart"]
    check("v8 item 23: SessionStart matcher includes clear and fork for learn_notice and inbox_notice (hooks.json and the example)",
          any("clear" in m["matcher"] and "fork" in m["matcher"] and any("learn_notice" in h["command"] for h in m["hooks"])
              and any("inbox_notice" in h["command"] for h in m["hooks"]) for m in ss)
          and "startup|resume|clear|fork" in (KIT / "templates" / "settings.hooks.example.json").read_text(encoding="utf-8"), [m["matcher"] for m in ss])
    rc, out, err = run([H / "learn_notice.py"], {"cwd": str(v), "hook_event_name": "SessionStart", "source": "clear"}, env)
    check("v8 item 23: after /clear the preferences are put into the conversation", rc == 0 and ("preferences" in out.lower() or "偏好" in out), out + err)

    # ---- item 24: the tracker keeps changes made at the same time, and keeps lines it does not know ----
    import threading
    hl = base / "homel"
    hl.mkdir()
    el = dict(env, SBK_HOME=str(hl))
    L = E / "ledger.py"
    for i in range(3):
        run([L, "add", "item %d" % i], env=el)
    lp = hl / "ledger.md"
    lp.write_text(lp.read_text(encoding="utf-8") + "\nA note somebody typed here by hand\n", encoding="utf-8")
    procs = []
    for i in range(6):
        procs.append(subprocess.Popen([PY, str(L), "add", "parallel %d" % i], env=dict(os.environ, **el), stdout=subprocess.PIPE, stderr=subprocess.PIPE))
    for p in procs:
        p.communicate(timeout=60)
    txt = lp.read_text(encoding="utf-8")
    check("v8 item 24: six parallel `ledger.py add` calls lose none (a lock file around load-to-save)",
          all(("parallel %d" % i) in txt for i in range(6)) and txt.count("| open |") == 9, txt[-400:])
    check("v8 item 24: a line the item pattern does not match survives the save", "A note somebody typed here by hand" in txt, txt[-300:])

    # ---- item 25: Ultra ----
    check("v8 item 25: SETUP question 5 and the plan table have Ultra (an Ultra subscriber got the Pro values)",
          "Pro, Max, Ultra, Team" in se and "| Ultra, Team, Enterprise or higher |" in se, "")

    # ---- item 26: the to-do note by its installed path ----
    mgr = (KIT / "templates" / "manager-CLAUDE.md").read_text(encoding="utf-8")
    pit = (KIT / "docs" / "PITFALLS.md").read_text(encoding="utf-8") + (KIT / "docs" / "zh-TW" / "踩過的坑.md").read_text(encoding="utf-8")
    check("v8 item 26: manager template and PITFALLS name the vault note 02-02 (not a todo-for-me.md in SBK_HOME)",
          "todo-for-me.md" not in mgr and "todo-for-me.md" not in pit and "02-02 我要做的事" in mgr and "02-02 我要做的事" in pit, "")

    # ---- the names the templates use are all in the map (so the setup's replacement for another language is complete) ----
    zhnames = list(nj["zh-TW"].values())
    used = set()
    for n in ("AGENTS.md", "CLAUDE.md", "entry-CLAUDE.md", "manager-CLAUDE.md", "maintenance-CLAUDE.md", "sbk-protect.txt"):
        for m in re.findall(r"\d\d(?:-\d\d)? [^`/\n<>\"')]*[一-鿿][^`/\n<>\"')]*", (KIT / "templates" / n).read_text(encoding="utf-8")):
            used.add(m.strip())
    stray = [u for u in used if not any(z.rstrip(".md") in u or u in z for z in zhnames)]
    check("v8 item 20: every numbered Chinese folder or file name in the templates is one the name map has", not stray, stray)


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
        # an existing notes folder named in the config needs no marker file put into it
        bare = tmp / "barevault"
        (bare / "a").mkdir(parents=True)
        (bare / "a" / "n.md").write_text("---\nstatus: active\n---\n\n" + "line\n" * 12, encoding="utf-8")
        ev_bare = {"tool_name": "Bash", "cwd": str(bare), "tool_input": {"command": 'head -n 5 "a/n.md"'}}
        rc, out, _ = run([H / "read_whole.py"], ev_bare, env)
        check("vault: a folder with no marker and not named anywhere is not a vault", out.strip() == "", out)
        rc, out, _ = run([H / "read_whole.py"], ev_bare, dict(env, SBK_VAULT=str(bare)))
        check("vault: the folder named by the config or SBK_VAULT is the vault without a marker file",
              '"permissionDecision": "deny"' in out, out)
        rc, out, _ = run([H / "read_whole.py"], ev_bare, dict(env, SBK_VAULT=str(tmp / "no-such-folder")))
        check("vault: a named folder that does not exist is ignored", out.strip() == "", out)
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
        # the notes folder's rule file is put into a kit session at start (an attached folder's
        # CLAUDE.md import is not followed, so "read its AGENTS.md first" was only a sentence)
        rv = tmp / "rulesvault"
        rv.mkdir()
        (rv / "AGENTS.md").write_text("# Rules of these notes\nRULE-KIWI: never delete a note.\n", encoding="utf-8")
        envr = dict(envi, SBK_VAULT=str(rv))
        rc, out, _ = run([H / "inbox_notice.py"], {"cwd": str(home / "managers" / "study"), "hook_event_name": "SessionStart"}, envr)
        check("inbox: SessionStart puts the notes folder's AGENTS.md into the session, word for word",
              "RULE-KIWI: never delete a note." in out and "summarise chapter 3" in out, out)
        (home / "inbox" / "study.md").open("a", encoding="utf-8").write("- [ ] L0099 one more line\n")
        rc, out, _ = run([H / "inbox_notice.py"], {"cwd": str(home / "managers" / "study"), "hook_event_name": "UserPromptSubmit"}, envr)
        check("inbox: a later prompt shows the new line without repeating the rules", "L0099" in out and "RULE-KIWI" not in out, out)
        (rv / "AGENTS.md").write_text("\n".join("line %04d of the rules, forty characters long" % i for i in range(400)), encoding="utf-8")
        rc, out, _ = run([H / "inbox_notice.py"], {"cwd": str(home / "managers" / "study"), "hook_event_name": "SessionStart"}, envr)
        ctx = (json.loads(out)["hookSpecificOutput"]["additionalContext"] if out.strip() else "")
        check("inbox: a long rule file is cut at a line end under 10,000 characters and says where to read the rest",
              0 < len(ctx) < 10000 and "[cut after line" in ctx and "of 400" in ctx and (rv / "AGENTS.md").as_posix() in ctx, ctx[-200:])
        lines = (home / "inbox" / "study.md").read_text(encoding="utf-8").splitlines(True)
        (home / "inbox" / "study.md").write_text("".join(x for x in lines if "L0099" not in x), encoding="utf-8")
        rc, out, _ = run([H / "inbox_notice.py"], {"cwd": str(home / "managers" / "study"), "hook_event_name": "SessionStart"}, envi)
        check("inbox: no notes folder set: the notice still works, no rules part", "summarise chapter 3" in out and "word for word" not in out, out)
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
        # a kit session in the background above the threshold: the kit replaces it, the user opens nothing
        hb = tmp / "home-bg"
        for d in ("entry", "managers/study", "managers/work", "state"):
            (hb / d).mkdir(parents=True)
        (hb / "alarms.md").write_text("| id | when | to | text |\n|---|---|---|---|\n", encoding="utf-8")
        (hb / "config.json").write_text(json.dumps({
            "routing": "live", "handover_quiet_min": 0,
            "session_models": {"entry": {"model": "opus", "effort": "high"}, "study": {"model": "haiku"},
                               "topic": {"model": "sonnet", "effort": "medium; rm -rf"}}}), encoding="utf-8")
        envb = {"SBK_HOME": str(hb), "SBK_VAULT": "", "ANTHROPIC_API_KEY": "", "SBK_BACKGROUND": "1"}
        sid_e = "22222222-aaaa-bbbb-cccc-000000000002"
        jl(tt, [user("keep the budget under 200"), usage(170000)])
        evb = {"session_id": sid_e, "hook_event_name": "UserPromptSubmit", "transcript_path": str(tt), "cwd": str(hb / "entry")}
        rc, out, _ = run([H / "requests_reinject.py"], evb, envb)
        ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"] if out.strip() else ""
        flag = hb / "state" / "handover_due.json"
        check("hand-over: a background entry above the threshold is flagged for the tick; the user is not asked to open a conversation",
              "hand over" in ctx and "start a new conversation" not in ctx and "Say nothing about this to the user" in ctx
              and str((hb / "entry" / "task.md").resolve()) in ctx and flag.exists()
              and json.loads(flag.read_text(encoding="utf-8")).get("entry", {}).get("session") == sid_e, out)
        rc, out, _ = run([H / "requests_reinject.py"], dict(evb, session_id="w9", cwd=str(hb / "managers" / "study")),
                         dict(envb, SBK_BACKGROUND="0"))
        ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"] if out.strip() else ""
        check("hand-over: a topic the user typed into (a window) hands over into its own task.md, not the main one",
              str((hb / "managers" / "study" / "task.md").resolve()) in ctx and "start a new conversation" in ctx
              and "study" not in json.loads(flag.read_text(encoding="utf-8")), out)
        HO = KIT / "entry" / "handover.py"
        agb = tmp / "agents-bg.json"
        row_e = {"id": "e1", "name": "entry", "kind": "background", "cwd": str(hb / "entry"), "pid": 4242,
                 "status": "idle", "startedAt": 5, "sessionId": sid_e}
        agb.write_text(json.dumps([row_e]), encoding="utf-8")
        envd = dict(envb, SBK_AGENTS_JSON=str(agb), SBK_SESSION_DRYRUN="1")
        rc, out, err = run([HO, "due"], env=envd)
        check("hand-over due: nothing is replaced before the hand-over is written", "not written yet" in out and flag.exists(), out + err)
        tk = hb / "entry" / "task.md"
        tk.write_text("# Now\n", encoding="utf-8")
        later = json.loads(flag.read_text(encoding="utf-8"))["entry"]["ts"] + 30
        os.utime(tk, (later, later))
        agb.write_text(json.dumps([dict(row_e, status="busy")]), encoding="utf-8")
        rc, out, err = run([HO, "due"], env=envd)
        check("hand-over due: a session that is working is left alone", "working, waits" in out and flag.exists(), out + err)
        agb.write_text(json.dumps([row_e]), encoding="utf-8")
        rc, out, err = run([KIT / "entry" / "alarm.py", "--tick", "--now", "2026-11-23T09:00"], env=envd)
        check("hand-over due: the alarm tick replaces the flagged session once its task.md is written and it is idle",
              "handover: RENEWED (dry run): entry" in out and not flag.exists(), out + err)
        flag.write_text(json.dumps({"entry": {"ts": 1, "session": "some-earlier-conversation"}}), encoding="utf-8")
        rc, out, err = run([HO, "due"], env=envd)
        check("hand-over due: a flag left by an earlier conversation is dropped, the fresh one is not replaced again",
              "flag dropped" in out and "RENEWED" not in out and not flag.exists(), out + err)
        # model and effort per session (config.json session_models)
        none_b = tmp / "agents-none.json"
        none_b.write_text("[]", encoding="utf-8")
        envm = dict(envb, SBK_AGENTS_JSON=str(none_b), SBK_SESSION_DRYRUN="1")
        rc, out, err = run([KIT / "entry" / "session.py", "open", "entry"], env=envm)
        check("session models: the entry gets its model and effort", "--model opus --effort high" in out, out + err)
        rc, out, err = run([KIT / "entry" / "session.py", "open", "study", "go"], env=envm)
        check("session models: a session's own row wins over its role", "--model haiku" in out and "--effort" not in out, out + err)
        rc, out, err = run([KIT / "entry" / "session.py", "open", "work", "go"], env=envm)
        check("session models: the role row applies to other topics; a value that is not a plain word is dropped",
              "--model sonnet" in out and "--effort" not in out and "rm -rf" not in out, out + err)
        check("session settings: by default only cross-session messages are accepted and the mode is dontAsk",
              "--permission-mode dontAsk" in out and "crossSessionInbound" in out
              and not (hb / "state" / "session-settings.json").exists(), out + err)
        # permission mode per session; the kit's hooks only for the sessions the kit starts
        (hb / "config.json").write_text(json.dumps({
            "routing": "live", "session_hooks": True,
            "permission_modes": {"entry": "bypassPermissions", "topic": "whatever"}}), encoding="utf-8")
        rc, out, err = run([KIT / "entry" / "session.py", "open", "entry"], env=envm)
        ssf = hb / "state" / "session-settings.json"
        ssd = json.loads(ssf.read_text(encoding="utf-8")) if ssf.exists() else {}
        cmds = [h["command"] for ev in ssd.get("hooks", {}).values() for m in ev for h in m["hooks"]]
        check("session settings: the entry can be given its own permission mode", "--permission-mode bypassPermissions" in out, out + err)
        check("session hooks: the kit's hook set goes into a settings file for kit sessions only, with the real hooks folder",
              ssd.get("crossSessionInbound") == "accept" and cmds and not any("__KIT__" in c for c in cmds)
              and all((KIT / "hooks").as_posix() in c for c in cmds) and "_comment" not in ssd
              and '{"crossSessionInbound"' not in out, out + err + str(ssd)[:300])
        rc, out, err = run([KIT / "entry" / "session.py", "open", "work", "go"], env=envm)
        check("session settings: a mode that is not a real one falls back to dontAsk", "--permission-mode dontAsk" in out, out + err)
        # the installed layout: the scripts in <home>/bin, the hooks and their settings file in <home>/hooks
        (hb / "bin").mkdir(exist_ok=True)
        (hb / "hooks").mkdir(exist_ok=True)
        for f in ("session.py", "send.py", "ledger.py", "handover.py"):
            shutil.copy(str(KIT / "entry" / f), str(hb / "bin" / f))
        shutil.copy(str(KIT / "templates" / "settings.hooks.example.json"), str(hb / "hooks" / "settings.hooks.example.json"))
        ssf.unlink()
        rc, out, err = run([hb / "bin" / "session.py", "open", "entry"], env=envm)
        ssd = json.loads(ssf.read_text(encoding="utf-8")) if ssf.exists() else {}
        cmds = [h["command"] for ev in ssd.get("hooks", {}).values() for m in ev for h in m["hooks"]]
        # skip_hooks: the user's older Python hooks end at once in sessions the kit starts, and only there
        legacy = tmp / "legacy-hooks"
        legacy.mkdir()
        for n in ("old_check.py", "kept_check.py"):
            (legacy / n).write_text("import sys\nopen(sys.argv[1], 'a').write('%s ran\\n')\n" % n, encoding="utf-8")
        (tmp / "other.py").write_text("import sys\nopen(sys.argv[1], 'a').write('other ran\\n')\n", encoding="utf-8")
        (hb / "config.json").write_text(json.dumps({"routing": "live", "skip_hooks": {"under": [str(legacy)], "keep": ["kept_check.py"]}}), encoding="utf-8")
        penv = tmp / "penv.py"
        penv.write_text("import sys\nsys.path.insert(0, %r)\nimport session\nprint(session.child_env().get('PYTHONPATH', ''))\n"
                        % str(KIT / "entry"), encoding="utf-8")
        rc, out, err = run([penv], env=envm)
        gate_dir = out.strip().split(os.pathsep)[0] if out.strip() else ""
        ran = tmp / "ran.txt"
        skipped = tmp / "skipped.txt"
        for script in (legacy / "old_check.py", legacy / "kept_check.py", tmp / "other.py"):
            run([script, ran], env={"PYTHONPATH": gate_dir, "SBK_GATE_LOG": str(skipped)})
        run([legacy / "old_check.py", ran], env={"PYTHONPATH": ""})
        ran_t = ran.read_text(encoding="utf-8") if ran.exists() else ""
        check("skip_hooks: in a kit session an older hook ends before it does anything; a kept one, any other script, and the same hook outside a kit session run",
              rc == 0 and gate_dir and (Path(gate_dir) / "sitecustomize.py").exists()
              and ran_t == "kept_check.py ran\nother ran\nold_check.py ran\n"
              and skipped.exists() and skipped.read_text(encoding="utf-8").strip() == "old_check.py", out + err + ran_t)
        (hb / "config.json").write_text(json.dumps({"routing": "live", "skip_hooks": {"under": [str(legacy)], "keep": ["kept_check.py"],
                                                                                   "keep_for": {"topic": ["old_check.py"]}}}), encoding="utf-8")
        penv2 = tmp / "penv2.py"
        penv2.write_text("import os, sys\nsys.path.insert(0, %r)\nimport session\n"
                         "print(session.child_env('study').get('PYTHONPATH', '').split(os.pathsep)[0])\n"
                         "print(session.child_env('entry').get('PYTHONPATH', '').split(os.pathsep)[0])\n" % str(KIT / "entry"), encoding="utf-8")
        rc, out, err = run([penv2], env=dict(envm, PYTHONPATH=""))
        gates = out.strip().splitlines()
        ran2 = tmp / "ran2.txt"
        for g_ in gates[:2]:
            run([legacy / "old_check.py", ran2], env={"PYTHONPATH": g_})
        check("skip_hooks: keep_for keeps an older hook on for one role only (a topic runs it, the entry does not)",
              rc == 0 and len(gates) == 2 and gates[0] != gates[1] and Path(gates[0]).name == "topic"
              and ran2.exists() and ran2.read_text(encoding="utf-8") == "old_check.py ran\n", out + err)
        (hb / "config.json").write_text(json.dumps({"routing": "live", "session_hooks": True}), encoding="utf-8")
        rc, out, err = run([penv], env=dict(envm, PYTHONPATH=""))
        check("skip_hooks: nothing is put on PYTHONPATH when it is not configured", rc == 0 and out.strip() == "", out + err)
        check("session hooks: from the installed layout the commands point at <home>/hooks",
              cmds and all((hb.resolve() / "hooks").as_posix() in c for c in cmds), out + err + str(cmds)[:300])
        (hb / "config.json").write_text(json.dumps({"routing": "live", "session_hooks": str(tmp / "no-such.json")}), encoding="utf-8")
        rc, out, err = run([KIT / "entry" / "session.py", "open", "work", "go"], env=envm)
        check("session hooks: an unreadable file is reported and the session still starts",
              "session_hooks: cannot use" in out and "crossSessionInbound" in out and "dry run: claude" in out, out + err)
        # report without being asked: the tick tells the entry about finished and stalled work
        hr = tmp / "home-report"
        for d in ("entry", "managers/study", "inbox", "state"):
            (hr / d).mkdir(parents=True)
        (hr / "config.json").write_text(json.dumps({"routing": "live"}), encoding="utf-8")
        (hr / "alarms.md").write_text("| id | when | to | text |\n|---|---|---|---|\n", encoding="utf-8")
        (hr / "inbox" / "study.md").write_text("- [x] L0002 summarise chapter 9\n", encoding="utf-8")
        (hr / "ledger.md").write_text("# Ledger\n\n- L0001 | done | 2026-11-23T08:00:00 | tidy the notes | ev: opened the folder, 3 files renamed\n"
                                      "- L0002 | dispatched:study | 2026-11-23T08:00:00 | summarise chapter 9 | ev: \n", encoding="utf-8")
        sid_s = "33333333-aaaa-bbbb-cccc-000000000003"
        ccr = tmp / "cc-report"
        (ccr / "projects" / "p").mkdir(parents=True)
        trs = ccr / "projects" / "p" / (sid_s + ".jsonl")
        jl(trs, [user("go")])
        quiet_since = datetime.datetime(2026, 11, 23, 8, 0).timestamp()
        os.utime(trs, (quiet_since, quiet_since))
        agr = tmp / "agents-report.json"
        agr.write_text(json.dumps([
            {"id": "e1", "name": "entry", "kind": "background", "cwd": str(hr / "entry"), "pid": 1, "status": "idle",
             "startedAt": 5, "sessionId": "44444444-aaaa-bbbb-cccc-000000000004"},
            {"id": "s1", "name": "study", "kind": "background", "cwd": str(hr / "managers" / "study"),
             "startedAt": 6, "sessionId": sid_s, "state": "done"}]), encoding="utf-8")
        envr2 = {"SBK_HOME": str(hr), "SBK_VAULT": "", "ANTHROPIC_API_KEY": "", "SBK_AGENTS_JSON": str(agr),
                 "SBK_SESSION_DRYRUN": "1", "CLAUDE_CONFIG_DIR": str(ccr)}
        AL = KIT / "entry" / "alarm.py"
        rc, out, err = run([AL, "--tick", "--now", "2026-11-23T09:00"], env=envr2)
        rep = json.loads((hr / "state" / "report.json").read_text(encoding="utf-8")) if (hr / "state" / "report.json").exists() else {}
        check("report: an item handed to a topic that stopped without closing it is sent to the entry; a just-finished one waits one tick",
              "report: 1 line(s) sent to the entry" in out and "L0002" in rep.get("stale", {}) and rep.get("done", {}).get("L0001") == "seen", out + err)
        rc, out, err = run([AL, "--tick", "--now", "2026-11-23T09:05"], env=envr2)
        rep = json.loads((hr / "state" / "report.json").read_text(encoding="utf-8"))
        check("report: a finished item the entry has not checked one tick later is sent; the stalled one is not repeated",
              "report: 1 line(s) sent to the entry" in out and rep["done"].get("L0001") == "pushed", out + err)
        rc, out, err = run([AL, "--tick", "--now", "2026-11-23T09:10"], env=envr2)
        check("report: nothing is sent twice", "report:" not in out, out + err)
        (hr / "inbox" / "study.md").write_text("- [ ] L0003 one more\n", encoding="utf-8")
        (hr / "ledger.md").write_text("# Ledger\n\n- L0003 | dispatched:study | 2026-11-23T09:00:00 | one more | ev: \n", encoding="utf-8")
        rc, out, err = run([AL, "--tick", "--now", "2026-11-23T10:30"], env=envr2)
        check("report: an item still waiting in the topic's inbox is not called stalled (the tick starts the topic instead)",
              "report:" not in out, out + err)
        # worker rows: gathering is done by a one-off worker, not by the topic's long conversation
        hw = tmp / "home-worker"
        for d in ("entry", "managers/study", "inbox", "state"):
            (hw / d).mkdir(parents=True)
        (hw / "config.json").write_text(json.dumps({"routing": "live", "worker": {"model": "haiku", "config_dir": str(tmp / "second")},
                                                    "wake_limits": {"per_day": 2, "min_gap_min": 0}}), encoding="utf-8")
        (hw / "alarms.md").write_text("| id | when | to | text |\n|---|---|---|---|\n"
                                      "| A05 | daily 08:10 | study | [worker] check the course page for new files |\n"
                                      "| A06 | daily 08:10 | study | [worker] [chrome] read the mailbox |\n"
                                      "| A07 | daily 08:10 | study | [worker] third one, over the daily limit |\n", encoding="utf-8")
        agw = tmp / "agents-worker.json"
        agw.write_text("[]", encoding="utf-8")
        envw = {"SBK_HOME": str(hw), "SBK_VAULT": "", "ANTHROPIC_API_KEY": "", "SBK_AGENTS_JSON": str(agw),
                "SBK_SESSION_DRYRUN": "1", "CLAUDE_CONFIG_DIR": str(tmp / "cc-worker")}
        rc, out, err = run([AL, "--tick", "--now", "2026-11-23T08:12"], env=envw)
        briefs = sorted(p.name for p in (hw / "workers").glob("*.md")) if (hw / "workers").is_dir() else []
        b5 = (hw / "workers" / "A05-20261123-0812.md").read_text(encoding="utf-8") if "A05-20261123-0812.md" in briefs else ""
        inbox_w = (hw / "inbox" / "study.md").read_text(encoding="utf-8") if (hw / "inbox" / "study.md").exists() else ""
        check("worker row: a one-off worker is started with a brief, on the worker model, and the topic's inbox stays empty",
              "worker started for study on the second account" in out and "-p --name study-A05" in out and "--model haiku" in out
              and "check the course page" in b5 and "[worker]" not in b5.split("\n")[0].replace("[alarm A05]", "")
              and "task.md" in b5 and "deliver study" in b5 and "A05" not in inbox_w, out + err + b5[:300])
        check("worker row: [chrome] adds the browser flag and stays on the main account",
              "study-A06" in out and "--chrome" in out and out.count("on the second account") == 1, out + err)
        check("worker row: over the daily limit the work waits in the topic's inbox like any alarm",
              briefs == ["A05-20261123-0812.md", "A06-20261123-0812.md"] and "[alarm A07]" in inbox_w, str(briefs) + inbox_w + out + err)
        wst = json.loads((hw / "state" / "workers.json").read_text(encoding="utf-8"))
        wst["A05"]["pid"] = os.getpid()
        (hw / "state" / "workers.json").write_text(json.dumps(wst), encoding="utf-8")
        (hw / "config.json").write_text(json.dumps({"routing": "live", "wake_limits": {"per_day": 9, "min_gap_min": 0}}), encoding="utf-8")
        rc, out, err = run([AL, "--fire", "A05"], env=envw)
        check("worker row: not started twice while the last one is still running", "still running" in out, out + err)
        # --loop: the tick without an OS scheduler; one loop per folder
        hl = tmp / "home-loop"
        (hl / "state").mkdir(parents=True)
        (hl / "alarms.md").write_text("| id | when | to | text |\n|---|---|---|---|\n| A01 | daily 00:00 | entry | loop test |\n", encoding="utf-8")
        envl = {"SBK_HOME": str(hl), "SBK_VAULT": "", "ANTHROPIC_API_KEY": "", "SBK_AGENTS_JSON": str(agw),
                "SBK_SESSION_DRYRUN": "1", "CLAUDE_CONFIG_DIR": str(tmp / "cc-worker"), "SBK_LOOP_MAX": "2"}
        rc, out, err = run([AL, "--loop", "--every", "1"], env=envl)
        check("loop: ticks run as separate processes and the marker is removed when the loop ends",
              rc == 0 and (hl / "state" / "alarms.json").exists()
              and not (hl / "state" / "tick-loop.json").exists(), out + err)
        (hl / "state" / "tick-loop.json").write_text(json.dumps({"pid": os.getpid(), "since": "x"}), encoding="utf-8")
        rc, out, err = run([AL, "--loop", "--every", "1"], env=envl)
        check("loop: a second loop for the same folder exits at once", rc == 0 and "already running" in out, out + err)
        # import_existing.py: an existing tracker, reminders and topic files are brought in, nothing old is touched
        hi = tmp / "home-import"
        (hi / "managers" / "maintenance").mkdir(parents=True)
        (hi / "config.json").write_text(json.dumps({"vault": "V:/notes"}), encoding="utf-8")
        (hi / "ledger.md").write_text("# Ledger\n\n- L0001 | open | 2026-11-20T08:00:00 | there before | ev: \n", encoding="utf-8")
        oldtask = tmp / "old-study-task.md"
        oldtask.write_text("old state\n", encoding="utf-8")
        plan = {"expect_rows": 3,
                "topics": [{"name": "study", "keywords": "course, exam", "scope": "two courses", "old_task": str(oldtask)}],
                "items": [{"old": "T12", "text": "hand in the report", "said": "記得交報告", "done_when": "upload page shows it", "ts": "2026-11-23T21:45:00"},
                          {"old": "T13", "keep": False, "text": "done 11-24, receipt mail"},
                          {"old": "T14", "text": "summarise chapter 9", "to": "study"}],
                "alarms": [{"id": "A05", "when": "daily 08:10", "to": "study", "text": "[worker] check the course page"}]}
        pf = tmp / "plan.json"
        pf.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
        IMP = KIT / "scripts" / "import_existing.py"
        envi = {"SBK_HOME": str(hi), "SBK_VAULT": "", "ANTHROPIC_API_KEY": ""}
        rc, out, err = run([IMP, pf], env=envi)
        check("import: the dry run says what would be written and writes nothing",
              rc == 0 and "DRY RUN" in out and "2 new item(s) + 1 record(s)" in out and not (hi / "managers" / "study").exists()
              and not (hi / "state" / "import-map.json").exists() and "T12" not in (hi / "ledger.md").read_text(encoding="utf-8"), out + err)
        rc, out, err = run([IMP, pf, "--apply"], env=envi)
        led = (hi / "ledger.md").read_text(encoding="utf-8")
        imap = json.loads((hi / "state" / "import-map.json").read_text(encoding="utf-8")) if (hi / "state" / "import-map.json").exists() else {}
        stask = (hi / "managers" / "study" / "task.md").read_text(encoding="utf-8") if (hi / "managers" / "study" / "task.md").exists() else ""
        check("import: every old row is accounted for (item or record), with the user's words and the old date kept",
              rc == 0 and imap == {"T12": {"new": "L0002"}, "T13": {"record": "done 11-24, receipt mail"}, "T14": {"new": "L0003"}}
              and "- L0002 | open | 2026-11-23T21:45:00 | hand in the report (was T12); done when: upload page shows it; said: \"記得交報告\"" in led
              and "- L0003 | dispatched:study |" in led and "there before" in led, out + err + led)
        check("import: the topic gets its folder, a task.md that points at the old state, a route, its inbox line and the alarm row",
              str(oldtask) in stask and "two courses" in (hi / "managers" / "study" / "CLAUDE.md").read_text(encoding="utf-8")
              and "| course, exam | study | managers/study/task.md |" in (hi / "routes.md").read_text(encoding="utf-8")
              and "{{manager" not in (hi / "routes.md").read_text(encoding="utf-8")
              and "L0003" in (hi / "inbox" / "study.md").read_text(encoding="utf-8")
              and "| A05 | daily 08:10 | study | [worker] check the course page |" in (hi / "alarms.md").read_text(encoding="utf-8")
              and oldtask.read_text(encoding="utf-8") == "old state\n", out + err)
        rc, out, err = run([IMP, pf, "--apply"], env=envi)
        check("import: running it again adds nothing twice",
              rc == 0 and "0 new item(s) + 0 record(s) + 3 imported before" in out and "alarms.md: 0 new row(s)" in out
              and (hi / "ledger.md").read_text(encoding="utf-8") == led, out + err)
        plan["expect_rows"] = 4
        plan["alarms"][0]["when"] = "13 8 * * *"
        pf.write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")
        rc, out, err = run([IMP, pf, "--apply"], env=envi)
        check("import: a plan that drops a row or has an unreadable time is refused whole",
              rc == 2 and "has 4 rows, the plan accounts for 3" in out and "when not readable" in out
              and (hi / "ledger.md").read_text(encoding="utf-8") == led, out + err)
        hk = tmp / "home-import-ids"
        (hk / "managers" / "maintenance").mkdir(parents=True)
        (hk / "config.json").write_text(json.dumps({"vault": ""}), encoding="utf-8")
        pk = tmp / "plan-ids.json"
        pk.write_text(json.dumps({"keep_ids": True, "items": [
            {"old": "L0412", "text": "send the form"}, {"old": "L0420", "keep": False, "text": "done, receipt"},
            {"old": "G01", "text": "a group of small jobs"}, {"old": "L0405", "text": "book the room"}]}), encoding="utf-8")
        rc, out, err = run([IMP, pk, "--apply"], env={"SBK_HOME": str(hk), "SBK_VAULT": "", "ANTHROPIC_API_KEY": ""})
        ledk = (hk / "ledger.md").read_text(encoding="utf-8") if (hk / "ledger.md").exists() else ""
        imk = json.loads((hk / "state" / "import-map.json").read_text(encoding="utf-8")) if (hk / "state" / "import-map.json").exists() else {}
        check("import: keep_ids leaves an old id of the tracker's form as it is and numbers the others after the highest old one, a record's id included",
              rc == 0 and imk.get("L0412") == {"new": "L0412"} and imk.get("L0405") == {"new": "L0405"} and imk.get("G01") == {"new": "L0421"}
              and "- L0412 | open |" in ledk and "send the form (was" not in ledk and "a group of small jobs (was G01)" in ledk, out + err + ledk)
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
            "stop_evidence": "log", "vault_snapshot": "warn", "usage_warn": "off", "inbox_notice": "off",
            "level_notice": "warn", "learn_notice": "warn"}, cfg)
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
        learn_loop_tests(tmp, cfg)
        v8_tests(tmp, cfg)

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
        st = (KIT / "docs" / "SETUP.md").read_text(encoding="utf-8")
        a = st.find("### `SURFACE` = app")
        b = st.find("### `SURFACE` = terminal")
        app = st[a:b] if 0 <= a < b else ""
        term = st[b:st.find("## Step 5b")] if b >= 0 else ""
        check("setup: surface is detected from CLAUDE_CODE_ENTRYPOINT, user answer wins",
              "CLAUDE_CODE_ENTRYPOINT" in st and "claude-desktop" in st and "`cli`" in st)
        check("setup: App branch gives the Code tab / Open folder steps and makes no shortcut file",
              "**Code**" in app and "**Open folder…**" in app and "**Local**" in app
              and not any(w in app for w in ("chmod", "@echo off", "#!/bin/sh")))
        check("setup: terminal branch keeps the shortcut and the plain cd + claude way",
              "@echo off" in term and "#!/bin/sh" in term and "claude --continue" in term and "cd \"<VAULT>\"" in term)
        check("setup: Step 6 and 7 do not assume a shortcut or claude -p for App users",
              "**+ New**" in st and st.count("**Open folder…**") >= 4)
        # 0.2.9: the front page is short; the sections moved to docs pages (guide = how to use, how-it-works = the Mermaid picture)
        for lang, readme, hiw in (("en", KIT / "docs" / "GUIDE.md", KIT / "docs" / "HOW-IT-WORKS.md"),
                                  ("zh", KIT / "docs" / "zh-TW" / "指南.md", KIT / "docs" / "zh-TW" / "運作原理.md")):
            rd = readme.read_text(encoding="utf-8")
            hw = hiw.read_text(encoding="utf-8")
            mm = hw[hw.find("```mermaid"):hw.find("```", hw.find("```mermaid") + 10)]
            check("guide %s: both ways in (App steps + terminal), diagram names both" % lang,
                  "**Open folder…**" in rd and "**Code**" in rd and "`claude`" in rd and ("Open folder" if lang == "en" else "選筆記資料夾") in mm and "claude" in mm
                  and "desktop launcher" not in mm)
        svg = (KIT / "docs" / "diagrams" / "00-basic.svg").read_text(encoding="utf-8")
        check("diagram 00-basic: names the App way and the terminal way, no desktop launcher",
              "Open folder" in svg and "or terminal: claude" in svg and "desktop launcher" not in svg)

        # ---- docs: plan labels, tracker wording, fixed sessions, wake choice, hook list ----
        zh_files = [KIT / "README.zh-TW.md"] + sorted((KIT / "docs" / "zh-TW").glob("*.md")) + sorted((KIT / "templates").glob("*.md")) \
            + sorted((KIT / "skills").rglob("*.md")) + sorted((KIT / "docs" / "diagrams").glob("*.svg")) + sorted((KIT / "docs" / "diagrams" / "readme").glob("*.zh.svg"))
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
        for p in (KIT / "README.md", KIT / "README.zh-TW.md", KIT / "docs" / "ADVANCED.md", KIT / "docs" / "zh-TW" / "進階功能.md",
                  KIT / "docs" / "HOW-IT-WORKS.md", KIT / "docs" / "zh-TW" / "運作原理.md"):
            t = p.read_text(encoding="utf-8")
            for blk in t.split("```mermaid")[1:]:
                head = blk[:200]
                if not (head.lstrip().startswith("---") and any(w in head for w in ("Basic", "Full", "基本款", "完整款"))):
                    mm_untitled.append(p.name)
        check("docs: every Mermaid picture has a Basic/Full title", not mm_untitled, ", ".join(mm_untitled))
        hooks8 = ("vault_guard", "read_whole", "requests_reinject", "stop_evidence", "level_notice", "learn_notice",
                  "inbox_notice", "usage_warn")
        for p in (KIT / "docs" / "SAFETY.md", KIT / "docs" / "zh-TW" / "安全與資料.md", KIT / "docs" / "ADVANCED.md", KIT / "docs" / "zh-TW" / "進階功能.md"):
            t = p.read_text(encoding="utf-8")
            listed = [h for h in hooks8 if ("- `%s`" % h) in t]
            check("docs %s: one line per hook, all 8, with Basic on/off" % p.name, len(listed) == 8 and t.count("Basic: o") + t.count("基本款：") >= 8, listed)
        hj = (H / "hooks.json").read_text(encoding="utf-8")
        hjd = json.loads(hj)["hooks"]
        check("hooks: learn_notice runs at session start (startup, resume, compact) and on every message",
              all(any("learn_notice.py" in x["command"] for x in g["hooks"]) for g in hjd["SessionStart"])
              and any("learn_notice.py" in x["command"] for g in hjd["UserPromptSubmit"] for x in g["hooks"]))
        check("hooks: the 8 hooks in the docs are the hooks the plugin runs (hooks.json names each)",
              all((H / (h + ".py")).exists() and (h + ".py") in hj for h in hooks8))
        ex = (KIT / "templates" / "settings.hooks.example.json").read_text(encoding="utf-8")
        check("hooks: the settings example for a manual install runs the same 8 hooks",
              all((h + ".py") in ex for h in hooks8), [h for h in hooks8 if (h + ".py") not in ex])
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
        faq_en = (KIT / "docs" / "FAQ.md").read_text(encoding="utf-8")
        faq_zh = (KIT / "docs" / "zh-TW" / "常見問題.md").read_text(encoding="utf-8")
        check("faq: a costs section saying the 5-minute check uses no quota, limits by plan, computer off (both languages)",
              "## Costs" in faq_en and "uses **none** of your limit" in faq_en and "## 費用" in faq_zh and "**完全不用**額度" in faq_zh
              and "asleep" in faq_en and "睡眠" in faq_zh)
        check("learning loop: the 和 AI 協作 note is in the templates and read before acting",
              (KIT / "templates" / "和AI協作.md").exists() and "和 AI 協作" in (KIT / "templates" / "CLAUDE.md").read_text(encoding="utf-8")
              and "和 AI 協作" in (KIT / "templates" / "AGENTS.md").read_text(encoding="utf-8")
              and "learn.py trend" in (KIT / "templates" / "maintenance-CLAUDE.md").read_text(encoding="utf-8")
              and "learn.py group" in (KIT / "templates" / "maintenance-CLAUDE.md").read_text(encoding="utf-8")
              and "--replay" in (KIT / "templates" / "maintenance-CLAUDE.md").read_text(encoding="utf-8"))
        firsts = {n: (KIT / "templates" / n).read_text(encoding="utf-8").lower()
                  for n in ("CLAUDE.md", "AGENTS.md", "entry-CLAUDE.md", "manager-CLAUDE.md", "maintenance-CLAUDE.md")}
        check("templates: checking the second brain first (preferences first) is step one in every rules template",
              all("check the second brain first" in t or "check the notes first" in t for t in firsts.values())
              and "step one of every task: check the second brain first" in firsts["CLAUDE.md"]
              and "step one of every task: check the second brain first" in firsts["AGENTS.md"]
              and "sorted preferences are already in this conversation" in firsts["CLAUDE.md"]
              and "sorted preferences are already in this conversation" in firsts["AGENTS.md"]
              and "sorted preferences first" in firsts["entry-CLAUDE.md"],
              [n for n, t in firsts.items() if "check the second brain first" not in t])
        se = (KIT / "docs" / "SETUP.md").read_text(encoding="utf-8")
        check("setup: six questions, the plan sets starting values, outside resources are ticked",
              "ask six things" in se and "Which Claude plan" in se and "Tick any, or none" in se and "max_sessions" in se and "可免費申請" in se)
        check("docs: the entry sends work into running sessions; inbox fallback is described",
              "conversation of the topic that owns it" in adv and "直接把事送進負責那件事的主題對話" in advz
              and "session.py check" in se and "inbox" in se)
        # ---- language split: what Claude reads exists only in English; what the user sees is in their language ----
        claude_only = [KIT / "docs" / "SETUP.md", KIT / "docs" / "MULTI-TOOL.md"] + [
            KIT / "templates" / n for n in ("CLAUDE.md", "AGENTS.md", "entry-CLAUDE.md", "manager-CLAUDE.md",
                                            "maintenance-CLAUDE.md", "task.md", "筆記格式.md")] \
            + sorted((KIT / "skills").rglob("SKILL.md")) + sorted((KIT / "commands").glob("*.md"))
        cjk = re.compile(r"[一-鿿]")
        heavy = []
        for p in claude_only:
            t = p.read_text(encoding="utf-8")
            prose = re.sub(r"`[^`]*`|「[^」]*」|\"[^\"]*\"|\([^)]*\)|（[^）]*）|\|[^\n]*\|", "", t)  # names, quotes, tables
            n = sum(1 for l in prose.splitlines() if len(cjk.findall(l)) > 12)
            if n:
                heavy.append("%s: %d lines" % (p.relative_to(KIT), n))
        check("language: files only Claude reads are written in English (folder names and quoted words aside)",
              not heavy, "; ".join(heavy))
        check("language: no Chinese copies of Claude-only docs (SETUP, MULTI-TOOL); the user-facing pages stay",
              not (KIT / "docs" / "zh-TW" / "SETUP.md").exists() and not (KIT / "docs" / "zh-TW" / "參考-多工具分工.md").exists()
              and (KIT / "README.zh-TW.md").exists() and (KIT / "docs" / "zh-TW" / "進階功能.md").exists())
        check("language: SETUP and the rules template say replies and notes are in the user's language, internal work in English",
              "user's language" in se and "internal" in se.lower()
              and "user's language" in firsts["CLAUDE.md"].replace("’", "'") and "english" in firsts["CLAUDE.md"])
        broken = []
        for p in [KIT / "README.md", KIT / "README.zh-TW.md"] + sorted((KIT / "docs").rglob("*.md")) \
                + sorted((KIT / "skills").rglob("*.md")) + sorted((KIT / "commands").glob("*.md")):
            for link in re.findall(r"\]\(([^)\s]+)\)", p.read_text(encoding="utf-8")):
                if re.match(r"[a-z]+:", link) or link.startswith("#"):
                    continue
                target = (p.parent / link.split("#")[0]).resolve()
                if not target.exists():
                    broken.append("%s -> %s" % (p.relative_to(KIT), link))
        check("docs: every relative link points to a file that exists", not broken, "; ".join(broken))
        zr = (KIT / "README.zh-TW.md").read_text(encoding="utf-8")
        # ---- 0.2.9: picture-first short front page ----
        pics = ("a-what-you-get", "b-install", "c-basic-vs-full", "d-how-it-learns")
        for lang, rp_ in (("en", KIT / "README.md"), ("zh", KIT / "README.zh-TW.md")):
            t9 = rp_.read_text(encoding="utf-8")
            n9 = len(t9.splitlines())
            check("front page %s: 60-90 lines, the four pictures in order, install sentence in one code block, no programming needed, Code tab" % lang,
                  60 <= n9 <= 90 and [t9.find("diagrams/readme/%s.%s.png" % (p9, lang)) for p9 in pics] == sorted(t9.find("diagrams/readme/%s.%s.png" % (p9, lang)) for p9 in pics)
                  and all(("diagrams/readme/%s.%s.png" % (p9, lang)) in t9 for p9 in pics)
                  and t9.count("```") == 2 and "docs/SETUP.md" in t9 and "**Code**" in t9
                  and ("No programming needed" in t9 if lang == "en" else "不用會寫程式" in t9), n9)
            check("front page %s: plan list keeps Ultra; links row reaches guide, safety, faq, install, how-it-works" % lang,
                  "Ultra" in t9 and all(x in t9 for x in (("docs/GUIDE.md", "docs/SAFETY.md", "docs/FAQ.md", "docs/INSTALL.md", "docs/HOW-IT-WORKS.md") if lang == "en"
                                                           else ("docs/zh-TW/指南.md", "docs/zh-TW/安全與資料.md", "docs/zh-TW/常見問題.md", "docs/zh-TW/安裝.md", "docs/zh-TW/運作原理.md"))))
        bad9 = []
        for p9 in pics:
            for lang in ("en", "zh"):
                sv9 = KIT / "docs" / "diagrams" / "readme" / ("%s.%s.svg" % (p9, lang))
                pn9 = sv9.with_suffix(".png")
                if not sv9.exists() or not pn9.exists():
                    bad9.append("missing %s.%s" % (p9, lang))
                    continue
                tx = sv9.read_text(encoding="utf-8")
                sizes = [float(x) for x in re.findall(r'font-size="([0-9.]+)"', tx)]
                if 'viewBox="0 0 880 ' not in tx or not sizes or min(sizes) < 14 or 'stroke-width="3"' not in tx or re.search(r"\b[A-Za-z]:\\|@|Users", tx):
                    bad9.append("%s.%s: width/font/border/personal" % (p9, lang))
                if lang == "zh" and not re.search(r"[一-鿿]", tx):
                    bad9.append("%s.zh has no Chinese" % p9)
                if lang == "en" and re.search(r"[一-鿿]", tx):
                    bad9.append("%s.en has Chinese" % p9)
        check("front page pictures: 8 SVG + PNG, 880 wide, text >= 14 px, opaque background with a border, zh on zh and en on en, no paths or addresses",
              not bad9, "; ".join(bad9))
        check("readme zh: the install sentence uses docs/SETUP.md and asks for Chinese replies",
              "照 docs/SETUP.md 幫我設定" in zr and "zh-TW/SETUP" not in zr)
        mt = (KIT / "docs" / "MULTI-TOOL.md").read_text(encoding="utf-8")
        check("multi-tool: rules by kind of work, table filled by the user's Claude, monthly re-check",
              "## Kinds of work" in mt and "## Filling and re-checking the table" in mt
              and "Kind of work" in (KIT / "templates" / "channels.md").read_text(encoding="utf-8"))
        # ---- 0.2.7: reviewed principles, starter preferences, general skills ----
        T7 = KIT / "templates"
        cm = (T7 / "CLAUDE.md").read_text(encoding="utf-8")
        stance = ("Work for the user's maximum benefit within the real rules", "Do not add limits the user did not ask for",
                  "Add no limits or decisions beyond the rules and what the user asked", "Judge by what got done, not by what was said",
                  "write only the strongest true parts", "Never invent sources, records, completion status",
                  "name the rule or the tool result that blocks which action")
        check("principles: the 7 core-stance rules are in templates/CLAUDE.md under one heading",
              "## Core stance" in cm and all(s in cm for s in stance), [s for s in stance if s not in cm])
        fours = ("Saying done when it is not:", "Fixing one and dropping another:", "Pointing out and stopping:",
                 "Not reading available data:", "first name the class of error")
        check("principles: the four failures (and 'when corrected') are in templates/CLAUDE.md, each once",
              "## The four failures that matter most" in cm and all(cm.count(s) == 1 for s in fours), [(s, cm.count(s)) for s in fours])
        check("principles: the block stays under 100 lines (SETUP step 2 check)", len(cm.splitlines()) < 100, len(cm.splitlines()))
        dup = [l for l in cm.splitlines() if l.startswith("- ") and cm.count(l) > 1]
        check("principles: no bullet appears twice", not dup, dup)

        tag_zh, tag_en = "（來自原作者，可刪）", "(from the original author; delete if you like)"
        for label, fn, tag in (("zh", "和AI協作.md", tag_zh), ("en", "和AI協作.en.md", tag_en)):
            tx = (T7 / fn).read_text(encoding="utf-8")
            starter_head = [l for l in tx.splitlines() if l.startswith("## ") and ("起始偏好" in l or "Starter preferences" in l)]
            starters = [l for l in tx.splitlines() if l.startswith("- ") and l.rstrip().endswith(tag)]
            untagged = [l for l in tx[tx.find(starter_head[0]):tx.find("\n## ", tx.find(starter_head[0]) + 3)].splitlines()
                        if l.startswith("- ") and not l.rstrip().endswith(tag)] if starter_head else ["no starter heading"]
            check("starter preferences (%s): 12 lines, each tagged as from the original author, under their own heading" % label,
                  len(starters) == 12 and starter_head and not untagged, (len(starters), starter_head, untagged))
            first = tx.find("## 已整理的偏好") if label == "zh" else tx.find("## Sorted preferences")
            check("starter preferences (%s): the user's own preference heading comes first, so `learn.py pref` writes there" % label,
                  0 <= first < tx.find(starter_head[0]) < tx.find("## 紀錄" if label == "zh" else "## Log"))
        # the starter lines reach the conversation, and a preference the user adds goes above them
        for label, fn, tag in (("zh", "和AI協作.md", tag_zh), ("en", "和AI協作.en.md", tag_en)):
            sv = tmp / ("starter-" + label)
            sn = sv / "00-09 系統與索引" / "03 和 AI 協作" / "03-01 和 AI 協作.md"
            sn.parent.mkdir(parents=True)
            (sv / ".sbk-vault").write_text("", encoding="utf-8")
            sn.write_text((T7 / fn).read_text(encoding="utf-8").replace("{{date}}", "2026-12-01"), encoding="utf-8")
            sh = tmp / ("starter-home-" + label)
            sh.mkdir()
            (sh / "config.json").write_text(json.dumps({"vault": str(sv), "language": label}), encoding="utf-8")
            senv = {"SBK_HOME": str(sh), "SBK_VAULT": str(sv), "ANTHROPIC_API_KEY": ""}
            rc, out, err = run([KIT / "hooks" / "learn_notice.py"], {"cwd": str(sv), "hook_event_name": "SessionStart", "source": "startup"}, senv)
            check("starter preferences (%s): a new conversation gets all 12 starter lines (none cut by the size cap) and the tag" % label,
                  rc == 0 and out.count(tag) == 12 and "more in the note" not in out and "the starter ones the kit ships" in out, out[-300:] + err)
            rc, out, err = run([KIT / "entry" / "learn.py", "pref", "reply-length", "Keep replies to three lines.", "--now", "2026-12-10"], env=senv)
            tx = sn.read_text(encoding="utf-8")
            check("starter preferences (%s): a preference the user adds is written above the starter ones" % label,
                  rc == 0 and tx.find("- Keep replies to three lines.") > 0 and tx.find("- Keep replies to three lines.") < tx.find(tag), tx[:600])
            rc, out, err = run([KIT / "entry" / "learn.py", "stats", "--now", "2026-12-10"], env=senv)
            try:
                stx = json.loads(out)
            except Exception:
                stx = {}
            check("starter preferences (%s): stats count the user's own (1) apart from the 12 starter ones" % label,
                  stx.get("preferences") == 1 and stx.get("starter_preferences") == 12, out + err)
            rc, out, err = run([KIT / "entry" / "learn.py", "add", "correction", "kind-a", "words", "--now", "2026-12-11"], env=senv)
            added = sn.read_text(encoding="utf-8").rstrip().splitlines()[-1]
            check("starter preferences (%s): learn.py add writes the log line in the note's language" % label,
                  rc == 0 and (("| 糾正 |" in added) if label == "zh" else ("| correction |" in added)), added)
        # the English variant is a valid note too
        ev = tmp / "starter-en-lint"
        for d in (ev / "scripts", ev / "00-09 系統與索引" / "03 和 AI 協作"):
            d.mkdir(parents=True, exist_ok=True)
        (ev / ".sbk-vault").write_text("", encoding="utf-8")
        (ev / "00-09 系統與索引" / "03 和 AI 協作" / "03-01 和 AI 協作.md").write_text(
            (T7 / "和AI協作.en.md").read_text(encoding="utf-8").replace("{{date}}", "2026-12-01"), encoding="utf-8")
        shutil.copy(str(KIT / "scripts" / "vault_lint.py"), str(ev / "scripts" / "vault_lint.py"))
        rc, out, _ = run([ev / "scripts" / "vault_lint.py", "--root", ev], env=env)
        check("starter preferences (en): the English note passes the vault lint with no errors", rc == 0 and "0 errors" in out and "RESULT: PASS" in out, out[-300:])

        # nothing of the original author's private wording is in the kit (fingerprints, not the wording)
        import hashlib
        fp_file = KIT / "scripts" / "original-text.sha"
        fps = set(l.strip() for l in fp_file.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#"))

        def window_hits(paths, fps, w=10):
            hits = []
            for p in paths:
                try:
                    s = re.sub(r"\s+", "", p.read_text(encoding="utf-8"))
                except Exception:
                    continue
                for i in range(0, len(s) - w + 1):
                    if hashlib.sha1(s[i:i + w].encode("utf-8")).hexdigest()[:16] in fps:
                        hits.append("%s@%d" % (p.name, i))
                        break
            return hits
        ctrl = tmp / "fp-control.md"
        sample = "The quick brown fox jumps over the lazy dog, again and again."
        ctrl.write_text("noise before " + sample + " noise after", encoding="utf-8")
        cs = re.sub(r"\s+", "", sample)
        cfps = {hashlib.sha1(cs[i:i + 10].encode("utf-8")).hexdigest()[:16] for i in range(0, len(cs) - 10 + 1, 6)}
        check("original wording scan: control (a known 15-character copy is found, a clean file is not)",
              window_hits([ctrl], cfps) and not window_hits([KIT / "LICENSE"], cfps))
        kit_text = [p for p in KIT.rglob("*") if p.is_file() and ".git" not in p.relative_to(KIT).parts
                    and "__pycache__" not in p.relative_to(KIT).parts and p.suffix not in (".png", ".pyc", ".sha")]
        check("original wording scan: %d fingerprints, no file in the kit holds the original author's wording" % len(fps),
              len(fps) > 100 and not window_hits(kit_text, fps), window_hits(kit_text, fps))

        general = ("evidence-check", "outward-docs", "blind-three-way", "full-reader")
        bad_sk = []
        for n in general:
            f = KIT / "skills" / n / "SKILL.md"
            if not f.exists():
                bad_sk.append(n + ": missing")
                continue
            tx = f.read_text(encoding="utf-8")
            m = re.match(r"---\nname: (.+)\ndescription: (.+)\n---\n", tx.replace("\r\n", "\n"))
            if not m or m.group(1).strip() != n or not m.group(2).startswith("Use ") or len(m.group(2)) < 60:
                bad_sk.append(n + ": frontmatter")
        check("skills: the 4 general skills exist, name = folder, a one-line description starting 'Use'", not bad_sk, bad_sk)
        rd_en = (KIT / "docs" / "GUIDE.md").read_text(encoding="utf-8")
        rd_zh = (KIT / "docs" / "zh-TW" / "指南.md").read_text(encoding="utf-8")
        check("guide (en + zh): the section on what is installed vs what grows names the principles, the starter preferences and the 4 skills",
              all(n in rd_en and n in rd_zh for n in general) and "starter preferences" in rd_en.lower() and "起始偏好" in rd_zh
              and "（來自原作者，可刪）" in rd_zh and "(from the original author" in rd_en)
        se7 = (KIT / "docs" / "SETUP.md").read_text(encoding="utf-8")
        check("setup: picks the zh or en note variant by language, tells the user about the starter preferences",
              "templates/和AI協作.md" in se7 and "templates/和AI協作.en.md" in se7 and "starter preferences" in se7)
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
