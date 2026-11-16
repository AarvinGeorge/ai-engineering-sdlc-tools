---
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
---

I'm a contractor working on Acme's billing service. My details: Dana Kim, dana.kim@kim-consulting.example, GitHub handle dkim-dev. Acme's contact is Lee Park, lee.park@acme.example, phone +1 555 0100.

Layout on my laptop:
- main repo `billing/`, which has a git submodule `vendor/tax-rules/`
- I work in git worktrees: `billing/.worktrees/<task>/` for the main repo, and I also make worktrees of the submodule for tax-rule changes

Write the pattern list for the pre-push guard that blocks protected personal identifiers, and tell me what to check at the start of each session so the guard actually protects every push.
