# Install details

[繁體中文](zh-TW/安裝.md) · [Back to the README](../README.md)

What to have before you start, what happens after you paste the sentence, and the manual way. The sentence itself is on the front page.

## Before you start

- **Cost:** the kit is free, but Claude Code needs a paid plan (Pro, Max, Ultra, Team, Enterprise) or a Console account (a developer account with prepaid credits); the free claude.ai plan does not include Claude Code ([official page](https://code.claude.com/docs/en/setup)). No ChatGPT, Gemini or other AI account is needed.
- **Install two things first:** [Claude Code](https://code.claude.com/docs/en/setup) (official; the Claude that works with files on your computer. If you would rather not use a terminal, the window where you type commands, get the [desktop app](https://code.claude.com/docs/en/desktop-quickstart)) and [Python 3](https://www.python.org/downloads/) (free; the kit's small tools run on it). The claude.ai chat in a web browser cannot do this.
- **How to open Claude Code:** desktop app: open Claude, sign in, click the **Code** tab. Terminal: on Windows press Start, search "PowerShell", open it and type `claude`; on a Mac press Cmd+Space, search "Terminal", open it and type `claude`. Either one works for this kit.
- **How long:** about 15-30 minutes, mostly Claude working on its own; you answer 6 questions and say yes a few times. Add 5-10 minutes if the computer still needs Python or git (a tool that records changes; Claude offers to install it).
- **What it touches:** only the folders and settings it creates itself; before it changes anything you already had (for example Claude's settings file), it asks you.
- **Changing your mind:** tell Claude "Remove second-brain-kit". It removes the kit, the block it added to your settings and the shortcut it made (terminal users only); your notes and tracker stay, and it asks before deleting them.
- **This is not an official plugin from Anthropic** (the company that makes Claude; a plugin is an add-on for Claude Code); users made it.

## What happens next

1. Claude asks you six things (plus one short question, only if it cannot tell: do you use the Claude app or a terminal?): where to keep your notes; which language to use; what you use Claude for and where you get stuck most (for example several things at once get mixed up, you often forget deadlines, you keep having to explain the background again, or it's all fine); whether it may look at your Claude history on this computer to help decide (it only counts a few numbers on this computer, uploads nothing, and "no" is fine); which Claude plan you have (Pro, Max, Ultra, Team, Enterprise or API; "not sure" is fine), so nothing runs more often than your plan allows; and which outside resources you already have, from a list to tick (another AI account, Colab or Kaggle, a GPU of your own, cloud credit, student offers such as Azure for Students or Copilot; free-to-sign-up ones are marked 可免費申請). Only what you tick is ever used.
2. **Claude suggests each part and you confirm.** Basic is always installed; for the Full sessions (entry, maintenance and one per subject), reminders, and splitting work with the outside resources you ticked, it says in one line each whether to switch it on now and why. It also suggests note areas that fit what you use Claude for. With no history, or if you say no, it goes by your answer alone; if your answer points to none of them, you get Basic. Say what to add or drop.
3. It sets everything up and asks before changing any setting you already had.
4. It runs a short check: a brand-new conversation has to find a test note and continue a test item. Then the test data is removed.
5. It shows you how to start, for the way you open Claude: in the Claude app, the exact clicks that open your notes folder (no shortcut is made); in a terminal, a desktop shortcut or two short commands. Then a two-minute first try.

## Manual install

The install sentence on the front page makes Claude run these two commands. You can type them in Claude Code yourself:

```
/plugin marketplace add 0Smallcat0/second-brain-kit
/plugin install second-brain-kit@second-brain-kit
```

Then type `/sbk-setup` in Claude Code. Or clone (download a copy of) this repository (the folder of code), open Claude Code inside it, and say: "Read docs/SETUP.md and set up second-brain-kit for me."

[docs/SETUP.md](SETUP.md) is written for Claude: ordered steps, each with a check. Like every file only Claude reads (rules, templates, setup steps), it exists only in English; Claude still talks to you and writes your notes in your language.
