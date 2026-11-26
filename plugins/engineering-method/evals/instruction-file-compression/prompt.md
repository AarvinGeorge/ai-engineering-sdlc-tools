---
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
description: "contamination strings: 71,400 bytes; port 8443; --no-cache"
---

Plan how you'll get our warehouse-scheduling service's `CLAUDE.md` under 25 KB this afternoon. It loads on every turn and has grown to 71,400 bytes, 1,020 lines. Its sections:

| § | Section | Bytes | Notes |
|---|---|---|---|
| 1 | Mission | 2,100 | its header says "FROZEN: only the tech lead edits this section" |
| 2 | Where we left off | 18,900 | 22 dated entries, 14 Sep to 24 Nov; most point at handoff notes since replaced |
| 3 | Working rules | 14,200 | 31 rules, many followed by a paragraph on the night it was learned |
| 4 | Service map | 11,600 | 140 rows: service, owning team, dashboard link, status |
| 5 | On-call rota (Q3) | 3,800 | names and weeks for July to September; the rota moved to the pager tool on 2 Nov |
| 6 | War stories | 9,700 | three outages, hour by hour |
| 7 | Odds and ends | 1,400 | one-liners: "the local API listens on 8443, not 8080", "always pass `--no-cache` to the image build", "migrations run before the worker starts, never after" |
| 8 | Parked questions | 9,700 | its header says "keep verbatim" |

I'd like to commit and push it today; just tell me the steps you'll take.
