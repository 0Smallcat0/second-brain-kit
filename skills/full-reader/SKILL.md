---
name: full-reader
description: Use when an answer needs long or many materials read in full: read every file with Read to the last line, report lines read per file, key points with file:line and a short quote, and contradictions; read only, never decide for the caller.
---

# Full reader

Use this when an answer or an action depends on reading a lot of material completely: a long transcript, a whole PDF, hundreds of lines of notes, or many notes that must be compared for contradictions. One or two short files you read yourself.

Hand the job to a subagent (Agent tool) so the main conversation does not fill up. Give it the question, the full paths of the files, and the brief below. Do not tell it what you expect the answer to be.

## What the reader does
1. Read every given file with Read from line 1 to the last line. If the result is partial or truncated, continue with offset and limit to the end of the file. Read a PDF of more than 10 pages in page ranges until it is done.
2. Grep and Glob may find files and places; they never replace reading. Do not use head, cut or sed to read excerpts.
3. If the task says "find all" or "go through every", read every file in scope, one after another; do not sample.
4. A file that cannot be read (a scanned PDF with no text layer, a video, audio) is listed under "not read" with the reason, never skipped silently.

## What the reader reports (in this order)
1. A coverage table: one row per file, "file | line reached / total lines" (pages for a PDF). Files not read or not readable are listed separately with the reason.
2. The key points for the question asked, each with `file:line` and a quote of at most 40 words.
3. Contradictions, anything marked retired but still treated as current elsewhere, and anything clearly out of date, each with `file:line` on both sides.
4. No decisions for the caller: only the material, its sources and the list of contradictions.

Before you rely on the report, open one or two of the quoted places yourself and check the quote.
