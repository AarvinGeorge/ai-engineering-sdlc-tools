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
    for raw in Path(path).read_text(encoding="utf-8-sig").splitlines():
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
    for n, line in enumerate(text.split("\n"), 1):
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
    out = subprocess.run(["git", "-C", str(root), "log", "--format=%H%x00%B%x01", "--end-of-options", rng],
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
            where = f"path #{idx}"
            name_hit = False
            for _, kind in scan_text(rel, patterns, tokens):
                hits.append(f"{where}: {kind}")  # never the name itself
                name_hit = True
            try:
                data = (root / rel).read_bytes()
            except OSError as e:
                print(f"scan_payload: unusable input: {type(e).__name__} reading {where}", file=sys.stderr)
                return 2
            if b"\0" in data[:8192]:
                skipped += 1
                continue
            scanned += 1
            for n, kind in scan_text(data.decode("utf-8", "replace"), patterns, tokens):
                hits.append(f"{where}:{n}: {kind}" if name_hit else f"{rel}:{n}: {kind}")
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
