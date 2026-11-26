#!/usr/bin/env python3
"""Compare a diff with a plan's steps and out-of-scope list; print a fixed block to paste.

What: reads one text holding a plan's numbered steps, its out-of-scope bullets, the
`git diff --stat` lines and any hunks, and prints PLAN_CONFORMANCE v1 ... end with one
MISMATCH line per out-of-scope change or step with no change (facts code settles), one CHECK
line per changed existing definition (the model judges whether a step covers it; it withholds
only when no step names the file), UNMATCHED lines for the model to judge, and a
VERIFIED: withheld | ok line.
Use when: tier b or c, a plan exists, and "verified" is about to be said
(references/measurement-and-state-claims.md).
Inputs: a path, or "-" for stdin (no argument is an error, never a wait).
Output: the block on stdout; exit 0 for either verdict (it reports, never gates); exit 2 and
"ERROR: cannot compare (...)" on stderr when there are no steps or no diff-stat lines.
Side effects: none (reads text only, runs no git).
Role: computes the plan-versus-diff facts; the owner rules on each mismatch.
"""
import re
import sys
from fnmatch import fnmatch

PATH = re.compile(r"`([\w./-]+(?:/|\.\w+))`")
STAT = re.compile(r"^\s*(\S+|\S*\{\S* => \S*\}\S*|\S+ => \S+)\s+\|\s+(?:\d+|Bin\b)")
SUMMARY = re.compile(r"^\s*(\d+) files? changed\b")
KEY = re.compile(r"""(--[\w-]+|def\s+\w+|class\s+\w+|^\s*[A-Za-z_]\w*\s*=)""")
HEAD = re.compile(r"^(?:\+\+\+ b/|diff --git a/)(\S+)")
WITHHELD = ("VERIFIED: withheld (owner rules on each: keep and add to the plan | revert | "
            "move to a later item | do the step)")


def parse(text):
    """What: split text into steps, out-of-scope items, changed files and hunk lines.
    Use when: conformance(). Inputs: text. Output: (steps, oos, files, removed, added).
    Side effects: none. Role: parsing."""
    steps, oos, files, removed, added = [], [], [], [], []
    section, cur, in_diff = None, None, False
    for line in text.splitlines():
        low = line.lower()
        if line.startswith("```"):
            in_diff = line.strip() == "```diff"
            continue
        m = STAT.match(line)
        if m:
            files.extend(stat_paths(m.group(1)))
            continue
        h = HEAD.match(line)
        if h or line.startswith("@@"):
            cur, in_diff = (h.group(1) if h else cur), True
            continue
        if in_diff and line.startswith("-") and not line.startswith("---"):
            removed.append((cur, line[1:]))
            continue
        if in_diff and line.startswith("+") and not line.startswith("+++"):
            added.append((cur, line[1:]))
            continue
        if in_diff and line[:1] in (" ", "\\"):
            continue
        item = re.match(r"\s*(\d+\.|[-*] )", line)
        if re.search(r"out[- ]of[- ]scope", low) and len(line) < 60 and not item:
            section = "oos"
            continue
        if re.search(r"\bsteps?\b", low) and len(line) < 60 and not item:
            section = "steps"
            continue
        hit = [f for f in files if names(line, f)] or [p for p in PATH.findall(line) if "/" in p]
        if hit and not re.match(r"\s*(\d+\.|[-*] )", line):
            cur = hit[0]
        if section == "steps" and re.match(r"\s*\d+\.", line):
            steps.append(line.strip())
        elif section == "oos" and re.match(r"\s*[-*] ", line):
            oos.append(line.strip()[2:])
    return steps, oos, files, removed, added


def stat_paths(p):
    """What: the path or paths one diff-stat name stands for (a rename gives old and new).
    Use when: parse(). Inputs: the name column of a stat line. Output: list of paths.
    Side effects: none. Role: parsing."""
    m = re.match(r"(.*)\{(.*) => (.*)\}(.*)$", p)
    if m:
        return [re.sub(r"/+", "/", m.group(1) + x + m.group(4)) for x in m.group(2, 3)]
    return p.split(" => ")


def key(line):
    """What: the definition key of a code line (--flag, def x, class x, name =).
    Use when: matching removed and added lines. Inputs: str. Output: str or None.
    Side effects: none. Role: parsing."""
    m = KEY.search(line)
    return m.group(1).strip().rstrip("=").strip() if m else None


def names(text, word):
    """What: whether text names word as a whole token, not inside a longer name or path.
    Use when: deciding if a step names a key or a file. Inputs: text, word (str).
    Output: bool. Side effects: none. Role: parsing."""
    return re.search(r"(?<![\w./-])%s(?![\w/-])" % re.escape(word), text) is not None


def count(n, word):
    """What: "<n> <word>", plural (s, or es after ch) unless n is 1. Use when: the CONFORMANCE
    line. Inputs: int, singular word. Output: str. Side effects: none. Role: plumbing."""
    return "%d %s%s" % (n, word, "" if n == 1 else ("es" if word.endswith("ch") else "s"))


def globbed(p):
    """What: a backticked path as a glob (a trailing / covers the directory). Use when: matching
    files. Inputs: str. Output: str. Side effects: none. Role: parsing."""
    return p + "*" if p.endswith("/") else p


def conformance(text):
    """What: the block lines for one text. Use when: main(). Inputs: text.
    Output: list of lines. Raises ValueError when it cannot compare. Side effects: none.
    Role: computes the mismatches."""
    steps, oos, files, removed, added = parse(text)
    if not steps or not files:
        raise ValueError("no numbered plan steps" if not steps else "no diff --stat lines")
    mism, checks, unmatched, held = [], [], [], 0
    for f in files:
        for item in oos:
            if any(fnmatch(f, globbed(g)) for g in PATH.findall(item)):
                mism.append("MISMATCH out-of-scope %s (out of scope: %s)" % (f, item))
                break
    step_text = " ".join(steps)
    step_code = " ".join(re.findall(r"`([^`]+)`", step_text))
    for cur, old in removed:
        k = key(old)
        new = next((n for c, n in added if c == cur and key(n) == k and n != old), None)
        if k and new is not None and not (
                names(step_code, k) or (re.search(r"[-_\dA-Z]", k) and names(step_text, k))):
            named = bool(cur) and names(step_text, cur)
            held += not named
            checks.append("CHECK changed-existing %s %s (%s -> %s) (existing definition changed; %s; "
                          "you judge whether a step covers it)" % (
                              cur, k, old.strip(), new.strip(),
                              "a step names %s" % cur if named else "no step names %s" % cur))
    for i, s in enumerate(steps, 1):
        named = [p for p in PATH.findall(s) if "/" in p or "." in p.split("/")[-1]]
        named = [p for p in named if not p.startswith("--")]
        if named and not any(any(fnmatch(f, globbed(p)) for f in files) for p in named):
            mism.append("MISMATCH step-without-change %s (step %d)" % (", ".join(named), i))
    flagged = " ".join(mism + checks)
    for f in files:
        if not names(flagged, f) and not names(step_text, f):
            unmatched.append("UNMATCHED %s (no step names it; you judge)" % f)
    out = ["PLAN_CONFORMANCE v1",
           "CONFORMANCE: %s, %s (%s, %s, %s changed)"
           % (count(len(mism), "mismatch"), count(len(checks), "check"), count(len(steps), "step"),
              count(len(oos), "out-of-scope item"), count(len(files), "file"))]
    said = [int(m.group(1)) for m in map(SUMMARY.match, text.splitlines()) if m]
    read = sum(1 for ln in text.splitlines() if STAT.match(ln))
    unread = []
    if said and sum(said) != read:
        unread.append("UNREAD diff-stat (its summary says %d files changed, %d stat lines read; a name "
                      "this script cannot parse, such as one with spaces; compare those by hand)"
                      % (sum(said), read))
    out += mism + checks + unmatched + unread
    out.append(WITHHELD if mism or held or unread else
               "VERIFIED: ok (diff matches the plan: %d steps, 0 out-of-scope changes)" % len(steps))
    return out + ["PLAN_CONFORMANCE end"]


def main(argv):
    """What: CLI entry. Use when: run as a script. Inputs: argv. Output: exit code.
    Side effects: prints. Role: plumbing."""
    try:
        if not argv:
            raise ValueError("give the plan+diff file path, or - for stdin")
        src = argv[0]
        if src == "-":
            text = sys.stdin.read()
        else:
            with open(src, encoding="utf-8") as fh:
                text = fh.read()
        lines = conformance(text)
    except (OSError, ValueError) as e:
        print("ERROR: cannot compare (%s)" % e, file=sys.stderr)
        return 2
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
