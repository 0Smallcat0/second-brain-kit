# Pitfalls: things that went wrong, and what the kit does about them

These come from months of working with Claude every day. Each entry is a mistake that really happened. The kit's defaults already include the fix; this page explains why, so you do not undo them by accident.

## 1. Rules were written but not executed
A rule in `CLAUDE.md` ("always verify before saying done") was in context when the mistake happened, and it was still made. Long rule files make it worse: the longer the file, the less of it is followed.
**Fix:** keep `CLAUDE.md` short (under 100 lines) and put the check in code at the moment of the action: a hook that looks at the tool call, a script that refuses the commit. When a rule keeps being broken, do not add a second sentence; turn it into a check.

## 2. Too many gates block finishing
A completion gate that can refuse forever is worse than no gate: a counter ("2 items MISSING") that never reaches zero because the thing it counts cannot be produced; verifier rounds that fail the same way six times in a row; a second session whose approval is needed before a third can proceed.
**Fix:** every gate must be able to let go. The Stop hook blocks once per turn (`stop_hook_active` means "already asked, let it through"). Nothing waits on another session's approval; topic sessions close their own ledger items by showing evidence. If you add a gate, say in one line how it ends when the check cannot pass.

## 3. Long approval chains
Request -> entry -> manager -> reviewer -> entry -> user: every hop is a place for work to stall, and each hop re-reads everything.
**Fix:** entry + topic sessions only. The entry routes and tracks; the topic session does the work and closes with evidence; the user sees the result.

## 4. Alarms multiply
Polling alarms ("check every 10 minutes whether X happened") and alarms created to re-ask about alarms grew from dozens to nearly eighty in a day. Each one fired into a session and created more work.
**Fix:** only daily / weekly / once rows; firing writes a ledger item or an inbox line and is skipped if the same one is still open; a warning above 20 rows; `--prune` for fired one-time rows. If nobody acts on an alarm, delete it.

## 5. Quota is wasted in boring ways
- The most expensive model used for loops and mechanical jobs.
- One large table sent to a paid API seven times, using about half a month's budget; only the changed part needed to be sent.
- A second pool of quota that sat mostly idle while the main account ran dry.
- Foreground polling of a tool that could have been started and read later.
**Fix:** choose model and effort per job (mechanical = cheap and low effort); send only what changed; look at weekly usage before a big job (`usage_warn` tells you at 80%); long jobs run in the background and write a result file.

## 6. A locked quota silently stops a queue
Some tools lock for days once used up (one lock lasted about six days). Work assigned to them just sits.
**Fix:** write "locked until" next to wherever work is assigned (`channels.md`) and read it before sending. See [MULTI-TOOL.md](MULTI-TOOL.md).

## 7. Browser tabs and files pile up
Automated runs open windows, tabs and scratch files and never close them.
**Fix:** end every automated job with "close what you opened, leave what was already open", and count the tabs yourself afterwards. Scratch files go in one known folder, not next to the user's work.

## 8. Wording checks get bypassed by rephrasing
A check that looks for the word "done" is beaten by "that should be everything". A check for forbidden phrases trains the model to use other phrases.
**Fix:** check facts, not words. The Stop hook's real test is the order of tool calls (was anything read back or run after the last edit?); the words are only the trigger. The ledger refuses to close an item without evidence text. Expect gaps; read the log.

## 9. New checks: log first, then block
A brand-new block that fires wrongly costs the user's trust faster than the mistake it prevents.
**Fix:** every hook has a mode (`off, log, warn, ask, deny, block`). Start a new or changed check in `log`, read `logs/*.log` after a few days, and only then switch to blocking.

## 10. Replay a new check on past mistakes before trusting it
**Fix:** run `python hooks/stop_evidence.py --replay <transcript.jsonl>` on real old sessions. It prints which turns would have been blocked. Too many false blocks: keep it in `log`. A check that has never seen a real example is a guess.

## 11. "Done" without opening the real thing
Tools report "success" for a write that landed in the wrong folder, an upload that dropped a field, a script that exited 0 after doing nothing.
**Fix:** `evidence-before-done` skill + the Stop hook. Open the file, run the test, read the page back, and say what you saw.

## 12. Several items: fix one, drop another
**Fix:** `task.md` for three or more items, each copied from the user's words with a done-when; the final reply lists every item as done / not done with the reason.

## 13. Only pointing at the problem
"X is blocked, you need to ..." and stop.
**Fix:** work until only the user's step is left (password, code, payment, signature, decision), prepare everything up to it, and list the minimum they must do in numbered lines. `todo-for-me.md` is that list; it must never hold something Claude could have done.

## 14. The entry does hands-on work
An entry session that starts doing long jobs fills its context, forgets to route, and the ledger stops being updated.
**Fix:** the entry's `CLAUDE.md` says: answer short questions, register everything else, hand it to a topic session, check the ledger.

## 15. Ledger and task.md rot
Items that are never closed, `task.md` files that say "in progress" for things finished weeks ago.
**Fix:** `ledger.py list` flags items older than 14 days; the default weekly alarm is a review; an item closes only with evidence or an explicit drop by the user.

## 16. Directions chosen alone
Big choices (what to build, which strategy, which design) made from one model's first idea.
**Fix:** write the requirements and facts without your own plan, ask a second model blind (web chat is enough), compare, then choose. See MULTI-TOOL.md.

## 17. Replies too long
The user needs the answer and the decision, not the process.
**Fix:** answer first, short, in the user's language; details only if asked.

## 18. Reading a fragment and concluding
`head -20 note.md`, then a confident answer that the rest of the note contradicts.
**Fix:** `read_whole` refuses fragment reads of vault notes; the principles say to read to the last line and to say how much was read.

## 19. Compaction rewrites the request
After a long session is summarised, the exact wording of what the user asked is gone and the summary quietly changes the goal.
**Fix:** `requests_reinject` puts the user's own messages back verbatim after compaction and saves the full list to a file.

## 20. Docs and code disagree
A README that promises a command the code does not have, or settings the code ignores.
**Fix:** `scripts/selftest.py` exercises every hook and tool the docs describe. When you change one, run it. When docs and code differ, trust the code and fix the docs.

## 21. Over-design
Each extra mechanism has a cost in tokens, attention and breakage.
**Fix:** before adding a rule, hook or table, write down which mistake that really happened it prevents. If you cannot, do not add it. Start with the entry and two topic sessions; add more only when one is overcrowded.

## 22. Hooks that only work on one machine
Hard-coded paths, a Windows-only call, a byte-order mark in a JSON line.
**Fix:** hooks are Python 3 standard library only, started through `hooks/run.sh` which finds whichever Python exists, and they exit 0 on any internal error (fail open) so a broken hook never traps a session.
