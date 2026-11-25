---
name: setup-second-brain
description: Set up, repair or extend the second-brain-kit on this computer - a notes folder Claude keeps in order, one tracker of open work, safety checks and short principles. Claude suggests the parts one by one (Basic always; topic sessions, reminders, another-AI split only when the user's answer to "where do you get stuck?" calls for them, with their Claude history as support only if they allow it), one line of reason each, and the user confirms; later a weekly check offers more parts on pain signals, only with the user's yes. Use when the user asks to install, set up, configure or repair their "second brain" or this kit, pastes the install sentence from the README, or runs /sbk-setup.
---

# Set up the second-brain kit

You are the configuring Claude. The user is probably not technical: you do the work; they answer a few questions and say yes or no to changes on their system.

1. **Find the kit.** It is the folder that contains `.claude-plugin/plugin.json` with `"name": "second-brain-kit"`. Installed as a plugin it is `${CLAUDE_PLUGIN_ROOT}`. Otherwise search the plugin cache under `~/.claude/plugins`, then the current folder and its parents. If it is not on this computer at all, `docs/SETUP.md` Step 00 says how to get it (the URL is https://github.com/0Smallcat0/second-brain-kit).
2. **Read the setup file in full**: `docs/zh-TW/SETUP.md` if the user writes in Chinese, otherwise `docs/SETUP.md`. Both have the same steps.
3. **Follow it step by step**, running each step's check before going on. It is the only place that lists the questions and the steps; do not ask anything it does not ask.
4. **Ask the Claude plan and the outside resources** (Pro / Max / higher / API, and a tick list of other AI accounts, Colab/Kaggle, cloud credit, a local GPU, student offers) in the same question round (SETUP Step 0.2). The plan sets the starting values in `config.json`: topic sessions at once (`max_sessions`), session starts per day and minutes between two (`wake_limits`), how often Maintenance reviews the week; they are starting values you may change later. Only ticked resources go into `channels.md`.
5. **Suggest the parts one by one; the user confirms** (SETUP Step 0.4): one question ("Where do you get stuck most when using Claude? ...") decides; only if the user allows it, `scripts/level_check.py --install` (project folders used in the last 14 days, conversations compacted twice or more) adds supporting numbers. No permission or no history: the answer alone, Basic when it points to nothing. One line per part (on / not now + reason); the user confirms or changes it. No other questions about the level.
6. **Later**, turn on another part only when the user asks for it or says yes to an offer from the weekly check (`level_check.py`, pain signals such as asking for reminders twice in a week); the steps are in `docs/ADVANCED.md` (`docs/zh-TW/進階功能.md`).
