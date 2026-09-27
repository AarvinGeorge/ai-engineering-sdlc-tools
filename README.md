# ai-engineering-sdlc-tools

Software-development-lifecycle tooling for AI engineering work — a Claude Code marketplace.

The through-line: **a coding agent's memory ends with its context window, and a human's
memory of what the agent did ends sooner than that.** These tools put the shared state
somewhere both sides can read, and make the reading automatic.

## Plugins

| Plugin | What it does |
|---|---|
| [`plan-layer`](plugins/plan-layer) | A shared planning surface between you and your coding agent. One JSON file is the state, a self-contained HTML page is the view, a gate catches drift and contradiction, session hooks brief the agent before the first word is typed, and history rolls off the front page into an archive in full so the page shows this month. Current: 0.15.2. |

## Install

```bash
claude plugin marketplace add AarvinGeorge/ai-engineering-sdlc-tools
claude plugin install plan-layer@ai-engineering-sdlc-tools
```

From a local checkout instead:

```bash
claude plugin marketplace add /path/to/ai-engineering-sdlc-tools
claude plugin install plan-layer@ai-engineering-sdlc-tools
```

### Picking up your own edits

A marketplace is **cached** at install time, and updating the marketplace only refreshes the
catalogue — it does **not** move the installed plugin. Both steps are needed:

```bash
claude plugin marketplace update ai-engineering-sdlc-tools   # refresh the catalogue
claude plugin update plan-layer@ai-engineering-sdlc-tools    # move the installed copy
```

Bump the version in **both** `.claude-plugin/marketplace.json` and the plugin's own
`plugin.json` first, or the second command finds nothing newer and does nothing. Confirm
with `claude plugin list`.

## Layout

```
.claude-plugin/marketplace.json    the catalogue — what is published and where to fetch it
plugins/<name>/                    one directory per plugin
  .claude-plugin/plugin.json       the plugin manifest
  hooks/hooks.json                 session-lifecycle hooks
  scripts/                         executables the hooks and skills call
  skills/<name>/SKILL.md           what the agent reads
  templates/                       what init copies into a project (plan.json, MAP.md)
  tests/                           run with: python3 -m unittest tests/*.py
plan/                              this repository's OWN plan, kept with plan-layer itself
```

Adding a plugin means adding a directory under `plugins/` and one entry to
`marketplace.json`. Nothing else moves.

This repository plans with itself: `plan/plan.json` at the root is plan-layer's own plan,
rendered to `plan/index.html` by the same scripts it ships. If the tool is not good enough to
run on its own roadmap, it is not good enough to publish.

## Works with

- **Archify** (`npx skills add tt-a1i/archify -g`, MIT, maintained separately) for drawings that live
  beside a planning page: plan-layer's `views` keep them honest (spec sha, measured revision, the
  gate's drift signals) and use Archify's own evidence primitives rather than reinventing them. Never
  bundled here: it updates from its author.

## Where each tool is honest about its limits

Every plugin here keeps a `ROADMAP.md` naming what it does **not** do, with the evidence that
revealed each gap. A tool that only documents its strengths is a sales page.

- [plan-layer/ROADMAP.md](plugins/plan-layer/ROADMAP.md)

## Design rules

These are what the tools have in common, and what a new one here should honour.

- **Standard library only.** These run inside session hooks on other people's machines. A
  missing dependency turns a briefing into a stack trace, and a tool that breaks a session
  gets uninstalled.
- **Silent where uninvited.** A hook that fires in every project must produce nothing in
  projects that have not opted in.
- **Fail open.** A tool that cannot do its job gets out of the way rather than blocking work.
- **Generated output announces staleness.** Anything derived carries a fingerprint of its
  source, so it can never quietly show old data.
- **Evidence over assertion.** Where a tool reports a state, it should be able to show what
  it measured.
- **Colour is measured, never eyeballed.** Every text token clears WCAG AA against every
  ground it sits on, in both themes, asserted by a test. Two tokens once shipped at 4.31:1
  and 4.09:1 — close enough to look right and still fail.

## Licence

MIT. See [LICENSE](LICENSE).
