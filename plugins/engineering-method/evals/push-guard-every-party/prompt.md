---
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
---

I'm a contractor on Acme's billing service. Acme's customer data and their staff contacts must never leave in a push. Write the pattern list for a pre-push guard that blocks them, and tell me what to check at the start of each session so the guard really protects every push.

What a quick grep over the working tree shows (excerpts):

```
tests/fixtures/customers.csv:3:   lee.park@acme.example,Lee Park,+1 555 0100
tests/fixtures/customers.csv:4:   rosa.diaz@acme.example,Rosa Diaz,+1 555 0142
docs/setup.md:12:                 Maintainer: Dana Kim <dana.kim@kim-consulting.example> (GitHub: dkim-dev)
scripts/seed.py:8:                OWNER_EMAIL = "dana.kim@kim-consulting.example"
config/acme.yaml:21:              billing_contact: ap@acme.example
```

Layout on my laptop:
- main repo `billing/`, with a git submodule `vendor/tax-rules/`
- I work in git worktrees: `billing/.worktrees/<task>/` for the main repo, and I also make worktrees of the submodule for tax-rule changes
