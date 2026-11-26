# Marketplace release gates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task by task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** every publish of this marketplace (a merge to `main`) passes three machine gates in one CI workflow: `claude plugin validate --strict`, a version-bump gate, and a whole-payload secret and private-identifier scan that reads the same pattern list as the local pre-push guard.

**Architecture:** one new workflow `.github/workflows/release-gates.yml` with three jobs (`validate`, `version-gate`, `payload-scan`). Two standard-library Python scripts under `.github/release-gates/` (outside every plugin payload, so adding them bumps no plugin) with `unittest` tests beside them. One committed file of generic secret shapes; the private identifier list never enters the repo (CI reads it from a repository secret, the local guard from its existing file outside the repo).

**Tech stack:** Python 3.13 standard library (`argparse`, `json`, `re`, `subprocess`, `unittest`), git, the Claude Code CLI pinned from npm, GitHub Actions pinned by SHA.

**Stakes tier:** b (internal). Public repository, CI only; the one payload-adjacent change (`whenToUse` removal) is a field Claude Code already ignores at load. Branch `release-gates` off `main` 5982357. No push, no PR, no publish from this plan; the owner pushes.

---

## Global constraints

- Standard library Python or plain shell only; tests written first and shown failing.
- Every action pinned by full SHA with its version in a comment.
- No private names, hosts, tracker links, ids or paths in any committed file, test, fixture, commit message or CI log. The scanners print where a hit is and which kind, never the matched text.
- Fake secrets in tests are built by string concatenation (`"gh" + "p_" + "A" * 24`) so the source file never contains a literal secret shape.
- Each gate is tied to its story. Nothing else ships here.
- Do not touch `.github/workflows/tests.yml` (open PRs #2 and #3 edit it; leaving it alone keeps their merge trivial).
- Do not touch any file under `plugins/*/` that is not exempt from the version gate (see S2 rule), so this branch bumps no plugin version and cannot collide with the two version-bump branches.

## Measured before planning (25 Nov 2026, ~23:40 UTC)

| Fact | Command | Result |
|---|---|---|
| Validate warnings | `claude plugin validate .` (CLI 2.1.332) at 5982357 | exit 0, **3 warnings**: `plugins[0].whenToUse`, `plugins[1].whenToUse`, `plugins[2].whenToUse`, "Unknown field 'whenToUse'. Claude Code ignores it at load time." The earlier "3 warnings" note was right; the brief's "[1] and [2]" missed `[0]`. |
| Strict fails today | `claude plugin validate --strict .` | exit 1 ("--strict treats warnings as errors") |
| Plugins pass strict | `claude plugin validate --strict plugins/<each>` | exit 0 for all three (directory-profile `ICON_MISSING` warnings appear but only count under `--profile directory`, which this plan does not use) |
| Fix proven | strict on a `git archive` copy with the three `whenToUse` keys removed, CLI **2.1.322** | marketplace and all three plugins exit 0; JSON report `errors: [] warnings: []` |
| CLI pin | `npm view @anthropic-ai/claude-code time` | 2.1.322 published 2026-11-10 (over two weeks old); has `--strict`; runs with an empty `HOME` (no login needed; exit 0) |
| Docs | code.claude.com/docs/en/plugin-marketplaces, "Validate and test" | validate reports "Unknown fields at the top level or in a plugin entry, as warnings"; flags and exit codes at code.claude.com/docs/en/plugins/cli-reference#plugin-validate; `--help`: "--strict Treat warnings as errors (exit 1). Use in CI to fail on unrecognized fields" |
| Open PR pins | `gh pr diff 2`, `gh pr diff 3` | `actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0 # v7.1.0`, `actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1`. The new workflow uses exactly these, so when #2 and #3 merge the repo has one pin per action. |
| Branch protection | `gh api repos/{repo}/branches/main/protection` | required contexts `["tests"]`, strict true; no rulesets; no repository secrets |
| Generic-pattern hits on the tree | the guard's key-shape regex plus `AKIA[0-9A-Z]{16}`, `git grep -cE` on `main` | 2 files, 2 lines each: `plugins/work-log/tests/test_scan.py:40-41` and `docs/superpowers/plans/2026-11-05-work-log.md:480-481` (both deliberate test fakes); 0 in commit messages; 0 binary tracked files (of 193) |
| Private-list hits | the guard's private list, case-insensitive fixed strings, on `main`, `origin/tracker-controller`, `root-cause-investigation` trees and their commit messages | 0 everywhere. Zero shown able to be non-zero: the list's own first line scanned against the list gives 1. |
| Version gate on the two bump branches (S2 rule below, applied by hand) | `git diff --name-only main...<b> -- plugins` minus exempt paths | `origin/tracker-controller` (PR #8): only `plan-layer` has release-relevant changes (15 files); plan-layer 0.18.0 → 0.19.0 in plugin.json **and** marketplace.json, README "Current: 0.19.0.", CHANGELOG top `## 0.19.0 — 2026-11-25`: **passes**. Its engineering-method and work-log changes are README-only: exempt. `root-cause-investigation` (local only, not on origin): only `engineering-method` relevant (7 files); 0.3.0 → 0.4.0 in both manifests, README, CHANGELOG `## 0.4.0 — 2026-11-25`: **passes**. Its plan-layer and work-log changes are README-only: exempt. |
| Plan code prototyped | the Python blocks of this plan extracted to a scratch folder, `python3 -m unittest discover -s tests` | `Ran 38 tests ... OK`; after the review fixes `Ran 40 tests ... OK`. With Step 7's concatenated fakes applied to a copy of the tree, plus the pattern file and this plan: 0 hits with the private list required, and the work-log `test_scan.py` still passes (27 passed). The prototype `version_gate.py` exits 0 on `main` (consistency) and with `--base main` on both branches above (changed `['plan-layer']`, `['engineering-method']`). The prototype `scan_payload.py` with the private list on the tree plus this plan: exactly the 4 known lines, 0 private hits, this plan file 0 hits. The prototype is not the build: the builder still writes tests first and shows them failing. |
| Not yet passing on those branches | | Both still carry `whenToUse` (S1 strict fails) and the two unmarked test-fake lines (S3 fails) until they rebase onto `main` after this lands. Expected, not a gate defect. |
| Local guard today | `.git/hooks/pre-push` execs a guard script outside every repo | Scans outgoing added lines (`git log -p`) with one inline key-shape regex (12 shapes) and a private fixed-string file (`grep -F`, case-sensitive); prints counts only; refuses a missing list. It does not read commit messages. |

## Fit with what exists

- **Exists:** `tests.yml` (unit suites per plugin); CONTRIBUTING "Versioning and changelogs" (the bump rule, by hand); the local pre-push guard and its rule in `engineering-method` `references/live-system-changes.md` "Pushing and backups" (scan every outgoing commit, list outside every repo, control run with a planted fake); `docs-and-decisions.md` line 93-96 (a rule missed more than once, "a changelog entry, a version bump", becomes a check that fails, CI or hook); `work-log` `scripts/scan.py` (a privacy scan for work-log output, a different job: it scans generated summaries, not the repo).
- **Extends:** the guard's key-shape regex moves into one committed file that the guard and CI both read (EXTENDS the guard; no second list). The guard's private file is the same content CI gets through a secret (EXTENDS; no second mechanism). CONTRIBUTING's bump rule becomes a check (EXTENDS, as `docs-and-decisions.md` asks). `tests.yml` is untouched; the gates are a sibling workflow.
- **New:** `version_gate.py`, `scan_payload.py`, the release-gates workflow. Nothing in the repo does any of the three today.
- **Unlocks:** a publish cannot carry an unknown manifest field, an unbumped plugin, a manifest/README/CHANGELOG version mismatch, a generic secret or a private identifier, including in commit messages. A future plugin is covered with no gate change (the gates read `marketplace.json`).
- **Goals (one line each):** S1 strict validate as a required check; S2 bump rule enforced exactly as CONTRIBUTING states it; S3 whole tracked tree plus PR commit messages scanned against one shared list, the private part never in the repo.

## Out of scope

- Editing `engineering-method` references to describe the shared list (that would bump engineering-method and collide with the 0.4.0 branch; follow-up after 0.4.0 ships).
- Plugin icons, `--profile directory`, `network.hosts` declarations.
- Scanning git history beyond the PR or push range; rewriting history.
- Checking `marketplace.json` entry edits other than version (descriptions, keywords).
- Changing `tests.yml` or the work-log `scan.py`.
- Any automation of the owner-run steps (secret entry, branch protection, guard edit).

## The S2 rule, precisely (from CONTRIBUTING "Versioning and changelogs" and the checklist "if the change is user-visible")

A file `plugins/<name>/<rest>` is **release-relevant** unless `<rest>` is exactly `README.md`, `ROADMAP.md` or `CHANGELOG.md`, or starts with `tests/` or `evals/`. Everything else (skills and their references, scripts, hooks, templates, schema, trackers, `.claude-plugin/plugin.json`) ships behaviour.

1. **Always (consistency, every event):** for every relative-path entry in `marketplace.json`, its `version` equals the plugin's `plugin.json` version, the root `README.md` row for that plugin reads `Current: <version>.`, and the plugin's `CHANGELOG.md` newest heading is `## <version> — YYYY-MM-DD`.
2. **On a pull request (bump):** for each plugin with a release-relevant file changed between the PR base and head, `plugin.json` version is strictly greater (semver) than at the base. A plugin absent at the base is new and needs only rule 1.

Rule 1 plus rule 2 together mean: bumped in both manifests, README updated, a new CHANGELOG entry at the top.

## File structure

```
.github/release-gates/secret-patterns.txt        generic secret shapes, one ERE per line (# comments)
.github/release-gates/version_gate.py            S2 gate
.github/release-gates/scan_payload.py            S3 scan
.github/release-gates/tests/test_version_gate.py
.github/release-gates/tests/test_scan_payload.py
.github/workflows/release-gates.yml              jobs: validate, version-gate, payload-scan
.claude-plugin/marketplace.json                  modified: three whenToUse keys removed
plugins/work-log/tests/test_scan.py              modified: lines 40-41 build their fakes by concatenation (tests/: exempt)
docs/superpowers/plans/2026-11-05-work-log.md    modified: lines 480-481 the same
CONTRIBUTING.md                                  modified: "Release gates" section
```

## Lanes and models

One branch, one worktree, so one writer at a time: tasks run serially. Tasks 1 and 5 are literal edits: **Sonnet** builds. Tasks 2, 3 and 4 carry literal code but have git edge cases that may need judgement when a test fails: **Opus** builds. **Fable 5.2** reviews the whole branch (Task 6) as a fresh agent in its own worktree and must execute probes, not read the diff. Every agent reports the model id it ran as. Bound: 40 tool calls per build task, 60 for the review.

---

### Task 1: S1, remove the unknown field

**Files:** Modify `.claude-plugin/marketplace.json`.

- [ ] **Step 1: show it failing.** Run `claude plugin validate --strict .`; expect exit 1 and the three `whenToUse` warnings.
- [ ] **Step 2: remove the keys** (and the comma before each) with a JSON round trip that keeps formatting:

```bash
python3 - <<'EOF'
import json
p = ".claude-plugin/marketplace.json"
d = json.load(open(p, encoding="utf-8"))
for e in d["plugins"]:
    e.pop("whenToUse")
open(p, "w", encoding="utf-8").write(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
EOF
git diff --stat   # expect only marketplace.json, 3 lines removed and 3 trailing-comma lines changed
```

- [ ] **Step 3: verify.** `claude plugin validate --strict .; echo $?` prints 0; repeat for each `plugins/*` directory.
- [ ] **Step 4: commit** `S1: drop whenToUse from marketplace entries (unknown field, ignored at load)`. The text it carried is not lost: each README row says what the plugin is for; the plan-layer CHANGELOG entry that added it stays as history.

### Task 2: S2, the version gate

**Files:** Create `.github/release-gates/version_gate.py`, `.github/release-gates/tests/test_version_gate.py`.

- [ ] **Step 1: write the failing tests.**

```python
"""Tests for version_gate.py: consistency (rule 1) and bump (rule 2)."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import version_gate as vg  # noqa: E402


def git(root, *args):
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def write(root, rel, text):
    p = Path(root) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def set_version(root, name, v, readme=True, changelog=True, manifest=True, market=True):
    if manifest:
        write(root, f"plugins/{name}/.claude-plugin/plugin.json", json.dumps({"name": name, "version": v}))
    if market:
        m = json.loads((Path(root) / ".claude-plugin/marketplace.json").read_text())
        for e in m["plugins"]:
            if e["name"] == name:
                e["version"] = v
        write(root, ".claude-plugin/marketplace.json", json.dumps(m))
    if readme:
        lines = (Path(root) / "README.md").read_text().splitlines()
        lines = [f"| [`{name}`](plugins/{name}) | Thing. Current: {v}. |" if f"[`{name}`]" in l else l for l in lines]
        write(root, "README.md", "\n".join(lines) + "\n")
    if changelog:
        cl = Path(root) / f"plugins/{name}/CHANGELOG.md"
        old = cl.read_text().replace("# Changelog\n", "") if cl.exists() else ""
        write(root, f"plugins/{name}/CHANGELOG.md", f"# Changelog\n\n## {v} — 2026-11-25\n\nChange.\n{old}")


class Repo:
    """A throwaway git repo with two plugins, alpha 0.1.0 and beta 1.0.0, committed as base."""

    def __enter__(self):
        self.tmp = tempfile.TemporaryDirectory()
        r = self.root = Path(self.tmp.name)
        git(r, "init", "-q", "-b", "main")
        git(r, "config", "user.email", "t@example.invalid")
        git(r, "config", "user.name", "t")
        write(r, ".claude-plugin/marketplace.json", json.dumps({"plugins": [
            {"name": "alpha", "source": "./plugins/alpha", "version": "0.1.0"},
            {"name": "beta", "source": "./plugins/beta", "version": "1.0.0"}]}))
        write(r, "README.md", "| [`alpha`](plugins/alpha) | A. Current: 0.1.0. |\n| [`beta`](plugins/beta) | B. Current: 1.0.0. |\n")
        for n, v in (("alpha", "0.1.0"), ("beta", "1.0.0")):
            write(r, f"plugins/{n}/.claude-plugin/plugin.json", json.dumps({"name": n, "version": v}))
            write(r, f"plugins/{n}/CHANGELOG.md", f"# Changelog\n\n## {v} — 2026-11-01\n\nFirst.\n")
            write(r, f"plugins/{n}/scripts/run.py", "x = 1\n")
        git(r, "add", "-A")
        git(r, "commit", "-q", "-m", "base")
        self.base = subprocess.run(["git", "-C", str(r), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        return self

    def commit(self):
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "head")

    def run(self, base=True):
        argv = ["--root", str(self.root)] + (["--base", self.base] if base else [])
        return vg.main(argv)

    def __exit__(self, *a):
        self.tmp.cleanup()


class Consistency(unittest.TestCase):
    def test_clean_repo_passes(self):
        with Repo() as r:
            self.assertEqual(r.run(base=False), 0)

    def test_marketplace_mismatch_fails(self):
        with Repo() as r:
            set_version(r.root, "alpha", "0.2.0", market=False)
            self.assertEqual(r.run(base=False), 1)

    def test_readme_mismatch_fails(self):
        with Repo() as r:
            set_version(r.root, "alpha", "0.2.0", readme=False)
            self.assertEqual(r.run(base=False), 1)

    def test_changelog_top_must_match(self):
        with Repo() as r:
            set_version(r.root, "alpha", "0.2.0", changelog=False)
            self.assertEqual(r.run(base=False), 1)

    def test_changelog_heading_needs_em_dash_and_date(self):
        with Repo() as r:
            write(r.root, "plugins/alpha/CHANGELOG.md", "# Changelog\n\n## 0.1.0 - 2026-11-01\n")
            self.assertEqual(r.run(base=False), 1)

    def test_bad_version_string_is_unusable(self):
        with Repo() as r:
            set_version(r.root, "alpha", "0.2")
            self.assertEqual(r.run(base=False), 2)

    def test_broken_json_is_unusable(self):
        with Repo() as r:
            write(r.root, ".claude-plugin/marketplace.json", "{")
            self.assertEqual(r.run(base=False), 2)


class Bump(unittest.TestCase):
    def test_script_change_without_bump_fails(self):
        with Repo() as r:
            write(r.root, "plugins/alpha/scripts/run.py", "x = 2\n")
            r.commit()
            self.assertEqual(r.run(), 1)

    def test_script_change_with_full_bump_passes(self):
        with Repo() as r:
            write(r.root, "plugins/alpha/scripts/run.py", "x = 2\n")
            set_version(r.root, "alpha", "0.2.0")
            r.commit()
            self.assertEqual(r.run(), 0)

    def test_bump_in_plugin_json_only_fails(self):
        with Repo() as r:
            write(r.root, "plugins/alpha/scripts/run.py", "x = 2\n")
            set_version(r.root, "alpha", "0.2.0", market=False, readme=False, changelog=False)
            r.commit()
            self.assertEqual(r.run(), 1)

    def test_version_going_down_fails(self):
        with Repo() as r:
            write(r.root, "plugins/beta/scripts/run.py", "x = 2\n")
            set_version(r.root, "beta", "0.9.0")
            r.commit()
            self.assertEqual(r.run(), 1)

    def test_semver_compares_numerically(self):
        self.assertGreater(vg.parse("0.10.0"), vg.parse("0.9.0"))

    def test_exempt_paths_need_no_bump(self):
        with Repo() as r:
            for rel in ("README.md", "ROADMAP.md", "tests/test_x.py", "evals/case/prompt.md"):
                write(r.root, f"plugins/alpha/{rel}", "doc\n")
            r.commit()
            self.assertEqual(r.run(), 0)

    def test_nested_readme_is_not_exempt(self):
        with Repo() as r:
            write(r.root, "plugins/alpha/skills/x/README.md", "doc\n")
            r.commit()
            self.assertEqual(r.run(), 1)

    def test_only_changed_plugin_must_bump(self):
        with Repo() as r:
            write(r.root, "plugins/alpha/scripts/run.py", "x = 2\n")
            set_version(r.root, "alpha", "0.2.0")
            r.commit()
            self.assertEqual(vg.changed_plugins(r.root, r.base), ["alpha"])
            self.assertEqual(r.run(), 0)

    def test_new_plugin_needs_only_consistency(self):
        with Repo() as r:
            m = json.loads((r.root / ".claude-plugin/marketplace.json").read_text())
            m["plugins"].append({"name": "gamma", "source": "./plugins/gamma", "version": "0.1.0"})
            write(r.root, ".claude-plugin/marketplace.json", json.dumps(m))
            write(r.root, "README.md", (r.root / "README.md").read_text() + "| [`gamma`](plugins/gamma) | G. Current: 0.1.0. |\n")
            write(r.root, "plugins/gamma/.claude-plugin/plugin.json", json.dumps({"name": "gamma", "version": "0.1.0"}))
            write(r.root, "plugins/gamma/CHANGELOG.md", "# Changelog\n\n## 0.1.0 — 2026-11-25\n")
            r.commit()
            self.assertEqual(r.run(), 0)

    def test_unknown_base_is_unusable(self):
        with Repo() as r:
            r.base = "0" * 40
            self.assertEqual(r.run(), 2)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: run and see it fail.** `python3 -m unittest discover -s .github/release-gates/tests -p 'test_version_gate.py' -v`; expect `ModuleNotFoundError: No module named 'version_gate'`.
- [ ] **Step 3: implement.**

```python
#!/usr/bin/env python3
"""Version-bump gate for the marketplace (release gate S2).

What: checks that every plugin's version agrees across marketplace.json, its
plugin.json, the root README row and the newest CHANGELOG heading; with --base,
also that every plugin whose shipped files changed since the base was bumped.
Why: CONTRIBUTING "Versioning and changelogs" states the rule; a rule missed more
than once becomes a check that fails (engineering-method docs-and-decisions).
Inputs: --root (repo root, default "."), --base (a commit; omit for consistency only).
Outputs: one line per problem, then a summary. Exit 0 clean, 1 problems, 2 unusable input.
Side effects: none; runs git read-only.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

EXEMPT_FILES = {"README.md", "ROADMAP.md", "CHANGELOG.md"}
EXEMPT_DIRS = ("tests/", "evals/")
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
HEADING = re.compile(r"^## (\d+\.\d+\.\d+) — \d{4}-\d{2}-\d{2}\s*$")
CURRENT = re.compile(r"Current: (\d+\.\d+\.\d+)\.")


def git(root, *args):
    """Run git read-only in root; raise CalledProcessError on failure."""
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=True).stdout


def parse(v):
    """'1.2.3' -> (1, 2, 3); ValueError on anything else."""
    if not isinstance(v, str) or not SEMVER.match(v):
        raise ValueError(f"not a MAJOR.MINOR.PATCH version: {v!r}")
    return tuple(int(x) for x in v.split("."))


def is_release_relevant(rel):
    """rel is a path inside one plugin directory; True when it ships behaviour."""
    return rel not in EXEMPT_FILES and not rel.startswith(EXEMPT_DIRS)


def changed_plugins(root, base):
    """Plugin directory names with a release-relevant change in base...HEAD."""
    names = set()
    for p in git(root, "diff", "--name-only", f"{base}...HEAD", "--", "plugins").splitlines():
        parts = p.split("/", 2)
        if len(parts) == 3 and is_release_relevant(parts[2]):
            names.add(parts[1])
    return sorted(names)


def readme_version(readme, name):
    for line in readme.splitlines():
        if f"[`{name}`](plugins/{name})" in line:
            m = CURRENT.search(line)
            return m.group(1) if m else None
    return None


def top_changelog_version(text):
    for line in text.splitlines():
        if line.startswith("## "):
            m = HEADING.match(line)
            return m.group(1) if m else None
    return None


def consistency(root):
    """Rule 1. Returns (problems, {plugin dir name: version})."""
    problems, versions = [], {}
    market = json.loads((root / ".claude-plugin/marketplace.json").read_text(encoding="utf-8"))
    readme = (root / "README.md").read_text(encoding="utf-8")
    for e in market["plugins"]:
        if not isinstance(e.get("source"), str):
            continue  # remote sources are not in this repo
        name, d = e["name"], root / e["source"]
        v = json.loads((d / ".claude-plugin/plugin.json").read_text(encoding="utf-8")).get("version")
        parse(v)
        versions[Path(e["source"]).name] = v
        if e.get("version") != v:
            problems.append(f"{name}: marketplace.json has {e.get('version')}, plugin.json has {v}")
        rv = readme_version(readme, name)
        if rv != v:
            problems.append(f"{name}: README.md row shows {rv}, plugin.json has {v}")
        cl = d / "CHANGELOG.md"
        cv = top_changelog_version(cl.read_text(encoding="utf-8")) if cl.exists() else None
        if cv != v:
            problems.append(f"{name}: CHANGELOG.md newest entry is {cv}, want '## {v} — YYYY-MM-DD' first")
    return problems, versions


def bump_problems(root, base, versions):
    """Rule 2: each plugin with shipped changes since base has a greater version."""
    git(root, "rev-parse", "--verify", f"{base}^{{commit}}")
    problems = []
    for name in changed_plugins(root, base):
        head = versions.get(name)
        if head is None:
            problems.append(f"{name}: files changed under plugins/{name} but no marketplace entry")
            continue
        r = subprocess.run(["git", "-C", str(root), "show", f"{base}:plugins/{name}/.claude-plugin/plugin.json"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            continue  # new plugin: rule 1 covers it
        old = json.loads(r.stdout).get("version")
        if parse(head) <= parse(old):
            problems.append(f"{name}: shipped files changed but version not bumped ({old} at base, {head} now)")
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=".")
    ap.add_argument("--base")
    a = ap.parse_args(argv)
    root = Path(a.root)
    try:
        problems, versions = consistency(root)
        changed = []
        if a.base:
            problems += bump_problems(root, a.base, versions)
            changed = changed_plugins(root, a.base)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as e:
        print(f"version_gate: unusable input: {e}", file=sys.stderr)
        return 2
    for p in problems:
        print(p)
    print(f"version_gate: {len(versions)} plugins checked; shipped changes since base: "
          f"{changed if a.base else 'not checked (no --base)'}; {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: run and see it pass.** Same command; expect all tests OK.
- [ ] **Step 5: run it on the real repo.** `python3 .github/release-gates/version_gate.py; echo $?` prints "3 plugins checked ... 0 problems", 0.
- [ ] **Step 6: the two bump branches (the brief's check, executed).**

```bash
G=$PWD/.github/release-gates/version_gate.py
git worktree add -q --detach ../vg-tc origin/tracker-controller
python3 "$G" --root ../vg-tc --base origin/main; echo "tracker-controller exit=$?"   # expect 0, changed ['plan-layer']
# control (a zero shown able to be non-zero): undo the bump in a scratch commit, expect exit 1
sed -i.bak 's/"version": "0.19.0"/"version": "0.18.0"/' ../vg-tc/plugins/plan-layer/.claude-plugin/plugin.json
rm ../vg-tc/plugins/plan-layer/.claude-plugin/plugin.json.bak
git -C ../vg-tc -c user.email=t@example.invalid -c user.name=t commit -qam ctl
python3 "$G" --root ../vg-tc --base origin/main; echo "control exit=$?"              # expect 1 (and consistency problems)
git worktree remove --force ../vg-tc
git worktree add -q --detach ../vg-rc root-cause-investigation
python3 "$G" --root ../vg-rc --base main; echo "root-cause exit=$?"                  # expect 0, changed ['engineering-method']
git worktree remove ../vg-rc
```

Record all three outputs in the task report.
- [ ] **Step 7: commit** `S2: version gate (consistency always, bump on PR); tests first`.

### Task 3: S3, the whole-payload scan and the shared pattern file

**Files:** Create `.github/release-gates/secret-patterns.txt`, `.github/release-gates/scan_payload.py`, `.github/release-gates/tests/test_scan_payload.py`. Modify `plugins/work-log/tests/test_scan.py` (lines 40-41) and `docs/superpowers/plans/2026-11-05-work-log.md` (lines 480-481).

**Design.** Two lists, two homes, one reader each place:
- *Generic shapes* (public knowledge: vendor key prefixes): `secret-patterns.txt`, committed, one extended regular expression per line, read by `scan_payload.py` in CI and by the local guard (Task 5). The patterns are kept to the subset that Python `re` and `grep -E` read the same way (a test enforces it). There is no allow marker and no exempt file (review C1, M1): a marker would hide a real secret on the same line, and the pattern file does not match itself (shown in Step 6). A deliberate fake in a test is built by string concatenation, so the file never holds the shape.
- *Private identifiers*: never in the repo. Locally, the guard's existing private file outside every repo. In CI, the repository secret `RELEASE_GATES_PRIVATE_LIST`, written to a temp file. Matched as case-insensitive fixed strings.
- *What ships*: every git-tracked file and every tracked path name (the marketplace installs from the repository, and the repository is public, so the tree is the payload), plus the commit messages of the PR range (or the push range on `main`). Commit author names and emails are not scanned (review M2; said in CONTRIBUTING).
- Output names the file and line, the commit, or `path #<n>` (the n-th line of `git ls-files`, so a hit in a path name never prints the name), and the kind ("generic pattern 4", "private list entry"); never the text. Nothing scanned, a missing pattern file, or a required private list that is missing or empty: exit 2.

- [ ] **Step 1: the pattern file** (the guard's 12 shapes, plus the AWS access key id shape that work-log's scan already checks):

```
# Generic secret shapes, one extended regular expression per line.
# Read by .github/release-gates/scan_payload.py (CI) and by the local pre-push guard.
# Keep to syntax Python re and grep -E read the same way: no (?...), no \d, no \b.
# Private identifiers never go here: they live outside the repository.
sk-ant-[A-Za-z0-9_-]{10,}
xox[abprs]-[0-9A-Za-z-]{10,}
xapp-[0-9A-Za-z-]{10,}
ghp_[A-Za-z0-9]{20,}
github_pat_[A-Za-z0-9_]{20,}
AIza[0-9A-Za-z_-]{30,}
-----BEGIN [A-Z ]*PRIVATE KEY
lsv2_[a-z]{2}_[A-Za-z0-9]{20,}
tvly-[A-Za-z0-9-]{20,}
GOCSPX-[A-Za-z0-9_-]{10,}
1//0[A-Za-z0-9_-]{20,}
ya29\.[A-Za-z0-9_-]{20,}
AKIA[0-9A-Z]{16}
```

- [ ] **Step 2: write the failing tests.**

```python
"""Tests for scan_payload.py. Fakes are built by concatenation so this file holds no secret shape."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import scan_payload as sp  # noqa: E402

PATTERNS = HERE.parent / "secret-patterns.txt"
FAKE_GH = "gh" + "p_" + "A" * 24
FAKE_AWS = "AK" + "IA" + "B" * 16
FAKE_PEM = "-----BEGIN " + "RSA PRIVATE KEY"
PRIVATE = "Zebulon" + "Quartz"  # an invented identifier standing in for a private one


def git(root, *args):
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


class Repo:
    def __enter__(self):
        self.tmp = tempfile.TemporaryDirectory()
        r = self.root = Path(self.tmp.name)
        git(r, "init", "-q", "-b", "main")
        git(r, "config", "user.email", "t@example.invalid")
        git(r, "config", "user.name", "t")
        (r / ".github/release-gates").mkdir(parents=True)
        shutil.copy(PATTERNS, r / ".github/release-gates/secret-patterns.txt")
        (r / "clean.md").write_text("nothing here\n")
        self.tokens = r.parent / (r.name + "-tokens.txt")
        self.tokens.write_text("# comment\n\n" + PRIVATE + "\n")
        return self

    def add(self, rel, text, msg="c"):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(text if isinstance(text, bytes) else text.encode())
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", msg)

    def run(self, *extra):
        return sp.main(["--root", str(self.root), *extra])

    def __exit__(self, *a):
        self.tokens.unlink(missing_ok=True)
        self.tmp.cleanup()


class PatternFile(unittest.TestCase):
    def test_every_pattern_compiles_in_python(self):
        self.assertGreaterEqual(len(sp.load_patterns(PATTERNS)), 13)

    def test_every_pattern_is_valid_for_grep_E(self):
        if not shutil.which("grep"):
            self.skipTest("grep not on PATH")
        for p in sp.load_lines(PATTERNS):
            r = subprocess.run(["grep", "-cE", "-e", p, "/dev/null"], capture_output=True)
            self.assertIn(r.returncode, (0, 1), f"grep -E rejects pattern {p!r}")

    def test_no_python_only_syntax(self):
        for p in sp.load_lines(PATTERNS):
            for bad in ("(?", "\\d", "\\b", "\\w", "\\s"):
                self.assertNotIn(bad, p)

    def test_each_fake_is_caught(self):
        pats = sp.load_patterns(PATTERNS)
        for fake in (FAKE_GH, FAKE_AWS, FAKE_PEM):
            self.assertTrue(any(p.search(fake) for p in pats), fake[:6])


class Files(unittest.TestCase):
    def test_clean_tree_passes(self):
        with Repo() as r:
            r.add("a.txt", "fine\n")
            self.assertEqual(r.run(), 0)

    def test_generic_secret_in_tracked_file_fails(self):
        with Repo() as r:
            r.add("plugins/x/scripts/run.py", f"KEY = '{FAKE_GH}'\n")
            self.assertEqual(r.run(), 1)

    def test_untracked_file_is_not_payload(self):
        with Repo() as r:
            r.add("a.txt", "fine\n")
            (r.root / "loose.txt").write_text(FAKE_GH)
            self.assertEqual(r.run(), 0)

    def test_no_marker_hides_a_secret(self):
        with Repo() as r:
            r.add("plugins/x/scripts/k.py", f"token = '{FAKE_GH}'  # release-gates: allow\n")
            self.assertEqual(r.run(), 1)

    def test_private_entry_in_path_name_fails_without_printing_it(self):
        with Repo() as r:
            r.add(f"notes/{PRIVATE}.md", "fine\n")
            out = subprocess.run([sys.executable, str(HERE.parent / "scan_payload.py"), "--root", str(r.root),
                                  "--tokens-file", str(r.tokens)], capture_output=True, text=True)
            self.assertEqual(out.returncode, 1)
            self.assertIn("path #", out.stdout)
            self.assertNotIn(PRIVATE.casefold(), (out.stdout + out.stderr).casefold())

    def test_generic_secret_in_path_name_fails(self):
        with Repo() as r:
            r.add(f"{FAKE_AWS}.txt", "fine\n")
            self.assertEqual(r.run(), 1)

    def test_private_entry_is_case_insensitive(self):
        with Repo() as r:
            r.add("doc.md", PRIVATE.upper() + "\n")
            self.assertEqual(r.run("--tokens-file", str(r.tokens)), 1)

    def test_output_never_contains_the_match(self):
        with Repo() as r:
            r.add("doc.md", f"{PRIVATE} {FAKE_GH}\n")
            out = subprocess.run([sys.executable, str(HERE.parent / "scan_payload.py"), "--root", str(r.root),
                                  "--tokens-file", str(r.tokens)], capture_output=True, text=True)
            self.assertEqual(out.returncode, 1)
            self.assertIn("doc.md:1", out.stdout)
            self.assertNotIn(PRIVATE, out.stdout + out.stderr)
            self.assertNotIn(PRIVATE.casefold(), (out.stdout + out.stderr).casefold())
            self.assertNotIn(FAKE_GH, out.stdout + out.stderr)

    def test_binary_file_skipped(self):
        with Repo() as r:
            r.add("img.bin", b"\x00\x01" + FAKE_GH.encode())
            self.assertEqual(r.run(), 0)

    def test_pattern_file_does_not_match_itself(self):
        with Repo() as r:
            r.add("a.txt", "1\n")
            self.assertEqual(r.run("--paths", ".github/release-gates/secret-patterns.txt"), 0)

    def test_paths_option_scans_only_given_files(self):
        with Repo() as r:
            ctl = r.root.parent / (r.root.name + "-ctl.txt")
            ctl.write_text(FAKE_AWS)
            try:
                self.assertEqual(r.run("--paths", str(ctl)), 1)
            finally:
                ctl.unlink()


class Commits(unittest.TestCase):
    def test_secret_in_commit_message_fails(self):
        with Repo() as r:
            r.add("a.txt", "1\n", msg="base")
            base = subprocess.run(["git", "-C", str(r.root), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
            r.add("b.txt", "2\n", msg=f"oops {FAKE_GH}")
            self.assertEqual(r.run("--commits", f"{base}..HEAD"), 1)

    def test_private_entry_in_commit_message_fails(self):
        with Repo() as r:
            r.add("a.txt", "1\n", msg="base")
            r.add("b.txt", "2\n", msg=f"met {PRIVATE}")
            self.assertEqual(r.run("--tokens-file", str(r.tokens), "--commits", "HEAD~1..HEAD"), 1)

    def test_bad_range_is_unusable(self):
        with Repo() as r:
            r.add("a.txt", "1\n")
            self.assertEqual(r.run("--commits", "nope..HEAD"), 2)


class FailLoudly(unittest.TestCase):
    def test_required_list_missing_is_unusable(self):
        with Repo() as r:
            r.add("a.txt", "1\n")
            self.assertEqual(r.run("--require-private-list"), 2)

    def test_required_list_empty_is_unusable(self):
        with Repo() as r:
            r.add("a.txt", "1\n")
            r.tokens.write_text("# only comments\n\n")
            self.assertEqual(r.run("--tokens-file", str(r.tokens), "--require-private-list"), 2)

    def test_tokens_file_named_but_absent_is_unusable(self):
        with Repo() as r:
            r.add("a.txt", "1\n")
            self.assertEqual(r.run("--tokens-file", str(r.root / "absent.txt")), 2)

    def test_missing_pattern_file_is_unusable(self):
        with Repo() as r:
            r.add("a.txt", "1\n")
            (r.root / ".github/release-gates/secret-patterns.txt").unlink()
            self.assertEqual(r.run(), 2)

    def test_nothing_scanned_is_unusable(self):
        with Repo() as r:
            self.assertEqual(r.run("--paths"), 2)


if __name__ == "__main__":
    unittest.main()
```

Note `Repo.__enter__` leaves the pattern file and `clean.md` uncommitted until the first `add`; every test calls `add` (or `--paths`) before it runs, except `test_nothing_scanned_is_unusable`, which passes an empty `--paths`.

- [ ] **Step 3: run and see it fail.** `python3 -m unittest discover -s .github/release-gates/tests -p 'test_scan_payload.py' -v`; expect `ModuleNotFoundError: No module named 'scan_payload'`.
- [ ] **Step 4: implement.**

```python
#!/usr/bin/env python3
"""Whole-payload secret and private-identifier scan for the marketplace (release gate S3).

What: scans every git-tracked file (or only --paths) and, with --commits, the commit
messages of a range, for generic secret shapes from the committed pattern file and,
when given, a private fixed-string list kept outside the repository.
Why: the pre-push guard sees only the lines a push adds; a release ships whole files.
Both read the same pattern file, so there is one list of generic shapes.
Inputs: --root, --patterns (default <root>/.github/release-gates/secret-patterns.txt),
--tokens-file (private list, one entry per line, # comments), --require-private-list,
--commits RANGE, --paths FILE... .
Outputs: one line per hit, "<file>:<line>: <kind>", "path #<n>: <kind>" (a hit in a path
name; n counts the scanned paths in order) or "commit <sha>: <kind>", never the matched text; then a summary. Exit 0 clean, 1 hits, 2 unusable input or nothing scanned.
Side effects: none; reads files and runs git read-only.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

PATTERN_FILE = ".github/release-gates/secret-patterns.txt"


def load_lines(path):
    """Non-empty, non-comment lines of a text file, stripped."""
    out = []
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if s and not s.startswith("#"):
            out.append(s)
    return out


def load_patterns(path):
    pats = [re.compile(p) for p in load_lines(path)]
    if not pats:
        raise ValueError(f"no patterns in {path}")
    return pats


def scan_text(text, patterns, tokens):
    """Yield (line number, kind) for each hit; at most one generic hit per line."""
    for n, line in enumerate(text.splitlines(), 1):
        low = line.casefold()
        if any(t in low for t in tokens):
            yield n, "private list entry"
        for i, p in enumerate(patterns, 1):
            if p.search(line):
                yield n, f"generic pattern {i}"
                break


def tracked_files(root):
    out = subprocess.run(["git", "-C", str(root), "ls-files", "-z"], capture_output=True, check=True).stdout
    return [p for p in out.decode("utf-8", "replace").split("\0") if p]


def commit_messages(root, rng):
    """Yield (sha, message) for each commit in rng."""
    out = subprocess.run(["git", "-C", str(root), "log", "--format=%H%x00%B%x01", rng],
                         capture_output=True, check=True).stdout.decode("utf-8", "replace")
    for rec in out.split("\x01"):
        sha, _, msg = rec.strip("\n").partition("\0")
        if sha:
            yield sha, msg


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=".")
    ap.add_argument("--patterns")
    ap.add_argument("--tokens-file")
    ap.add_argument("--require-private-list", action="store_true")
    ap.add_argument("--commits", metavar="RANGE")
    ap.add_argument("--paths", nargs="*")
    a = ap.parse_args(argv)
    root = Path(a.root)
    hits, scanned, skipped, ncommits = [], 0, 0, 0
    try:
        patterns = load_patterns(a.patterns or root / PATTERN_FILE)
        tokens = [t.casefold() for t in load_lines(a.tokens_file)] if a.tokens_file else []
        if a.require_private_list and not tokens:
            raise ValueError("private list required but missing or empty")
        files = a.paths if a.paths is not None else tracked_files(root)
        for idx, rel in enumerate(files, 1):
            for _, kind in scan_text(rel, patterns, tokens):
                hits.append(f"path #{idx}: {kind}")  # never the name itself
            data = (root / rel).read_bytes()
            if b"\0" in data[:8192]:
                skipped += 1
                continue
            scanned += 1
            for n, kind in scan_text(data.decode("utf-8", "replace"), patterns, tokens):
                hits.append(f"{rel}:{n}: {kind}")
        if a.commits:
            for sha, msg in commit_messages(root, a.commits):
                ncommits += 1
                for _, kind in scan_text(msg, patterns, tokens):
                    hits.append(f"commit {sha[:12]}: {kind}")
        if scanned == 0 and ncommits == 0:
            raise ValueError("nothing was scanned")
    except (OSError, ValueError, re.error, subprocess.CalledProcessError) as e:
        print(f"scan_payload: unusable input: {e}", file=sys.stderr)
        return 2
    for h in hits:
        print(h)
    private = f"on ({len(tokens)} entries)" if tokens else "off"
    print(f"scan_payload: {scanned} files, {skipped} binary skipped, {ncommits} commit messages, "
          f"{len(patterns)} generic patterns, private list {private}; {len(hits)} hits")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: run and see it pass.** Same command; all OK.
- [ ] **Step 6: run on the real tree, see the two known fakes.** `python3 .github/release-gates/scan_payload.py; echo $?` expects exactly four hit lines (`plugins/work-log/tests/test_scan.py:40`, `:41`, `docs/superpowers/plans/2026-11-05-work-log.md:480`, `:481`), exit 1. Any other hit stops the task and is reported. The pattern file must not appear (it does not match itself).
- [ ] **Step 7: build the deliberate fakes by concatenation** (as line 40's `"ghp_" + "a1" * 12` already does), so the committed lines hold no secret shape and the Step 9 commit passes the guard's own regex. In both files replace the two lines with (indentation as in each file; the runtime values are unchanged):

```python
        for k in ["sk-" + "ant-abcdefghijklmnop1234", "AK" + "IAABCDEFGHIJKLMNOP", "ghp_" + "a1" * 12,
                  "xox" + "b-1234567890-abc", "-----BEGIN " + "PRIVATE KEY", "Zx9" * 12]:
```

The plan doc is a record, but these two lines are code in it and a public file; the edit changes no meaning. `tests/` is exempt from the version gate, so work-log is not bumped. Re-run: 0 hits, exit 0. Run the work-log suite: `python3 -m pytest plugins/work-log/tests -q` still passes.
- [ ] **Step 8: private list, locally.** `python3 .github/release-gates/scan_payload.py --tokens-file "$PRIVATE_LIST" --require-private-list --commits origin/main..HEAD; echo $?` where `$PRIVATE_LIST` is the path the guard already reads (the owner supplies it; never written into a file in this repo). Expect 0 hits. Control: `head -n1 "$PRIVATE_LIST" > "$TMPDIR/ctl.txt"; python3 .github/release-gates/scan_payload.py --paths "$TMPDIR/ctl.txt" --tokens-file "$PRIVATE_LIST"; echo $?; rm "$TMPDIR/ctl.txt"` expects 1 with a line naming only the temp path.
- [ ] **Step 9: commit** `S3: whole-payload scan and the shared generic pattern file; test fakes built by concatenation`. Before it, run the guard's own check on the outgoing lines: `PAT=$(grep -v '^[[:space:]]*\(#\|$\)' .github/release-gates/secret-patterns.txt | paste -sd'|' -); git diff --cached | grep '^+' | grep -cE -e "$PAT"` prints 0 (the owner-step-2 form: comment lines stripped, joined, passed with `-e`; `-f` on the raw file would read the comments as patterns).

### Task 4: the workflow

**Files:** Create `.github/workflows/release-gates.yml`.

- [ ] **Step 1: write it.**

```yaml
name: release-gates

on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  gate-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
      - uses: actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0 # v7.1.0
        with:
          python-version: "3.13"
      - name: release-gate unit tests
        run: python -m unittest discover -s .github/release-gates/tests -v

  validate:
    runs-on: ubuntu-latest
    env:
      CLAUDE_CODE_VERSION: "2.1.322"
      CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC: "1"
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
      - name: Install the Claude Code CLI (pinned)
        run: npm install -g "@anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}"
      - name: claude plugin validate --strict (marketplace and every plugin)
        run: |
          set -euo pipefail
          claude --version
          claude plugin validate --strict .
          for d in plugins/*/; do claude plugin validate --strict "$d"; done

  version-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          fetch-depth: 0
      - uses: actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0 # v7.1.0
        with:
          python-version: "3.13"
      - name: Versions agree (every event)
        if: github.event_name != 'pull_request'
        run: python .github/release-gates/version_gate.py
      - name: Versions agree and changed plugins are bumped (pull request)
        if: github.event_name == 'pull_request'
        env:
          BASE: ${{ github.event.pull_request.base.sha }}
        run: python .github/release-gates/version_gate.py --base "$BASE"

  payload-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          fetch-depth: 0
      - uses: actions/setup-python@6d4fd22b20465ccc0f7354476588e8df7c9ca0e0 # v7.1.0
        with:
          python-version: "3.13"
      - name: Write the private list (never echoed)
        env:
          PRIVATE_LIST: ${{ secrets.RELEASE_GATES_PRIVATE_LIST }}
        run: |
          umask 077
          printf '%s\n' "$PRIVATE_LIST" > "$RUNNER_TEMP/private-list.txt"
      - name: Control runs (a scan that never fired is not shown able to)
        env:
          REQUIRE: ${{ github.event_name == 'push' || (github.event.pull_request.head.repo.full_name == github.repository && github.actor != 'dependabot[bot]') }}
        run: |
          set -uo pipefail
          printf 'AK%s%s\n' 'IA' 'CCCCCCCCCCCCCCCC' > "$RUNNER_TEMP/ctl-generic.txt"
          python .github/release-gates/scan_payload.py --paths "$RUNNER_TEMP/ctl-generic.txt"; rc=$?
          [ "$rc" -eq 1 ] || { echo "generic control did not fire (exit $rc)"; exit 1; }
          if [ "$REQUIRE" = "true" ]; then
            grep -v '^[[:space:]]*\(#\|$\)' "$RUNNER_TEMP/private-list.txt" | head -n1 > "$RUNNER_TEMP/ctl-private.txt"
            python .github/release-gates/scan_payload.py --paths "$RUNNER_TEMP/ctl-private.txt" \
              --tokens-file "$RUNNER_TEMP/private-list.txt" --require-private-list > /dev/null; rc=$?
            [ "$rc" -eq 1 ] || { echo "private control did not fire (exit $rc)"; exit 1; }
          fi
          rm -f "$RUNNER_TEMP"/ctl-*.txt
      - name: Scan every tracked file and the commit messages
        env:
          REQUIRE: ${{ github.event_name == 'push' || (github.event.pull_request.head.repo.full_name == github.repository && github.actor != 'dependabot[bot]') }}
          RANGE: ${{ github.event_name == 'pull_request' && format('{0}..{1}', github.event.pull_request.base.sha, github.event.pull_request.head.sha) || format('{0}..{1}', github.event.before, github.sha) }}
        run: |
          set -uo pipefail
          args=(--commits "$RANGE")
          # first push of a branch: "before" is all zeros; scan every message reachable from the new head
          case "$RANGE" in 0000000000000000000000000000000000000000..*) args=(--commits "${RANGE#*..}");; esac
          if [ "$REQUIRE" = "true" ]; then
            args+=(--tokens-file "$RUNNER_TEMP/private-list.txt" --require-private-list)
          else
            echo "::warning::Fork or Dependabot pull request: the private list is not available here. The maintainer runs scan_payload.py --tokens-file on this head before merging; CI checks it again on the push to main (detection after publish)."
          fi
          python .github/release-gates/scan_payload.py "${args[@]}"
      - name: Remove the private list
        if: always()
        run: rm -f "$RUNNER_TEMP/private-list.txt"
```

The `validate` job uses the runner's preinstalled Node. If the pinned CLI refuses that Node version on the first CI run, add `actions/setup-node` pinned by SHA (read its latest release tag and SHA in the same pass), not an unpinned install.

- [ ] **Step 2: lint locally.** `python3 -c "import yaml" 2>/dev/null` may be absent; instead check structure with `ruby -ryaml -e 'YAML.load_file(".github/workflows/release-gates.yml")'` or `actionlint` if installed; at minimum `grep -n 'uses:' .github/workflows/release-gates.yml` shows only the two SHAs above.
- [ ] **Step 3: dry run the job bodies locally** (the shell parts): run each `run:` block by hand in the worktree with `RUNNER_TEMP=$TMPDIR`, `REQUIRE=true`, a `RANGE` of `origin/main..HEAD`, and the owner's private list path. Expect: controls exit as designed, scan 0 hits, version gate 0, validate 0 with CLI 2.1.322.
- [ ] **Step 4: commit** `release-gates workflow: validate --strict, version gate, payload scan, gate tests`.

### Task 5: owner-run steps and CONTRIBUTING

**Files:** Modify `CONTRIBUTING.md` (new section "Release gates" after "Versioning and changelogs"; list the three gates; the S2 rule verbatim from this plan; "pre-push guard and CI read `.github/release-gates/secret-patterns.txt`"; there is no allow marker, so a fake in a test is built by string concatenation; commit author names and emails are not scanned; for a pull request from a fork or from Dependabot, the maintainer runs `python3 .github/release-gates/scan_payload.py --tokens-file <private list> --require-private-list` on its head before merging, because CI cannot read the secret there and its check on the push to `main` is detection after publish). Commit `CONTRIBUTING: release gates`.

Owner-run (founder gates: credentials and repository settings; not done by an agent; each says how to undo). **Step 1 is done before the branch's first pull request is opened**: without the secret, every same-repository PR fails payload-scan by design (required list empty, exit 2).

1. **Secret.** `gh secret set RELEASE_GATES_PRIVATE_LIST < "$PRIVATE_LIST"` (reads the file the guard already uses; nothing typed or echoed). Undo: `gh secret delete RELEASE_GATES_PRIVATE_LIST`.
2. **Guard reads the shared file** (edit to the guard script outside the repo, which `.git/hooks/pre-push` execs; back it up first). Replace the inline key-shape assignment with:

   ```bash
   top=$(git rev-parse --show-toplevel)
   shared="$top/.github/release-gates/secret-patterns.txt"
   if [ -s "$shared" ]; then PAT=$(grep -v '^[[:space:]]*\(#\|$\)' "$shared" | paste -sd'|' -); else PAT='<the existing inline value>'; fi
   ```

   Keep the fallback inline value and add the AWS shape `AKIA[0-9A-Z]{16}` to it, so both copies start equal. Pass the joined pattern with `-e "$PAT"` (one shape starts with `-----`, which `grep` would otherwise read as an option if it ever came first), and add `-i` to the private-list `grep` so local and CI matching agree (case-insensitive), and add the outgoing commit messages to the scanned text (one line: `msgs=$(git log --format=%B $range)`, appended to `added` before the two counts). The guard has no allow marker either. Its private file is read with `grep -Ff`, which treats every line as a token, `#` lines included, while the scanner strips `#` and blank lines: keep that file free of comments and blank lines (a blank line would match everything). Control: a commit adding a fake built at the shell (`printf 'AK%s%s\n' IA CCCCCCCCCCCCCCCC`) is refused by a push to a throwaway remote. Undo: restore the backup.
3. **Required checks**, after the first green run on a PR: `gh api -X POST repos/{owner}/{repo}/branches/main/protection/required_status_checks/contexts -f 'contexts[]=validate' -f 'contexts[]=version-gate' -f 'contexts[]=payload-scan' -f 'contexts[]=gate-tests'`. Read back with `gh api repos/{owner}/{repo}/branches/main/protection/required_status_checks`. Undo: the same call with `-X DELETE`.

### Task 6: whole-branch review (Fable 5.2, fresh worktree)

Brief (diff plus this plan, not the corpus). The reviewer must execute:
- Run both test suites and the three gates on the branch; paste outputs.
- Plant, in a scratch commit on a throwaway branch: a generic fake in a skill file (scan exits 1), a private-list stand-in via a temp tokens file (exit 1, output does not contain it), a script change without a bump (version gate exits 1), a README-only change (exit 0).
- Re-run Task 2 Step 6 on `origin/tracker-controller` and `root-cause-investigation`; confirm exit 0 and the control exit 1.
- Check every `uses:` SHA against PRs #2 and #3.
- Fit check: no second pattern list exists anywhere in the repo (`git grep -n 'sk-ant-'` lists only the pattern file and this plan's pattern block; the work-log fakes no longer match); no private identifier in any committed file (run the scan with the owner's list).
- Report findings as Critical / Important / Minor with the probe that showed each; an unreproduced finding is labelled a hypothesis.

Done means: three gates green on this branch, both version-bump branches pass the version gate as written, controls fire, review findings closed or answered.

## Rulings (owner, after the Fable 5.2 plan review)

1. **Fork and Dependabot pull requests:** accepted. Never use `pull_request_target`. CI cannot read the secret there, so its private-list check on the push to `main` is detection after publish, said plainly; the maintainer runs `scan_payload.py --tokens-file` on the head before merging (CONTRIBUTING).
2. **Guard matching:** case-insensitive (`-i`), as CI.
3. **Guard fallback list:** kept for the owner's other repositories, with the AWS shape added so both copies start equal.
4. **Guard scans commit messages:** yes, one line (owner step 2).
5. **engineering-method wording** (the list "lives outside every repository"): deferred to the release after 0.4.0.
