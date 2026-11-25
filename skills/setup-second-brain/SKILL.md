---
name: setup-second-brain
description: Set up the second-brain-kit working method on this computer - principles in CLAUDE.md, a numbered notes vault with lint, an entry session plus topic sessions with a ledger and alarms, and guard hooks. Use when the user asks to set up, install, configure or repair their Claude working method, "second brain", or runs /sbk-setup. Asks which AI tools the user has first and enables only those.
---

# Set up the second-brain kit

You are the configuring Claude. The user is probably not technical: you do the work, they answer a few questions and approve the steps that change their system.

## 1. Find the kit

The kit root is the folder that contains `.claude-plugin/plugin.json` with name `second-brain-kit`. Installed as a plugin it is `${CLAUDE_PLUGIN_ROOT}`; otherwise it is the folder the user cloned or unzipped. If you cannot resolve the path, search for that file (plugin cache under `~/.claude/plugins`, then the current folder and its parents).

## 2. Ask first, once, in plain words

Ask these in ONE message and wait for the answers. Default is "none of them": one Claude account is enough.

1. Do you have a second Claude account (for example a friend's plan or a second subscription you pay for)?
2. Do you have ChatGPT, and do you want to use the Codex command-line tool?
3. Do you use Gemini (website, Antigravity, or an API key)?
4. Do you have Google Colab, or a computer with a GPU you want to use for heavy jobs?
5. Do you use OpenRouter (free models)?

Also ask: where should the notes vault live (suggest `~/second-brain`), which language the notes and replies should be in, and "what are the two main areas where you use Claude?" (for example studying and a part-time job) - they become the two starting topic sessions.

Do not enable, install or explain any tool the user said no to.

## 3. Run the setup

Read `docs/SETUP.md` in the kit root in full and follow it step by step, doing the check after each step before going on. It installs everything by default (principles, vault, hooks, entry + two topic sessions, ledger, alarms). Ask permission before the steps it marks as system changes (editing `~/.claude/settings.json`, scheduler entries).

For each tool the user said yes to, also read `skills/multi-tool-routing/SKILL.md` and set up only that tool's part. Treat it as reference material, not a checklist.

## 4. Finish

Run `python <kit>/scripts/selftest.py`; report its result. Then give the user, in their language: where everything is, the three commands they will use (`/sbk-status`, `ledger.py add`, `vault_lint.py`), and what you did not do and why. Never claim a step is done that you did not check.
