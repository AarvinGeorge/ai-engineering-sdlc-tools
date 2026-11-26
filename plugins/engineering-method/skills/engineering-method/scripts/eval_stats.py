#!/usr/bin/env python3
"""Compute the figures a behaviour-eval report needs, as fixed blocks to paste.

What: three subcommands. floor: k of n, a Wilson 95% interval, pass^n and a reliable /
not-reliable verdict for a never-break criterion (runs marked I are invalid and not counted).
calibrate: a judge's agreement with the owner's rulings, split into answers the owner passed
and answers the owner failed; rates only at 30 labels a side or more. runs: classify every run
in a claude plugin eval result.json as valid, invalid (a case's fixture input never reached
the agent, read from the kept trace), errored or no-trace.
Use when: writing an eval report (references/behaviour-evals.md); paste the block as printed.
Inputs: argv; calibrate reads a CSV path or "-" (stdin); runs reads a result.json and the
trace files it points to.
Output: an "EVAL_STATS <cmd> v1" ... "EVAL_STATS end" block on stdout. Exit 0 whenever it
computed (any verdict: it reports, it never gates); exit 2 on bad input, "ERROR: ..." on
stderr and nothing on stdout.
Side effects: none (reads files only, no network).
Role: computes facts so the model relays them instead of working them out by hand.
"""
import argparse
import csv
import io
import json
import math
import os
import re
import sys
from statistics import NormalDist

Z = NormalDist().inv_cdf(0.975)
MIN_PER_SIDE = 30
MISS_STARTS = ("no files found", "file does not exist", "no matches found")
MISS_END = "no such file or directory"


class BadInput(Exception):
    """What: an input the script will not compute on. Use when: any parse or check fails.
    Inputs: message. Output: exception. Side effects: none. Role: fail loudly (exit 2)."""


def wilson(k, n):
    """What: Wilson 95% score interval for k successes of n. Use when: any k of n is shown.
    Inputs: ints, n > 0. Output: (low, high) clamped to [0, 1]. Side effects: none. Role: math."""
    p = k / n
    d = 1 + Z * Z / n
    c = (p + Z * Z / (2 * n)) / d
    h = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def pass_k(k, n):
    """What: chance all n runs pass at the observed rate k/n, from the exact fraction.
    Use when: a never-break criterion. Inputs: ints, n > 0. Output: float. Side effects: none.
    Role: math."""
    return (k / n) ** n


def f2(x):
    """What: two-decimal text. Use when: printing any rate. Inputs: float. Output: str.
    Side effects: none. Role: formatting."""
    return format(x, ".2f")


def floor_block(name, results):
    """What: the floor block for one criterion. Use when: `floor`. Inputs: name, letters P/F/I.
    Output: list of lines. Side effects: none. Role: computes the never-break verdict."""
    name = " ".join(name.split())
    r = results.strip().upper()
    if not r:
        raise BadInput("no runs for criterion %r" % name)
    bad = sorted(set(r) - set("PFI"))
    if bad:
        raise BadInput("results for %r hold %r; use P, F or I per run" % (name, "".join(bad)))
    fails = [str(i) for i, c in enumerate(r, 1) if c == "F"]
    inval = [str(i) for i, c in enumerate(r, 1) if c == "I"]
    n, k = len(r) - len(inval), r.count("P")
    out = ["EVAL_STATS floor v1", "CRITERION: %s" % name,
           "RUNS: %d of %d passed; failed runs: %s; invalid runs: %s" % (
               k, n, ", ".join(fails) or "none",
               (", ".join(inval) + " (not counted)") if inval else "none")]
    if n == 0:
        out += ["WILSON95: n/a (0 valid runs)", "PASS_K: n/a (0 valid runs)", "PASS_K_LOW: n/a (0 valid runs)",
                "VERDICT: no valid runs (re-run after delivery is confirmed)"]
    else:
        lo, hi = wilson(k, n)
        out += ["WILSON95: %s-%s (true per-run rate, %d of %d)" % (f2(lo), f2(hi), k, n),
                "PASS_K: pass^%d = %s at the observed rate %s" % (n, f2(pass_k(k, n)), f2(k / n)),
                "PASS_K_LOW: pass^%d = %s at the interval's lower bound %s" % (n, f2(lo ** n), f2(lo))]
        out.append("VERDICT: reliable on this sample (%d of %d; rates below %s not ruled out)" % (k, n, f2(lo))
                   if k == n else "VERDICT: not-reliable (a never-break rule needs %d of %d)" % (n, n))
    return out + ["EVAL_STATS end"]


def read_labels(path):
    """What: parse the labels CSV. Use when: `calibrate`. Inputs: path or "-".
    Output: list of dicts with criterion, owner, judge (lower-cased). Side effects: reads a file
    or stdin. Role: input check (duplicates and bad values are errors, never skipped)."""
    try:
        if path == "-":
            text = sys.stdin.read()
        else:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
    except (OSError, UnicodeDecodeError) as e:
        raise BadInput("cannot read labels: %s" % e)
    rd = csv.DictReader(io.StringIO(text))
    if not rd.fieldnames:
        raise BadInput("labels have no header (answer_id,criterion,owner,judge)")
    missing = [c for c in ("answer_id", "criterion", "owner", "judge") if c not in rd.fieldnames]
    if missing:
        raise BadInput("labels lack column(s) %s" % ", ".join(missing))
    rows, seen = [], set()
    for i, row in enumerate(rd, 2):
        owner, judge = (row["owner"] or "").strip().lower(), (row["judge"] or "").strip().lower()
        if owner not in ("pass", "fail") or judge not in ("pass", "fail"):
            raise BadInput("row %d: owner and judge must be pass or fail" % i)
        key = ((row["answer_id"] or "").strip(), " ".join((row["criterion"] or "").split()))
        if not key[0] or not key[1]:
            raise BadInput("row %d: answer_id and criterion must not be empty" % i)
        if key in seen:
            raise BadInput("row %d: answer %s is labelled twice for %r" % (i, key[0], key[1]))
        seen.add(key)
        rows.append({"criterion": key[1], "owner": owner, "judge": judge})
    return rows


def side_line(label, verb, k, n, side):
    """What: one TRUE_POSITIVE / TRUE_NEGATIVE line. Use when: `calibrate`. Inputs: counts.
    Output: str (a rate only when n >= MIN_PER_SIDE). Side effects: none. Role: formatting rule."""
    if n == 0:
        return "%s: not measured (0 answers the owner %s)" % (label, side)
    if n >= MIN_PER_SIDE:
        lo, hi = wilson(k, n)
        return "%s: %s (%d of %d, Wilson95 %s-%s)" % (label, f2(k / n), k, n, f2(lo), f2(hi))
    return "%s: judge %s %d of %d answers the owner %s" % (label, verb, k, n, side)


def calibrate_blocks(rows):
    """What: one calibrate block per criterion, sorted by name. Use when: `calibrate`.
    Inputs: rows from read_labels. Output: list of lines. Side effects: none.
    Role: computes the judge's agreement per side."""
    out = ["EVAL_STATS calibrate v1"]
    crits = sorted({r["criterion"] for r in rows}) or [None]
    for c in crits:
        rs = [r for r in rows if r["criterion"] == c]
        op = [r for r in rs if r["owner"] == "pass"]
        of = [r for r in rs if r["owner"] == "fail"]
        tp = sum(r["judge"] == "pass" for r in op)
        tn = sum(r["judge"] == "fail" for r in of)
        out += ["CRITERION: %s" % (c if c is not None else "(none labelled)"),
                "LABELS: %d (owner-pass %d, owner-fail %d)" % (len(rs), len(op), len(of)),
                side_line("TRUE_POSITIVE", "passed", tp, len(op), "passed"),
                side_line("TRUE_NEGATIVE", "failed", tn, len(of), "failed")]
        if len(op) >= MIN_PER_SIDE and len(of) >= MIN_PER_SIDE:
            out.append("STATUS: calibrated")
        else:
            gaps = [s for s, m in (("true positive", len(op)), ("true negative", len(of))) if m == 0]
            out.append("STATUS: uncalibrated, n = %d (needs %d owner-pass and %d owner-fail; has %d and %d%s)" % (
                len(rs), MIN_PER_SIDE, MIN_PER_SIDE, len(op), len(of),
                "".join("; %s rate unmeasured" % g for g in gaps)))
    return out + ["EVAL_STATS end"]


def trace_events(path):
    """What: (tool_use, tool_result) pairs from a stream-json trace. Use when: `runs`.
    Inputs: trace path. Output: list of (name, input dict, result text, is_error).
    Side effects: reads the file. Role: input check (a malformed line is an error, never skipped)."""
    uses, pairs = {}, []
    with open(path, encoding="utf-8") as fh:
        for ln, line in enumerate(fh, 1):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except ValueError:
                raise BadInput("%s line %d is not JSON" % (path, ln))
            msg = obj.get("message", obj) if isinstance(obj, dict) else {}
            content = msg.get("content") if isinstance(msg, dict) else None
            for b in content if isinstance(content, list) else []:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "tool_use":
                    uses[b.get("id")] = (b.get("name"), b.get("input") if isinstance(b.get("input"), dict) else {})
                elif b.get("type") == "tool_result" and b.get("tool_use_id") in uses:
                    c = b.get("content")
                    text = c if isinstance(c, str) else " ".join(
                        str(x.get("text") or "") if x.get("type", "text") == "text" else "[%s block]" % x.get("type")
                        for x in (c if isinstance(c, list) else [c] if c else []) if isinstance(x, dict))
                    name, inp = uses[b["tool_use_id"]]
                    pairs.append((name, inp, text, bool(b.get("is_error")) or "<tool_use_error>" in text))
    return pairs


def delivered(pairs, prefix):
    """What: True when a tool call on a path under prefix returned content. Use when: `runs`
    with --fixture. Inputs: pairs, prefix. Output: bool. Side effects: none.
    Role: the 'confirmed in a kept trace' fact."""
    want = re.compile(r"(?:^|[\s'\"=/])" + re.escape(prefix.strip("/")) + r"(?:$|[\s'\"/])")
    for _name, inp, text, err in pairs:
        targets = [v for v in inp.values() if isinstance(v, str)]
        if any(want.search(t) for t in targets) and not err and not is_miss(text):
            return True
    return False


def is_miss(text):
    """What: True when a tool result is only a nothing-there message, not content.
    Use when: deciding delivery or a SIGNAL line. Inputs: result text. Output: bool.
    Side effects: none. Role: reads the whole message, so file text that quotes such a phrase is content."""
    low = text.strip().lower()
    return not low or low.startswith(MISS_STARTS) or ("\n" not in low and low.endswith(MISS_END))


def runs_block(path, fixtures):
    """What: the runs block for one result.json. Use when: `runs`. Inputs: path,
    {case: prefix}. Output: list of lines. Side effects: reads files. Role: classifies runs."""
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as e:
        raise BadInput("cannot read %s: %s" % (path, e))
    if not isinstance(data, dict):
        raise BadInput("%s is not a JSON object" % path)
    if data.get("schemaVersion") != 1:
        raise BadInput("schemaVersion is %r; this script reads 1" % data.get("schemaVersion"))
    cases = data.get("cases")
    if not isinstance(cases, list):
        raise BadInput("result has no cases list")
    for c in cases:
        if not isinstance(c, dict) or not isinstance(c.get("name"), str):
            raise BadInput("a case in %s is not an object with a name" % path)
    names = [c.get("name") for c in cases]
    for f in fixtures:
        if f not in names:
            raise BadInput("--fixture names %r, which is not a case in the result" % f)
    base = os.path.dirname(os.path.abspath(path))
    counts = {"valid": 0, "invalid": 0, "errored": 0, "no-trace": 0}
    case_lines, signals, reruns, total = [], [], [], 0
    for c in cases:
        arms = c.get("arms")
        if not isinstance(arms, dict):
            raise BadInput("case %r has no arms" % c.get("name"))
        for arm, runs in arms.items():
            per = {"valid": 0, "invalid": 0, "errored": 0, "no-trace": 0}
            confirmed, tallies = 0, {}
            if not isinstance(runs, list):
                raise BadInput("case %r arm %r is not a list of runs" % (c["name"], arm))
            for i, r in enumerate(runs, 1):
                total += 1
                if not isinstance(r, dict) or not isinstance(r.get("graders"), list) or "passed" not in r \
                        or not all(isinstance(g, dict) for g in r["graders"]) \
                        or not isinstance(r.get("tracePath"), (str, type(None))):
                    raise BadInput("case %r run %d lacks graders or passed" % (c.get("name"), i))
                tp = r.get("tracePath")
                tpath = tp if tp and os.path.isabs(tp) and os.path.exists(tp) else (
                    os.path.join(base, tp) if tp else None)
                if r.get("error"):
                    kind = "errored"
                elif not tpath or not os.path.exists(tpath):
                    kind = "no-trace"
                else:
                    try:
                        pairs = trace_events(tpath)
                    except (OSError, UnicodeDecodeError) as e:
                        raise BadInput("cannot read trace %s: %s" % (tpath, e))
                    if c["name"] in fixtures:
                        ok = delivered(pairs, fixtures[c["name"]])
                        kind, confirmed = ("valid", confirmed + 1) if ok else ("invalid", confirmed)
                    else:
                        kind = "valid"
                        for name, _inp, text, _err in pairs:
                            if text.strip().lower().startswith(MISS_STARTS[0]):
                                signals.append('SIGNAL: %s run %d: %s returned "%s"' % (
                                    c["name"], i, name, " ".join(text.split())[:60]))
                per[kind] += 1
                counts[kind] += 1
                if kind == "valid":
                    for g in r["graders"]:
                        t = tallies.setdefault(g.get("name"), [0, 0])
                        t[0] += bool(g.get("passed"))
                        t[1] += 1
            n = len(runs)
            label = c["name"] + ("" if arm == "with" else " [%s]" % arm)
            if per["invalid"]:
                case_lines.append("CASE: %s: invalid %d of %d (no tool result under %s returned content "
                                  "in the kept trace)" % (label, per["invalid"], n, fixtures[c["name"]]))
                if c["name"] not in reruns:
                    reruns.append(c["name"])
            else:
                gr = ", ".join("%s %d of %d" % (g, k, m) for g, (k, m) in tallies.items())
                conf = ("; delivery confirmed in %d of %d kept traces" % (confirmed, n)) if c["name"] in fixtures else ""
                case_lines.append("CASE: %s: valid %d of %d%s; graders over valid runs: %s" % (
                    label, per["valid"], n, conf, gr or "none"))
    if total == 0:
        raise BadInput("no runs in %s" % path)
    unchecked = [n for n in names if n not in fixtures]
    out = ["EVAL_STATS runs v1",
           "RESULT: %s (schemaVersion 1, partial %s, %d runs)" % (path, str(bool(data.get("partial"))).lower(), total),
           "COUNTS: valid %(valid)d, invalid %(invalid)d, errored %(errored)d, no-trace %(no-trace)d" % counts]
    out += case_lines + signals
    if unchecked:
        out.append("DELIVERY: not checked for %d case%s (no --fixture given)" % (
            len(unchecked), "" if len(unchecked) == 1 else "s"))
    for name in reruns:
        out.append("RERUN: %s, after delivery is fixed; confirm with eval_stats.py runs <new result.json> "
                   "--fixture %s=%s" % (name, name, fixtures[name]))
    out.append("VERDICT: suite scored on %d valid runs; %d invalid reported apart, not counted as failed%s"
               % (counts["valid"], counts["invalid"],
                  " (delivery not checked for %d case%s)" % (len(unchecked), "" if len(unchecked) == 1 else "s")
                  if unchecked else ""))
    return out + ["EVAL_STATS end"]


class Parser(argparse.ArgumentParser):
    """What: argparse that raises BadInput on a usage error instead of exiting.
    Use when: building the CLI (subparsers inherit it). Inputs: as argparse.
    Output: a parser. Side effects: none. Role: keeps every bad input on the one ERROR: exit-2 path."""

    def error(self, message):
        """What: turn argparse's usage error into BadInput. Use when: argparse rejects argv.
        Inputs: argparse's message. Output: none (raises BadInput). Side effects: none.
        Role: plumbing for the exit-2 contract."""
        raise BadInput(message)


def main(argv):
    """What: CLI entry. Use when: run as a script. Inputs: argv. Output: exit code.
    Side effects: prints the block or an error. Role: plumbing."""
    ap = Parser(prog="eval_stats.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("floor")
    f.add_argument("--name", action="append", default=[])
    f.add_argument("--results", action="append", default=[])
    c = sub.add_parser("calibrate")
    c.add_argument("--labels", required=True)
    r = sub.add_parser("runs")
    r.add_argument("result")
    r.add_argument("--fixture", action="append", default=[])
    try:
        try:
            a = ap.parse_args(argv)
        except SystemExit as e:
            return 0 if e.code in (0, None) else 2
        if a.cmd == "floor":
            if not a.name or len(a.name) != len(a.results):
                raise BadInput("give --name and --results in pairs")
            lines = [ln for n, rs in zip(a.name, a.results) for ln in floor_block(n, rs)]
        elif a.cmd == "calibrate":
            lines = calibrate_blocks(read_labels(a.labels))
        else:
            fx = {}
            for item in a.fixture:
                if "=" not in item:
                    raise BadInput("--fixture takes CASE=PATH_PREFIX, got %r" % item)
                k, v = item.split("=", 1)
                if not k or not v.strip("/") or k in fx:
                    raise BadInput("--fixture needs one non-empty CASE=PATH_PREFIX per case, got %r" % item)
                fx[k] = v
            lines = runs_block(a.result, fx)
    except BadInput as e:
        print("ERROR: %s" % e, file=sys.stderr)
        return 2
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
