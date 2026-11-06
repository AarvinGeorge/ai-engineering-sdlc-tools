# Contributing

Thanks for helping. This repository is a Claude Code plugin marketplace; each plugin lives in its own directory under `plugins/` and is versioned on its own.

By taking part you agree to the [Code of Conduct](CODE_OF_CONDUCT.md). Contributions are licensed under the [MIT License](LICENSE).

## Proposing a change

- **Bug or small fix:** open a pull request directly, or an issue first if the cause is unclear.
- **New feature or a new plugin:** open an issue using the feature request template before writing code, so the shape can be agreed. A plugin should solve one clear problem for people working with a coding agent, and ship with tests (or evals, for prompt-only plugins) and a README.
- **Security problem:** do not open a public issue. See [SECURITY.md](SECURITY.md).

## Layout

```
.claude-plugin/marketplace.json    the catalogue: what is published and where to fetch it
plugins/<name>/
  .claude-plugin/plugin.json       the plugin manifest (name, version, license)
  skills/<skill>/SKILL.md          what the agent reads
  scripts/, hooks/, templates/     what the skills and hooks call (where the plugin has them)
  tests/                           unit tests (plan-layer, work-log)
  evals/                           behaviour evals (engineering-method, work-log)
  README.md, CHANGELOG.md          user docs and release notes
docs/                              design notes and plans
```

Adding a plugin means adding a directory under `plugins/` and one entry to `.claude-plugin/marketplace.json`.

## Running the tests

Python 3.10 or newer. Run from the repository root.

```bash
# plan-layer: standard library only
(cd plugins/plan-layer && python3 -m unittest tests/*.py)

# work-log: pytest; openpyxl is needed for the workbook read-back test
python3 -m pip install pytest openpyxl
python3 -m pytest plugins/work-log/tests -q
```

`engineering-method` has no unit tests; it is a skill, checked by the cases under `plugins/engineering-method/evals/`. The same suites run in CI on every pull request (`.github/workflows/tests.yml`).

## Versioning and changelogs

- Each plugin is versioned independently with [Semantic Versioning](https://semver.org/): patch for fixes, minor for backwards-compatible features, major for breaking changes.
- Each plugin keeps a `CHANGELOG.md` in [Keep a Changelog](https://keepachangelog.com/) style. Add an entry for every user-visible change, newest first.
- When you bump a version, change it in **both** `.claude-plugin/marketplace.json` and the plugin's own `.claude-plugin/plugin.json`, and update the version shown in the root `README.md`.

## Review rule

The reviewer must be someone other than the author, and the reviewer **runs the change**: checks out the branch, runs the tests, and exercises the behaviour that changed, rather than only reading the diff. Say in the pull request what you ran and what you saw.

## Pull request checklist

- Tests pass locally, and new behaviour has a test.
- No secrets, personal data, or private project names in code, tests, docs or fixtures.
- Changelog entry and version bump, if the change is user-visible.
