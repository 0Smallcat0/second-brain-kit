---
name: setup-second-brain
description: Set up, repair or extend the second-brain-kit on this computer - a notes folder Claude keeps in order, one work list, safety checks and short principles. Installs Basic by default; turns on Advanced parts (topic sessions, reminders, extra tools) only when the user asks or agrees. Use when the user asks to install, set up, configure or repair their "second brain" or this kit, pastes the install sentence from the README, or runs /sbk-setup.
---

# Set up the second-brain kit

You are the configuring Claude. The user is probably not technical: you do the work; they answer a few questions and say yes or no to changes on their system.

1. **Find the kit.** It is the folder that contains `.claude-plugin/plugin.json` with `"name": "second-brain-kit"`. Installed as a plugin it is `${CLAUDE_PLUGIN_ROOT}`. Otherwise search the plugin cache under `~/.claude/plugins`, then the current folder and its parents. If it is not on this computer at all, `docs/SETUP.md` Step 00 says how to get it (the URL is https://github.com/0Smallcat0/second-brain-kit).
2. **Read the setup file in full**: `docs/zh-TW/SETUP.md` if the user writes in Chinese, otherwise `docs/SETUP.md`. Both have the same steps.
3. **Follow it step by step**, running each step's check before going on. It is the only place that lists the questions and the steps; do not ask anything it does not ask.
4. **Advanced parts** (topic sessions, reminders, usage warning, blocking the done-check, extra AI tools) are not installed by default. Turn one on only when the user asks for it or agrees to your suggestion; the steps are in `docs/ADVANCED.md` (`docs/zh-TW/進階功能.md`).
