# SETUP - instructions for the configuring Claude

This file is written **for you, Claude**, not for the user. The user asked you to set up second-brain-kit. They may not be technical: you do the work; they answer six short questions, confirm what you suggest installing, and say yes or no to changes on their system. This is the only place that lists the questions and steps (`/sbk-setup` and the `setup-second-brain` skill just point here). It exists only in English, like every file only Claude reads.

**You recommend the parts one by one and the user confirms** (Step 0.4): mainly from their answer to "Where do you get stuck most when using Claude?"; if they allow you to look at their Claude history on this computer, its numbers are supporting evidence. If they say no, or this computer has no history (a new user), go by the answer alone; if the answer points to no part, install Basic. Each part gets one line with your suggestion and the reason; the user may change any of it.
- **Basic**: one main Claude session that works directly in the notes folder; the notes folder with only the areas the user needs; the tracker (`ledger.py`: open work items, one per line, each closed with a note of how it was checked), used by you, never typed by the user; safety checks; short general principles.
- **Extra parts** (sessions: the fixed entry and maintenance sessions, plus topic sessions the entry opens and sends work into; reminders; splitting work with outside resources): suggested one by one; only the ones the user confirms are switched on in Step 5b with the steps in [ADVANCED.md](ADVANCED.md). With any extra part on, the config records `full` (Full). The comparison table is in ADVANCED.md, "Basic and Full".

Everything else stays off. After setup, a weekly check (`level_check.py`) measures whether another part would help; you then offer it as one yes/no question.

Words used below:
- `KIT` - the folder that contains `.claude-plugin/plugin.json` with `"name": "second-brain-kit"`. Installed as a plugin it is `${CLAUDE_PLUGIN_ROOT}` (set inside plugin hooks and commands; in this session search the plugin cache under `~/.claude/plugins` for that file). Cloned by hand it is the clone folder.
- `SBK_HOME` - `~/.sbk` (the tracker, logs, settings of the kit). Not inside `~/.claude`: Claude Code asks before Claude's own file tools write there, so a background session could not write its task.md. An install from before 0.2.5 has `~/.claude/sbk`; the kit keeps using it while `~/.sbk` does not exist; with the user's yes, move the folder to `~/.sbk` and fix the paths in the scheduler task.
- `VAULT` - the notes folder the user chooses (default `~/second-brain`).
- `SURFACE` - how the user opens Claude: `app` (the Claude desktop app, its **Code** tab) or `terminal` (the `claude` command in a terminal window). Step 0.2 decides it; Steps 5, 6 and 7 differ by it.
- `PY` - the command that runs Python 3 on this computer (`python`, `python3` or `py`, the one that printed a version in Step 0.1). Step 0.3 stores it as `python_cmd` in `config.json`; the commands below are written with `python`: use `PY` in their place, in the commands you run and in every file you copy (Steps 1, 2, 3: see "Filling in the copied files" in Step 1).
- `NAMES` - the folder and file names of the notes folder, from `names` in `config.json` (Step 0.3). Every script reads them from there; the paths in this file and in the templates are the `zh-TW` set.
- Paths: use forward slashes or quoted paths on Windows.

Rules while you work:
- Language: everything the user sees (the questions as you ask them, your messages, the notes they read, `VAULT/README.md`, the final report) is in the user's language, from the first message on (the language they wrote the install request in; question 2 confirms it). Everything only Claude reads, the internal work, stays in English: the rules (`~/.claude/CLAUDE.md` block, `AGENTS.md`, the format note), task.md, tracker items, dispatches, hand-overs, prompts for subagents. The user's own words are always kept verbatim.
- Ask before anything that edits `~/.claude/settings.json`, `~/.claude/CLAUDE.md`, the system scheduler, or any file the user already had. Never overwrite an existing file; show the difference and get a yes.
- Nothing is pushed to a git remote, no message is sent, and no note is given to an outside resource the user did not tick. Do not tell the user it is "offline": Claude itself is an online service.
- Small reversible choices are yours (folder names, test names, a placeholder git identity): pick one and say which in the report. Ask only what only the user knows or must allow.
- Each step ends with a **Check**. Run it; continue only when it passes. If it fails, fix the cause and run it again; never report a step as done that you did not check.
- Report every step with exactly one of these: **done** / **not enabled** (an option the user did not want) / **n.a.** (does not apply here) / **needs you** (only the user can do it; say exactly what) / **not verified** (could not be checked; say why).

---

## Step 00 - Get the kit (skip if `KIT` is already on this computer)

The user may have pasted only the sentence from the README ("Install second-brain-kit from https://github.com/0Smallcat0/second-brain-kit and set me up by its docs/SETUP.md ..."). That sentence is their request to install, so do not ask again.
1. Run `claude plugin marketplace add 0Smallcat0/second-brain-kit`, then `claude plugin install second-brain-kit@second-brain-kit` (the command-line twins of `/plugin marketplace add ...` and `/plugin install ...`).
2. If the `claude` command cannot be run from here (an App user may not have it: the desktop app does not need it) or the install fails: clone `https://github.com/0Smallcat0/second-brain-kit` into a new folder (for example `~/second-brain-kit-src`) and use it as `KIT`. Hooks then use Step 4's manual route.
3. Find `KIT` (see Words) and read this file from there before going on.

**Check:** `KIT/.claude-plugin/plugin.json` exists and says `second-brain-kit`; `claude plugin list` shows second-brain-kit (clone route: write down that you used it).

## Step 0 - Check the computer, ask six things, suggest the parts

1. Run `python --version` (or `python3` / `py`) and `git --version`; Python 3.8+ and git are needed. Terminal users also need `claude --version` to work; App users do not (the desktop app has Claude Code built in, and has no `claude -p`).
   If one is missing, offer to install it ("OK if I install Python?") and after a yes do it: Windows `winget install -e --id Python.Python.3.12` / `winget install -e --id Git.Git`; macOS `xcode-select --install` (gives git and python3) or `brew install python git` if Homebrew exists; Linux the package manager. If it needs an administrator password or a click in an installer window, that part is **needs you**: tell the user exactly which window or command, then continue.
   **After anything was installed here** (Python, Git, anything on the PATH) the running app or terminal does not see it: every new conversation inherits the old PATH, and the safety hooks (Step 4) would start and find no Python, with no message. So before Step 4 add one **needs you** step and wait for it: "Quit the Claude app completely and reopen it (terminal: close this window and open a new one), start a new conversation and say 'continue the setup'." Work that uses full paths (Steps 1 to 3) may go on first; Step 4 and everything after it start in the new conversation, where Step 0's check is run again.
   **Windows without Git Bash:** Claude Code runs the kit's hooks (shell form) in Git Bash, or in PowerShell when Git Bash is not installed, and `sh` does not exist there. Look: `where git` shows `<Git folder>\cmd\git.exe`, and `<Git folder>\bin\bash.exe` exists. If the user said no to Git, or there is no `bash.exe`: the hooks of Step 4 are **not enabled** (every hook is registered with `onFailure: continue`, so nothing is blocked, but none of them runs); say that in the report in one line, and do not tell the user the safety checks are on.
2. Find `SURFACE` first. Read the environment variable `CLAUDE_CODE_ENTRYPOINT` (`echo $CLAUDE_CODE_ENTRYPOINT`; PowerShell `$env:CLAUDE_CODE_ENTRYPOINT`): `claude-desktop` or `claude-desktop-3p` -> `app`; `cli` -> `terminal`. These are the values Anthropic's monitoring page lists for how a session was launched; the variable itself is not documented, so treat it as a hint. Any other value (`claude-vscode`, `sdk-cli`, ...) or none: you cannot tell, so add to question 1 below "Do you open Claude through the Claude app (the Code tab) or in a terminal window?" and use the answer. The user's own answer always wins over the variable.
   Then ask these six in **one message**, in plain words, and wait:
   1. "Where should your notes live? I suggest `~/second-brain` (say OK to accept)."
   2. "Which language should I use for notes and replies?"
   3. "What do you mainly use Claude for (school, a job, a side project, freelance work...), and where do you get stuck most? For example: several things at once get mixed up, you often forget deadlines, you keep having to explain the background again, or it's all fine?"
   4. "May I look at your Claude history on this computer to help decide? At install I only count how many project folders were used in the last two weeks and whether a conversation got so long it was summarised twice or more; after that, about once a week, I only look at conversations in your notes folder and count how often you asked me to remind you or said things got mixed up. It is counted on this computer only, nothing is uploaded or changed. 'No' is completely fine."
   5. "Which Claude plan do you have: Pro, Max, Ultra, Team, Enterprise, or API (pay per use)? 'Not sure' is fine. It sets how much may run by itself so it fits your usage limit: the reminder check every 5 minutes only reads files on this computer and uses none of your limit; only starting or messaging a Claude session does."
   6. "Besides this Claude account, do you have any of these? Tick any, or none: (a) another AI account (ChatGPT, Gemini, a second Claude, Codex...), (b) Colab or Kaggle, (c) cloud or API credit (Azure, Google Cloud, AWS, an API key with credit), (d) a computer with a graphics card (GPU) for heavy jobs, (e) a student offer (Azure for Students, GitHub Copilot for students). None is completely fine: one Claude account is enough."
   Do not ask anything else, here or later in the setup. The only things that do not count as extra questions: the app-or-terminal question when the variable did not tell you, asking permission for a change on their system, and, in point 4's message, which things to split into topic sessions and whether the suggested note areas fit. No profile questions, no "Basic or Full?". For question 6, only what they tick counts: nothing unticked is ever assumed. ChatGPT and Gemini web, Colab, Kaggle and the student offers are free to sign up: you may add one line "free to sign up (可免費申請): ..." with the ones that fit, and explain how only if they say they want to.
3. Create `SBK_HOME`. If `SBK_HOME/config.json` does not exist, copy `KIT/templates/config.json` there and fill `vault` (absolute path), `language`, `uses` (their words for question 3), `outside_resources` (question 6: only what they ticked, in their words; empty if none), `read_history` (question 4: yes `true`, no `false`), `plan` (question 5: `pro`, `max`, `ultra`, `team`, `enterprise` or `api`; empty if not sure), `python_cmd` (`PY`), `names` (the `zh-TW` set from `KIT/templates/names.json` when the language is Chinese, the `en` set otherwise: replace the `names` object of the config with it) and the plan's starting values from the table in point 4 (`max_sessions`, `wake_limits`, `review`). If it exists (a repair or second run), keep every value it has and only add missing keys from the template.
4. **Suggest the parts one by one; the user confirms.**
   - Question 4 was yes: run `python KIT/scripts/level_check.py --install`. It only counts, on this computer: project folders in `~/.claude/projects` used in the last 14 days, and whether one conversation was summarised (compacted) two or more times. It reads no conversation content and changes nothing. If the output says `"partial": true`, the count stopped after 30 seconds: use what it found.
   - Question 4 was no: do not run it and do not look in `~/.claude/projects`. A yes with `active_projects_14d` = 0 (a new user, no history) is the same: go by the answer alone.
   - Each part follows the answer to question 3; history numbers are only supporting evidence and never switch on a part the answer did not point to:
     - **topic sessions** (ADVANCED A1: the fixed entry and maintenance sessions; the entry keeps one conversation per subject and sends work into it): only when this computer can start background sessions, which needs the `claude` command (terminal users; an app user who also has it). They said several things get mixed up; or they answered "not sure" and the history shows 3 or more project folders used in the last two weeks and `session_compacted_2plus_14d` is 1. **App only, no `claude` command: not offered.** The app can message its own Code-tab sessions but does not see a terminal's, a scheduled task there only fires while the app is open and starts a new session (Desktop pages), so a topic session would mean the user opening each one by hand. For these users suggest the Basic tracker with `[topic]` tags instead and say in the message: "With the app only, one conversation handles everything and keeps each subject apart with a tag; you click nothing extra."
     - **reminders** (A2): they said they often forget deadlines, or want reminders.
     - **splitting work with outside resources** (A5): only if they ticked something in question 6.
     - "I keep explaining the background again": Basic already handles this (notes found again in a new conversation, the tracker, their own words put back after a long conversation is summarised), so no extra part; if they also said several things get mixed up, follow the topic-sessions line.
     - "It's all fine", no answer, or an answer that points to none of the above: **Basic**, nothing extra.
   Disk space, operating system or the number of git commits decide whether a part *can* run, not whether it is needed: they are not reasons.
   - In **one message**, in their language, one line per part: switch it on or not now, plus one reason with its numbers; end with "Is that OK? Tell me anything to add or drop." Add one line with the note areas you suggest from question 3 (Step 3 has examples by role). When you suggest topic sessions, add what the user will click (terminal: nothing, the entry opens them in the background; if a session needs them, they open a folder in a second window) and ask in the same message "Which things should each get their own conversation? (two to four)". For example:
     "Here is what I suggest:
     - Basic: always (notes, tracker, safety checks).
     - Reminders: on. You said you often forget deadlines.
     - Topic sessions: not now. You said things don't get mixed up; only 1 project folder was used here in the last two weeks.
     - Splitting work with outside resources: not now. You ticked none.
     - Note areas: 20-29 學習與讀書 and 40-49 專案, since you use Claude for courses and a side project.
     Is that OK? Tell me anything to add or drop."
     Wait for the answer. What they confirm is the decision; if they change their mind later, follow them.
   - **Plan starting values.** Written into `config.json` from question 5 whatever the parts; Full uses them. A topic session started in the background uses the plan's quota like any conversation, so the plan caps how many run at once and how often the scheduler may start or message one:

     | Plan (question 5) | Topic sessions at once (`max_sessions`) | Starts per day / minutes between two for one session (`wake_limits`) | Maintenance's weekly review (`review`) |
     |---|---|---|---|
     | Pro | 2 | 4 / 120 | weekly, Sunday 20:00 |
     | Max | 4 | 12 / 60 | twice a week, Wednesday and Sunday 20:00 |
     | Ultra, Team, Enterprise or higher | 6 | 24 / 30 | twice a week, Wednesday and Sunday 20:00 |
     | API (pay per use), or not sure | 2 | 4 / 120 | weekly, Sunday 20:00 |

     These are starting values: you (the user's Claude) may change them later in `config.json`, for example when the weekly review shows work waiting on the cap; tell the user in one line when you do. Say it plainly in the message: "The reminder check runs every 5 minutes on this computer and uses none of your limit; only starting or messaging a session does, at most N times a day."
   - Write `level` (`full` if any extra part is on, else `basic`), `level_reason` (those lines, joined into one) and the confirmed note areas (`areas`, a list of folder names) into `SBK_HOME/config.json`. For each part you suggested but they did not want, run `python KIT/scripts/level_check.py --decline <ids>` (`multi_session`, `alarms`, `multi_tool`) so the weekly check does not ask again for 4 weeks.

**Check:** `python -c "import json,os;c=json.load(open(os.path.expanduser('~/.sbk/config.json'),encoding='utf-8'));print(c['level'],c['read_history'],c['vault'],c['plan'],c['max_sessions'],c['wake_limits'],c['outside_resources'],c['modes'])"` prints `basic` or `full` (what the user confirmed), `True` or `False` (question 4), the vault path, the plan (question 5) with its starting values from the table, what they ticked in question 6 (or nothing), and the modes from the template (or the user's earlier modes on a repair).

## Step 1 - The tracker tools (ledger.py)

1. Create `SBK_HOME/bin` and `SBK_HOME/logs`.
2. Copy `KIT/entry/ledger.py`, `status.py`, `send.py`, `alarm.py`, `session.py`, `handover.py`, `learn.py`, `KIT/hooks/_common.py` and `KIT/scripts/level_check.py` into `SBK_HOME/bin/` (they import each other; `handover.py` reads conversation files with `_common.py`; `/sbk-status` and the weekly check run `level_check.py`). Copy `KIT/templates/task.md` to `SBK_HOME/task-template.md`. Always copy; do not point at the plugin cache, whose path changes on update. Write the kit's version (`version` in `KIT/.claude-plugin/plugin.json`) as the only content of `SBK_HOME/bin/VERSION`: the hooks compare it with the plugin's version and say once a day when the copy is old.
3. Clone route only (the plugin route has them already): copy `KIT/commands/*.md` into `~/.claude/commands/` (skip a name that exists), so `/sbk-status` and `/sbk-setup` exist.

**Filling in the copied files.** Everything below that copies a template (Steps 2, 3, 5b) copies it with these replacements, so that the commands in it work on this computer: (a) a command that starts with `python ` (`python ~/.sbk/...`, `python ../bin/...`, `python scripts/...`) gets `PY` in place of `python` when `PY` is not `python`; (b) `{{vault}}` becomes the vault's full path; (c) when `names` in `config.json` is not the `zh-TW` set, every `zh-TW` name from `KIT/templates/names.json` that appears in the file is replaced by the same key's name from `config.json` (the folder paths, the note names). The selftest checks that the templates use no name that the map lacks.

**The user already keeps a to-do tracker, reminders or per-topic working files from before the kit** (their own scripts, another assistant's files): do not retype them and do not start empty. Read the old files (read-only), write a plan file as `KIT/scripts/import_existing.py` describes at its top (every old tracker row is either an item to keep or a record with the reason; `expect_rows` = the old row count, so nothing is dropped silently), show the user the dry run (`python KIT/scripts/import_existing.py plan.json`), and after a yes run it with `--apply`. It writes only under `SBK_HOME`, never changes an old file, and `SBK_HOME/state/import-map.json` then answers where each old row went. While the old setup still works on a topic, leave `to` out of that topic's items: two sessions on one job do it twice. Move topics one at a time, each when it has no deadline in the next days.

**Check** (works on a new or an existing tracker):
1. `python SBK_HOME/bin/ledger.py list` - write the output down.
2. `python SBK_HOME/bin/ledger.py add "sbk setup check"` prints a new id; use the id it printed (do not assume `L0001`).
3. `python SBK_HOME/bin/ledger.py done <id> --evidence "setup step 1: add, done and list ran"` prints `<id> done`.
4. `ledger.py list` prints exactly what it printed in 1 (older items untouched), and `ledger.py list --all` shows `<id>` as done.

## Step 2 - General principles in `~/.claude/CLAUDE.md` (with consent)

`KIT/templates/CLAUDE.md` holds only general safety and evidence rules. It goes into the user's global `~/.claude/CLAUDE.md`, which affects every Claude session on this computer, so ask first, and show the block before the yes: "OK to add this block of general rules to your Claude settings for all projects? It makes Claude check results before saying done, ask before deleting or publishing, and it also contains a section called Core stance: work for your benefit within the real rules, add no extra caution or warnings you did not ask for, and when writing for you to others, leave out weaknesses. Here it is in full: ..." (paste the block, or its section titles with Core stance in full). The notes rules stay inside the notes folder; the block applies in every project.
1. Copy the template in English, whatever the user's language (only Claude reads it, and it tells Claude to reply and write notes in the user's language), with the replacements of "Filling in the copied files" in Step 1: `{{vault}}` becomes the vault's full path, so the block names it by absolute path and works from any folder.
2. The block always sits between a line `<!-- sbk:begin -->` and a line `<!-- sbk:end -->`:
   - file missing: create it with just the block (markers included);
   - file exists, no markers: show the user the block, and after a yes append it at the end; never remove or reorder their text;
   - markers already there (second run): replace only what is between them, after showing the difference. Never add a second block.
3. A no is fine: mark the step **not enabled**; the notes rules still work from `VAULT/AGENTS.md`.

**Check:** the file contains exactly one `<!-- sbk:begin -->` and one `<!-- sbk:end -->`, the begin line comes first, and the block between them has fewer than 100 lines (or the step is **not enabled**).

## Step 3 - The notes folder (`VAULT`)

1. Create only these area folders (numbers and names in the style of the **example** table in `KIT/templates/筆記格式.md` section 1). The kit's own folders and files are named by `NAMES` (`names` in `config.json`, Chinese or English, shipped in `KIT/templates/names.json`); the user's own areas are named in the user's language:
   - `sys_dir` (default `00-09 系統與索引`) with `index_dir` (`00 索引`), `rules_dir` (`01 規則`), `inbox_dir` (`02 收件匣`), `ai_dir` (`03 和 AI 協作`);
   - the one or two areas the user confirmed in Step 0.4. You proposed them from question 3 (and the history, if allowed); examples by role: a student -> `20-29 學習與讀書`; an office worker -> `30-39 工作`; a freelancer -> `30-39 接案` (clients and jobs) and `60-69 金錢與行政` (invoices); someone with a side project -> `40-49 專案`. These are examples, not a fixed list: name an area after what this user does. If the answer showed nothing, no extra area; the first one is created when the first note needs it;
   - `archive_dir` (`90-99 封存`).
   Do not create empty category folders; categories are created when the first note needs one. After copying `筆記格式.md` (next point), replace the rows of its example table with the user's areas and keep the word 範例 only on rows they did not take.
2. Copy into the vault, replacing `{{date}}` with today (`YYYY-MM-DD`). If a file already exists, keep it and compare instead (repair):
   - `templates/AGENTS.md` -> `VAULT/AGENTS.md`; and `VAULT/CLAUDE.md` containing exactly one line: `@AGENTS.md`
   - `templates/筆記格式.md` -> `VAULT/<sys_dir>/<rules_dir>/<format_note>`
   - `templates/todo-for-me.md` -> `VAULT/<sys_dir>/<inbox_dir>/<todo_note>` (the note where steps only the user can do are written; topic sessions write there, not into a file in `SBK_HOME`)
   - the learning loop's note -> `VAULT/<sys_dir>/<ai_dir>/<ai_note>` (one line per correction or confirmation; Basic and Full). It also carries 12 starter preferences (the kit's general ways of working that the global block of Step 2 does not already say), each tagged as from the original author and free to delete. Pick the variant by the user's language: Traditional Chinese -> `templates/和AI協作.md`; any other language -> `templates/和AI協作.en.md`, translated into that language (tag and headings too; keep the rules in point 3). Tell the user in one line that the starter preferences are there, are theirs to delete, and that Claude follows them from the first conversation
   - an inbox note `VAULT/<sys_dir>/<inbox_dir>/<inbox_note>` with valid frontmatter (`type: log`, `status: active`, a one-sentence summary, today's dates, `origin: agent-drafted`) and one line saying "Put anything not yet filed here."
   - `templates/sbk-protect.txt` -> `VAULT/.sbk-protect` (its `00-09 系統與索引/01 規則/` line becomes `<sys_dir>/<rules_dir>/`); an empty file `VAULT/.sbk-vault`; `VAULT/.gitignore` with one line `__pycache__/` (Python leaves that folder next to the scripts)
   - `KIT/scripts/{vault_lint.py,gen_jdex.py,check_overwrite.py,pre-commit}` -> `VAULT/scripts/`; on macOS/Linux `chmod +x VAULT/scripts/pre-commit`.
3. `AGENTS.md` and the format note stay in English (rules only Claude reads). The notes the user reads (the inbox note, the to-do note, the learning note) are in the user's language: the templates are written in Traditional Chinese; for another language translate their text, but keep field names and values such as `type: preference` exactly (the checker depends on them), keep the line format `- date | kind | ... | ...`, and keep a word for "preferences" (`偏好` or `Preferences`) in the headings of both preference sections, the user's own first and the starter one second (`learn.py pref` writes into the first heading it finds). Keep the tag on every starter line, and keep the log heading as `紀錄` in Chinese and `Log` otherwise (`learn.py add` reads it to choose the language of the kind word). Folder and file names are exactly the `NAMES` of `config.json` - they are neither translated by hand nor left in Chinese for an English user: that is what the map is for. The scripts (`learn.py`, `learn_notice`, `gen_jdex.py`, `vault_guard`, `level_check.py`) find the folders only through the map; a name you invent makes them fail without a message. `gen_jdex.py` prints the index page's fixed text in the user's language.
4. `python VAULT/scripts/gen_jdex.py --root VAULT` creates the index.
5. Git, local only (it keeps the history of changes; nothing is pushed):
   - `git init` in `VAULT` if `VAULT/.git` does not exist.
   - Check `git -C VAULT config user.name` and `git -C VAULT config user.email` **separately**. For each one that is empty, set it for this vault only (no `--global`): the user's name if they gave it, otherwise `second-brain`; email `second-brain@localhost`. Tell the user which you set.
   - `git -C VAULT config core.hooksPath scripts`.
   - First run: add the files by name and commit "Initial vault". Repair: commit only the files you added or changed. Afterwards the `vault_snapshot` hook (Step 4) commits the notes Claude changed, when each reply ends, so "git keeps the history of changes" is done by a program and not by a rule that can be forgotten; it is local only and never pushes.

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

A hook is a small program Claude Code runs automatically at certain moments (before a command, when Claude says it is finished). It is not another AI. Every kit hook is registered with `"onFailure": "continue"`: if one cannot start or breaks, the tool call goes ahead instead of being blocked (the Claude Code hooks page, "Failed hooks on Windows without Git Bash", says that without `onFailure` a failing shell-form `PreToolUse` hook blocks there). That is why a hook that is **not running** looks the same as a hook that is quiet; so each hook run stamps `SBK_HOME/state/hooks-heartbeat.json` (`hooks/run.sh`), and `status.py` prints "hooks: last ran ..." or "NO STAMP". Hooks need Python (any of `python3`, `python`, `py`) and, on Windows, Git Bash; **after anything was installed in this setup, the app or terminal must have been restarted** (Step 0.1) or they do not run.

- **Plugin install:** `KIT/hooks/hooks.json` is active from the next session on. Check with `claude plugin list` that second-brain-kit is enabled.
- **Clone route:** copy `KIT/hooks/*.py` and `run.sh` to `SBK_HOME/hooks/`; then, after a yes (it edits settings), merge the `hooks` block of `KIT/templates/settings.hooks.example.json` into `~/.claude/settings.json`, replacing `__KIT__` with the `SBK_HOME/hooks` path. Merge, do not replace: keep every hook the user already has. In the same yes, copy each folder in `KIT/skills/` into `~/.claude/skills/` (skip a name that already exists there); the plugin route installs the skills by itself.

- **The user's `~/.claude/settings.json` already has hooks of their own** (count them first: `python -c "import json,os;print({k:len(v) for k,v in json.load(open(os.path.expanduser('~/.claude/settings.json'),encoding='utf-8')).get('hooks',{}).items()})"`): do not install the plugin and do not merge the block; either would run the kit's hooks next to theirs in every conversation. Copy `KIT/hooks/*.py`, `run.sh` and `KIT/templates/settings.hooks.example.json` to `SBK_HOME/hooks/` and set `"session_hooks": true` in `config.json`: `session.py` then gives the kit's hooks to the sessions it starts (entry, topics, maintenance, workers) through `--settings`, and no other conversation gets them. `settings.json` is not edited. Two things stay the user's decision, each after a yes: whether their own hooks should skip conversations started under `SBK_HOME` (their hooks, their edit), and whether the notes folder's guard should also cover conversations the kit did not start (then that one hook goes into `settings.json`).

Every hook reads its mode from `SBK_HOME/config.json` -> `modes` (values: off, log, warn, ask, deny, block). Basic is the template's set; tell the user one plain line per hook:

| Hook | What the user notices | Basic mode |
|---|---|---|
| `vault_guard` | Claude asks before `git push`, skipping git checks, throwing away git work, deleting a whole folder (Bash `rm -r`, PowerShell `Remove-Item -Recurse` and its aliases), changing protected rule files, or shrinking a note to a fraction of it. It does not ask before deleting or moving a single note, or before uploading a note; those are left to Claude Code's own permission prompts | ask |
| `read_whole` | Inside the notes folder: a shell command that reads a note through `head`, `tail`, `Get-Content -TotalCount` and the like is refused; when a Read of a note stops before its last line, Claude gets one line saying which lines it has and is told to read the rest (no effect outside the notes folder) | deny |
| `requests_reinject` | When a long conversation gets summarised, the user's own messages are put back word for word; a copy is kept in `~/.sbk/requests/` on this computer. Above 150k tokens Claude writes a hand-over into `task.md` in a fixed place and tells the user to start a new conversation; the new one finds the hand-over by itself at its start (the user says nothing) | warn |
| `stop_evidence` | Notes in `~/.sbk/logs/stop_evidence.log` when Claude said "done" after an edit without looking at the result; it does not interrupt | log |
| `vault_snapshot` | When a reply ends, the notes Claude changed are committed to the notes folder's own local git (`snapshot <date>: N file(s)`), so an earlier version can always be got back. Nothing is pushed | warn |
| `usage_warn` | nothing (Advanced) | off |
| `inbox_notice` | nothing (Advanced, for topic sessions) | off |
| `level_notice` | At most once a week, at the first session start in the notes folder: if what happened to you shows another part would help (for example you asked Claude to remind you twice in a week; table in ADVANCED.md), Claude asks one yes/no question and quotes the numbers. In Basic it also starts the light review of the learning loop: Claude groups the week's lines in the 和 AI 協作 note by kind, shows you the preferences (and any skill or check) it would add, and writes them only after your yes. Nothing changes without a yes; if you said no to question 4 it does not read your conversations. It speaks only in the notes folder and the entry folder, and once a day it says when the kit was updated and the copied tools are old | warn |
| `learn_notice` | When your message looks like a correction ("that's wrong", "I told you", 不對, 我說過) or a confirmation ("that's it", 就是這樣), Claude is reminded to write one line in the 和 AI 協作 note: the date, your words, which kind. Nothing is blocked; if the message was not one, nothing is written. When a conversation starts (and after a summary), it puts the note's sorted preferences into the conversation | warn |

Replay, only if question 4 of Step 0 was yes (already allowed; do not ask again): run `python KIT/hooks/stop_evidence.py --replay <file>` on the newest five `~/.claude/projects/*/*.jsonl` (skip this setup conversation) and tell the user in one line how many turns it would have flagged. If there are no old conversations, skip quietly (**n.a.**). If question 4 was no, this is **not enabled**. The check stays in `log` either way; blocking is Advanced (A4).

Then run `python KIT/scripts/selftest.py`.

**Check:** `selftest.py` prints `0 failed`; the modes printed in Step 0's check are the Basic set (or the user's earlier modes on a repair); this call prints a line containing `"permissionDecision": "ask"`:
`echo '{"tool_name":"Bash","tool_input":{"command":"git push"},"cwd":"VAULT"}' | python KIT/hooks/vault_guard.py` and the same with `"tool_name":"PowerShell"` (put the real path in place of `VAULT`); on Windows the PowerShell one is the one that matters, because Claude uses the PowerShell tool there. The hooks' matchers are `Bash|PowerShell`; whether they run inside a real session is read in Step 6 from the heartbeat.

## Step 5 - How the user opens the main session

The main session is Claude Code started inside `VAULT`; there it reads `VAULT/CLAUDE.md`, which loads `AGENTS.md` (the desktop app and the terminal read the same files). What you do depends on `SURFACE`; never assume a desktop shortcut.

### `SURFACE` = app: no shortcut file

Make no `.cmd`, `.command` or `.sh` file. Tell the user these steps in their language, with the app's own button names (from Anthropic's desktop quickstart and desktop pages), and put them in `VAULT/README.md` in Step 7:
1. Open Claude (macOS: Applications folder; Windows: Start menu; Linux: application launcher) and click the **Code** tab at the top of the sidebar. If the tabs show only icons, hover over one to see its name.
2. In the row under the prompt box, click the first control (the environment selector) and pick the top entry in the **Local** group. Then click the project folder control next to it, choose **Open folder…**, and pick `<VAULT>` (write the full path).
3. Type to Claude as in a chat. Next time, click that session in the sidebar to carry on; **+ New** in the sidebar starts a fresh one, and you pick the folder again the same way. Clicking the session's title in the title bar renames it (for example "Second brain") so it is easy to find.
- If a new session shows the environment above the prompt box instead of under it, the app has the earlier layout: choose the folder above the prompt box, or update the app (macOS **Claude > Check for Updates…**, Windows **Help > Check for Updates…**).
- The docs describe no pin or "recent folders" feature, so do not promise one; the session list in the sidebar is the way back.

**Check:** `VAULT/CLAUDE.md` contains `@AGENTS.md` and `VAULT/AGENTS.md` exists (those are what the app loads on opening the folder). Opening the folder in the app is **not verified** until the user does it in Step 7.

### `SURFACE` = terminal: a shortcut, or two plain commands

Make a double-click launcher named in the user's language (for example "Second brain"). It is a new file; if one with that name exists, ask before replacing it.
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
Also tell the user the plain way that needs no shortcut: open a terminal, `cd "<VAULT>"`, type `claude`; `claude --continue` goes back to the last conversation there.

**Check:** the launcher file exists and contains the vault path; and Claude Code runs from that folder: Windows `cmd /c "cd /d "<VAULT>" && claude --version"`, macOS/Linux `sh -c 'cd "<VAULT>" && claude --version'` prints a version. Opening the launcher itself is **not verified** until the user does it in Step 7.

## Step 5b - The extra parts the user confirmed

No extra part: **n.a.** Otherwise follow [ADVANCED.md](ADVANCED.md) for each part the user confirmed in Step 0, in the order A1, A2, A5. Install-time rules:
- A1: always the two fixed sessions (entry and maintenance), plus the topics the user said to split in Step 0 (two to four); anything unclear goes to one `general` topic. Do not ask A1's "which subjects" question again. Then live routing (A1 step 5): `python SBK_HOME/bin/session.py check` writes `routing` (`live` when this computer can start background sessions and pass messages, else `inbox`). With `live`, ask once "OK if I mark the folder `~/.sbk` as trusted for Claude Code, so the entry can start topic sessions there in the background?" and after a yes run `session.py trust`. With `inbox` (App only, no `claude` command) topic sessions are not set up: the entry does the work itself in its one conversation (Step 0.4); say so in one line. A user who has the app and the `claude` command gets `live`, and the entry then opens the topics in the background.
- The learning loop: Maintenance's weekly review (alarm rows M01, and M02 on Max or higher) needs the scheduler, so the scheduler question is asked once (A1 or A2). Without a working scheduler the entry gets the Basic light review at session start instead whenever no `[review]` tracker item was closed in the last 8 days (it falls back on evidence, not on configuration).
- A2: its scheduler question asks permission and is still asked; a no is **not enabled** for the scheduler only.
- A5: only what the user ticked in question 6.

Each part gets its own status word and its own Check from ADVANCED.md.

## Step 6 - End-to-end test: a new session finds what this one saved

Technical checks passing does not prove the second brain works. Prove it with test data, then remove the test data.
1. Pick a token, for example `SBKTEST-` plus six random letters.
2. Save a test note `VAULT/00-09 系統與索引/02 收件匣/02-99 SBK 安裝測試.md` with valid frontmatter (`type: log`, `status: active`, `summary: setup test note, deleted after the test`, today's dates, `origin: agent-drafted`) and one body line: `Setup test <token>.` Do not commit it.
3. Write down `ledger.py list`. Add a test item: `python SBK_HOME/bin/ledger.py add "Setup test <token>: add the line resumed by a new session to the note 02-99 SBK 安裝測試"`; note the printed id.
4. Start a **new** session in the vault that knows nothing of this one:
   `cd "<VAULT>"` then
   `claude -p "Setup test. Follow this folder's AGENTS.md: find the open tracker item that mentions <token>, open the note it names, add the line 'resumed by a new session' at the end, close the item with evidence. Do not commit. Reply with the note path and the item id." --allowedTools "Read,Grep,Glob,Edit,Bash(python:*),Bash(python3:*),Bash(py:*),PowerShell(python:*),PowerShell(python3:*),PowerShell(py:*)"` (the same interpreters and both shell tools as the allowlist in `entry/session.py`; a Mac with only `python3`, or a Windows session that uses the PowerShell tool, is otherwise refused without a prompt)
   If `claude -p` cannot run here (App users often have no `claude` command, and the app has no `-p`), ask the user to open a second session on the notes folder - app: **+ New** in the sidebar, then **Open folder…** `<VAULT>` as in Step 5; terminal: the launcher from Step 5, or `cd "<VAULT>"` then `claude` in a second window - say "Continue the setup test item", and tell you when it has answered; keep this session open meanwhile.
5. Read the hooks: `python SBK_HOME/bin/status.py` prints a `hooks:` line. `last ran <time>` newer than step 4 proves the hooks started in a real session. `NO STAMP` means they did not run: Python or Git Bash was not found, or the app was not restarted after an install; fix that (Step 0.1) before going on. On Windows without Git Bash this is expected: the hooks stay **not enabled**.
6. Clean up: delete the test note; run `gen_jdex.py` and `vault_lint.py` again; the test item stays closed in the tracker (closed items are not shown).

**Check:** before the cleanup, the note ends with `resumed by a new session`, `ledger.py list --all` shows the test id as done with evidence written by the new session, and `status.py` shows `hooks: last ran` (or Step 4 is **not enabled**); after the cleanup, the note is gone, lint ends with `RESULT: PASS`, `git -C VAULT status --short` shows no test file, and `ledger.py list` prints exactly what it printed in 3. If the new session did not find the item, read what it answered, fix the cause (usually `VAULT/CLAUDE.md` or the tracker path in `AGENTS.md`) and run the test again.

## Step 7 - Final check, handover and a two-minute first use

1. `python KIT/scripts/selftest.py` -> `0 failed`; `vault_lint.py` -> `RESULT: PASS`; `python SBK_HOME/bin/status.py` runs.
2. Write the start-here page `VAULT/README.md` (the checker allows this name in the vault root) in the user's language, under 30 lines, for the user (not for Claude). It covers only how to start, how to make Claude remember, how to see what is open, and how to get something fixed:
   - how to start, by `SURFACE`: app - the Step 5 steps (Code tab, **Open folder…**, click the session in the sidebar next time); terminal - the launcher name and where it is, or `cd` into the notes folder and type `claude`. Full: new requests go to the entry session; it sends them into the topic conversation that owns them (one conversation per topic, continued even after Claude Code stopped its process), or, on a computer that cannot run background sessions, does the work itself; you get one result from the entry after it has checked the evidence;
   - four example sentences: "Remember this: ...", "Find my notes about ...", "What is still open?", "Continue where we stopped on ...";
   - "If something gets in the way, tell Claude, for example: the done-check is too strict, make it quieter";
   - where things live: notes in this folder; the tracker and logs in `~/.sbk/`; local git keeps the history of changes but is **not** a backup of the disk: copy this folder to another disk or a cloud drive you trust from time to time;
   - "Claude learns from you: when you correct it, or say 'yes, like that', it writes one line in the note 和 AI 協作 and reads it before it starts work. About once a week it groups those lines and asks you before writing any of them as a preference."
   - "About once a week Claude checks whether more would help (topic sessions, reminders, outside resources) and asks you first. You can also just ask, for example: turn on topic sessions."
3. The final message, short, in the user's language:
   - first line: what was installed (Basic + the parts they confirmed) and why (the lines from Step 0.4, joined);
   - one line per step with its status word (done / not enabled / n.a. / needs you / not verified);
   - what each safety check will do to them in practice;
   - what you did not do and why; what only they can do, as a numbered list (if anything);
   - **the two-minute first use**: (1) app: in the Claude app, click the notes-folder session in the sidebar (or **+ New**, then **Open folder…** `<VAULT>`); terminal: close this window and double-click the launcher (or `cd` into the notes folder and type `claude`); (2) say "Remember this: I want to finish chapter 3 this week" - Claude saves it; (3) say "What is still open?" - Claude shows the tracker; (4) say "Find what I said about chapter 3" - Claude finds the note. That is the whole daily routine.

**Check:** `VAULT/README.md` exists and lint still passes; the final message starts with the what-was-installed line and has a status word for Steps 00 to 7 (including 5b).

---

## Updating, repairing, removing

- **Repair or second run:** run the steps again in order. Each step keeps what exists: config values, notes (the 和 AI 協作 note too), the tracker (`ledger.md`), `task.md` files, `requests/`, `logs/` and, in Advanced, `routes.md`, `alarms.md` and `state/` are never deleted or reset. An older config with `wake` and no `routing`: drop `wake` and add the plan's starting values (point 4 of Step 0); an older `other_tools` becomes `outside_resources`. Only missing pieces are added; changed kit files are shown to the user before they replace anything.
- **Update:** update the plugin (`claude plugin update second-brain-kit@second-brain-kit`) or `git pull` the clone; then redo Step 1's copy (including `bin/VERSION`, and `commands/` on the clone route) and, for a clone install, Step 4's copy. Nothing else tells the user an update happened except the line "[second-brain-kit update] ... copy the tools again" that `level_notice` says once a day while `SBK_HOME/bin/VERSION` differs from the plugin's version. Do not touch the user's notes or tracker.
- **Remove:** remove the block between the `sbk` markers in `~/.claude/CLAUDE.md`, uninstall the plugin (or remove the hook entries from `settings.json`), delete the launcher if one was made (terminal users only), and in Advanced the scheduler entry. The vault and `SBK_HOME` (tracker, logs) are kept by default; ask before deleting either: they hold the user's data. End by telling the user what was kept and where.

## Advanced

Setup switches on only the parts the user confirmed in Step 0.4. Later, when the user asks for more, or the weekly check (`level_check.py`, run by the `level_notice` hook and by `/sbk-status`) finds one of the triggers in [ADVANCED.md](ADVANCED.md) "When Claude suggests it" and the user says yes, follow that file's steps A1-A5.
