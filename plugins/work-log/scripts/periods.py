#!/usr/bin/env python3
"""Week maths for work-log: last week (Mon-Sun) and the weekly gap finder.

  periods.py last-week [--today D]
  periods.py missing-weeks --scope-name NAME [--today D] [--earliest D] [--titles-json FILE|-]

Every candidate week lands in exactly one of to_create / skipped_by_cap /
unrecoverable / already_saved. Exit codes: 0 ok, 3 bad input.
"""
import argparse, json, re, sys
from datetime import date, datetime, timedelta

TITLE_RE = re.compile(r"Work log · (?P<scope>.*) · (?P<a>\d{4}-\d{2}-\d{2}) to (?P<b>\d{4}-\d{2}-\d{2})")
SINGLE_TAB = " (single tab)"   # suffix of the read-back fallback upload; counts as saved


def last_week(today):
    monday = today - timedelta(days=today.weekday() + 7)
    return monday, monday + timedelta(days=6)


def week_title(scope_name, start, end):
    return "Work log · %s · %s to %s" % (scope_name, start.isoformat(), end.isoformat())


def saved_weeks(titles, scope_name):
    out = set()
    for title in titles:
        if title.endswith(SINGLE_TAB):
            title = title[:-len(SINGLE_TAB)]
        m = TITLE_RE.fullmatch(title)
        if not m or m.group("scope") != scope_name:
            continue
        try:
            a = date.fromisoformat(m.group("a")); b = date.fromisoformat(m.group("b"))
        except ValueError:
            continue
        if a.weekday() == 0 and b == a + timedelta(days=6):
            out.add(a)
    return out


def missing_weeks(titles, scope_name, today, earliest, max_weeks=8):
    saved = saved_weeks(titles, scope_name)
    last_mon, _ = last_week(today)
    if saved:
        cur = max(saved) + timedelta(days=7)
    else:
        cur = last_mon
    candidates = []
    while cur <= last_mon:
        candidates.append(cur)
        cur += timedelta(days=7)
    r = {"to_create": [], "skipped_by_cap": [], "unrecoverable": [],
         "already_saved": [last_mon.isoformat()] if last_mon in saved else []}
    creatable = []
    for s in candidates:
        e = s + timedelta(days=6)
        if earliest is None or e < earliest:
            r["unrecoverable"].append({"start": s.isoformat(), "end": e.isoformat()})
        else:
            creatable.append({"start": s.isoformat(), "end": e.isoformat(),
                              "title": week_title(scope_name, s, e), "partial": s < earliest})
    if max_weeks < 0:
        max_weeks = 0
    cut = len(creatable) - max_weeks
    if cut > 0:
        r["skipped_by_cap"] = [{"start": w["start"], "end": w["end"]} for w in creatable[:cut]]
        creatable = creatable[cut:]
    r["to_create"] = creatable
    return r


def _d(s):
    try:
        return date.fromisoformat(s)
    except ValueError:
        sys.stderr.write("periods: bad date %r (want YYYY-MM-DD)\n" % s)
        sys.exit(3)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="periods.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("last-week"); a.add_argument("--today")
    b = sub.add_parser("missing-weeks")
    b.add_argument("--scope-name", required=True); b.add_argument("--today")
    b.add_argument("--earliest"); b.add_argument("--titles-json")
    b.add_argument("--max-weeks", type=int, default=8)
    a_ = ap.parse_args(argv)
    today = _d(a_.today) if a_.today else datetime.now().astimezone().date()
    if a_.cmd == "last-week":
        s, e = last_week(today)
        print(json.dumps({"start": s.isoformat(), "end": e.isoformat()}))
        return 0
    titles = []
    if a_.titles_json:
        try:
            raw = sys.stdin.read() if a_.titles_json == "-" else open(a_.titles_json, encoding="utf-8").read()
            titles = json.loads(raw)
            if not isinstance(titles, list):
                raise ValueError("not a list")
            if not all(isinstance(x, str) for x in titles):
                raise ValueError("every title must be a string")
        except (OSError, ValueError) as ex:
            sys.stderr.write("periods: bad titles JSON: %s\n" % ex)
            return 3
    earliest = _d(a_.earliest) if a_.earliest else None
    print(json.dumps(missing_weeks(titles, a_.scope_name, today, earliest, a_.max_weeks), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
