# Completion gate with an independent verifier (design only)

Idea: before a deliverable (a report, a document, a batch of edits) is closed, a fresh subagent that has not seen the conversation checks it against the user's original words and lists missing items. The ledger item closes only after it passes.

Why it is not shipped: in real use a heavier version got stuck. A counter of missing items never reached zero because some "missing" things could not be produced, and the verifier failed the same way six rounds in a row, so nothing could be closed.

If you want to try it, keep these rules:
1. **One round.** The verifier runs once per deliverable. Whatever it reports, the second attempt to close passes, with its findings written into the ledger evidence.
2. **Findings are a list for the user, not a lock.** A finding the worker cannot fix is moved to `todo-for-me.md` with the reason, and no longer counts as missing.
3. **The verifier gets only** the user's original words, the deliverable, and the sources needed to judge it. It reads, it does not edit.
4. **Start in `log` mode:** write its findings to a file for a week and compare with what you would have caught yourself before letting it block anything.
5. Say in one line how the gate ends if the check can never pass.
