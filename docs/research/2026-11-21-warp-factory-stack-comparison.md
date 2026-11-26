---
summary: This toolkit compared layer by layer with Warp's seven-layer "Factory Stack" (00 factories-as-code to 06 access). The toolkit covers orchestration (process) and part of improvement well, borrows data, inference and access from Claude Code, and has no compute layer. Three gaps worth closing are named.
status: record
covers: Warp Factory Stack, factories-as-code, scorers, benchmarks, observer loop, layering of this toolkit
key_facts: plan-layer 0.18.0, engineering-method 0.3.0 (21 eval cases), work-log 0.1.0, repo head 5982357; closest match layer 05; biggest gaps 02 compute and 06 access
updated: 2026-11-21
---

# This toolkit against Warp's Factory Stack

Written 21 Nov 2026. A layered picture of Warp's "software factory" stack, from a lecture, prompted the question:
how far is this toolkit from that picture, and is it layered the same way?

## Sources (vendor material: product claims are Warp's own)

- Zach Lloyd, [The Factory Stack](https://www.warp.dev/blog/the-factory-stack), 5 Sep 2026: defines layers 00 to 06.
- Ben Holmes, [Terraform for agents](https://www.warp.dev/blog/software-factory-as-code), 30 Sep 2026: `factory.yaml` plus `agents/`, `automations/`, `runners/`, `scorers/`, `benchmarks/`.
- [Closing the loop with self-improving cloud software factories](https://www.warp.dev/blog/agent-self-improving-software-factories), 27 Aug 2026: metrics, scorers, the observer loop, benchmarks.
- [Warp Factories](https://www.warp.dev/factories), [Factories as Code](https://www.warp.dev/factories/configuration), [Oz docs](https://docs.warp.dev/agent-platform/cloud-agents).
- Unverified: the Factory Stack post says Fortune 500 enterprises are deploying it; a third-party comparison ([agentastic.dev](https://www.agentastic.dev/compare/best-ai-software-factory-tools)) says Factories is in closed early access.
- Small mismatch: the lecture slide lists metrics as "autonomy · cost · cycle time"; the Factory Stack post says cost per PR, automation measurements and cycle times; the self-improvement post lists PR throughput, cost per PR and "automation percent" (average human touchpoints per PR).

## What this toolkit is (read from this repository at 5982357)

- `plan-layer` 0.18.0: plan state in JSON, an HTML view, a gate (`check.py`), hooks at SessionStart, PreCompact and Stop (the Stop hook runs the gate), history rolled to `plan/archive/`, and `tracker.py`, which reconciles the plan into an external tracker (expected vs actual, exit 1 on drift).
- `engineering-method` 0.3.0: one skill (principles scaled by stakes, a stage map), hooks at SessionStart and UserPromptSubmit, and 21 behaviour eval cases (`claude plugin eval`), each written to fail without its rule and pass with it.
- `work-log` 0.1.0: reads Claude Code transcripts and git history into a dated work log.
- CI: `.github/workflows/tests.yml`.

## Layer by layer

| Layer | Warp | This toolkit | Status |
|---|---|---|---|
| 00 Factories-as-code | One `factory.yaml` plus agent, automation, runner, scorer and benchmark files, reviewed as PRs | Versioned and PR-reviewed (`marketplace.json`, `hooks.json`, `SKILL.md`), but the factory's settings are prose: model per role, stage map and gates are written in the skill and in a project's instructions file, not in a manifest | partial |
| 01 Data and context | Traces, memory (vector store), artifacts, MCPs, RBAC | Claude Code transcripts (work-log reads them), file-based memory with no vector store, plan state and archive, whatever MCP connectors the user has; attribution by commit trailers; no RBAC (single user) | partial |
| 02 Compute | Sandboxes (Docker, Kubernetes), runners on Mac, Linux and Windows, computer use | None of its own: the agent runs on the developer's machine; parallel work is isolated by git worktree, not container | absent |
| 03 Inference | Frontier and open-weight models, bring your own, self-improving routing | One vendor through Claude Code; routing is a written rule set (`references/model-routing-and-cost.md`) the controller agent applies by hand | partial |
| 04 Improvement | Metrics, scorers on finished runs, replay benchmarks, a self-improvement agent proposing config diffs as PRs | Benchmarks in a narrow form: every rule's eval is an A/B of the skill with and without that rule. A cross-model reviewer scores each change. No automatic cost, autonomy or cycle-time metric; no sampled scoring of finished sessions; improvement is human-driven | partial |
| 05 Orchestration | Triage, spec, implement, review, verify; multiple harnesses; human in the loop; triggers and cron | Closest match: intent, grounded, planned, building, verified, recorded, plus the stage map and its skills; hooks as event triggers; a strong human-in-the-loop posture. But it runs inside one interactive session on one harness, and the plan page is a status view, not a live control room | mostly |
| 06 Access | Factory MCP, Slack or Teams, Jira or Linear, code forge, any device, API | Work enters through the agent's chat only. A tracker is an output mirror (it cannot launch work). No Factory MCP, no API, no webhook triggers | absent |

## Is the toolkit layered this way?

No, and on purpose. Warp's stack is layered by **infrastructure** for running many agents unattended in the cloud.
This toolkit is layered by **lifecycle stage and stakes** for one human and one controller agent working
interactively. Its goals differ too: Warp's headline metric is fewer human touchpoints per PR; this toolkit
keeps human gates deliberately (a declined permission stops; owner gates for spend, credentials, sends).
It occupies layer 05 (the process half), part of 04, and the versioned-and-reviewed principle of 00; it
relies on Claude Code for 01, 03 and 06.

## Gaps worth closing (for this toolkit), in order

1. **Run metrics from transcripts (04).** work-log already parses Claude Code transcripts; adding tokens,
   turns and human touchpoints per task gives cost and autonomy numbers with no new infrastructure.
2. **A session scorer (04).** plan-layer `ROADMAP.md` Gap 2 already sketches it: a read-only auditor over a
   sample of finished sessions whose findings arrive as proposed changes. That is Warp's observer loop with
   the human kept in.
3. **A small manifest (00).** Move the model-per-role table and the stage map into a YAML the hooks read, so a
   change to the method is a reviewable data diff rather than a prose edit.

Left alone deliberately: compute (02), multi-vendor inference (03) and new ways for work to enter (06). They pay
off only if the goal becomes unattended agents at scale, which is a scope and spend decision, not a gap in
the method.

## Limits of this comparison

- Warp's claims are from its own blog and docs; none was tested.
- The toolkit's test suites were not re-run for this note.
