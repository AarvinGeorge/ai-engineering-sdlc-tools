# ai-engineering-sdlc-tools

Software-development-lifecycle tooling for AI engineering work — a Claude Code marketplace.

The through-line: **a coding agent's memory ends with its context window, and a human's
memory of what the agent did ends sooner than that.** These tools put the shared state
somewhere both sides can read, and make the reading automatic.

## Plugins

| Plugin | What it does |
|---|---|
| [`plan-layer`](plugins/plan-layer) | A shared planning surface between you and your coding agent. One JSON file is the state, a self-contained HTML page is the view, a gate catches drift, and session hooks brief the agent before the first word is typed. |

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

A local-directory marketplace is **cached** at install time. After editing the source, run
`claude plugin marketplace update ai-engineering-sdlc-tools` to pick the changes up.

## Layout

```
.claude-plugin/marketplace.json    the catalogue — what is published and where to fetch it
plugins/<name>/                    one directory per plugin
  .claude-plugin/plugin.json       the plugin manifest
  hooks/hooks.json                 session-lifecycle hooks
  scripts/                         executables the hooks and skills call
  skills/<name>/SKILL.md           what the agent reads
```

Adding a plugin means adding a directory under `plugins/` and one entry to
`marketplace.json`. Nothing else moves.

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

## Licence

MIT. See [LICENSE](LICENSE).
