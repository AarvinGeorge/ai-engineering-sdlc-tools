"""Collector for work-log: Claude Code transcripts + git log -> sessions JSON.

Standard library only. Never uses the network, never writes prose.
Exit codes: 0 ok, 2 fail-loud zero (nothing in scope for the period), 3 format change or bad input.
"""
import argparse
import glob
import json
import os
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wl_common as C  # noqa: E402

DEFAULT_MARKER = "[work-log weekly run]"
MAX_REQUESTS = 20
REQUEST_CHARS = 300
FORMAT_HITS_SHOWN = 5


# ---------------------------------------------------------------- time engine

def active_intervals(ts, idle_s):
    """Consecutive timestamps within idle_s form active intervals; touching ones merge."""
    pts = sorted(ts)
    out = []
    for a, b in zip(pts, pts[1:]):
        if 0 < b - a <= idle_s:
            if out and out[-1][1] == a:
                out[-1] = (out[-1][0], b)
            else:
                out.append((a, b))
    return out


def split_days(iv, tz):
    """Split (a, b) at local midnights -> [(YYYY-MM-DD, a, b)]. DST-safe via zoneinfo."""
    a, b = iv
    out = []
    while a < b:
        la = datetime.fromtimestamp(a, tz)
        nxt = datetime.combine(la.date() + timedelta(days=1), time(0), tzinfo=tz).timestamp()
        end = min(b, nxt)
        out.append((la.date().isoformat(), a, end))
        a = end
    return out


def allocate(per_session):
    """Divide each elementary segment equally among live sessions; total == union length.

    Event sweep: O(E log E) for E interval endpoints. A session's own overlapping
    intervals count once (live while its open-interval depth is > 0).
    """
    got = {s: 0.0 for s in per_session}
    events = []
    for s, ivs in per_session.items():
        for a, b in ivs:
            if b > a:
                events.append((a, 1, s))
                events.append((b, -1, s))
    events.sort(key=lambda e: e[0])
    depth = defaultdict(int)
    live = set()
    i, n = 0, len(events)
    while i < n:
        x = events[i][0]
        while i < n and events[i][0] == x:
            _, d, s = events[i]
            depth[s] += d
            if depth[s] > 0:
                live.add(s)
            else:
                live.discard(s)
            i += 1
        if i < n and live:
            share = (events[i][0] - x) / len(live)
            for s in live:
                got[s] += share
    return got


# ---------------------------------------------------------------- errors

class BadInput(Exception):
    pass


class _Parser(argparse.ArgumentParser):
    def error(self, message):  # argparse exits 2 by default; 2 means "fail-loud zero" here
        self.print_usage(sys.stderr)
        sys.stderr.write("bad input: %s\n" % message)
        sys.exit(3)


def _parse_date(s, flag):
    try:
        return date.fromisoformat(s)
    except (TypeError, ValueError):
        raise BadInput("%s must be YYYY-MM-DD, got %r" % (flag, s))


# ---------------------------------------------------------------- transcripts

def _request_texts(rec):
    """Human request texts on a user line (string content or list text blocks)."""
    if rec.get("isMeta") or rec.get("isCompactSummary"):
        return []
    msg = rec.get("message")
    content = msg.get("content") if isinstance(msg, dict) else None
    if isinstance(content, str):
        raw = [content]
    elif isinstance(content, list):
        raw = [b.get("text") for b in content
               if isinstance(b, dict) and b.get("type") == "text" and isinstance(b.get("text"), str)]
    else:
        raw = []
    out = []
    for t in raw:
        t = t.strip()
        if t and not t.startswith("<"):
            out.append(t[:REQUEST_CHARS])
    return out


def read_session(path, stats, problems):
    """Parse one transcript file. Appends format problems; returns a session dict."""
    base = os.path.basename(path)
    with open(path, encoding="utf-8", errors="replace") as fh:
        raw = fh.read().splitlines()
    nonempty = [(i + 1, l) for i, l in enumerate(raw) if l.strip()]
    last_no = nonempty[-1][0] if nonempty else None
    sess = {"session_id": base[:-len(".jsonl")] if base.endswith(".jsonl") else base,
            "first_cwd": None, "title": None, "first_request": None,
            "events": [],     # (ts, gitBranch) of timed lines
            "requests": [],   # (ts, text)
            "all_ts": []}     # every user/assistant timestamp, sidechain included
    stats["files"] += 1
    for no, text in nonempty:
        stats["lines"] += 1
        try:
            rec = json.loads(text)
        except ValueError:
            rec = None
        if not isinstance(rec, dict):
            if no == last_no:
                stats["partial_last_lines"] += 1
            else:
                problems.append("format change: %s line %d: not JSON" % (base, no))
            continue
        if isinstance(rec.get("aiTitle"), str):
            sess["title"] = rec["aiTitle"]
        typ = rec.get("type")
        if typ not in ("user", "assistant"):
            stats["skipped_types"][str(typ)] += 1
            continue
        missing = [f for f in ("timestamp", "cwd") if not rec.get(f)]
        if missing:
            for f in missing:
                problems.append("format change: %s line %d: missing %s" % (base, no, f))
            continue
        try:
            ts = C.parse_ts(rec["timestamp"])
        except ValueError:
            problems.append("format change: %s line %d: bad timestamp" % (base, no))
            continue
        sess["all_ts"].append(ts)
        if typ == "user" and sess["first_cwd"] is None:
            sess["first_cwd"] = rec["cwd"]
        if rec.get("isSidechain") is True:
            continue
        branch = rec.get("gitBranch")
        sess["events"].append((ts, branch if isinstance(branch, str) and branch else None))
        if typ == "user":
            for t in _request_texts(rec):
                if sess["first_request"] is None:
                    sess["first_request"] = t
                sess["requests"].append((ts, t))
    return sess


def in_scope(cwd, scopes):
    if scopes is None:
        return True
    if not cwd:
        return False
    for c in {cwd, os.path.realpath(cwd)}:
        for s in scopes:
            if c == s or c.startswith(s.rstrip("/") + "/"):
                return True
    return False


def session_days(sess, idle_s, lo, hi, tz):
    """{day: {"iv": [(a, b)], "ts": [...], "branches": set, "requests": [...]}} inside [lo, hi)."""
    days = defaultdict(lambda: {"iv": [], "ts": [], "branches": set(), "requests": []})
    for a, b in active_intervals([t for t, _ in sess["events"]], idle_s):
        a, b = max(a, lo), min(b, hi)
        if a < b:
            for d, x, y in split_days((a, b), tz):
                days[d]["iv"].append((x, y))
    for ts, br in sess["events"]:
        if lo <= ts < hi:
            d = datetime.fromtimestamp(ts, tz).date().isoformat()
            days[d]["ts"].append(ts)
            if br:
                days[d]["branches"].add(br)
    for ts, t in sess["requests"]:
        if lo <= ts < hi:
            d = datetime.fromtimestamp(ts, tz).date().isoformat()
            if len(days[d]["requests"]) < MAX_REQUESTS:
                days[d]["requests"].append(t)
    return {d: v for d, v in days.items() if v["iv"] or v["requests"]}


# ---------------------------------------------------------------- git

def _git(args):
    r = subprocess.run(["git"] + args, capture_output=True, text=True)
    return r.returncode, r.stdout


def _toplevel(d):
    if not d or not os.path.isdir(d):
        return None, False
    code, out = _git(["-C", d, "rev-parse", "--show-toplevel"])
    if code != 0:
        return None, False   # not a repo: not an error
    return os.path.realpath(out.strip()), True


def collect_commits(dirs, start, end, tz, mapping, read):
    """Period membership and the shown date/time both use the AUTHOR date in tz.

    git's --since filters on committer date, which is >= author date in normal history,
    so --since=<start midnight> never drops an in-period authored commit; there is no
    --until (a commit authored inside but committed after the period still counts) and
    the author date is filtered here.
    """
    lo = datetime.combine(start, time(0), tzinfo=tz)
    hi = datetime.combine(end + timedelta(days=1), time(0), tzinfo=tz)
    tops = []
    for d in dirs:
        top, ok = _toplevel(d)
        if ok and top not in tops:
            tops.append(top)
    seen, commits, filtered = set(), [], False
    for top in tops:
        args = ["-C", top, "log", "--all", "--no-merges",
                "--since=" + lo.isoformat(timespec="seconds"),
                "--format=%H%x1f%aI%x1f%s"]
        _, email = _git(["-C", top, "config", "user.email"])
        email = email.strip()
        if email:
            # fixed string, anchored by the ident's angle brackets: no regex lookalikes
            args += ["--fixed-strings", "--author=<" + email + ">"]
            filtered = True
        code, out = _git(args)
        if code != 0:
            read["git_errors"] += 1
            continue
        for row in out.splitlines():
            parts = row.split("\x1f")
            if len(parts) != 3 or parts[0] in seen:
                continue
            seen.add(parts[0])
            try:
                at = C.parse_ts(parts[1])
            except ValueError:
                read["git_errors"] += 1
                continue
            if not lo.timestamp() <= at < hi.timestamp():
                continue
            when = datetime.fromtimestamp(at, tz)
            commits.append({"project": C.project_name(top, mapping), "date": when.date().isoformat(),
                            "time": when.strftime("%H:%M"), "subject": parts[2]})
    commits.sort(key=lambda c: (c["date"], c["time"], c["project"]))
    return commits, filtered


# ---------------------------------------------------------------- main

def build_parser():
    p = _Parser(prog="collect.py", description="Claude Code transcripts + git -> work-log sessions JSON")
    p.add_argument("--start", required=True)
    p.add_argument("--end", required=True)
    g = p.add_mutually_exclusive_group()
    g.add_argument("--scope", action="append", metavar="PATH")
    g.add_argument("--all", action="store_true")
    p.add_argument("--idle-minutes", type=float, default=15)
    p.add_argument("--tz")
    p.add_argument("--projects-dir", default=os.path.join("~", ".claude", "projects"))
    p.add_argument("--projects-map")
    p.add_argument("--exclude-marker", default=DEFAULT_MARKER)
    p.add_argument("--no-git", action="store_true")
    return p


def run(a):
    start, end = _parse_date(a.start, "--start"), _parse_date(a.end, "--end")
    if end < start:
        raise BadInput("--end %s is before --start %s" % (end, start))
    if a.idle_minutes <= 0:
        raise BadInput("--idle-minutes must be positive")
    try:
        tz, tzname = C.local_zone(a.tz)
    except Exception:
        raise BadInput("unknown time zone %r (use an IANA name such as America/New_York)" % (a.tz,))
    mapping = {}
    if a.projects_map:
        try:
            with open(os.path.expanduser(a.projects_map)) as fh:
                mapping = json.load(fh)
        except (OSError, ValueError) as e:
            raise BadInput("cannot read --projects-map: %s" % e)
        if not isinstance(mapping, dict) or not all(isinstance(v, str) for v in mapping.values()):
            raise BadInput("--projects-map must be a JSON object of path -> project name")
    scopes = None if a.all else [os.path.realpath(os.path.expanduser(s)) for s in (a.scope or [os.getcwd()])]
    if scopes is None:
        scope_name = "All projects"
    else:
        scope_name = " + ".join(C.project_name(s, mapping) for s in scopes)
    pdir = os.path.realpath(os.path.expanduser(a.projects_dir))

    files = sorted(f for f in glob.glob(os.path.join(glob.escape(pdir), "*", "*.jsonl")) if os.path.isfile(f))
    if not files:
        json.dump({"error": "no transcripts found", "projects_dir": pdir, "scope_name": scope_name}, sys.stderr)
        sys.stderr.write("\n")
        return 2

    read = {"files": 0, "lines": 0, "partial_last_lines": 0, "skipped_types": Counter(),
            "excluded_by_marker": 0, "git_errors": 0}
    problems, sessions = [], []
    for f in files:
        sessions.append(read_session(f, read, problems))
    if problems:
        for msg in problems[:FORMAT_HITS_SHOWN]:
            sys.stderr.write(msg + "\n")
        if len(problems) > FORMAT_HITS_SHOWN:
            sys.stderr.write("format change: %d more\n" % (len(problems) - FORMAT_HITS_SHOWN))
        return 3
    read["skipped_types"] = dict(sorted(read["skipped_types"].items()))

    all_ts = [t for s in sessions for t in s["all_ts"]]
    earliest = datetime.fromtimestamp(min(all_ts), tz).date().isoformat() if all_ts else None
    lo = datetime.combine(start, time(0), tzinfo=tz).timestamp()
    hi = datetime.combine(end + timedelta(days=1), time(0), tzinfo=tz).timestamp()
    idle_s = a.idle_minutes * 60

    kept = []
    for s in sessions:
        if a.exclude_marker and s["first_request"] and a.exclude_marker in s["first_request"]:
            read["excluded_by_marker"] += 1
            continue
        s["days"] = session_days(s, idle_s, lo, hi, tz)
        kept.append(s)
    scoped = [s for s in kept if in_scope(s["first_cwd"], scopes)]
    active = [s for s in scoped if s["days"]]

    git_filter, commits = False, []
    if not a.no_git:
        dirs = [s["first_cwd"] for s in scoped] + (scopes or [])
        commits, git_filter = collect_commits(dirs, start, end, tz, mapping, read)

    if not active:
        json.dump({"error": "no sessions in scope for the period", "scope_name": scope_name,
                   "files_read": read["files"],
                   "sessions_total": len(sessions), "sessions_in_scope_any_date": len(scoped),
                   "sessions_in_period_any_scope": sum(1 for s in kept if s["days"]),
                   "earliest_activity": earliest, "commits_in_scope": len(commits),
                   "excluded_by_marker": read["excluded_by_marker"]}, sys.stderr)
        sys.stderr.write("\n")
        return 2

    keyed = {(s["session_id"], d): v["iv"] for s in active for d, v in s["days"].items()}
    secs = allocate(keyed)
    day_secs = defaultdict(float)
    for (sid, d), v in secs.items():
        day_secs[d] += v
    rows = []
    for s in active:
        project = C.project_name(s["first_cwd"], mapping) if s["first_cwd"] else "Unknown project"
        for d in sorted(s["days"]):
            v = s["days"][d]
            ts = v["ts"] or [x for iv in v["iv"] for x in iv]
            rows.append({"session_id": s["session_id"], "date": d, "project": project,
                         "start": datetime.fromtimestamp(min(ts), tz).strftime("%H:%M"),
                         "end": datetime.fromtimestamp(max(ts), tz).strftime("%H:%M"),
                         "active_minutes": round(secs[(s["session_id"], d)] / 60, 1),
                         "title": s["title"], "branches": sorted(v["branches"]),
                         "requests": v["requests"], "first_cwd": s["first_cwd"]})
    rows.sort(key=lambda r: (r["date"], r["start"], r["session_id"]))
    out = {"version": C.plugin_version(), "tz": tzname,
           "idle_minutes": int(a.idle_minutes) if float(a.idle_minutes).is_integer() else a.idle_minutes,
           "period": {"start": start.isoformat(), "end": end.isoformat()},
           "scope": "all" if scopes is None else scopes, "scope_name": scope_name,
           "read": read, "earliest_activity": earliest, "sessions": rows,
           "day_totals": {d: round(day_secs[d] / 60, 1) for d in sorted({r["date"] for r in rows})},
           "commits": commits, "git_author_filter": git_filter}
    json.dump(out, sys.stdout, indent=1)
    sys.stdout.write("\n")
    return 0


def main(argv=None):
    a = build_parser().parse_args(argv)
    try:
        return run(a)
    except BadInput as e:
        sys.stderr.write("bad input: %s\n" % e)
        return 3


if __name__ == "__main__":
    sys.exit(main())
