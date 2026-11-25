# SETUP - instructions for the configuring Claude

This file is written **for you, Claude**, not for the user. The user asked you to set up the second-brain-kit working method. They may not be technical: you do the work, they answer a few questions and approve system changes. Do the steps in order; after each step run its **Check** and only continue if it passes. If a check fails, fix the cause and re-run it; do not skip it, and never tell the user a step is done that you did not check.

Words used below:
- `KIT` - the folder this file is in, one level up (contains `.claude-plugin/plugin.json`).
- `SBK_HOME` - `~/.claude/sbk` (runtime folder: ledger, alarms, routes, inbox, logs, task.md files).
- `VAULT` - the notes folder the user chooses (default `~/second-brain`).
- Use forward slashes or quoted paths on Windows. Use Python 3 (`python3`, `python` or `py`, whichever runs).

Rules while you work: ask before anything that edits `~/.claude/settings.json`, `~/.claude/CLAUDE.md`, the system scheduler, or any existing file of the user's. Never overwrite an existing file; show the difference and get a yes. Nothing here is pushed anywhere or sent to anyone.

---

## Step 00 - Get the kit (skip if `KIT` already exists on disk)

The user may have pasted only: "Install the Claude Code plugin from https://github.com/0Smallcat0/second-brain-kit and set me up by its docs/SETUP.md." If `KIT` (the folder with `.claude-plugin/plugin.json`) is not on this computer yet:
1. Ask once: "OK to add the second-brain-kit plugin from github.com/0Smallcat0/second-brain-kit? It changes your Claude Code plugin list." After a yes, run `claude plugin marketplace add 0Smallcat0/second-brain-kit` and then `claude plugin install second-brain-kit@second-brain-kit` (the command-line twins of `/plugin marketplace add ...` and `/plugin install ...`).
2. If the `claude` command cannot be run from here, or the install fails, clone `https://github.com/0Smallcat0/second-brain-kit` into a new folder (for example `~/second-brain-kit-src`) and use that folder as `KIT`; the hooks are then installed by Step 4's manual route.
3. Read `docs/SETUP.md` from `KIT` again (it is this file) and continue with Step 0.

**Check:** `KIT/.claude-plugin/plugin.json` exists and `claude plugin list` shows second-brain-kit (or, for the clone route, the folder exists and you said so).

---

## Step 0 - Preflight and the questions

1. Run `python --version`, `git --version`, `claude --version`. Python 3.8+ and git are required. If one is missing, tell the user exactly what to install (only they can) and stop here.
2. Ask the user these questions in **one message** and wait. The default for every tool is "no": one Claude account is enough.
   1. Do you have a **second Claude account** (a second subscription you pay for, or a family/friend plan you may use)?
   2. Do you have **ChatGPT**, and do you want to use the **Codex CLI**?
   3. Do you use **Gemini** (website, Antigravity, or an API key)?
   4. Do you have **Google Colab**, or a computer with a **GPU** for heavy jobs?
   5. Do you use **OpenRouter** (free models)?
   6. Where should the notes vault live? (suggest `~/second-brain`)
   7. Which language for notes and replies?
   8. What are the **two main areas** where you use Claude? (for example studying and a part-time job) They become the two starting topic sessions.
3. Create `SBK_HOME` and write `SBK_HOME/config.json`:
   `{"vault": "<VAULT absolute path>", "language": "<lang>", "tools": {"second_claude": false, "codex": false, "gemini": false, "colab_gpu": false, "openrouter": false}, "modes": {}}` with `true` only for the tools the user said yes to.

**Check:** `python -c "import json,os;print(json.load(open(os.path.expanduser('~/.claude/sbk/config.json')))['tools'])"` prints the tool answers you were given.

## Step 1 - Install the command-line tools

1. Create `SBK_HOME/{bin,hooks,managers,inbox,logs,state,entry}`.
2. Copy `KIT/entry/ledger.py`, `send.py`, `alarm.py`, `status.py`, `worker.ps1`, `worker.sh` into `SBK_HOME/bin/`. (Always copy, do not rely on the plugin cache path: it changes when the plugin updates. After an update, copy again.)

**Check:** `python SBK_HOME/bin/ledger.py add "setup check"` prints `L0001`; then `python SBK_HOME/bin/ledger.py done L0001 --evidence "setup step 1 check ran"` prints `L0001 done`; `ledger.py list` prints `nothing open`.

## Step 2 - Principles (`CLAUDE.md`)

1. Read `KIT/templates/CLAUDE.md`. If the user's language is not Traditional Chinese, translate it faithfully (keep the structure and meaning; keep it under 100 lines).
2. If `~/.claude/CLAUDE.md` does not exist, create it with the content. If it exists, show the user what you would add and, after a yes, append it between the lines `<!-- sbk:begin -->` and `<!-- sbk:end -->`. Never remove or reorder their existing text.

**Check:** the file contains both markers; the block between them has fewer than 100 lines.

## Step 3 - The notes vault

1. Create `VAULT` with the area and category folders from `KIT/templates/筆記格式.md` section 1 (translate folder names only if the user wants; keep the `NN-NN` / `NN` numbers).
2. Copy into the vault, replacing `{{date}}` with today's date (`YYYY-MM-DD`):
   - `templates/AGENTS.md` -> `VAULT/AGENTS.md`; and `VAULT/CLAUDE.md` containing exactly one line: `@AGENTS.md`
   - `templates/筆記格式.md` -> `VAULT/00-09 系統與索引/01 規則/01-01 筆記格式.md`
   - `templates/todo-for-me.md` -> `VAULT/00-09 系統與索引/02 收件匣/02-02 我要做的事.md`
   - an inbox note `VAULT/00-09 系統與索引/02 收件匣/02-01 收件匣.md` with valid frontmatter (`type: log`, `status: active`, a one-sentence summary, today's dates, `origin: agent-drafted`) and one line saying "Put anything not yet filed here."
   - `templates/sbk-protect.txt` -> `VAULT/.sbk-protect`; an empty file `VAULT/.sbk-vault`
   - `KIT/scripts/{vault_lint.py,gen_jdex.py,check_overwrite.py,pre-commit}` -> `VAULT/scripts/`; on macOS/Linux `chmod +x VAULT/scripts/pre-commit`.
3. Translate the copied Chinese notes if the user wants another language (keep field names and values such as `type: skill` exactly, as the lint depends on them).
4. `python VAULT/scripts/gen_jdex.py --root VAULT` to create the index.
5. `git init` in `VAULT`; if `git config user.name` is empty, ask the user for a name/email and set them for this repo only. `git config core.hooksPath scripts`. Add the files by name and make the first commit "Initial vault".
6. Optional, with a yes: interview the user with five short questions about themselves (what they study or do, current goals, how they like replies, what annoys them about AI) and save the answers as `VAULT/10-19 自己與生活/11 .../11-01 關於我.md` with `type: profile`, `origin: user`, using their words. Do not invent facts.

**Check:** `python VAULT/scripts/vault_lint.py --root VAULT` ends with `RESULT: PASS`; the first commit exists (`git -C VAULT log --oneline`); and the pre-commit hook really runs: stage a copy of a note with most lines deleted in a scratch branch and confirm the commit is refused (then reset). If it does not refuse, fix `core.hooksPath` before going on.

## Step 4 - Guard hooks

Installed as a plugin, `KIT/hooks/hooks.json` is already active; check with `/hooks` that Stop, PreToolUse, UserPromptSubmit and SessionStart entries from second-brain-kit are listed. Cloned manually: copy `KIT/hooks/*.py` and `run.sh` to `SBK_HOME/hooks/`, then (after a yes from the user, because it edits settings) merge the `hooks` block of `KIT/templates/settings.hooks.example.json` into `~/.claude/settings.json`, replacing `__KIT__` with the `SBK_HOME/hooks` path. Merge, do not replace: keep every hook the user already has.

What each one does (tell the user in one line each):
| Hook | Effect | Default mode |
|---|---|---|
| `stop_evidence` | Said "done" after editing but never looked at the result: asks for evidence, once | block once |
| `requests_reinject` | After compaction, puts the user's own messages back word for word | warn |
| `read_whole` | Refuses `head`/`tail`/`sed -n` on vault notes; read the whole note | deny |
| `vault_guard` | Asks before git push, `--no-verify`, destructive git, big deletes, protected-file edits | ask |
| `usage_warn` | Warns once when weekly plan usage passes 80% (never blocks) | warn |
| `inbox_notice` | Shows a topic session what the entry sent it | warn |

Modes can be changed without editing code: `SBK_HOME/config.json` -> `"modes": {"stop_evidence": "log"}` (values: off, log, warn, ask, deny, block). Every decision is also written to `SBK_HOME/logs/<hook>.log`.

**Replay before you trust it.** Find the user's recent transcripts (`~/.claude/projects/*/*.jsonl`, newest five) and run `python KIT/hooks/stop_evidence.py --replay <file>` on each. If more than about one turn in four is flagged, the check is too noisy for this user: set `"stop_evidence": "log"`, tell the user, and plan a review of `logs/stop_evidence.log` after a week. Then run `python KIT/scripts/selftest.py`.

**Check:** `selftest.py` prints `0 failed`; replay ran on at least one transcript (or you wrote down that none exist yet).

## Step 5 - Entry session and two topic sessions

1. `SBK_HOME/entry/CLAUDE.md` <- `templates/entry-CLAUDE.md`, with `{{vault}}` replaced.
2. For each of the two areas from Step 0: pick a short ASCII id (for example `study`, `work`), create `SBK_HOME/managers/<id>/`, put `templates/manager-CLAUDE.md` in as `CLAUDE.md` (fill `{{manager}}`, `{{vault}}`, `{{scope}}` with a one-line description of the area in the user's words) and `templates/task.md` in as `task.md` (fill `{{topic}}`).
3. `SBK_HOME/routes.md` <- `templates/routes.md`: fill the table with the two ids and 5-10 keywords each (words the user would really say). `SBK_HOME/alarms.md` <- `templates/alarms.md`. `SBK_HOME/channels.md` only if the user has extra tools (Step 7).
4. Tell the user how to start them (once, written to `SBK_HOME/START-HERE.md` too):
   - entry: `cd ~/.claude/sbk/entry` then `claude --add-dir "<VAULT>" -n entry`
   - topic: `cd ~/.claude/sbk/managers/<id>` then `claude --add-dir "<VAULT>" -n <id>`
   - All new requests go to the entry. They can add a topic session later by copying a manager folder and adding a row to `routes.md`; start with two and add one only when a topic keeps crowding another.

**Check:** `python SBK_HOME/bin/send.py <id> "setup check"` prints `L0001 -> <id>` (or the next number); `SBK_HOME/inbox/<id>.md` contains the line; `SBK_HOME/bin/status.py` shows it; then close the test item: `ledger.py drop L000N --evidence "setup test item"` and tick the inbox line `[x]`.

## Step 6 - Alarms

1. Explain in one sentence: a small table of reminders that land in the ledger or a topic inbox; the default row is a weekly review on Sunday 20:00. Keep it short; every row must lead to an action.
2. The runner needs the system scheduler to call it every 5 minutes. This changes the system, so ask first ("OK to add a scheduled task that runs `alarm.py --tick` every 5 minutes?"). After a yes:
   - Windows: `schtasks /Create /SC MINUTE /MO 5 /TN sbk-alarm /TR "\"<path to pythonw.exe>\" \"%USERPROFILE%\.claude\sbk\bin\alarm.py\" --tick"` (use `pythonw.exe` so no window flashes)
   - macOS/Linux: add `*/5 * * * * python3 "$HOME/.claude/sbk/bin/alarm.py" --tick` to `crontab -e`.
   If they say no, alarms simply do not fire; `alarm.py --fire A01` still works by hand.

**Check:** `python SBK_HOME/bin/alarm.py --list` shows the default row; `schtasks /Query /TN sbk-alarm` (or `crontab -l`) shows the entry; `alarm.py --tick --now <next Sunday 20:01>` writes a ledger item (then drop that test item with evidence, and delete `SBK_HOME/state/alarms.json` so the real run starts clean).

## Step 7 - Extra tools (only the ones the user said yes to)

If every answer was "no", skip this step and say so in the final report. Otherwise, for each yes read the matching section of `docs/MULTI-TOOL.md` (it is reference material: take what fits) and:
1. Create `SBK_HOME/channels.md` from `templates/channels.md` with one row per tool.
2. Second Claude account: have the user run `/login` once with `CLAUDE_CONFIG_DIR` set to a new folder for that account (give them the exact command for their OS), then test `entry/worker.ps1 -DryRun` or `SBK_DRYRUN=1 worker.sh` and read the printed command.
3. Codex / Gemini / Colab / OpenRouter: confirm the tool launches (version command or a one-line job).
4. Run one tiny real job per tool whose result is a file, and open the file.

**Check:** each enabled tool has a row in `channels.md` and a result file you opened. Tools the user did not choose appear nowhere.

## Step 8 - Final verification and handover

1. `python KIT/scripts/selftest.py` -> `0 failed`; `vault_lint.py` -> PASS; `status.py` runs.
2. Write `SBK_HOME/START-HERE.md` (user's language, under 30 lines): the two start commands, `status.py`, `ledger.py add/list/done --evidence`, how to add a topic session or an alarm, how to switch a hook mode, and where the logs are.
3. Final message to the user, short, in their language: what is installed and where; what each hook will do to them in practice (so a block does not surprise them); what you did NOT do and why; what only they can do (if anything). Per step: done / not done.

## Updating and removing

- Update: update the plugin (or `git pull` the kit), then redo Step 1 (copy tools) and, for a manual install, Step 4's copy. Do not touch the user's notes, `task.md` files, ledger, routes or alarms.
- Remove: remove the markers block from `CLAUDE.md`, remove the hook entries (or the plugin), delete the scheduler entry. Ask before deleting `SBK_HOME` or the vault; those hold the user's data.
