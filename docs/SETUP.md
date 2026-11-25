# SETUP - instructions for the configuring Claude

This file is written **for you, Claude**, not for the user. The user asked you to set up second-brain-kit. They may not be technical: you do the work; they answer four short questions and say yes or no to changes on their system. This is the only place that lists the questions and steps (`/sbk-setup` and the `setup-second-brain` skill just point here); `docs/zh-TW/SETUP.md` has the same steps in Traditional Chinese.

**You decide whether to install Basic or Full** (Step 0.4), from one question and what this computer shows; you say the choice and the reason in one line, and the user may override it.
- **Basic**: one main Claude session that works directly in the notes folder; the notes folder with only the areas the user needs; one work list (the ledger), used by you, never typed by the user; safety checks; short general principles.
- **Full** = Basic + only the Advanced parts the facts call for (topic sessions, reminders, the other-tool guide), switched on in Step 5b with the steps in [ADVANCED.md](ADVANCED.md).

Everything else stays off. After setup, a weekly check (`level_check.py`) measures whether another part would help; you then offer it as one yes/no question.

Words used below:
- `KIT` - the folder that contains `.claude-plugin/plugin.json` with `"name": "second-brain-kit"`. Installed as a plugin it is `${CLAUDE_PLUGIN_ROOT}` (set inside plugin hooks and commands; in this session search the plugin cache under `~/.claude/plugins` for that file). Cloned by hand it is the clone folder.
- `SBK_HOME` - `~/.claude/sbk` (the work list, logs, settings of the kit).
- `VAULT` - the notes folder the user chooses (default `~/second-brain`).
- Paths: use forward slashes or quoted paths on Windows. Python: `python3`, `python` or `py`, whichever runs Python 3.

Rules while you work:
- Ask before anything that edits `~/.claude/settings.json`, `~/.claude/CLAUDE.md`, the system scheduler, or any file the user already had. Never overwrite an existing file; show the difference and get a yes.
- Nothing is pushed to a git remote, no message is sent, and no note is given to another AI tool. Do not tell the user it is "offline": Claude itself is an online service.
- Small reversible choices are yours (folder names, test names, a placeholder git identity): pick one and say which in the report. Ask only what only the user knows or must allow.
- Each step ends with a **Check**. Run it; continue only when it passes. If it fails, fix the cause and run it again; never report a step as done that you did not check.
- Report every step with exactly one of these: **done** / **not enabled** (an option the user did not want) / **n.a.** (does not apply here) / **needs you** (only the user can do it; say exactly what) / **not verified** (could not be checked; say why).

---

## Step 00 - Get the kit (skip if `KIT` is already on this computer)

The user may have pasted only the sentence from the README ("Install second-brain-kit from https://github.com/0Smallcat0/second-brain-kit and set me up by its docs/SETUP.md ..."). That sentence is their request to install, so do not ask again.
1. Run `claude plugin marketplace add 0Smallcat0/second-brain-kit`, then `claude plugin install second-brain-kit@second-brain-kit` (the command-line twins of `/plugin marketplace add ...` and `/plugin install ...`).
2. If the `claude` command cannot be run from here or the install fails: clone `https://github.com/0Smallcat0/second-brain-kit` into a new folder (for example `~/second-brain-kit-src`) and use it as `KIT`. Hooks then use Step 4's manual route.
3. Find `KIT` (see Words) and read this file from there before going on.

**Check:** `KIT/.claude-plugin/plugin.json` exists and says `second-brain-kit`; `claude plugin list` shows second-brain-kit (clone route: write down that you used it).

## Step 0 - Check the computer, ask four things, decide Basic or Full

1. Run `python --version` (or `python3` / `py`), `git --version`, `claude --version`. Python 3.8+ and git are needed.
   If one is missing, offer to install it ("OK if I install Python?") and after a yes do it: Windows `winget install -e --id Python.Python.3.12` / `winget install -e --id Git.Git`; macOS `xcode-select --install` (gives git and python3) or `brew install python git` if Homebrew exists; Linux the package manager. If it needs an administrator password or a click in an installer window, that part is **needs you**: tell the user exactly which window or command, then continue.
2. Ask in **one message**, in plain words, and wait:
   1. "Where should your notes live? I suggest `~/second-brain` (press Enter / say OK to accept)."
   2. "Which language should I use for notes and replies?"
   3. "What do you mainly want to use Claude for? For example studying, coding, a side project. 'Not sure yet' is fine."
   4. "How many different things are you working on at the same time right now (for example a course, a job, a project)? Any deadlines you want to be reminded of on time?"
   5. Optional, in the same message: "If you also use other AI tools (for example ChatGPT or Gemini), tell me in one sentence. If not, skip this: one Claude account is enough."
   Do not ask anything else, here or later in the setup (asking permission for a change on their system is not an extra question): no profile questions, no tool-by-tool list, no "Basic or Full?".
3. Create `SBK_HOME`. If `SBK_HOME/config.json` does not exist, copy `KIT/templates/config.json` there and fill `vault` (absolute path), `language`, `uses` (their words), `other_tools` (their sentence or empty). If it exists (a repair or second run), keep every value it has and only add missing keys from the template.
4. **Decide Basic or Full yourself.** Run `python KIT/scripts/level_check.py --install`. It only counts, on this computer: project folders in `~/.claude/projects` used in the last 14 days, and whether one conversation was summarised (compacted) two or more times in that time. It reads nothing else and changes nothing. Then:
   - **topic sessions** (ADVANCED A1) if the user named 3 or more ongoing things, or `active_projects_14d` is 3 or more, or `session_compacted_2plus_14d` is 1;
   - **reminders** (A2) if they mentioned a deadline or wanting to be reminded;
   - **the other-tool guide** (A5) only for tools they said they have;
   - none of these: **Basic**. Any of them: **Full** = Basic + exactly those parts.
   Disk space, operating system or the number of git commits decide whether a part *can* run, not whether it is needed: they are not reasons.
   Tell the user in **one line**, in their language, the choice, the reason with its numbers, and that they can say otherwise. For example: "I'll install Full (Basic + topic sessions + reminders): you are working on 4 things and have exam dates, and 5 project folders were used here in the last two weeks. Say 'just Basic' if you prefer." or "I'll install Basic: one main thing, no deadlines, no earlier Claude use here. I'll suggest more when the numbers show it would help." Then go on without waiting; if the user overrides, now or later in the setup, follow them.
   Write `level` (`basic` or `full`) and `level_reason` (that line) into `SBK_HOME/config.json`. If the user chose Basic although the facts called for parts, run `python KIT/scripts/level_check.py --decline <ids>` with those parts (`multi_session`, `alarms`, `multi_tool`) so the weekly check does not ask again for 4 weeks. If the output says `"partial": true`, the count stopped after 30 seconds: decide from what it found and the answers.
   Tools named in question 5 are recorded; they are connected only in Full (A5).

**Check:** `python -c "import json,os;c=json.load(open(os.path.expanduser('~/.claude/sbk/config.json'),encoding='utf-8'));print(c['level'],c['vault'],c['modes'])"` prints `basic` or `full` (the choice you told the user), the vault path, and the modes from the template (or the user's earlier modes on a repair).

## Step 1 - The work list tools

1. Create `SBK_HOME/bin` and `SBK_HOME/logs`.
2. Copy `KIT/entry/ledger.py`, `status.py`, `send.py`, `alarm.py` and `KIT/scripts/level_check.py` into `SBK_HOME/bin/` (`status.py` imports `ledger.py` and `send.py`; `/sbk-status` and the weekly check run `level_check.py`). Copy `KIT/templates/task.md` to `SBK_HOME/task-template.md`. Always copy; do not point at the plugin cache, whose path changes on update.

**Check** (works on a new or an existing work list):
1. `python SBK_HOME/bin/ledger.py list` - write the output down.
2. `python SBK_HOME/bin/ledger.py add "sbk setup check"` prints a new id; use the id it printed (do not assume `L0001`).
3. `python SBK_HOME/bin/ledger.py done <id> --evidence "setup step 1: add, done and list ran"` prints `<id> done`.
4. `ledger.py list` prints exactly what it printed in 1 (older items untouched), and `ledger.py list --all` shows `<id>` as done.

## Step 2 - General principles in `~/.claude/CLAUDE.md` (with consent)

`KIT/templates/CLAUDE.md` holds only general safety and evidence rules. It goes into the user's global `~/.claude/CLAUDE.md`, which affects every Claude session on this computer, so ask first: "OK to add a short block of general rules (check results before saying done, ask before deleting or publishing) to your Claude settings for all projects? The notes rules stay inside the notes folder."
1. If the user's language is not Traditional Chinese, translate the template faithfully (same structure and meaning, under 100 lines).
2. The block always sits between a line `<!-- sbk:begin -->` and a line `<!-- sbk:end -->`:
   - file missing: create it with just the block (markers included);
   - file exists, no markers: show the user the block, and after a yes append it at the end; never remove or reorder their text;
   - markers already there (second run): replace only what is between them, after showing the difference. Never add a second block.
3. A no is fine: mark the step **not enabled**; the notes rules still work from `VAULT/AGENTS.md`.

**Check:** the file contains exactly one `<!-- sbk:begin -->` and one `<!-- sbk:end -->`, the begin line comes first, and the block between them has fewer than 100 lines (or the step is **not enabled**).

## Step 3 - The notes folder (`VAULT`)

1. Create only these area folders (names from the table in `KIT/templates/筆記格式.md` section 1; keep the `NN-NN` numbers; translate the words only if the user wants another language):
   - `00-09 系統與索引` with `00 索引`, `01 規則`, `02 收件匣`;
   - the one or two areas that match what the user said in Step 0 (studying -> `20-29 學習與讀書`; coding or a side project -> `40-49 專案`; a job -> `30-39 工作與打工`; ...). "Not sure yet": no extra area; the first one is created when the first note needs it;
   - `90-99 封存`.
   Do not create empty category folders; categories are created when the first note needs one.
2. Copy into the vault, replacing `{{date}}` with today (`YYYY-MM-DD`). If a file already exists, keep it and compare instead (repair):
   - `templates/AGENTS.md` -> `VAULT/AGENTS.md`; and `VAULT/CLAUDE.md` containing exactly one line: `@AGENTS.md`
   - `templates/筆記格式.md` -> `VAULT/00-09 系統與索引/01 規則/01-01 筆記格式.md`
   - `templates/todo-for-me.md` -> `VAULT/00-09 系統與索引/02 收件匣/02-02 我要做的事.md`
   - an inbox note `VAULT/00-09 系統與索引/02 收件匣/02-01 收件匣.md` with valid frontmatter (`type: log`, `status: active`, a one-sentence summary, today's dates, `origin: agent-drafted`) and one line saying "Put anything not yet filed here."
   - `templates/sbk-protect.txt` -> `VAULT/.sbk-protect`; an empty file `VAULT/.sbk-vault`; `VAULT/.gitignore` with one line `__pycache__/` (Python leaves that folder next to the scripts)
   - `KIT/scripts/{vault_lint.py,gen_jdex.py,check_overwrite.py,pre-commit}` -> `VAULT/scripts/`; on macOS/Linux `chmod +x VAULT/scripts/pre-commit`.
3. If the user wants another language, translate the copied notes (keep field names and values such as `type: skill` exactly; the checker depends on them).
4. `python VAULT/scripts/gen_jdex.py --root VAULT` creates the index.
5. Git, local only (it keeps the history of changes; nothing is pushed):
   - `git init` in `VAULT` if `VAULT/.git` does not exist.
   - Check `git -C VAULT config user.name` and `git -C VAULT config user.email` **separately**. For each one that is empty, set it for this vault only (no `--global`): the user's name if they gave it, otherwise `second-brain`; email `second-brain@localhost`. Tell the user which you set.
   - `git -C VAULT config core.hooksPath scripts`.
   - First run: add the files by name and commit "Initial vault". Repair: commit only the files you added or changed.

**Check:**
1. `python VAULT/scripts/vault_lint.py --root VAULT` ends with `RESULT: PASS`.
2. `git -C VAULT log --oneline` shows the commit; `git -C VAULT config core.hooksPath` prints `scripts`.
3. The overwrite guard really runs, tested on a synthetic note in a test folder, never on a real note:
   1. Write down `git -C VAULT rev-parse HEAD`.
   2. Create `VAULT/.sbk-setup-test/test-note.md` with 20 lines (`test line 1` ... `test line 20`); `git -C VAULT add .sbk-setup-test/test-note.md`; `git -C VAULT commit -m "sbk setup test (removed again)"` - this must succeed.
   3. Overwrite the file with one line, `git add` it, commit again - this must be **refused** with `check_overwrite: commit refused`.
   4. Clean up: `git -C VAULT reset -q --soft <HEAD from 1>`, `git -C VAULT rm -r -q --cached .sbk-setup-test`, delete the folder `.sbk-setup-test`.
   5. `git -C VAULT rev-parse HEAD` equals the value from 1, `.sbk-setup-test` is gone, `git -C VAULT status --short` shows nothing from the test.
   If step 3 was not refused, fix `core.hooksPath` (and on macOS/Linux the `chmod`) and run the test again.

## Step 4 - Safety checks (hooks)

A hook is a small program Claude Code runs automatically at certain moments (before a command, when Claude says it is finished). It is not another AI. The kit's hooks never trap a session: if one breaks, it lets Claude carry on.

- **Plugin install:** `KIT/hooks/hooks.json` is active from the next session on. Check with `claude plugin list` that second-brain-kit is enabled.
- **Clone route:** copy `KIT/hooks/*.py` and `run.sh` to `SBK_HOME/hooks/`; then, after a yes (it edits settings), merge the `hooks` block of `KIT/templates/settings.hooks.example.json` into `~/.claude/settings.json`, replacing `__KIT__` with the `SBK_HOME/hooks` path. Merge, do not replace: keep every hook the user already has.

Every hook reads its mode from `SBK_HOME/config.json` -> `modes` (values: off, log, warn, ask, deny, block). Basic is the template's set; tell the user one plain line per hook:

| Hook | What the user notices | Basic mode |
|---|---|---|
| `vault_guard` | Claude asks before `git push`, skipping git checks, throwing away git work, deleting a whole folder, changing protected rule files, or shrinking a note to a fraction of it | ask |
| `read_whole` | Inside the notes folder Claude reads a note whole, not just the first lines (no effect outside the notes folder) | deny |
| `requests_reinject` | When a long conversation gets summarised, the user's own messages are put back word for word; a copy is kept in `~/.claude/sbk/requests/` on this computer | warn |
| `stop_evidence` | Notes in `~/.claude/sbk/logs/stop_evidence.log` when Claude said "done" after an edit without looking at the result; it does not interrupt | log |
| `usage_warn` | nothing (Advanced) | off |
| `inbox_notice` | nothing (Advanced, for topic sessions) | off |
| `level_notice` | At most once a week, in a session in the notes folder: if the measured numbers say another part would help (table in ADVANCED.md), Claude asks one yes/no question and quotes the numbers. Nothing changes without a yes | warn |

Replay, only with consent: ask "OK to test the done-check on your last few Claude conversations? It runs only on this computer and changes nothing." After a yes, run `python KIT/hooks/stop_evidence.py --replay <file>` on the newest five `~/.claude/projects/*/*.jsonl` (skip this setup conversation) and tell the user in one line how many turns it would have flagged. If there are no old conversations, skip quietly (**n.a.**). A no is **not enabled**. The check stays in `log` either way; blocking is Advanced (A4).

Then run `python KIT/scripts/selftest.py`.

**Check:** `selftest.py` prints `0 failed`; the modes printed in Step 0's check are the Basic set (or the user's earlier modes on a repair); this call prints a line containing `"permissionDecision": "ask"`:
`echo '{"tool_name":"Bash","tool_input":{"command":"git push"},"cwd":"VAULT"}' | python KIT/hooks/vault_guard.py` (put the real path in place of `VAULT`).

## Step 5 - A launcher for the main session

The main session is Claude Code started inside `VAULT`; there it reads `VAULT/CLAUDE.md`, which loads `AGENTS.md`. Make a double-click launcher named in the user's language (for example "Second brain"). It is a new file; if one with that name exists, ask before replacing it.
- **Windows:** `<Desktop>\Second brain.cmd` (find the real Desktop with `powershell -NoProfile -Command "[Environment]::GetFolderPath('Desktop')"`; it may be inside OneDrive), saved as UTF-8 without BOM:
  ```
  @echo off
  chcp 65001 >nul
  cd /d "C:\full\path\to\VAULT"
  claude
  ```
- **macOS:** `~/Desktop/Second brain.command`, then `chmod +x` it:
  ```
  #!/bin/sh
  cd "/full/path/to/VAULT" || exit 1
  exec claude
  ```
- **Linux:** the same script as `~/Desktop/second-brain.sh` (or `~/second-brain.sh` if there is no Desktop folder), `chmod +x`.
Also tell the user the plain way: open a terminal, `cd` into the notes folder, type `claude`; `claude --continue` goes back to the last conversation there.

**Check:** the launcher file exists and contains the vault path; and Claude Code runs from that folder: Windows `cmd /c "cd /d "<VAULT>" && claude --version"`, macOS/Linux `sh -c 'cd "<VAULT>" && claude --version'` prints a version. Opening the launcher itself is **not verified** until the user does it in Step 7.

## Step 5b - Full only: the parts the decision called for

Basic: **n.a.** Full: follow [ADVANCED.md](ADVANCED.md) for each part in the Step 0 decision, in the order A1, A2, A5. Install-time rules:
- A1: the topics are the things the user named in question 4 (two to four topics). If they gave only a number, use what they said in question 3 plus one `general` topic for the rest. Do not ask A1's "which two subjects" question.
- A2: its scheduler question asks permission and is still asked; a no is **not enabled** for the scheduler only.
- A5: only the tools from question 5.

Each part gets its own status word and its own Check from ADVANCED.md.

## Step 6 - End-to-end test: a new session finds what this one saved

Technical checks passing does not prove the second brain works. Prove it with test data, then remove the test data.
1. Pick a token, for example `SBKTEST-` plus six random letters.
2. Save a test note `VAULT/00-09 系統與索引/02 收件匣/02-99 SBK 安裝測試.md` with valid frontmatter (`type: log`, `status: active`, `summary: setup test note, deleted after the test`, today's dates, `origin: agent-drafted`) and one body line: `Setup test <token>.` Do not commit it.
3. Write down `ledger.py list`. Add a test item: `python SBK_HOME/bin/ledger.py add "Setup test <token>: add the line resumed by a new session to the note 02-99 SBK 安裝測試"`; note the printed id.
4. Start a **new** session in the vault that knows nothing of this one:
   `cd "<VAULT>"` then
   `claude -p "Setup test. Follow this folder's AGENTS.md: find the open work-list item that mentions <token>, open the note it names, add the line 'resumed by a new session' at the end, close the item with evidence. Do not commit. Reply with the note path and the item id." --allowedTools "Read,Grep,Glob,Edit,Bash(python:*)"`
   If `claude -p` cannot run here, ask the user to open the launcher from Step 5 in a second window, say "Continue the setup test item", and tell you when it has answered; keep this session open meanwhile.
5. Clean up: delete the test note; run `gen_jdex.py` and `vault_lint.py` again; the test item stays closed in the work list (closed items are not shown).

**Check:** before the cleanup, the note ends with `resumed by a new session` and `ledger.py list --all` shows the test id as done with evidence written by the new session; after the cleanup, the note is gone, lint ends with `RESULT: PASS`, `git -C VAULT status --short` shows no test file, and `ledger.py list` prints exactly what it printed in 3. If the new session did not find the item, read what it answered, fix the cause (usually `VAULT/CLAUDE.md` or the ledger path in `AGENTS.md`) and run the test again.

## Step 7 - Final check, handover and a two-minute first use

1. `python KIT/scripts/selftest.py` -> `0 failed`; `vault_lint.py` -> `RESULT: PASS`; `python SBK_HOME/bin/status.py` runs.
2. Write the start-here page `VAULT/README.md` (the checker allows this name in the vault root) in the user's language, under 30 lines, for the user (not for Claude). It covers only how to start, how to make Claude remember, how to see what is open, and how to get something fixed:
   - how to start: the launcher name and where it is; the terminal way (Full: new requests go to the entry launcher; open a topic launcher to let that topic work);
   - four example sentences: "Remember this: ...", "Find my notes about ...", "What is still open?", "Continue where we stopped on ...";
   - "If something gets in the way, tell Claude, for example: the done-check is too strict, make it quieter";
   - where things live: notes in this folder; the work list and logs in `~/.claude/sbk/`; local git keeps the history of changes but is **not** a backup of the disk: copy this folder to another disk or a cloud drive you trust from time to time;
   - "About once a week Claude checks whether more would help (topic sessions, reminders, other AI tools) and asks you first. You can also just ask, for example: turn on topic sessions."
3. The final message, short, in the user's language:
   - first line: Basic or Full and why (the line from Step 0.4);
   - one line per step with its status word (done / not enabled / n.a. / needs you / not verified);
   - what each safety check will do to them in practice;
   - what you did not do and why; what only they can do, as a numbered list (if anything);
   - **the two-minute first use**: (1) close this window and double-click the launcher; (2) say "Remember this: I want to finish chapter 3 this week" - Claude saves it; (3) say "What is still open?" - Claude shows the work list; (4) say "Find what I said about chapter 3" - Claude finds the note. That is the whole daily routine.

**Check:** `VAULT/README.md` exists and lint still passes; the final message starts with the Basic/Full line and has a status word for Steps 00 to 7 (including 5b).

---

## Updating, repairing, removing

- **Repair or second run:** run the steps again in order. Each step keeps what exists: config values, notes, the work list (`ledger.md`), `task.md` files, `requests/`, `logs/` and, in Advanced, `routes.md`, `alarms.md` and `state/alarms.json` are never deleted or reset. Only missing pieces are added; changed kit files are shown to the user before they replace anything.
- **Update:** update the plugin (`claude plugin update second-brain-kit@second-brain-kit`) or `git pull` the clone; then redo Step 1's copy and, for a clone install, Step 4's copy. Do not touch the user's notes or work list.
- **Remove:** remove the block between the `sbk` markers in `~/.claude/CLAUDE.md`, uninstall the plugin (or remove the hook entries from `settings.json`), delete the launcher, and in Advanced the scheduler entry. Ask before deleting `SBK_HOME` or the vault: they hold the user's data.

## Advanced

Full installs only the parts Step 0.4 called for. Later, when the user asks for more, or the weekly check (`level_check.py`, run by the `level_notice` hook and by `/sbk-status`) finds one of the triggers in [ADVANCED.md](ADVANCED.md) "When Claude suggests it" and the user says yes, follow that file's steps A1-A5.
