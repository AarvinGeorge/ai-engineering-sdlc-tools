# Permission profiles per stakes tier

A rule kept in prose is a suggestion; a permission rule is enforced by Claude Code, "not by the
model" (code.claude.com/docs/en/permissions, "Manage permissions"). Each stakes tier gets a profile
the harness enforces, so the floor holds when the skill was not loaded and in every permission mode.
Paste it; never let an agent rewrite a settings file to loosen it.

## What the harness does (read the pages again before relying on a line)

- **Order:** deny, then ask, then allow; the first match decides, and specificity does not change
  the order. An allow rule cannot carve an exception out of a deny; an ask prompts even when a more
  specific allow matches. (permissions, "Manage permissions")
- **Across files, deny wins:** lists merge across user, project, local and managed settings; a deny
  at any level beats an allow at any other. (permissions, "Settings precedence"; settings, "Lists
  merge instead of overriding"). For a tier c profile, or when asked whether another settings file
  can loosen a rule, check it with `python3 <the skill's base directory>/scripts/permissions_check.py --file
  <scope>=<settings file> --command "<a command the profile must stop>"` (save a draft to a file
  first; `--inline <scope>='<json>'` suits only a one-line JSON; the base directory is the one the
  Skill tool printed when the skill loaded) and paste each block as printed; its CROSS_FILE_PROBE
  line shows an allow in user or local settings cannot undo the deny. Call it by its full path, not
  after cd.
- **Every mode:** deny blocks in every mode, `bypassPermissions` included. A call matching an ask
  rule is never auto-approved in any mode: it prompts, or is denied where no prompt is possible
  (`dontAsk`); an installed mod is the one exception ("Mods" below). Command-content ask rules fall back to a prompt in auto mode; allow rules do nothing
  in `bypassPermissions`. (permission-modes, "Available modes", "Skip all checks with
  bypassPermissions mode", "How auto mode evaluates actions"; permissions, "Permission modes")
- **`disableBypassPermissionsMode`:** valid in any settings file, but the docs call it "most useful in
  managed settings where they can't be overridden"; in a project file it is a team default, not a
  lock. (permissions, "Permission modes")
- **Where to put it:** the committed `.claude/settings.json`. Its `deny` and `ask` rules apply at
  once; its `allow` rules wait until each person trusts the folder. (permissions, "Project allow
  rules and workspace trust") `defaultMode` `bypassPermissions` or `auto` set there does not take
  effect. (permission-modes, "Which mode a session starts in")
- **Pattern form:** `Bash(git log *)`: everything before the first `*` is matched as written, and
  the space before a trailing `*` is part of the rule. Deny and ask apply to any subcommand of a
  compound command, a subshell or a command substitution. (permissions, "Wildcard patterns",
  "Compound commands")

## What it does not do

- **A Bash rule is not a security boundary.** It matches the command text as written: `Bash(rm *)`
  does not stop `/bin/rm …` or `bash -c 'rm …'`. Where the floor must hold, add the sandbox's
  filesystem and network rules or a PreToolUse hook. (permissions, "What a Bash rule doesn't match")
- **Mods:** without managed settings, a managed MCP file or a Team or Enterprise login, an installed
  mod can approve some calls a deny rule refuses and can skip an ask rule's prompt. Read what a mod
  does before installing it on a live-tier machine. (permissions, "Precedence among rules, hooks, and mods")
- **Read and Edit denies cover Claude's file tools, not every process.** They apply to the built-in
  file tools and, in a Bash command Claude Code can analyse, to redirections and recognised file
  commands such as `cat`, `head`, `sed` and `tee`; a script or program a command runs can still read
  the file. Keep secrets out of the working tree where that matters. (permissions, "What `Read` and
  `Edit` rules cover")
- **Edit rules cover every file-editing tool,** `Write` and `NotebookEdit` included; a
  `Write(path)` or `NotebookEdit(path)` rule is accepted but never matched, so the profiles deny
  with `Edit(...)`. (permissions, "`Write(path)`, `Glob(path)`, and `Grep(path)` rules don't match")
- `Bash(command:…)` parameter rules are ignored; write `Bash(… *)`. (permissions, "Match by input
  parameter")

## Profiles (cumulative: each tier keeps every deny and ask of the tier below)

Replace the example commands with this project's own: its test command, its push and publish
commands, and every command that can change the live system.

### Exploration (tier a)

```json
{
  "permissions": {
    "allow": ["Bash(python3 -m unittest *)", "Bash(git diff *)", "Bash(git log *)", "Bash(git status)"],
    "deny": ["Read(./.env)", "Read(./.env.*)", "Read(./secrets/**)"]
  }
}
```

### Internal (tier b)

```json
{
  "permissions": {
    "allow": ["Bash(python3 -m unittest *)", "Bash(git diff *)", "Bash(git log *)", "Bash(git status)"],
    "ask": ["Bash(git push *)", "Bash(gh pr merge *)", "Bash(npm publish *)"],
    "deny": ["Read(./.env)", "Read(./.env.*)", "Read(./secrets/**)", "Read(~/.ssh/**)"]
  }
}
```

### Live (tier c)

```json
{
  "permissions": {
    "defaultMode": "default",
    "disableBypassPermissionsMode": "disable",
    "allow": ["Bash(python3 -m unittest *)", "Bash(git diff *)", "Bash(git log *)", "Bash(git status)"],
    "ask": ["Bash(git push *)", "Bash(gh pr merge *)", "Bash(npm publish *)",
            "Bash(ssh *)", "Bash(scp *)", "Bash(rsync *)", "Bash(./deploy/release *)"],
    "deny": ["Read(./.env)", "Read(./.env.*)", "Read(./secrets/**)", "Read(~/.ssh/**)",
             "Edit(./.env)", "Edit(./.env.*)", "Edit(./secrets/**)", "Edit(~/.ssh/**)"]
  }
}
```

The live tier puts every command that can change the live system under **ask**, never allow, because
an ask is never auto-approved in any mode (it prompts, or is denied where no prompt is possible; an
installed mod is the one exception, "Mods" above); a destructive command the project never wants run goes under
**deny**. Principle 13's "ask before mutating" is then enforced by the harness, and principle 14
applies to each prompt: a declined prompt means stop.

*Why:* the tier model was held by prose and reminders only; a session that skipped the skill had no
floor. Industry baseline: least privilege, and Warp's agent profiles, where a denylist "takes
precedence over your other permission settings". Mapping: Warp's denylist means "always ask", which
is Claude Code's `ask`; Warp's "Never" is `deny`. Warp's personal denylist can be bypassed by "Run until
completion" when its auto-approve setting allows it; only team-enforced rules are never bypassed. This method departs by setting the profile per
stakes tier rather than per user, and by printing it for a person to paste rather than writing it.
*Test:* `tests/test_permission_profiles.py` (valid JSON, documented rule form, no mode a project file
cannot set, cumulative deny and ask, bypass disabled on live).
