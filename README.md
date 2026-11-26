# ai-engineering-sdlc-tools

[![tests](https://github.com/AarvinGeorge/ai-engineering-sdlc-tools/actions/workflows/tests.yml/badge.svg)](https://github.com/AarvinGeorge/ai-engineering-sdlc-tools/actions/workflows/tests.yml)

Software-development-lifecycle tooling for AI engineering work — a Claude Code marketplace.

The through-line: **a coding agent's memory ends with its context window, and a human's
memory of what the agent did ends sooner than that.** These tools put the shared state
somewhere both sides can read, and make the reading automatic.

## Use cases

- **plan-layer** answers "where are we?" from a file, in every new session. [Use cases](plugins/plan-layer/README.md#use-cases).
- **engineering-method** makes the agent show evidence and scale its process to the stakes. [Use cases](plugins/engineering-method/README.md#use-cases).
- **work-log** turns your sessions into a timesheet you can hand to someone. [Use cases](plugins/work-log/README.md#use-cases).

**The three together.** You spend two weeks on a small internal tool. Each morning the session
opens with the plan's active item and what is next, so you never re-explain. The agent names the
work "internal", so changes get tests and a review by a different model, and "is it merged?" is
answered with a command and its output. When tasks finish, `/plan-layer sync` re-renders the page
and the gate flags anything left behind. On Monday you ask "work log for last week" and get a
sheet of what was done, with estimated hours per day.

## Plugins

| Plugin | What it does |
|---|---|
| [`plan-layer`](plugins/plan-layer) | A shared planning surface between you and your coding agent. One JSON file is the state, a self-contained HTML page is the view, a gate catches drift and contradiction, session hooks brief the agent before the first word is typed, and history rolls off the front page into an archive in full so the page shows this month; it can mirror the plan into an external tracker (Notion first) and write a handoff when work pauses. Opt-in controller: one script is the only writer of plan state, co-change rules run on events, and an inventory is checked against every list that must cover it. Current: 0.20.0. |
| [`engineering-method`](plugins/engineering-method) | An engineering method carried to every project as one skill that hooks re-apply at session start, after compaction and at each stage change: principles with their reason and a test, scaled by stakes (prototype, internal tool, live system with real users), a thin layer over Superpowers. Current: 0.3.0. |
| [`work-log`](plugins/work-log) | Turns your Claude Code activity into a dated, time-estimated, plain-language work log for any period (last week, October, Q4), saved as a new Google Sheet in a `Work Logs` Drive folder or as a local `.xlsx`. Runs on request or weekly from a Claude Desktop local task, with a pre-upload privacy scan. Current: 0.1.0. |

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
```

Adding a plugin means adding a directory under `plugins/` and one entry to
`marketplace.json`. Nothing else moves.

## Works with

- **Archify** (`npx skills add tt-a1i/archify -g`, MIT, maintained separately) for drawings that live
  beside a planning page: plan-layer's `views` keep them honest (spec sha, measured revision, the
  gate's drift signals) and use Archify's own evidence primitives rather than reinventing them. Never
  bundled here: it updates from its author.

## Where each tool is honest about its limits

plan-layer and work-log each keep a `ROADMAP.md` naming what it does **not** do, with the evidence that
revealed each gap. A tool that only documents its strengths is a sales page.

- [plan-layer/ROADMAP.md](plugins/plan-layer/ROADMAP.md)
- [work-log/ROADMAP.md](plugins/work-log/ROADMAP.md)

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

## Contributing

Issues and pull requests are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for the layout, how to run each plugin's tests, and the review rule, and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for community expectations.

## Security

Report vulnerabilities privately through GitHub's **Security** tab, not as public issues. See [SECURITY.md](SECURITY.md).

## Licence

MIT. See [LICENSE](LICENSE).
