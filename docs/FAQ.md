# Questions and costs

[繁體中文](zh-TW/常見問題.md) · [Back to the README](../README.md)

Common questions and the cost details.

## Questions

**The install failed.** Paste the error into Claude Code and say "Fix the second-brain-kit install". If Claude cannot add the kit as a plugin, it can download it and install it by hand (see [Manual install](INSTALL.md#manual-install)).

**A check is too strict or gets in the way.** Tell Claude, for example "The done-check is too strict, make it quieter" or "Stop asking me before X". Every check has a switch; Claude changes it for you.

**Do I need ChatGPT, Gemini, Colab or anything else?** No. One Claude account with Claude Code is enough; the kit splits work inside it (a cheaper model for mechanical jobs, a fresh helper for an independent check). At install you tick what you already have; you can add more later.

**How do I remove it?** See "Changing your mind" under [Before you start](INSTALL.md#before-you-start).

## Costs

- **The kit is free.** It uses your Claude plan like any conversation does.
- **Basic** uses only what you do yourself.
- **Full:** every topic session that is working uses your limit like a conversation; an idle one uses none. The reminder check that runs every 5 minutes only reads files on your computer and uses **none** of your limit; only starting a session or sending one a message does.
- **Limits by plan** (starting values; your Claude may change them and tells you when): Pro - 2 topic sessions at once, a reminder may start or message one at most 4 times a day, 2 hours apart; Max - 4 at once, 12 a day, 1 hour apart; Team, Enterprise or higher - 6 at once, 24 a day, 30 minutes apart; API or not sure - same as Pro. Over a limit the work waits and runs later.
- **Computer off or asleep:** nothing runs. At the next check a missed reminder runs once, marked "(late)".
