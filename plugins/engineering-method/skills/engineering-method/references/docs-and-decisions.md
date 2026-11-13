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
- Each entry: its id (`D-001`, below), the date and time (measured), the decision, who made it,
  the reason, and what it supersedes.
- Instructions files (`CLAUDE.md`) carry context and navigation; findings and analysis go in dated
  documents; decisions go in the log.

## Using the record

- **Re-test an old decision for currency before citing it.** Name its date and check later direction
  has not overtaken it; if it now blocks the product, raise it as "aged, recommend revisiting",
  never defend it as settled. *Why:* a two-month-old rule nobody recalled was cited as binding and
  shaped a deferred list built on it. *Test:* every decision cited as a reason carries its id and
  date, and a deferred item names the decision it rests on.
- **Search the record before recommending a removal or giving a step.** The decision log and the
  setup records hold rulings and proven forms. *Why:* removals of things kept on purpose, and
  commands the records had already corrected, were proposed from memory. *Test:* the
  recommendation cites the entry it was checked against, or says none was found and where it
  looked.
- **A repeated reminder is encoded where it is read, in the same turn.** The first time the person
  restates a rule, write it to the instructions file, memory or a guard, and say where. *Why:* advice
  that lives only in conversation is lost at the next compaction. *Test:* the reply names the file
  and line that now holds the rule.

## Names: one hierarchy, never renamed

The industry's work breakdown (Scrum, Jira, SAFe: initiative, epic, story, task), plus numbered
releases, findings and ADR-style decision records. Each level has exactly one source of truth, and
a name says what kind of thing it is.

| Level | Form | What it is | Source of truth |
|---|---|---|---|
| Initiative | `I-1` | a theme the epics serve | the plan's north star |
| Epic | `E-01 slug` | one body of work: one plan document, one branch `e-01-slug` | its plan document |
| Story | `E-01.S2` | a slice that ships in ONE release | the plan document |
| Task | `E-01.S2.T3` | one build step: one implementer, one review, one commit range | the task ledger |
| Release | `R-04` | exactly what was promoted; the deployment ledger's sequence number, one per promotion, never reused | the deployment ledger |
| Finding | `E-01.F1` | a defect from a review or a bench, numbered within its epic | the task ledger, then a story |
| Decision | `D-001` | one decision-log entry | the decision log |

- **A name, once given, never changes.** *Why:* a renamed item breaks every link, commit message and
  record that used the old name. *Test:* a search for any old name finds it in the crosswalk.
- **Adopting it mid-flight: a crosswalk.** A living document maps each old name to its new one, its
  plan document and its state at adoption; old branches are not renamed, new ones use the new form;
  decision ids start at `D-001` with the first entry after adoption (earlier entries are cited by
  timestamp). Plan documents keep their number and gain the epic in their title and header
  (`covers: E-01`). *Why:* without it, every old record points at a name nothing uses any more.
  *Test:* each old name in use at adoption has a crosswalk row.
- The planning page uses the same names (plan-layer can enforce it with `meta.naming`).

## Plans

Tier b: a short decision note, and a numbered plan only when the work spans sessions. Tier c: a
numbered plan before building, with verifiable steps, an explicit
out-of-scope list, and each capability marked EXTENDS or NEW. Update the plan's stage when the work
moves, not afterwards.

## Branches

Name branches and plan documents for the capability they add, never for the document or meeting that
produced them.
