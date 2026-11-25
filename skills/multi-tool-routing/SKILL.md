---
name: multi-tool-routing
description: Reference for splitting work across extra AI tools (a second Claude account, Codex CLI, Gemini/Antigravity, Colab or a local GPU, OpenRouter free models, web chats). Advanced, optional: consult it only for tools the user said they have, while configuring or when deciding where a big job should run. Not used by the default Basic setup (one Claude account).
---

# Multi-tool routing (reference, not mandatory)

The default setup is one Claude account. Use this only for tools the user said they have (the optional sentence at setup, or later). If they have none, stop reading.

1. Read `docs/MULTI-TOOL.md` in the kit root, but only the "Ground rules" section and the sections of the tools the user has.
2. When deciding where a job should run, use the "Which work goes where" table, then check `~/.claude/sbk/channels.md` for lock times before sending anything.
3. Non-negotiables, even if you skip the rest:
   - Split by kind of work. Never build automatic failover from one account to another when a limit is hit.
   - Free tiers and routers never get credentials or private records.
   - A job is a task file (the worker scripts call it a brief) in and a result file out; you open the result yourself before reporting it done.
   - Send a second model only requirements and facts, never your own plan, when you want an independent opinion.
   - Tools that lock out by quota (Antigravity can lock for days) get their lock time shown where work is assigned.
4. To enable a tool, follow "Enabling a tool" at the end of `docs/MULTI-TOOL.md` and finish with one tiny real job whose result file you open.
