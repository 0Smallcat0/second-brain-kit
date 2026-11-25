---
name: vault-tidy
description: Tidy the user's numbered notes vault safely - run lint, fix warnings, file the inbox, archive finished notes, refresh the JDex index. Use when the user says "tidy my notes", "clean up the vault", "整理一下筆記", before a long break, or when lint reports warnings.
---

# Tidy the notes vault

Work in the vault root (the folder with `.sbk-vault`). Read `AGENTS.md` and `00-09 系統與索引/01 規則/01-01 筆記格式.md` first, all the way to the end.

## Steps (check after each)

1. **Baseline.** `python scripts/vault_lint.py` and keep the output. Write down the counts. Note anything the user asked about specifically.
2. **ERRORs first.** Broken `[[links]]`: find the real note and fix the link; if the note no longer exists, ask before removing the link. Missing embeds, unclosed frontmatter, duplicate names: fix them. Re-run lint; ERRORs must be 0.
3. **File the inbox.** Open each note in `02 收件匣`. For each: give it a category and the next free number from the JDex, rename, fill frontmatter. If you cannot tell where it goes, leave it and list it for the user. Never delete.
4. **WARNs, one kind at a time.**
   - `summary-missing`: read the note, write one honest sentence.
   - `type-invalid` / `status-invalid` / `origin-invalid`: pick the right value from the list in the format note; use `agent-inferred` when unsure.
   - `stale-active`: ask the user whether it is still active (one question for the whole batch), then set `status` accordingly.
   - `archived-not-moved` / `archive-misfiled`: move to or from `90-99 封存` and make status match.
   - `todo-stale`: report them to the user instead of ticking or deleting.
5. **Index.** `python scripts/gen_jdex.py`, then lint once more.
6. **Commit** only your own files: `git commit -m "tidy: ..." -- <paths>`. The pre-commit hook may refuse a mass rewrite; that is intended, do not bypass it.
7. **Report.** Counts before and after, and a list of what you moved, renamed, archived, and what you left for the user and why.

## Do not
- Rewrite a whole note to fix one field; edit only that line.
- Change what a note says. Tidying is structure, not content.
- Skip reading a note before moving or archiving it.
- Say "clean" without a final lint run showing `RESULT: PASS`.
