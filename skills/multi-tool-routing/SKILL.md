---
name: multi-tool-routing
description: Rules for splitting work across extra AI tools the user has (a second Claude account, Codex, Gemini, Colab or a GPU, OpenRouter, web chats) by kind of work, never by fixed model roles - the user's own table in ~/.claude/sbk/channels.md says which tool does what now, filled at install and re-checked monthly or when a new model comes out. Full plan, optional: use it only for tools the user said they have, while configuring, during the monthly re-check, or when deciding where a big job should run. Not used by Basic (one Claude account).
---

# Multi-tool routing (reference, not mandatory)

The default setup is one Claude account. Use this only for tools the user said they have (the optional sentence at setup, or later). If they have none, stop reading.

1. Read `docs/MULTI-TOOL.md` in the kit root: "Ground rules", "Kinds of work", "Filling and re-checking the table", and only the lesson sections of the tools the user has.
2. No tool has a fixed role. Models change; which tool is best for a kind of work is decided per user, in `~/.claude/sbk/channels.md` ("Kind of work -> tool now"), from the accounts they have.
3. When deciding where a job should run: name its kind (mechanical batch / judgement / long reading / heavy compute / independent review), read that row of `channels.md`, check "locked until"; if that tool is locked or out of quota, pick the next best one that has quota, on purpose, and say so.
4. Fill the table at install (A5) and re-check it monthly (Full: alarm row T01 to the maintenance session) and when the user says a new model came out.
5. Non-negotiables, even if you skip the rest:
   - Split by kind of work. Never build automatic failover from one account to another when a limit is hit.
   - Free tiers and routers never get credentials or private records.
   - A job is a task file (the worker scripts call it a brief) in and a result file out; you open the result yourself before reporting it done.
   - Send a second model only requirements and facts, never your own plan, when you want an independent opinion.
   - Tools that lock out by quota (Antigravity can lock for days) get their lock time shown where work is assigned.
6. To enable a tool, follow "Enabling a tool" at the end of `docs/MULTI-TOOL.md` and finish with one tiny real job whose result file you open.
