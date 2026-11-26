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
