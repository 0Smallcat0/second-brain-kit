---
name: evidence-before-done
description: Before telling the user that something is finished, fixed, sent, saved or "works", look at the real result and quote the evidence. Use whenever you are about to report completion of edits, files, tests, pages, uploads, migrations or any multi-item task, and when a Stop hook asks for evidence.
---

# Evidence before "done"

"Done" means the user can rely on it without checking. A tool saying "success" is not looking at the result.

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

## Then report like this

1. What you looked at (path, command, page).
2. What you saw (a short quote or number).
3. What you could not check, said plainly: "not verified: ...".
4. For several items: one line each with done or not done and the reason.

## Rules
- Do not say "should work", "looks good" or "done" if nothing was opened or run after the last edit.
- If the check fails, say so and fix it; do not report the first attempt as the result.
- A negative claim ("nothing there", "it did not happen") needs a check that could have found it: first run it on a case where the answer is known.
- If you did not read all of something, say how much you read.
- Hand back to the user only what only they can do (password, code, payment, signature, a decision), and prepare everything up to that step.
