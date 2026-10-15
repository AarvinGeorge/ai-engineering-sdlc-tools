# Docs and decisions

Scale this to the tier: a prototype needs a README line; a live system needs all of it.

## Layout

- `docs/` — plans and analyses, **numbered in order of creation** (`01_`, `02_`, …), lowercase
  snake_case. Snapshots (audits, evaluations, option analyses) carry a date suffix `_YYYY-MM-DD`;
  living documents (runbooks, architecture) do not.
- `research/<date>/` — research reports, by day.
- `archive/` — finished or superseded material. Nothing deleted without asking.
- `INDEX.md` — the map. **Add each new document the same day.** Nothing loose at the top level.

## A header on every Markdown document a task uses

Added or refreshed when a task touches the document, never in a sweep:

```
---
summary: one or two sentences on what it says and decides
status: current | record | superseded by doc NN
covers: the topics, plans or decisions it holds
key_facts: the few numbers or decisions most often needed
updated: YYYY-MM-DD
---
```

Purpose: a later reader judges relevance from the header instead of reading the whole document. The
header describes; it never replaces reading the body when the task depends on the detail.

## Decision log

- **Append-only and chronological.** Newest at the bottom; past entries are never rewritten. A
  reversed decision is a new entry that names the old one.
- Each entry: the date and time (measured), the decision, who made it, the reason, and what it
  supersedes.
- Instructions files (`CLAUDE.md`) carry context and navigation; findings and analysis go in dated
  documents; decisions go in the log.

## Plans

A numbered plan exists before building on tier b and c work: verifiable steps, an explicit
out-of-scope list, and each capability marked EXTENDS or NEW. Update the plan's stage when the work
moves, not afterwards.

## Branches

Name branches and plan documents for the capability they add, never for the document or meeting that
produced them.
