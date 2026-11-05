"""Collector for work-log. Task 1: active-time engine only. Standard library only."""
from datetime import datetime, time, timedelta


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
    """Divide each elementary segment equally among live sessions; total == union length."""
    pts = sorted({p for ivs in per_session.values() for iv in ivs for p in iv})
    got = {s: 0.0 for s in per_session}
    for x, y in zip(pts, pts[1:]):
        live = [s for s, ivs in per_session.items() if any(a <= x and y <= b for a, b in ivs)]
        for s in live:
            got[s] += (y - x) / len(live)
    return got
