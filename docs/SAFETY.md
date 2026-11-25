# Safety and your data

[繁體中文](zh-TW/安全與資料.md) · [Back to the README](../README.md)

The nine safety checks and where your data lives.

## The safety checks

The safety checks (hooks) are small programs Claude Code runs automatically, for example before Claude pushes to the internet or deletes a folder. They watch both shell tools Claude uses (Bash, and PowerShell on Windows). On Windows they need Git for Windows; if it is missing they stay off and nothing is blocked. What each one does:

- `vault_guard` - asks you before Claude pushes, deletes a whole folder, throws away git work, skips git checks, changes protected rule files or shrinks a note to a fraction of it. Basic: on.
- `read_whole` - in the notes folder, refuses a shell command that reads a note through `head`/`tail` and the like, and when Claude's Read of a note stops before its last line, tells it which lines it has and to read the rest. Basic: on.
- `requests_reinject` - when a long conversation is summarised, puts your own messages back word for word; when it gets too long, tells Claude to write a hand-over and you to start a fresh one. Basic: on.
- `stop_evidence` - notices when Claude says "done" after a change without looking at the result. Basic: on, writes a log line only.
- `level_notice` - about once a week, asks one yes/no question when what happened to you shows another part would help, and runs the light weekly review of the 和 AI 協作 lines (it proposes; nothing changes before your yes). Basic: on.
- `learn_notice` - when your message reads like a correction or a confirmation, reminds Claude to write one line in the 和 AI 協作 note; when a conversation starts, puts your sorted preferences into it, so they are followed without Claude having to remember to look. Basic: on.
- `inbox_notice` - shows the work waiting in a Full session's inbox, and in the entry the work done and waiting for its check. Basic: off (on with the Full sessions).
- `usage_warn` - warns once when your weekly Claude usage passes 80%. Basic: off (on if you ask).
- `vault_snapshot` - when each reply ends, commits the notes Claude changed in the notes folder (local git only, never pushed), so an older version can be brought back. Basic: on.

## Where your data lives

- **Your notes:** the folder you chose (suggested: `second-brain` in your home folder). Plain text files you can open with any editor.
- **The tracker, logs and settings:** in a settings folder in your personal folder (`~/.sbk/`; before 0.2.5 it was `~/.claude/sbk/`, which keeps working until you move it; `~` means your personal folder, for example `C:\Users\your-name` on Windows).
- **Your own words, kept for long conversations:** when a long conversation gets summarised, the kit puts your own messages back word for word and keeps a copy in `requests` in the same settings folder, on this computer only.
- **Whether it reads your conversations:** only if you said yes at install. At install it only counts in how many different folders you used Claude in the last two weeks and whether a conversation got so long it was summarised twice or more; after that, about once a week, it looks only at conversations in your notes folder and counts how often you asked Claude to remind you or said things got mixed up. Yes or no, it counts the open items in the tracker and the done-check's log. Everything is counted on this computer and no setting is changed.
- **History:** the notes folder uses git, a tool that keeps the history of changes on this computer: when each reply ends, the notes Claude changed are committed (the `vault_snapshot` check), so an older version can be brought back. It is **not a backup**: if the disk dies, the history dies with it. Copy the notes folder to another disk or a cloud drive you trust from time to time.

The kit uploads nothing to GitHub (a website for code), sends nothing anywhere, and hands nothing to outside resources you did not tick. Claude itself is an online service, as always: what you tell it goes to Anthropic, the same as any Claude use.
