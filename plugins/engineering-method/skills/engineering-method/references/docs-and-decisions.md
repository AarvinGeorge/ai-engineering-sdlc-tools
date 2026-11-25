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

## A header on every module, class and function a task touches (tier b and c)

The same idea for code; tier a (exploration) skips it. Every new or changed module, class and
function carries a header (a docstring or comment block) with these labelled fields, each present
even when it is "none":

- `What:` it does, in one sentence;
- `Use when:` why and when to use it (and when not to);
- `Inputs:` and `Output:`;
- `Side effects:` writes, sends, network, or "none";
- `Role:` its place in the module or system.

Added when a task creates or changes the code, never in a sweep over untouched code; a sweep is a
separate, planned task. **A check enforces it, and the first change that adds a header adds the
check if the repository has none:** a test in the normal suite (or a lint rule) fails when a module,
class or function added or changed against the base has no header, and a planted header-less one
turns it red. *Why:* code could not be found or reused without reading the bodies, and a header
rule kept only in prose was not kept. *Test:* the diff's new and changed code all has headers,
untouched code is unchanged, and the check is in the suite.

A minimal check (Python; adapt the idea to the language). The base is passed in, defaulting to the
merge-base with the default branch:

```python
# test_headers.py
"""What: fails when a module, class or function changed against the base lacks a header.
Use when: in the normal suite, on tier b and c work. Inputs: HEADER_BASE (env, optional).
Output: test result. Side effects: runs git read-only. Role: enforces the code-header rule."""
import ast, os, re, subprocess
FIELDS = ("What:", "Use when:", "Inputs:", "Output:", "Side effects:", "Role:")
def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.strip()
def base_ref():
    if os.environ.get("HEADER_BASE"):
        return os.environ["HEADER_BASE"]
    default = git("symbolic-ref", "--short", "refs/remotes/origin/HEAD")  # e.g. origin/main
    return git("merge-base", "HEAD", default)
def changed_lines(base):
    lines, path = {}, None
    for row in git("diff", "-U0", base, "--", "*.py").splitlines():
        if row.startswith("+++ "):
            path = row[6:] if row.startswith("+++ b/") else None
        elif row.startswith("@@") and path:
            start, _, count = re.search(r"\+(\d+)(,(\d+))?", row).groups()
            n = int(count) if count is not None else 1
            lines.setdefault(path, set()).update(range(int(start), int(start) + n))
    return lines
def test_changed_code_has_headers():
    missing = []
    for path, touched in changed_lines(base_ref()).items():
        tree = ast.parse(open(path).read())
        nodes = [tree] + [n for n in ast.walk(tree) if isinstance(
            n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
        for node in nodes:
            span = (set(range(node.lineno, node.end_lineno + 1))
                    if hasattr(node, "lineno") else touched)  # the module counts if any line changed
            if touched & span and not all(f in (ast.get_docstring(node) or "") for f in FIELDS):
                missing.append(f"{path}:{getattr(node, 'lineno', 1)} {getattr(node, 'name', '<module>')}")
    assert not missing, missing
```

Only code whose lines the diff touches is checked, so untouched code is never forced into a sweep.

The same pattern answers any rule that has been missed more than once (a changelog entry, a version
bump, an index line): a check that fails without it (CI, a pre-push hook or a test), not another line in
the instructions file (SKILL.md principle 7).

## Decision log

- **Append-only and chronological.** Newest at the bottom; past entries are never rewritten. A
  reversed decision is a new entry that names the old one.
- Each entry: its id (`D-001`, below), the date and time (measured), the decision, who made it,
  the reason, and what it supersedes.
- Instructions files (`CLAUDE.md`) carry context and navigation; findings and analysis go in dated
  documents; decisions go in the log. One that outgrows its cap is compressed by the next section.

## Keeping instruction files small

A file loaded on every turn (a project `CLAUDE.md`, an agent's instructions, a memory index) holds
binding rules and current pointers only. The baseline is Anthropic's: "target under 200 lines per
CLAUDE.md file. Longer files consume more context and reduce adherence"; `@`-imports "don't reduce
its context cost" (code.claude.com/docs/en/memory, "Write effective instructions"), so detail moves
to files read by path when needed. Recall falls as context grows ("context rot",
anthropic.com/engineering/effective-context-engineering-for-ai-agents). `/doctor prompt-audit`
finds outdated and conflicting lines; its report feeds step 3. What this adds: a compression is a
change that can drop rules and invent facts, so it is archived, classified, checked and reviewed
like code. Report each step done with its evidence:

1. **Measure** every always-loaded file: bytes, lines, sections (`wc -c -l`, `grep -c '^#'`).
2. **Archive the whole file first, verbatim,** and prove the copy equals the committed file
   (`git show HEAD:<file> | cmp - <copy>`, exit 0). Nothing is deleted: what leaves the file lives
   in the archive, the decision log or a dated document.
3. **Classify each section:** binding rule · current pointer · frozen text · stale state · history ·
   reference list.
4. **Keep by class.** Binding rules: rule + reason + decision id or date. Current pointers: in the
   resume block only. Frozen sections: byte-identical, each extracted by its heading from the copy
   and the new file and compared (`shasum` equal, or an empty `diff`).
5. **Move by class.** Stale state, superseded tables, incident narratives and document lists go to
   the archive, the decision log, or a one-line pointer to the index.
6. **Every fact the rewrite adds carries its source** (command, file and line, decision id). In the
   first real run, most errors the review found were new claims, not drops.
7. **Grep for the one-liners.** Before rewriting, list the short single-line rules (names never to
   use, guard tests, branch rules, naming traps); afterwards, grep the new file for each. They are
   the easiest to lose.
8. **An independent reviewer before the commit:** a different model diffs old against new, lists
   each lost rule and each wrong new claim with its evidence, and confirms the frozen sections;
   its findings are applied before committing (principle 10).
9. **Write the size rule into the file itself:** its cap; old resume entries move to the archive
   verbatim; findings go to dated documents.
10. **Scan for secrets and personal data before the push** (live-system-changes.md, "Pushing and
   backups").

*Why:* a file read every turn grows a little each session until its rules are followed less, and a
one-pass rewrite drops short rules and adds confident, wrong facts that only an independent diff
catches. *Test:* the archive `cmp` exits 0; each frozen section compares equal; every listed
one-liner is found in the new file; each review finding is applied or answered before the commit;
the file states its cap.

## Using the record

- **Re-test an old decision for currency before citing it.** Name its date and check later direction
  has not overtaken it; if it now blocks the product, raise it as "aged, recommend revisiting",
  never defend it as settled. *Why:* a two-month-old rule nobody recalled was cited as binding and
  shaped a deferred list built on it. *Test:* every decision cited as a reason carries its id and
  date, and a deferred item names the decision it rests on.
- **A settled owner ruling is not re-raised without new evidence of real harm.** Before carrying
  any proposal (a gap list, a review finding, a backlog item), check it against the owner's stated
  design and the decision log. One that contradicts a ruling or the design is not carried, as
  written or reworded into the backlog; name the ruling (id and date) and drop it. It comes back only
  with new evidence of harm (an incident, a measurement), and then as a question to the owner, not a
  backlog item. This is the counterpart of the currency rule above: currency asks whether later
  direction overtook a decision; it never treats age alone as a reason to reopen one. *Why:* the
  owner had to restate the same rulings again and again and called the re-asks regressive. *Test:*
  each proposal carries "consistent with" or "contradicts D-NNN", and every contradicting one that
  is carried names its new evidence.
- **"Did we decide this before?" is answered by searching under every synonym.** List the terms
  first (for a data-retention question: retention, keep, delete, purge, expiry, TTL, archive,
  backup window), search the log and the design for each, and say which terms were searched and
  which entry matched. *Why:* a prior decision was missed because only one term was searched, and it
  was worded differently. *Test:* the answer lists the terms searched beside the entry found, or
  says none matched.
- **Search the record before recommending a removal or giving a step.** The decision log and the
  setup records hold rulings and proven forms. *Why:* removals of things kept on purpose, and
  commands the records had already corrected, were proposed from memory. *Test:* the
  recommendation cites the entry it was checked against, or says none was found and where it
  looked.
- **A repeated reminder is encoded where it is read, in the same turn.** The first time the person
  restates a rule, write it to the instructions file, memory or a guard, and say where. *Why:* advice
  that lives only in conversation is lost at the next compaction. *Test:* the reply names the file
  and line that now holds the rule.

- **Keep a lessons register.** One table: what failed, what works, its source, whether it still
  holds; a row is added the turn the lesson is learned, and searched before any setup or deploy
  step. *Why:* lessons scattered across records were relearned. *Test:* the step cites its row.
- **Setup records are append-only, written right after each part completes.** One record per
  instance or environment being provisioned. Never write a section ahead of the work: a part not yet
  done has no entry (a to-do list is a plan, kept elsewhere). Each entry, written the moment its part
  completes:

  | Field | Content |
  |---|---|
  | when | date and time, read from the clock |
  | part | what was set up |
  | order that worked | the steps in the order they actually ran, commands included |
  | values | names, regions, sizes, ids, key *names* (never secret values) |
  | pitfalls | what failed first and what fixed it |
  | automate | what the provisioning script should do next time |

  A correction is a new entry that names the one it corrects, never an edit. *Why:* sections written
  before the work described the intent, not what happened. *Test:* every entry's time is after its
  part completed, no entry describes undone work, and no secret value appears.
- **Record each platform assumption with the version it was checked on,** pinned by a boundary
  test. *Why:* an upgrade silently changes behaviour the code relied on. *Test:* the upgrade
  rehearsal reads the list and every entry has its test.

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
moves, not afterwards. **A plan for a fix carries a "Fit with what exists" section** holding
SKILL.md principle 17's four REQUIRED lines (Exists, Extends, Unlocks, Goals), one row each, plus a row per stated quality goal. *Test:* the
section exists and has every row. **Every finding has a home before a plan is called complete:** a coverage
table maps each finding from the traces and reviews to the story that fixes it, or to a stated
deferral. *Why:* fixes were dropped between the trace and the plan. *Test:* the table has no
finding without a row.

## Branches

Name branches and plan documents for the capability they add, never for the document or meeting that
produced them.
