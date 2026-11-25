---
name: evidence-before-done
description: Before telling the user that something is finished, fixed, sent, saved or "works", look at the real result and write the evidence where it gets checked (the tracker, ledger.py), then tell the user the result. Use whenever you are about to report completion of edits, files, tests, pages, uploads, migrations or any multi-item task, and when a Stop hook asks for evidence.
---

# Evidence before "done"

"Done" means the user can rely on it without checking. A tool saying "success" is not looking at the result.

Who the evidence is for: the sessions that check the work, not the user. It goes into the tracker (`ledger.py done <id> --evidence "..."`), where a later session (in Basic) or the entry and the supervisor (in Full) open it and check it. The user sees only the result.

## The check, by kind of work

| You did | Look at |
|---|---|
| Edited or wrote a file | Open it again and read the changed part. Check the path is the one the user expects. |
| Changed code | Run it or its test. Quote the command and the last lines of output. |
| Made a page, document, slide, image | Open or render it and look at the actual output, not the source. |
| Uploaded or submitted something | Reload the page or read it back from the server; compare each field. |
| Moved, renamed or deleted files | List the folder after, both the old and the new place. |
| Fixed a bug | Reproduce the original failure first, then show it gone. |
| Several items | Go through the user's list one by one, and mark each done / not done. |

## Then write it down and report

Evidence, in the tracker (for the checking sessions):
1. What you looked at (path, command, page), so another session can open the same thing.
2. What you saw (a short quote or number).

To the user, short:
1. The result: what is done and where to see it (full path or link).
2. What you could not check, said plainly: "not verified: ...".
3. For several items: one line each with done or not done and the reason.
The evidence itself only if the user asks for it.

## Rules
- Do not say "should work", "looks good" or "done" if nothing was opened or run after the last edit.
- If the check fails, say so and fix it; do not report the first attempt as the result.
- A negative claim ("nothing there", "it did not happen") needs a check that could have found it: first run it on a case where the answer is known.
- If you did not read all of something, say how much you read.
- Hand back to the user only what only they can do (password, code, payment, signature, a decision), and prepare everything up to that step.
