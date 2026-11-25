# Notes folder handbook (for any AI working in this folder)

This is the user's second brain: numbered markdown notes plus a tracker (open work, one item per line; each closed with a note of how it was checked). You are here to read, find, record and tidy it. Read this whole page first. The user does not need to know numbers, commands or formats; you handle them.

Language: notes and replies are in the user's language (`language` in `~/.sbk/config.json`); keep folder names, field names and field values exactly as they are. Internal work (task.md, tracker items, hand-overs, prompts for other sessions) is in English; the user's words stay verbatim.

**Step one of every task: check the second brain first** - the tracker, the JDex, the related notes, and the 和 AI 協作 note (`00-09 系統與索引/03 和 AI 協作/03-01 和 AI 協作.md`): read its sorted preferences first, then its recent lines (what the user corrected and which ways of working they confirmed). Use earlier decisions and methods; then start.

## First three things
1. Open `00-09 系統與索引/00 索引/00-01 JDex 索引.md`: every number in the folder, how many notes each category has, the next free number.
2. To find something: read the one-line summaries in the JDex, then search by keyword; open what you find and read it to the last line.
3. Before writing a new note or changing a format: read `00-09 系統與索引/01 規則/01-01 筆記格式.md`.

## Continuing earlier work
- When the user mentions earlier work ("that project from last time", "my chapter 3 notes"): look at the tracker (next section), then the JDex and the related notes, and answer only after reading them. Do not load the whole folder or a whole old conversation.
- If you cannot find it, say so and where you looked; never fill in from memory.

## The tracker (ledger.py)
One file lists what the user asked for that is not finished yet, one item per line, so it is found again in a new conversation. It lives at `~/.sbk/ledger.md`; change it only with these commands. The user never types any of them.
- A request that will not be finished in this reply, or will be continued later: `python ~/.sbk/bin/ledger.py add "[topic] the user's words or a one-line summary"` and tell the user the id (for example L0003). A question answered at once is not recorded. `[topic]` is one or two words for which piece of work this is (for example `[study]`, `[job]`), the same word every time; a deadline goes into the text as `due YYYY-MM-DD`. The weekly check counts "how many different pieces of work" and "anything overdue" from these two marks.
- Done: look at the real result first, then `python ~/.sbk/bin/ledger.py done L0003 --evidence "what you opened and what you saw"`. No evidence, no closing. The evidence is for the next session (and in Full the entry) to check; tell the user only the result (what was done, where to see it, what was not verified) and give the evidence if they ask.
- The user drops it: `python ~/.sbk/bin/ledger.py drop L0003 --evidence "user said drop it"`.
- The user asks "what is still open?": run `python ~/.sbk/bin/status.py` and answer from its output, not from memory.
- One large job (many steps, or three or more requirements) gets its own `~/.sbk/task.md`, in the format of `~/.sbk/task-template.md`, with the tracker id on the goal line; only one at a time. When finished, check every item, then rename it `task-L0003-done.md` and keep it.

## What goes into notes and what does not
| Content | What to do |
|---|---|
| Something the user says to "remember" or "save" | Save it as a note; tell the user the file name |
| A confirmed decision (for example which method a project uses) | Update the related note |
| Organised learning material | Save it in its category |
| Your guess, not confirmed | Write "to be confirmed", `origin: agent-inferred`; never as fact |
| Small talk | Not saved |
| Passwords, keys, codes, ID numbers | Never saved (notes are plain unencrypted text) |
| Personal data (health, family, contact details) | Not collected; saved only when the user says so, `origin: user` |
| Corrections and confirmations of your work | One line in the 和 AI 協作 note (below), at once |

## Map of the folders
- `00-09 系統與索引`: the index, the rules, the inbox (`02 收件匣`: things not filed yet and the user's own to-dos), and `03 和 AI 協作` (the learning loop: one line per correction or confirmation, written the moment it happens with `python ~/.sbk/bin/learn.py add correction|confirmed "<kind>" "<the user's words>"`; sorted preferences at the top, written only after the user agrees in a weekly review).
- At first only the one or two areas the user uses and `90-99 封存` exist. Other areas (full list in section 1 of the format note) are created when the first note needs them; categories too.
- `90-99 封存`: notes no longer used but kept.
- `scripts/`: lint, the JDex generator, the pre-commit check. Do not edit by hand; ask first.

The JDex is the truth about which areas and categories are in use.

## Names and format (the essentials)
- File name `AC-NN title.md`: AC is the two-digit category number, NN the running number inside the category, joined by a hyphen.
- Every note starts with frontmatter: type, status, summary, created, modified, origin.
- `summary` is one sentence saying what the note is; the JDex and search depend on it.
- Link notes with `[[file name]]` (without .md).

## Reading
- Never conclude from head/tail or the first lines; read the whole note with Read, in consecutive parts if it is long.
- Say "read it all" only when you did; say what you did not read.
- Facts in notes can be stale: look at `modified` and `valid_until`; when stale or contradicting, tell the user instead of silently picking one.

## Writing
- Change only what must change; never rewrite a whole note. Set `modified` to today.
- A new note takes the JDex's next free number; afterwards run `python scripts/gen_jdex.py` to refresh the index.
- `origin`: `agent-inferred` for anything uncertain, `user` for what the user said. Never write a guess as the user's words; this field is what keeps "the user said" apart from "the AI inferred".
- A note no longer used: `status: archived` and move it to `90-99 封存`. Never delete.
- Protected, ask the user before changing: this AGENTS.md, CLAUDE.md, the `01 規則` folder, `scripts/`.
- Before tidying the whole folder run the lint, and again afterwards; ERROR must be 0 (how to tidy: the `vault-tidy` skill).

## Before you stop
1. `python scripts/vault_lint.py`: ERROR must be 0; explain or fix each WARN.
2. `python scripts/gen_jdex.py`: the index is refreshed.
3. Say what you did: which notes were added, changed or moved (file names), which tracker items were closed or added.

## Commits
`git commit -m "message" -- <the files you changed>`: commit only the files you changed, never `git add -A`, never skip hooks. Git here is only the local history of changes; nothing is pushed unless the user says so.
