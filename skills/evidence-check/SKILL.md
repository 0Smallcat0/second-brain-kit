---
name: evidence-check
description: Use before stating a number, saying something is missing, broken or did not happen, handing over a converted file, or citing research: separate measured from inferred, check every read path, verify the file the recipient will open in the recipient's environment.
---

# Evidence check

A conclusion is only as good as the check behind it. Run the list that fits what you are about to say. Rules already in the general principles (say "done" only after looking at the result; test a new measurement on a case with a known answer; an empty result is not "nothing there") are not repeated here.

## Numbers
- For every number, say whether you measured it or inferred it. Mark inferred ones as inferred; if one can be measured, measure it.
- When a number comes out, ask "what did I do that made it come out this way?", then measure again on something you did not touch: another dimension, time window or threshold.
- If you changed a condition and the number did not move, treat the change as not having taken effect. Look at the changed file or behavior; do not trust a script that prints OK.
- A metric judged by text that drops to zero: ask whether the work was done or only the words were swapped.
- Check the measuring tool itself: a hit rate that is too good to be true usually means both sides of the comparison are the same thing; a sample count is not an event count; a field borrowed as an ID must be checked for granularity; ask what the unit is.
- Verify "what the number is" and "why" separately. When an old conclusion is overturned and the cause was not verified, write "cause not established".
- Pin a key field from one source (above all a date that decides when information became visible) against a known value from another source.
- Numbers in a limitations or small-sample paragraph meet the same standard as the headline: read them from the output file or compute them on the spot.
- Before saying two sources verify each other, measure how much their observation units overlap and what they depend on in common. If they are not independent, say "consistent", not "verified".

## "Nothing there", "broken", "did not happen"
- Before saying "cannot be fetched", "does not exist" or "is broken", list every read path for that data and try each one. A failure that was cached as a result looks exactly like real absence.
- Before saying a log shows that something "did not happen", ask what the log records and what it does not (for example: writes but not reads).
- Not finding something by searching the code does not mean that what was actually sent is absent; find the layer that really sends it.
- Test through the product's real call path, not through what a comment says.

## Converted or packaged output
- Verify the file the recipient will open, not the source. After splitting, look at the head and tail for references that point outside the piece. After renumbering, search for the old numbers and paths (zero hits). After a conversion, count tables and images and search for leftover markup. After packaging, compare what should be in it with what is.
- Output of a web fetch, a search summary, OCR or an extractor is also a converted product. Merged cells, multi-column text, footnote exceptions and "or / at least one" clauses go back to the original.
- Do the last check in the recipient's environment: open the page in a browser and read the screen and the console. A 200 response with a matching hash does not prove the page looks right.
- When the same kind of mistake happens a third time, put the check into the converting program. A new check must stay silent on clean input and must fire on a deliberate violation.
- For anything in outgoing text that the recipient will click or run, go through it the way the recipient will before sending.

## Citing research and reading results
- Before writing "belongs to" or "according to", be able to write down how the original study measured it, whose attribute defines the groups, and that each example fits. State the study's preconditions and confirm they hold here.
- Write what an instrument shows as "what I saw": a screen, search results, a log, a single field. If a screen says "and N others", the platform is telling you it is incomplete.
- When your reading of something conflicts with the data you hold, suspect the reading first. If it takes three or more assumptions to make the story fit, a premise is wrong.
- Open the original before writing that someone did or did not do something. Before judging a person's or channel's claims, say how many of their items you read out of how many.
- If the user saw something with their own eyes, assume they are right and look for the evidence. For causes, cite only reporting from the day itself.
