"""Tests for scan_payload.py. Fakes are built by concatenation so this file holds no secret shape."""
import contextlib
import io
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
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return sp.main(["--root", str(self.root), *extra])

    def cli(self, *extra):
        return subprocess.run([sys.executable, str(HERE.parent / "scan_payload.py"), "--root", str(self.root), *extra],
                              capture_output=True, text=True)

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

    def test_tracked_symlink_to_directory_is_skipped(self):
        with Repo() as r:
            r.add("a.txt", "fine\n")
            (r.root / "sub").mkdir()
            (r.root / "sub/b.txt").write_text("x\n")
            (r.root / "link").symlink_to("sub")
            git(r.root, "add", "-A")
            git(r.root, "commit", "-q", "-m", "link")
            out = r.cli()
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertIn("1 binary skipped", out.stdout)

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

class Leaks(unittest.TestCase):
    def test_token_as_name_and_content_never_printed(self):
        with Repo() as r:
            r.add(f"notes/{PRIVATE}.md", f"{PRIVATE}\n")
            out = r.cli("--tokens-file", str(r.tokens))
            self.assertEqual(out.returncode, 1)
            self.assertIn("path #", out.stdout)
            self.assertNotIn(PRIVATE.casefold(), (out.stdout + out.stderr).casefold())

    def test_deleted_tracked_file_with_token_name_does_not_leak(self):
        with Repo() as r:
            r.add(f"notes/{PRIVATE}.md", "x\n")
            (r.root / f"notes/{PRIVATE}.md").unlink()
            out = r.cli("--tokens-file", str(r.tokens))
            self.assertEqual(out.returncode, 2)
            self.assertNotIn(PRIVATE.casefold(), (out.stdout + out.stderr).casefold())
            self.assertIn("path #", out.stderr)

    def test_bom_in_private_list_is_ignored(self):
        with Repo() as r:
            r.add("doc.md", PRIVATE + "\n")
            r.tokens.write_bytes(b"\xef\xbb\xbf" + PRIVATE.encode() + b"\n")
            self.assertEqual(r.run("--tokens-file", str(r.tokens)), 1)

    def test_commit_range_cannot_be_an_option(self):
        with Repo() as r:
            r.add("a.txt", "1\n")
            self.assertEqual(r.run("--commits=--output=x"), 2)
            self.assertFalse((r.root / "x").exists())

    def test_line_numbers_count_only_newlines(self):
        with Repo() as r:
            r.add("doc.md", "a\u2028" + PRIVATE + "\n")
            out = r.cli("--tokens-file", str(r.tokens))
            self.assertIn("doc.md:1:", out.stdout)


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
