# Reference: working with several AI tools

> **For the configuring Claude to consult. Not mandatory.** The default setup is ONE Claude account and nothing else. This is part of the Full plan ([ADVANCED.md](ADVANCED.md), A5). **No tool has a fixed role here:** models get better and cheaper all the time, so the kit only gives rules by kind of work; which tool does which kind of work is the user's own table (`~/.claude/sbk/channels.md`), filled by their Claude at install from the accounts they have and re-checked every month or when a new model comes out. Read only the lesson sections for tools the user said they have. Every lesson was measured or went wrong in real use, in one person's setup in 2026; re-measure before relying on it.

## Ground rules for every extra tool

1. **Split by kind of work, never by failure.** Decide in advance which jobs go where. Do not build "when account A hits its limit, silently continue on B": consumer terms forbid getting around usage limits, and it hides how much you really use.
2. **Show the state where work is assigned.** If a tool can be locked out by quota (see Antigravity, Codex), keep a one-line status in `~/.claude/sbk/channels.md` (tool, what it is for, locked until) and look at it before sending work. A queue that silently stops is worse than no queue.
3. **Send a task file, get a file back.** Every job is a task file (goal, inputs with full paths, output path, "not doing", how you will check it). The result is a file you open yourself; you do not trust "done" from the other tool (see `evidence-before-done`).
4. **Personal data stays on the tools you trust with it.** Free tiers and third-party routers are for work that contains no credentials, no private records, nothing you would not post publicly.
5. **Pick by kind of work, then by "best right now and has quota".** Name the kind of work first (table below), then use the tool that is currently best for it among the ones the user has and that still has quota. Do not hard-wire a model to a job: when a better or cheaper model comes out, the table changes, not the rules.
6. **Ask a second opinion blind.** When you want another model's view on a direction, send only the requirements and the facts, not your own plan or preference, then compare. Otherwise it tends to agree with you.

## Kinds of work

General rules only. The concrete "which tool now" goes in the user's `channels.md`.

| Kind of work | Examples | What makes a tool the best choice right now |
|---|---|---|
| Mechanical batch | move or rename files, bulk edits, scan and compare, run scripts and wait, upload and read back | Reliable at following a task file exactly; cheapest per job; its own quota, so the main conversation is not slowed. Low reasoning effort. |
| Judgement | decisions, anything other people will read, hard debugging, anything personal | The strongest model the user has, with the conversation's context, on an account trusted with private data. |
| Long reading | a pile of papers or logs, a long transcript, a first draft from a lot of text | The largest context window that is cheap per token and still has quota; private data only to accounts trusted with it. |
| Heavy compute | training, rendering, big data runs | A GPU or runtime with free capacity; a second machine is for running in parallel, not for speed. |
| Independent review | a second opinion on a direction, checking finished work | A different model (ideally another company's) that has not seen your plan: send it only the requirements and the facts. |

## Filling and re-checking the table

- **At install (A5):** for each kind of work, write in `channels.md` the tool the user has that is best for it now, with one line of why and today's date. A kind with no extra tool stays on Claude. Only accounts the user said they have.
- **Every month (Full: alarm row `T01 | monthly 1 10:00 | maintenance | ...`) and whenever the user says a new model came out:** the maintenance session re-checks each row - what each of the user's tools offers now (the providers' own model and pricing pages), whether a newer model is better or cheaper for that kind of work, which accounts still exist and have quota - updates the rows that changed and closes the tracker item with what it looked at.
- **When sending a job:** read the row for its kind, check "locked until"; if that tool is locked or out of quota, pick the next best one on purpose and say so. Never switch silently.

## Lessons from specific tools

Measured or seen in one setup in 2026. They are notes on how each tool behaves, not roles: what a tool is "good for" changes with every model release, so decide with the table above.

## Second Claude account (quota pool)

- **What it adds:** a second pot of quota that you legitimately own - for example a second subscription - used for background jobs so your main account stays free for conversations.
- **Send:** long background jobs with a clear task file (research, bulk edits, batch checks).
- **How:** run the job with `entry/worker.ps1` (Windows) or `entry/worker.sh` with the second account's config folder. The launcher sets `CLAUDE_CONFIG_DIR` to that folder and clears `CLAUDE_CODE_OAUTH_TOKEN` and `ANTHROPIC_API_KEY`; if either variable stays set it overrides the login and the job quietly runs on the wrong account. First log in once per account: start `claude` with that `CLAUDE_CONFIG_DIR` and run `/login`.
- **Lessons:**
  - Split by task. Do not auto-switch on a limit (rule 1).
  - The hooks read usage per config folder, so each account has its own warning.
  - A pool that is mostly idle is wasted: look at both accounts' weekly usage when planning a big job, and put long background work on the one with room.

## Claude in Chrome (browser extension)

- **What it adds:** acting in the user's real browser with their sign-ins.
- **Lessons:**
  - It belongs to the account that is signed in to the extension. A job that runs on another account cannot use it.
  - An environment token (`CLAUDE_CODE_OAUTH_TOKEN`, made by `claude setup-token`) disables it in `claude -p` runs. Jobs that need the browser must run with `--chrome` and without that variable (`worker.ps1 -Chrome`).
  - Automated browser jobs leave tabs and windows open and they pile up. End every browser job with "close what you opened, leave what was already open", and check the tab count yourself afterwards.

## Codex CLI (ChatGPT subscription or API key)

- **Seen used for (2026):** mechanical runs (move/rename files, batch edits, scan and compare, run scripts and wait for results, upload and read back) and a fresh pair of eyes that has not seen your conversation.
- **How:** `codex exec --sandbox read-only --skip-git-repo-check "<task file or request>"` for read-only checks; drop `--sandbox read-only` only for jobs that must write, with the target folder named in the task file. Use low reasoning effort for mechanical work (it is faster and uses much less of the limit).
- **Limits:** it has a 5-hour window and a weekly limit. Check before queuing a big batch and write the lock time in `channels.md` if you hit it.
- **Lessons:**
  - Do not poll it from the foreground in a loop; start it, do other work, read the result file.
  - Open the result yourself; "finished" from the tool is not evidence.
  - Judgement work (decisions, text for other people, hard debugging) goes to whatever the table names for "judgement", not to the tool that happens to be running.

## Gemini: website, Antigravity, API

- **Web chat (free):** a second opinion. Ask blind (ground rule 6).
- **Antigravity (an IDE with Gemini agents):**
  - Seen used for long reading and first drafts at no cost to the Claude quota (2026). Hand over work as a task file in a shared folder and read the output file it writes.
  - Its quota can lock for about 6 days once used up. A job queue then stops without any error. Put the lock time next to wherever work is assigned (`channels.md`) and check it before sending anything; if it is locked, route the job elsewhere on purpose.
- **Gemini API (pay as you go):**
  - Use it last. Failed calls can still hold reservations that count against the budget.
  - One large table was sent again and again (7+ times) and used about half of a month's budget. Send only what changed since the last call; keep the stable part in a file and refer to it.
  - Set a spending cap on the account before the first call.

## Colab or a local GPU

- **What it adds:** a second GPU running in parallel with your own.
- **Lessons:**
  - The free T4 was not faster than a laptop RTX 4060 for the same model (118 ms/step versus 103.5 ms/step). Colab's value is running a second job at the same time, not running one job faster.
  - An idle runtime disconnected after about 80 minutes and everything in `/content` was lost. Write checkpoints and outputs to Google Drive from the start, and copy results back before you walk away.
  - Keep the run script and the data on Drive so a new runtime can resume.

## OpenRouter free models

- **Seen used for (2026):** mechanical text work with no personal data (reformatting, classifying public text, first-pass summaries of public pages), at volume.
- **Never send:** credentials, private records, anything the user would not publish. Free tiers may log prompts.
- **Lessons:** free models change and disappear; list the model in the task file and check it answers before queuing a batch. Verify outputs by sampling.

## Small local models

- Cheap and private, but unreliable on counting and exact bookkeeping: a small local model miscounted a simple log job (9 instead of 26). Use them for rough sorting only, and do exact counts with a script.

## Web ChatGPT / web Gemini as second opinion

- Free, takes two minutes. Write the requirements and facts in a file, give no hint of your own answer, and ask for their approach. Compare with yours; where they differ, work out why before choosing. Use it for direction-setting, not for routine work.

## Enabling a tool (for the configuring Claude)

For each tool the user has, and only those:
1. Add the account to `~/.claude/sbk/channels.md` ("Accounts the user has"): tool, account or plan, how to call it, "locked until" (empty at first).
2. Fill "Kind of work -> tool now" for every kind (see "Filling and re-checking the table"); a kind with no better tool stays on Claude.
3. Run one tiny real job end to end (a task file that asks for one line written to a file) and open the file. Only then tell the user it works.
4. Full: add the monthly re-check row `| T01 | monthly 1 10:00 | maintenance | Re-check channels.md: best tool per kind of work, new models, quota |` to `alarms.md` (create it from the template if missing).
