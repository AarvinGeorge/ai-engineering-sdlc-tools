#!/usr/bin/env python3
"""Pre-upload privacy and style scan for a work-log entries JSON.

Usage: scan.py ENTRIES.json [--never FILE]
Exit 0 clean, 1 hits (one line each, never the matched text), 3 unreadable input.
"""
import argparse
import json
import os
import re
import sys

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE = re.compile(r"\+?\d[\d\s().-]{7,}\d")
KEY_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"xox[abprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"-----BEGIN"),
    re.compile(r"eyJ[A-Za-z0-9_-]{10,}\."),
]
LONG_TOKEN = re.compile(r"[A-Za-z0-9+/_=-]{32,}")
FILE_PATH = re.compile(r"(?:^|\s)(?:~|\.{0,2})/\S+|\b[\w-]+\.(?:py|js|ts|tsx|md|json|ya?ml|sh|html|css|toml|ipynb)\b")
COMMIT = re.compile(r"\b(?=[0-9a-f]*\d)(?=[0-9a-f]*[a-f])[0-9a-f]{7,40}\b")
BRANCH = re.compile(r"\b(?:feat|fix|chore|hotfix|release|bugfix)/[\w.-]+")
CODE_MARK = re.compile(r"`|[\w]+\(\)")
INTERNAL = re.compile(r"\b(?:doc|ADR|RFC|PR|ticket|issue)\s?#?\d+\b|#\d+\b|\b[A-Z]{2,6}-\d+\b|\bv\d+\.\d+(?:\.\d+)?\b")
ABBREV = re.compile(r"\b[A-Z]{2,}s?\b")
ABBREV_OK = {"AI", "HR", "CEO", "CFO", "CTO", "PDF", "UK", "US", "EU", "OK"}


def privacy_rules(text, never):
    hits = []
    if EMAIL.search(text):
        hits.append("email")
    if any(sum(c.isdigit() for c in m.group(0)) >= 10 for m in PHONE.finditer(text)):
        hits.append("phone")
    key = any(p.search(text) for p in KEY_PATTERNS)
    if not key:
        for m in LONG_TOKEN.finditer(text):
            t = m.group(0)
            if any(c.isalpha() for c in t) and any(c.isdigit() for c in t):
                key = True
                break
    if key:
        hits.append("key-like")
    if any(n.search(text) for n in never):
        hits.append("never-list")
    return hits


def style_rules(summary, style):
    hits = []
    if len(summary.split()) > 30:
        hits.append("over-30-words")
    if style != "detailed":
        if FILE_PATH.search(summary):
            hits.append("file-path")
        if COMMIT.search(summary):
            hits.append("commit-hash")
        if BRANCH.search(summary):
            hits.append("branch-name")
        if CODE_MARK.search(summary):
            hits.append("code-mark")
        if INTERNAL.search(summary):
            hits.append("internal-code")
        if any(m.group(0).rstrip("s") not in ABBREV_OK and m.group(0) not in ABBREV_OK
               for m in ABBREV.finditer(summary)):
            hits.append("abbreviation")
    return hits


def load_never(path):
    pats = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            pats.append(re.compile(r"(?<!\w)" + re.escape(line) + r"(?!\w)", re.IGNORECASE))
    return pats


def fail_input(msg):
    sys.stderr.write("scan: %s\n" % msg)
    sys.exit(3)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("entries")
    ap.add_argument("--never")
    args = ap.parse_args(argv)

    try:
        with open(args.entries, encoding="utf-8") as f:
            data = json.load(f)
        meta = data["meta"]
        rows = data["entries"]
        if not isinstance(meta, dict) or not isinstance(rows, list):
            raise ValueError("meta/entries have the wrong type")
        for e in rows:
            if not isinstance(e, dict):
                raise ValueError("entry is not an object")
            for k in ("summary", "project"):
                if not isinstance(e.get(k, ""), str):
                    raise ValueError("entry %s is not text" % k)
        notes = meta.get("notes") or []
        scope = meta.get("scope_name", "")
        if not isinstance(notes, list) or not isinstance(scope, str) \
                or not all(isinstance(n, str) for n in notes):
            raise ValueError("meta fields have the wrong type")
    except (OSError, ValueError, KeyError, TypeError) as ex:
        fail_input("cannot read entries (%s)" % type(ex).__name__)

    never_path = args.never
    explicit = never_path is not None
    if not explicit:
        never_path = os.path.join(os.path.expanduser("~"), ".config", "work-log", "never.txt")
    never = []
    if explicit or os.path.exists(never_path):
        try:
            never = load_never(never_path)
        except (OSError, UnicodeDecodeError) as ex:
            fail_input("cannot read never-list (%s)" % type(ex).__name__)

    style = meta.get("style", "hr")
    out = []

    def emit(eid, field, rules):
        for r in rules:
            out.append("entry %s field %s: %s" % (eid, field, r))

    emit("meta", "scope_name", privacy_rules(scope, never))
    for i, n in enumerate(notes):
        emit("meta", "notes[%d]" % i, privacy_rules(n, never))
    for idx, e in enumerate(rows):
        eid = str(e.get("id") or "#%d" % (idx + 1))
        summary = e.get("summary", "")
        emit(eid, "project", privacy_rules(e.get("project", ""), never))
        if not summary.strip():
            emit(eid, "summary", ["empty-summary"])
            continue
        emit(eid, "summary", privacy_rules(summary, never) + style_rules(summary, style))

    if out:
        print("\n".join(out))
        return 1
    print("scan: clean (%d entries)" % len(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
