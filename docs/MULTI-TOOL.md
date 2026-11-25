# Reference: working with several AI tools

> **For the configuring Claude to consult. Not mandatory.** The default setup is ONE Claude account and nothing else. Read only the sections for tools the user said they have (see the questions in [SETUP.md](SETUP.md)). Everything here is something that was measured or that went wrong in real use; the numbers are from one person's setup, so re-measure before relying on them.

## Ground rules for every extra tool

1. **Split by kind of work, never by failure.** Decide in advance which jobs go where. Do not build "when account A hits its limit, silently continue on B": consumer terms forbid getting around usage limits, and it hides how much you really use.
2. **Show the state where work is assigned.** If a tool can be locked out by quota (see Antigravity, Codex), keep a one-line status in `~/.claude/sbk/channels.md` (tool, what it is for, locked until) and look at it before sending work. A queue that silently stops is worse than no queue.
3. **Send a brief, get a file back.** Every job is a brief file (goal, inputs with full paths, output path, "not doing", how you will check it). The result is a file you open yourself; you do not trust "done" from the other tool (see `evidence-before-done`).
4. **Personal data stays on the tools you trust with it.** Free tiers and third-party routers are for work that contains no credentials, no private records, nothing you would not post publicly.
5. **Mechanical work to the cheaper tool, judgement to Claude.** Moving files, scanning, running scripts and waiting, formatting, bulk edits: send away. Decisions, anything that goes to other people, hard debugging: keep.
6. **Ask a second opinion blind.** When you want another model's view on a direction, send only the requirements and the facts, not your own plan or preference, then compare. Otherwise it tends to agree with you.

## Which work goes where

| Kind of work | First choice | Why |
|---|---|---|
| Short questions, anything personal, final wording, decisions | Claude (main account) | You have the context; privacy |
| Mechanical batch work, script runs, fresh independent check | Codex CLI (if available) | Cheap, separate quota |
| Very long reading or a first draft from a big pile of text | Antigravity / Gemini (if available) | Saves the main quota |
| Same job as another one but on a second machine/GPU | Colab (if available) | Parallel capacity, not speed |
| Mechanical work with no personal data, very high volume | OpenRouter free models (if available) | Free |
| Direction-setting or a decision with real consequences | Claude + one blind second opinion from a web chat | Catches blind spots |

## Second Claude account (quota pool)

- **What it is good for:** a second pot of quota that you legitimately own - for example a second subscription - used for background jobs so your main account stays free for conversations.
- **Send:** long background jobs with a clear brief (research, bulk edits, batch checks).
- **How:** run the job with `entry/worker.ps1` (Windows) or `entry/worker.sh` with the second account's config folder. The launcher sets `CLAUDE_CONFIG_DIR` to that folder and clears `CLAUDE_CODE_OAUTH_TOKEN` and `ANTHROPIC_API_KEY`; if either variable stays set it overrides the login and the job quietly runs on the wrong account. First log in once per account: start `claude` with that `CLAUDE_CONFIG_DIR` and run `/login`.
- **Lessons:**
  - Split by task. Do not auto-switch on a limit (rule 1).
  - The hooks read usage per config folder, so each account has its own warning.
  - A pool that is mostly idle is wasted: look at both accounts' weekly usage when planning a big job, and put long background work on the one with room.

## Claude in Chrome (browser extension)

- **What it is good for:** acting in the user's real browser with their sign-ins.
- **Lessons:**
  - It belongs to the account that is signed in to the extension. A job that runs on another account cannot use it.
  - An environment token (`CLAUDE_CODE_OAUTH_TOKEN`, made by `claude setup-token`) disables it in `claude -p` runs. Jobs that need the browser must run with `--chrome` and without that variable (`worker.ps1 -Chrome`).
  - Automated browser jobs leave tabs and windows open and they pile up. End every browser job with "close what you opened, leave what was already open", and check the tab count yourself afterwards.

## Codex CLI (ChatGPT subscription or API key)

- **What it is good for:** mechanical runs (move/rename files, batch edits, scan and compare, run scripts and wait for results, upload and read back) and a fresh pair of eyes that has not seen your conversation.
- **How:** `codex exec --sandbox read-only --skip-git-repo-check "<brief or request>"` for read-only checks; drop `--sandbox read-only` only for jobs that must write, with the target folder named in the brief. Use low reasoning effort for mechanical work (it is faster and uses much less of the limit).
- **Limits:** it has a 5-hour window and a weekly limit. Check before queuing a big batch and write the lock time in `channels.md` if you hit it.
- **Lessons:**
  - Do not poll it from the foreground in a loop; start it, do other work, read the result file.
  - Open the result yourself; "finished" from the tool is not evidence.
  - Keep judgement work (decisions, text for other people, hard debugging) on Claude.

## Gemini: website, Antigravity, API

- **Web chat (free):** a second opinion. Ask blind (ground rule 6).
- **Antigravity (an IDE with Gemini agents):**
  - Good for long reading and first drafts at no cost to your Claude quota. Hand over work as a brief file in a shared folder and read the output file it writes.
  - Its quota can lock for about 6 days once used up. A job queue then stops without any error. Put the lock time next to wherever work is assigned (`channels.md`) and check it before sending anything; if it is locked, route the job elsewhere on purpose.
- **Gemini API (pay as you go):**
  - Use it last. Failed calls can still hold reservations that count against the budget.
  - One large table was sent again and again (7+ times) and used about half of a month's budget. Send only what changed since the last call; keep the stable part in a file and refer to it.
  - Set a spending cap on the account before the first call.

## Colab or a local GPU

- **What it is good for:** a second GPU running in parallel with your own.
- **Lessons:**
  - The free T4 was not faster than a laptop RTX 4060 for the same model (118 ms/step versus 103.5 ms/step). Colab's value is running a second job at the same time, not running one job faster.
  - An idle runtime disconnected after about 80 minutes and everything in `/content` was lost. Write checkpoints and outputs to Google Drive from the start, and copy results back before you walk away.
  - Keep the run script and the data on Drive so a new runtime can resume.

## OpenRouter free models

- **Good for:** mechanical text work with no personal data (reformatting, classifying public text, first-pass summaries of public pages), at volume.
- **Never send:** credentials, private records, anything the user would not publish. Free tiers may log prompts.
- **Lessons:** free models change and disappear; list the model in the brief and check it answers before queuing a batch. Verify outputs by sampling.

## Small local models

- Cheap and private, but unreliable on counting and exact bookkeeping: a small local model miscounted a simple log job (9 instead of 26). Use them for rough sorting only, and do exact counts with a script.

## Web ChatGPT / web Gemini as second opinion

- Free, takes two minutes. Write the requirements and facts in a file, give no hint of your own answer, and ask for their approach. Compare with yours; where they differ, work out why before choosing. Use it for direction-setting, not for routine work.

## Enabling a tool (for the configuring Claude)

For each tool the user has, and only those:
1. Add one line to `~/.claude/sbk/channels.md`: tool, what it is for, how to call it, "locked until" (empty at first).
2. Add the tool's work type to the routing notes of the topic sessions that will use it (one sentence in the manager's `task.md` Rules section).
3. Run one tiny real job end to end (a brief that writes one line to a file) and open the file. Only then tell the user it works.
