---
name: multi-tool-routing
description: Rules for using the user's outside resources (外部資源) - other AI (a second Claude account, Codex, ChatGPT/Gemini web, Antigravity, OpenRouter), compute (Colab, Kaggle, a local GPU), credits and services (Azure for Students, Copilot, API credit) - by kind of work, never by fixed roles. The user's own table in ~/.sbk/channels.md says which resource does what now; it holds only what the user ticked at install and is re-tested monthly or when a new model comes out. Also covers the one-account case (cheaper-model subagent for mechanical work, a fresh subagent for independent review). Use while configuring, during the monthly re-check, or when deciding where a big job or an independent review should run.
---

# Outside resources (reference, not mandatory)

The default setup is one Claude account. Outside resources are only what the user ticked at setup (SETUP Step 0.2) or said later; never assume one.

1. Read `docs/MULTI-TOOL.md` in the kit root: "Outside resources: one table", "The one rule", "With one Claude account only", "Kinds of work", "Filling and re-checking the table", and only the lesson sections of the resources the user has.
2. No resource has a fixed role. Which one is best for a kind of work is decided per user, in `~/.sbk/channels.md` ("Kind of work -> resource now"), from what they have.
3. When deciding where a job should run: name its kind (mechanical batch / judgement / long reading / heavy compute / independent review), read that row of `channels.md`, check "locked until"; if that resource is locked or out of quota, pick the next best one that has quota, on purpose, and say so. With one account only: mechanical work goes to a subagent on a cheaper Claude model, an independent check to a fresh subagent that never sees the original answer, heavy compute only to what the user ticked.
4. Fill the table at install (A5) from the ticked list only; mark free-to-sign-up ones 可免費申請 and explain sign-up only if the user asks. Re-test it monthly (Full: alarm row T01 to the maintenance session) and when the user says a new model came out.
5. Non-negotiables, even if you skip the rest:
   - Split by kind of work. Never build automatic failover from one account to another when a limit is hit.
   - Free tiers and routers never get credentials or private records.
   - A job is a task file in and a result file out; you open the result yourself before reporting it done.
   - Before deciding a direction, other models see only the requirements and facts, never your plan.
   - Resources that lock out by quota (Antigravity can lock for days) get their lock time shown where work is assigned.
6. To enable a resource, follow "Enabling a resource" at the end of `docs/MULTI-TOOL.md` and finish with one tiny real job whose result file you open.
