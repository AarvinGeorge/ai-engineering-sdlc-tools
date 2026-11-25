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
  tests/                           unit tests (plan-layer, work-log, engineering-method hooks)
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

# engineering-method hooks: standard library only
python3 -m unittest discover -s plugins/engineering-method/tests -v
```

`engineering-method` is mostly a skill, checked by the cases under `plugins/engineering-method/evals/`; only its hooks (`scripts/method_hook.py`) have unit tests. The same suites run in CI on every pull request (`.github/workflows/tests.yml`).

## Versioning and changelogs

- Each plugin is versioned independently with [Semantic Versioning](https://semver.org/): patch for fixes, minor for backwards-compatible features, major for breaking changes.
- Each plugin keeps a `CHANGELOG.md`: one dated entry per version (`## 0.1.1 — 2026-10-15`), newest first. Add an entry for every user-visible change.
- When you bump a version, change it in **both** `.claude-plugin/marketplace.json` and the plugin's own `.claude-plugin/plugin.json`, and update the version shown in the root `README.md`.

## Release gates

Three checks run on every pull request and on every push to `main` (`.github/workflows/release-gates.yml`), next to the unit suites. A fourth job runs the gates' own tests.

- **`validate`**: `claude plugin validate --strict` on the marketplace and on every plugin, with the CLI version pinned in the workflow. An unknown field in a manifest fails it.
- **`version-gate`** (`.github/release-gates/version_gate.py`): enforces the versioning rule above.
  A file `plugins/<name>/<rest>` is **release-relevant** unless `<rest>` is exactly `README.md`, `ROADMAP.md` or `CHANGELOG.md`, or starts with `tests/` or `evals/`. Everything else (skills and their references, scripts, hooks, templates, schema, trackers, `.claude-plugin/plugin.json`) ships behaviour.
  1. Always: for every relative-path entry in `marketplace.json`, its `version` equals the plugin's `plugin.json` version, the root `README.md` row for that plugin reads `Current: <version>.`, and the plugin's `CHANGELOG.md` newest heading is `## <version> — YYYY-MM-DD`.
  2. On a pull request: for each plugin with a release-relevant file changed between the PR base and head, the `plugin.json` version is strictly greater (semver) than at the base. A plugin absent at the base is new and needs only rule 1.
- **`payload-scan`** (`.github/release-gates/scan_payload.py`): scans every tracked file, every tracked path name and the commit messages of the pull request (or push) for secret shapes and for private identifiers. The marketplace installs from this public repository, so the whole tree is the payload.

Things to know when a gate fails or when you write a test:

- The generic secret shapes live in one file, `.github/release-gates/secret-patterns.txt`. The local pre-push guard and CI both read it, so there is one list.
- Private identifiers are never in the repository. CI reads them from the repository secret `RELEASE_GATES_PRIVATE_LIST`; the maintainer's local guard reads its own file outside every repository.
- There is **no allow marker** and no exempt file. A fake secret in a test is built by string concatenation (`"gh" + "p_" + "A" * 24`), so no committed line holds the shape.
- Bump `CLAUDE_CODE_VERSION` in `release-gates.yml` when `validate` rejects a newer field.
- Output names a file and line, a commit, or `path #<n>` and the kind of hit. It never prints the matched text.
- Commit author names and emails are not scanned; only file contents, path names and commit messages are.
- **Pull requests from a fork or from Dependabot**: CI cannot read the secret there, so the private-list check is skipped with a warning. The maintainer runs `python3 .github/release-gates/scan_payload.py --tokens-file <private list> --require-private-list` on the pull request head before merging. CI's check on the push to `main` is detection after publish, not prevention.
- The local guard reads its private file with `grep -Ff`, which treats every line as an entry, comment lines included. Keep that file free of comments and blank lines (a blank line matches everything). The scanner strips both, so the two agree on a clean file.

## Review rule

The reviewer must be someone other than the author, and the reviewer **runs the change**: checks out the branch, runs the tests, and exercises the behaviour that changed, rather than only reading the diff. Say in the pull request what you ran and what you saw.

## Turning an investigation lesson into a method change

engineering-method's root-cause steps end by recording, in the project's own method record, any lesson the steps do not cover (step RC-9 in `plugins/engineering-method/skills/engineering-method/references/root-cause-investigation.md`). When such a lesson applies beyond its project, it enters this repository through the same path as any other change (see "Proposing a change" and "Review rule"):

- open an issue stating it generally (no project, person or host names) with the evidence summarised;
- write its behaviour eval first and show it failing on the current version;
- then change the reference or SKILL.md, show the eval passing, and add its row to `plugins/engineering-method/evals/COVERAGE.md`.

A lesson without a failing eval is not a method change yet.

## Pull request checklist

- Tests pass locally, and new behaviour has a test.
- No secrets, personal data, or private project names in code, tests, docs or fixtures.
- Changelog entry and version bump, if the change is user-visible.
