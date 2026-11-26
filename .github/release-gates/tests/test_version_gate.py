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
