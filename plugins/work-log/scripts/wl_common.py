"""Shared helpers for work-log scripts. Standard library only."""
import json
import os
import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo


def parse_ts(s):
    """ISO-8601 (Z or offset) -> UTC epoch seconds. ValueError on junk or naive input."""
    if not isinstance(s, str):
        raise ValueError("timestamp must be a string: %r" % (s,))
    t = s.strip()
    if t.endswith(("Z", "z")):
        t = t[:-1] + "+00:00"
    # Python 3.9/3.10 fromisoformat only accepts 3 or 6 fractional digits: normalise to 6.
    m = re.match(r"^(.*T\d{2}:\d{2}:\d{2})\.(\d+)(.*)$", t)
    if m:
        t = "%s.%s%s" % (m.group(1), m.group(2)[:6].ljust(6, "0"), m.group(3))
    dt = datetime.fromisoformat(t)  # raises ValueError on junk
    if dt.tzinfo is None:
        raise ValueError("timestamp has no timezone: %r" % (s,))
    return dt.timestamp()


def _fixed_zone():
    tz = datetime.now().astimezone().tzinfo
    off = datetime.now().astimezone().utcoffset()
    mins = int(off.total_seconds() // 60) if off is not None else 0
    sign = "+" if mins >= 0 else "-"
    mins = abs(mins)
    return tz, "UTC%s%02d:%02d (fixed)" % (sign, mins // 60, mins % 60)


def local_zone(name=None):
    """Explicit IANA name, else $TZ, else /etc/localtime symlink, else fixed offset."""
    if name:
        return ZoneInfo(name), name
    env = os.environ.get("TZ")
    if env:
        env = env.lstrip(":")
        try:
            return ZoneInfo(env), env
        except Exception:
            pass
    try:
        target = os.path.realpath("/etc/localtime")
        marker = "zoneinfo/"
        if marker in target:
            zname = target.split(marker, 1)[1]
            return ZoneInfo(zname), zname
    except Exception:
        pass
    return _fixed_zone()


def plugin_version():
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "..", ".claude-plugin", "plugin.json")
    with open(path) as fh:
        return json.load(fh)["version"]


def _under(path, prefix):
    prefix = prefix.rstrip("/")
    return path == prefix or path.startswith(prefix + "/")


def project_name(path, mapping):
    path = path.rstrip("/") or path
    best = None
    for key in mapping:
        if _under(path, key) and (best is None or len(key.rstrip("/")) > len(best.rstrip("/"))):
            best = key
    if best is not None:
        return mapping[best]
    for marker in ("/.claude/worktrees/", "/.worktrees/"):
        if marker in path:
            path = path.split(marker, 1)[0]
    cur = path
    base = None
    while True:
        if os.path.exists(os.path.join(cur, ".git")):
            base = os.path.basename(cur)
            break
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    if base is None:
        base = os.path.basename(path)
    base = re.sub(r"[-_.]", " ", base)
    base = re.sub(r" +", " ", base).strip()
    return base[:1].upper() + base[1:]
