#!/usr/bin/env python3
"""Decide how Claude Code's permission rules treat a Bash command, across settings files.

What: merges the permission lists of the given settings layers (lists merge across files),
applies deny, then ask, then allow (first match decides; specificity does not reorder), splits
compound commands (deny and ask apply if any part matches, including nested bodies; allow
needs every part), and prints one fixed block per command, including a cross-file probe: the
same command with an allow added to user and to local settings.
Use when: writing or checking a permission profile (references/permission-profiles.md);
paste the block as printed. Source: code.claude.com/docs/en/permissions ("Manage permissions",
"Settings precedence", "Wildcard patterns", "Compound commands", "Wrappers", "Exec wrappers
and find").
Inputs: --inline SCOPE=JSON or --file SCOPE=PATH (SCOPE: managed, cli, local, project, user),
and one or more --command.
Output: blocks on stdout; exit 0 whenever computed; exit 2 and "ERROR: ..." on stderr on bad
input. Never prints advice, echoes only rules found in the given layers, never prints the
bypass-lock setting name, and prints a "Bash(ssh" rule text only when a given layer holds one.
Side effects: none (reads the given files only).
Role: computes the documented precedence; the model writes the profile and explains it. The
cross-file probe restates the documented order: for a deny or an ask it can only print "deny"
or "ask", so it is an observed line, not a discovery.
Undocumented cases (labelled hypotheses, never allow): how a wrapper's own arguments are
skipped (H1); nested bodies, which are checked for deny and ask only (H2); matching on the raw
text after a whitespace trim (H3); no matching rule gives "no-rule", the mode decides (H4).
Claude Code strips wrappers and some env assignments before matching allow rules too (docs,
"Wrappers"); this checker does not compute allow past wrappers or env assignments and prints
no-rule there, which is not a statement about what Claude Code does.
"""
import argparse
import json
import re
import sys

SCOPES = ("managed", "cli", "local", "project", "user")
KINDS = ("deny", "ask", "allow")
SEPS = ("&&", "||", "|&", ";", "|", "&", "\n")
WRAPPERS = ("timeout", "time", "nice", "nohup", "stdbuf", "command", "builtin", "noglob", "xargs")
EXEC_WRAPPERS = ("watch", "setsid", "ionice", "flock")
FIND_ACTIONS = ("-exec", "-execdir", "-ok", "-okdir", "-delete", "-rm", "-fprint", "-fprint0",
                "-fprintf", "-files0-from")
KEYWORDS = ("if", "then", "else", "elif", "do", "while", "until", "{", "!")
ENV = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=(\"[^\"]*\"|'[^']*'|\S*)\s*")
GUARD_KEY = re.compile("disablebypasspermissionsmode", re.I)
SSH = "Bash(ssh"
HEREDOC = re.compile(r"<<-?[ \t]*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1([^\n]*)\n"
                     r"(?:[^\n]*\n)*?[ \t]*\2[ \t]*(?=\n|$)")


class BadInput(Exception):
    """What: an input the script will not compute on. Use when: any parse fails. Inputs: message.
    Output: exception. Side effects: none. Role: fail loudly (exit 2)."""


def rule_matches(spec, cmd):
    """What: whether a permission rule matches one Bash command text.
    Use when: decide(). Inputs: rule text such as "Bash(ls *)", command text.
    Output: bool. Side effects: none. Role: the docs' wildcard rules."""
    if spec in ("Bash", "Bash(*)"):
        return True
    m = re.fullmatch(r"Bash\((.*)\)", spec, re.S)
    if not m:
        return False
    body = m.group(1)
    if body.endswith(":*"):
        body = body[:-2] + " *"
    if body.count("*") == 1 and body.endswith(" *"):
        return cmd == body[:-2] or cmd.startswith(body[:-1])
    return _glob(body, cmd)


def _glob(body, cmd):
    """What: whether cmd matches body, where each "*" matches any text (spaces included).
    Use when: rule_matches(). Inputs: rule body, command text. Output: bool.
    Side effects: none. Role: the docs' wildcard rule, matched left to right in linear time
    (a backtracking regex hangs on a rule with many "*")."""
    segs = body.split("*")
    if len(segs) == 1:
        return cmd == body
    head, tail, mids = segs[0], segs[-1], segs[1:-1]
    if len(cmd) < len(head) + len(tail) or not cmd.startswith(head) or not cmd.endswith(tail):
        return False
    pos, end = len(head), len(cmd) - len(tail)
    for seg in mids:
        k = cmd.find(seg, pos, end)
        if k < 0:
            return False
        pos = k + len(seg)
    return True


def _close(cmd, i, end):
    """What: index of the character that closes a nested body opened just before i.
    Use when: scan(). Inputs: text, start index, closing char (")" or "`").
    Output: index, or -1 when it never closes. Side effects: none. Role: parsing (H2)."""
    depth, q = 1, None
    while i < len(cmd):
        ch = cmd[i]
        if ch == "\\" and q != "'":
            i += 2
            continue
        if q:
            if ch == q:
                q = None
        elif end == "`":
            if ch == "`":
                return i
        elif ch in "'\"":
            q = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def scan(cmd):
    """What: top-level subcommands of a command, outside quotes and nested bodies.
    Use when: split() and analyse(). Inputs: command text.
    Output: (parts, nested_flags, bodies, parseable). nested_flags[i] says part i holds a
    $(...), backtick or (...) body; bodies are those bodies' texts; a dangling && or ||, an
    unclosed quote or an unclosed body makes it unparseable for allow. Here-doc bodies are
    dropped before quote tracking (an apostrophe in a body must not hide a later command from
    deny); any "<<" still makes the command never-allow.
    Side effects: none. Role: parsing."""
    cmd = HEREDOC.sub(lambda m: "<<" + m.group(2) + m.group(3), cmd)
    parts, flags, bodies = [], [], []
    cur, q, i, parseable, nested = "", None, 0, True, False
    while i < len(cmd):
        ch = cmd[i]
        if ch == "\\" and q != "'":
            cur, i = cur + cmd[i:i + 2], i + 2
            continue
        if q == "'":
            cur += ch
            if ch == "'":
                q = None
            i += 1
            continue
        if q is None:
            if cmd.startswith("$'", i):
                j = i + 2
                while j < len(cmd) and cmd[j] != "'":
                    j += 2 if cmd[j] == "\\" else 1
                if j >= len(cmd):
                    parseable = False
                cur, i = cur + cmd[i:j + 1], j + 1
                continue
            if ch == "#" and (i == 0 or cmd[i - 1] in " \t\n;&|("):
                j = cmd.find("\n", i)
                i, parseable = (len(cmd) if j < 0 else j), False
                continue
            if cmd.startswith("<<", i):
                parseable = False
            if cmd[i:i + 2] in (">&", "<&", "&>"):
                cur, i = cur + cmd[i:i + 2], i + 2
                continue
        opener = None
        if ch == "`":
            opener, start, end = "`", i + 1, "`"
        elif cmd.startswith("$(", i):
            opener, start, end = "$(", i + 2, ")"
        elif ch == "(" and q is None:
            opener, start, end = "(", i + 1, ")"
        if opener:
            j = _close(cmd, start, end)
            if j < 0:
                parseable, j = False, len(cmd)
            bodies.append(cmd[start:j])
            cur, i, nested = cur + cmd[i:j + 1], j + 1, True
            continue
        if q == '"':
            cur += ch
            if ch == '"':
                q = None
            i += 1
            continue
        if ch in "'\"":
            q, cur, i = ch, cur + ch, i + 1
            continue
        sep = next((s for s in SEPS if cmd.startswith(s, i)), None)
        if sep:
            parts.append(cur.strip())
            flags.append(nested)
            cur, i, nested = "", i + len(sep), False
            if sep in ("&&", "||") and not cmd[i:].strip():
                parseable = False
            continue
        cur += ch
        i += 1
    if q:
        parseable = False
    parts.append(cur.strip())
    flags.append(nested)
    kept = [(p, f) for p, f in zip(parts, flags) if p]
    return [p for p, _ in kept], [f for _, f in kept], bodies, parseable


def split(cmd):
    """What: top-level subcommands and whether the command parses for allow.
    Use when: block(). Inputs: command text. Output: (parts, parseable). Side effects: none.
    Role: parsing."""
    parts, _, _, parseable = scan(cmd)
    return parts, parseable


def _strip_wrapper(part):
    """What: the command a wrapper runs, after its own arguments (heuristic H1).
    Use when: candidates(). Inputs: one subcommand. Output: inner text, or None when the part
    does not start with a wrapper. Side effects: none. Role: parsing."""
    toks = part.split()
    if not toks or toks[0] not in WRAPPERS:
        return None
    if toks[0] == "command" and len(toks) > 1 and toks[1] == "-v":
        return None
    if toks[0] == "xargs" and len(toks) > 1 and toks[1].startswith("-"):
        return None
    rest = toks[1:]
    while rest and rest[0].startswith("-"):
        flag = rest.pop(0)
        if rest and "=" not in flag and re.fullmatch(r"-[A-Za-z]", flag) and re.fullmatch(r"-?\d+", rest[0]):
            rest.pop(0)
    if toks[0] == "timeout" and rest and re.fullmatch(r"\d+(\.\d+)?[smhd]?", rest[0]):
        rest.pop(0)
    return " ".join(rest) or None


def candidates(part):
    """What: every text a deny or ask rule is checked against for one subcommand: the part as
    written, then past control-flow keywords, env assignments and wrappers.
    Use when: decide(). Inputs: one subcommand. Output: (texts, plain) where plain says
    nothing was stripped (only a plain part can be allowed). Side effects: none. Role: parsing."""
    out, cur, plain = [part], part, True
    while True:
        toks = cur.split(None, 1)
        nxt = None
        if toks and toks[0] in KEYWORDS:
            nxt = toks[1] if len(toks) > 1 else ""
        elif ENV.match(cur):
            nxt = cur[ENV.match(cur).end():]
        else:
            nxt = _strip_wrapper(cur)
        if nxt is None:
            return out, plain
        nxt = nxt.strip()
        plain = False
        if not nxt or nxt in out:
            return out, plain
        out.append(nxt)
        cur = nxt


def _exact_only(part):
    """What: whether only a rule with no wildcard may allow this part (exec wrappers, find
    with an action). Use when: decide(). Inputs: one subcommand. Output: bool.
    Side effects: none. Role: the docs' "Exec wrappers and find"."""
    toks = part.split()
    if not toks:
        return False
    return toks[0] in EXEC_WRAPPERS or (toks[0] == "find" and any(t in FIND_ACTIONS for t in toks))


def allowed_by(r, part):
    """What: whether one allow rule allows one plain subcommand. Use when: decide().
    Inputs: rule tuple, subcommand. Output: bool; an exec wrapper or find action needs a rule
    with no wildcard. Side effects: none. Role: the docs' allow matching."""
    if _exact_only(part) and "*" in r[1] and r[1] != "Bash":
        return False
    return rule_matches(r[1], part)


def rules_of(layers):
    """What: every rule as (kind, spec, scope, source). Use when: decide().
    Inputs: {scope: (settings dict, source label)}. Output: list. Side effects: none.
    Role: merges lists across files."""
    out = []
    for scope in SCOPES:
        if scope not in layers:
            continue
        data, src = layers[scope]
        p = data.get("permissions") or {}
        if not isinstance(p, dict):
            raise BadInput("%s permissions is not a JSON object" % scope)
        for kind in KINDS:
            specs = p.get(kind) or []
            if not isinstance(specs, list):
                raise BadInput("%s %s is not a list" % (scope, kind))
            for spec in specs:
                if not isinstance(spec, str):
                    raise BadInput("%s %s holds a non-string rule %r" % (scope, kind, spec))
                out.append((kind, spec, scope, src))
    return out


def decide(cmd, layers):
    """What: the decision for one command. Use when: blocks and the probe. Inputs: command,
    layers. Output: (decision, deciding rules, other matching rules). Side effects: none.
    Role: deny > ask > allow across all files; anything undocumented never allows."""
    parts, flags, bodies, parseable = scan(cmd)
    texts = [cmd]
    todo = list(parts)
    while bodies:
        b = bodies.pop(0)
        bp, _, bb, _ = scan(b)
        todo += bp
        bodies += bb
    for p in todo:
        for t in candidates(p)[0]:
            if t not in texts:
                texts.append(t)
    rules = rules_of(layers)
    hit = lambda r: any(rule_matches(r[1], t) for t in texts)
    for kind in ("deny", "ask"):
        found = [r for r in rules if r[0] == kind and hit(r)]
        if found:
            return kind, found[:1], [r for r in rules if hit(r) and r is not found[0]]
    allows = [r for r in rules if r[0] == "allow"]

    plain = all(candidates(p)[1] for p in parts) and not any(flags)
    if parseable and plain and parts and all(any(allowed_by(r, p) for r in allows) for p in parts):
        first = next(r for r in allows if any(allowed_by(r, p) for p in parts))
        return "allow", [first], [r for r in allows if hit(r) and r is not first]
    return "no-rule", [], [r for r in rules if hit(r)]


def fmt(r):
    """What: one rule as text. Use when: RULE / ALSO_MATCHED lines. Inputs: rule tuple.
    Output: str. Side effects: none. Role: formatting."""
    return "%s [%s] in %s (%s)" % (r[1], r[0], r[2], r[3])


def block(cmd, layers, ssh_supplied=False):
    """What: the fixed block for one command. Use when: main(). Inputs: command, layers,
    whether a given layer holds a "Bash(ssh" text. Output: list of lines. Side effects: none.
    Role: reports the computed facts."""
    parts, _ = split(cmd)
    decision, deciding, also = decide(cmd, layers)
    shown = cmd if ssh_supplied else re.sub(r"(?i)bash\(ssh", "Bash( ssh", cmd)
    out = ["PERMISSIONS_CHECK v1", "COMMAND: %s" % shown, "SUBCOMMANDS: %d" % len(parts),
           "DECISION: %s" % decision,
           "RULE: %s" % (fmt(deciding[0]) if deciding else "none (the permission mode decides)"),
           "ORDER: deny > ask > allow; first match decides; specificity does not reorder",
           "ALSO_MATCHED: %s" % ("; ".join(fmt(r) + " -- not reached" for r in also) if also else "none")]
    if decision in ("deny", "ask"):
        probe = []
        for scope in ("user", "local"):
            trial = dict(layers)
            data, src = trial.get(scope, ({}, "probe"))
            extra = json.loads(json.dumps(data))
            perms = extra.get("permissions")
            if not isinstance(perms, dict):
                perms = extra["permissions"] = {}
            if not isinstance(perms.get("allow"), list):
                perms["allow"] = []
            perms["allow"].append("Bash(%s)" % cmd)
            trial[scope] = (extra, src)
            probe.append("added to %s -> %s" % (scope, decide(cmd, trial)[0]))
        label = "Bash(%s)" % cmd
        if not ssh_supplied and SSH.lower() in label.lower():
            label = "for this exact command"
        else:
            label = '"%s"' % label
        out.append("CROSS_FILE_PROBE: allow %s %s" % (label, "; ".join(probe)))
        out.append("LOOSENED_BY_OTHER_FILE: no (%s)" % (
            "lists merge across managed, cli, local, project and user; a deny in any file is checked "
            "before an allow in any file" if decision == "deny"
            else "an ask in any file is checked before an allow in any file"))
    else:
        out += ["CROSS_FILE_PROBE: n/a", "LOOSENED_BY_OTHER_FILE: n/a"]
    out += ["TRUST: project allow rules apply only after workspace trust; deny and ask apply at once",
            "LIMIT: matches command text as written; /full/path, sh -c and other forms are not covered; "
            "permission rules are not a security boundary; the hard floor is the OS sandbox or a "
            "PreToolUse hook that blocks the command",
            "NOTES: deny and ask are also checked past wrappers (their own arguments skipped by a "
            "heuristic), env assignments, control-flow keywords and nested bodies; this checker does not "
            "compute allow past wrappers or env assignments and prints no-rule there, which is not a "
            "statement about what Claude Code does; redirections and built-in read-only commands are "
            "not modelled"]
    for scope in ("project", "local"):
        p = layers.get(scope, ({}, ""))[0].get("permissions")
        mode = p.get("defaultMode") if isinstance(p, dict) else None
        if mode in ("bypassPermissions", "auto"):
            out.append("MODE: defaultMode %s in %s -> not applied (only user or managed settings can set it)"
                       % (mode, scope))
    for scope in SCOPES:
        if scope in layers and "defaultMode" in layers[scope][0]:
            out.append("MODE: %s (top-level defaultMode key, not documented; not evaluated)"
                       % json.dumps(layers[scope][0]["defaultMode"]).strip('"'))
    out.append("END")
    return [GUARD_KEY.sub("[setting name withheld]", ln) for ln in out]


def main(argv):
    """What: CLI entry. Use when: run as a script. Inputs: argv. Output: exit code.
    Side effects: reads --file paths, prints. Role: plumbing."""
    ap = argparse.ArgumentParser(prog="permissions_check.py", add_help=False)
    ap.add_argument("--inline", action="append", default=[])
    ap.add_argument("--file", action="append", default=[])
    ap.add_argument("--command", action="append", default=[])
    if argv and argv[0] in ("-h", "--help"):
        ap.print_usage(sys.stdout)
        print("SCOPE: %s; exit 0 = computed, 2 = bad input" % ", ".join(SCOPES))
        return 0
    try:
        a = ap.parse_args(argv)
    except SystemExit:
        print("ERROR: bad arguments (see the usage line above)", file=sys.stderr)
        return 2
    try:
        layers, raw = {}, []
        for item, is_file in [(x, False) for x in a.inline] + [(x, True) for x in a.file]:
            if "=" not in item:
                raise BadInput("give SCOPE=%s, got %r" % ("PATH" if is_file else "JSON", item))
            scope, val = item.split("=", 1)
            if scope not in SCOPES:
                raise BadInput("scope %r is not one of %s" % (scope, ", ".join(SCOPES)))
            if scope in layers:
                raise BadInput("scope %s given twice" % scope)
            try:
                if is_file:
                    with open(val, encoding="utf-8") as fh:
                        text = fh.read()
                else:
                    text = val
                data = json.loads(text)
            except (OSError, ValueError) as e:
                raise BadInput("%s settings unreadable: %s" % (scope, e))
            if not isinstance(data, dict):
                raise BadInput("%s settings are not a JSON object" % scope)
            layers[scope] = (data, val if is_file else "inline")
            raw.append(text)
        if not a.command:
            raise BadInput("give at least one --command")
        specs = rules_of(layers)
        ssh = any(SSH.lower() in t.lower() for t in raw)
        lines = [ln for c in a.command for ln in block(c, layers, ssh)]
    except BadInput as e:
        print("ERROR: %s" % GUARD_KEY.sub("[setting name withheld]", str(e)), file=sys.stderr)
        return 2
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
