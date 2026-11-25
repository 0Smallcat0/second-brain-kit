# What it does, day to day

[繁體中文](zh-TW/指南.md) · [Back to the README](../README.md)

What Basic does, what comes ready and what grows, how to use it, and when Claude suggests more. Moved here from the front page, wording unchanged.

## What Basic does for you

Basic is the part that is always installed. Compared with Claude Code on its own:

- **Your notes are found again in a new conversation.** Say "remember this" today; next month a brand-new conversation finds it. Before every task Claude checks the notes first.
- **One tracker** (`ledger.py`). Claude writes down what is still open, so you do not have to. It closes an item only with a note of how it was checked; that note is for the session that checks the work later, not for you: you just get the result.
- **Done-check: a reminder for Claude to look at the result before it says "done".** When it says done without looking, Basic writes that down but does not stop it (you can turn on stopping later).
- **It asks before the risky things.** Before pushing to the internet, deleting a whole folder, throwing away git work, skipping git checks, changing the protected rule files, or shrinking a note to a fraction of it, Claude stops and asks you. Deleting or moving a single note is left to Claude Code's own permission prompts, and every change to your notes is committed to the notes folder's own history, so an older version can be brought back.
- **Your own words come back when a chat gets long.** In a long conversation Claude Code automatically squeezes older parts into a summary, and details can get lost; the kit puts your own messages back word for word, which lowers the chance that a request gets lost. When a conversation gets very long, Claude writes a hand-over and tells you to start a fresh one; the new conversation finds the hand-over by itself, so you do not have to say anything.
- **Claude learns from you (you give the skeleton, use grows the rest).** When you correct it or confirm it did something right, a small check (`learn_notice`) reminds it to write one line in a note (和 AI 協作: date, your words, what kind of thing it was). Once a week, at the first conversation of the week, it groups those lines by kind and proposes preferences (and, for a mistake that keeps coming back, a skill or a check); nothing is written until you say yes. Every new conversation starts with those preferences already in it (the same check puts them there), and before a task Claude also reads the recent lines.

## Ready on day one, and what grows with use

**It comes with the kit (nothing to learn first):**
- **Working principles.** With your OK, setup adds a short block to Claude's rules for all projects: work for your benefit within the real rules, no warnings or caveats you did not ask for, judge by what got done and not by what was said, and never invent a source or a "done". It also puts in the four failures Claude checks before every reply: saying "done" when it is not; fixing one thing and dropping another; pointing out a problem and stopping; skipping data it has.
- **12 starter preferences** in the 和 AI 協作 note: general ways of working from the kit's original author (for example: prepare everything up to your last step; change only what you asked and say what you changed; give one numbered list when you must act). Each ends with "(from the original author; delete if you like)". They apply from the first conversation. Delete any line that does not fit you, or tell Claude "not this one".
- **Four general skills** that Claude picks up when the job fits: `evidence-check` (before it states a number, or says something is missing or broken), `outward-docs` (before it writes something others will read for you), `blind-three-way` (before choosing a direction: independent proposals, compared side by side) and `full-reader` (reads long material to the last line and reports where it stopped).

**It grows with use (and is yours):** your own preferences, written after your corrections and your yes, always above the starter ones; ways that worked, added to the matching skill; a check for a mistake that keeps coming back; your notes and the tracker. Nothing you did not agree to is changed, and the starter lines are never counted as yours.

## Basic and Full

| | Basic | Full |
|---|---|---|
| Sessions | One, in your notes folder | Two fixed: **entry** (the only one you talk to) and **maintenance** (the kit itself and the weekly learning loop), plus one per subject of yours that the entry starts and sends work into |
| Checking "done" | Claude closes items with evidence | Topic sessions report to the entry, which opens the evidence; you get one result message |
| Learning from use | `learn_notice` reminds Claude to write one line per correction or confirmation; a light weekly review groups the lines and proposes preferences, written after your yes; preferences are read before every task | The same, run by the maintenance session: preferences, skills and (only for a mistake that came back) a new check, after your yes; one trend line a week |
| Long conversations | Claude writes a hand-over; you start a fresh one | The same; long idle background sessions are replaced by a fresh one automatically |
| Reminders | None | Weekly review, a monthly re-check of your outside resources, the daily hand-over check, your own |
| Outside resources | Not used | Only what you ticked at install (other AI, Colab or Kaggle, credits), picked by kind of work |
| Suits | Starting out; a few things at a time | Several subjects that get mixed up, deadlines you forget |

Full is not one switch: each part is switched on by itself, at install or later ("Turn on topic sessions"); "Back to Basic" switches them off and keeps your files. Every part, side by side: [ADVANCED.md, "Basic and Full"](ADVANCED.md#basic-and-full).

## How to use it after

Open Claude on your notes folder, then type to Claude the way you would chat. There are two ways in; use the one you installed with:

- **Claude app:** open Claude and click the **Code** tab (top of the sidebar). In the row under the prompt box, click the first control and pick the top entry under **Local**, then click the folder control next to it, choose **Open folder…** and pick your notes folder. Next time, click that session in the sidebar to carry on; **+ New** starts a fresh one in the same way.
- **Terminal:** the shortcut Claude made for you, or without it: open the terminal, type `cd` and your notes folder's path, then `claude` (`claude --continue` returns to the last conversation).

Then say, for example:

- "Remember this: I want to finish chapter 3 this week."
- "Find my notes about linear algebra."
- "What is still open?"
- "Continue where we stopped on the project report."

## When Claude suggests more

Claude never adds a part on its own. About once a week a small script looks at the things below on your computer. It looks at **trouble you actually ran into**, not at how busy you are. When one holds, Claude asks you one question, "Turn on X?", with the numbers; it does it only after your yes. Say no and it will not ask about that again for four weeks.

- In one week you told Claude twice or more that things got mixed up (for example "you mixed up the two reports", "not that project") -> the Full sessions: an entry session you talk to, a maintenance session and one conversation per subject (topic sessions). How many open items you have, and in how many subjects, is shown with it for reference. The entry sends each job straight into the topic session that owns it and starts it if needed, within your plan's limits; you get the result from the entry. Where background sessions cannot run (for example the desktop app alone), the entry tells you which session to open.
- In one week you asked Claude to remind you twice or more, or something with a deadline is still open three days after the date -> reminders.
- Claude said "done" without looking at the result, this has been written down for two weeks or more and at least 20 times, and at least 3 of every 4 times you later said something was wrong -> it asks whether Claude should be stopped and made to check first.
- You told Claude you have an outside resource (another AI account, Colab, Kaggle, cloud credit) -> a table for splitting work with it by kind of work. Just naming one in a conversation does not count.

You can also ask for any of them at any time, and for a usage warning (a heads-up when your weekly Claude usage is nearly used up). Details in [docs/ADVANCED.md](ADVANCED.md); it also has the full Basic and Full comparison and six pictures of how the parts fit together.
