# What the toolkit could adopt from Warp's philosophy

Written 25 Nov 2026. Builds beyond `docs/research/2026-11-21-warp-factory-stack-comparison.md` (the companion note), which covered the seven-layer Factory Stack and three gaps (run metrics, session scorer, settings manifest). Those are not repeated.

> **How this was read.** Warp's pages were read through a summarising fetch tool on 25 Nov 2026, and most Warp docs pages carry no date. Short quotes below are paraphrases unless marked otherwise; check the page before quoting it elsewhere. Nothing about Warp was tested; behaviour is as Warp's pages describe it.

Model that ran this research: `claude-sonnet-5-5`.

Evidence rules: every Warp claim below is from a Warp page or a named source, read 25 Nov 2026 through a page-reading tool that summarises the page. So wording in quotes is as the tool returned it; re-read the page before quoting it publicly. Warp's own claims are vendor claims. Nothing here was tested.

## (A) Warp's philosophy, in nine named principles

**P1. The human is the reviewer.** Warp keeps people as final reviewers and does not add an AI reviewer to check an AI. Quote: "Instead of relying on an AI to check another AI's work, Warp makes the human the reviewer." Source: Agents 3.0, 19 Nov 2025, https://www.warp.dev/blog/agents-3-full-terminal-use-plan-code-review-integration. Note the factory posts (P9) do add review and verification agents, with a human reviewing their output; the two positions coexist.

**P2. A plan is a checkpoint before execution.** "Planning introduces a deliberate checkpoint into the development process." Plans are versioned, saved, editable, and can be run in full or one section at a time. Sources: same blog (19 Nov 2025); https://docs.warp.dev/agents/capabilities/planning/ (read 25 Nov 2026, undated).

**P3. Autonomy is set per permission type, and a deny list wins.** Each permission type takes one of four levels: Agent Decides, Always ask, Always allow, Never. "The denylist takes precedence over both the allowlist and `Agent decides`." A team-set denylist "always require[s] approval and [is] never bypassed", even by auto-approve. Source: https://docs.warp.dev/agents/capabilities/agent-profiles-permissions.md (read 25 Nov 2026, undated). Defaults: the agent asks before it runs commands, edits files or calls MCP servers.

**P4. Everything the agent does happens in the foreground.** "Everything happens in the foreground — no opaque background jobs or hidden output streams." Source: Agents 3.0 blog (19 Nov 2025). Cloud agents give the same: each run has a link and a record, and teammates can "hop in and steer it". Source: Oz launch, 10 Feb 2026, https://www.warp.dev/blog/oz-orchestration-platform-cloud-agents.

**P5. Context is files in the repo, the same everywhere.** Rules, Skills and MCP servers "apply the same way in the app, the CLI, and the cloud" (https://docs.warp.dev/agents.md, read 25 Nov 2026). Project rules live in `AGENTS.md`; the nearest file wins (subdirectory, then root, then Global Rules). Warp reads other tools' files, `CLAUDE.md` included. Skills load only when the task calls for them and are found in `.agents/skills/`, `.claude/skills/` or `.github/skills/`. Sources: https://docs.warp.dev/agents/capabilities/rules.md and https://docs.warp.dev/agents/capabilities/skills/ (read 25 Nov 2026).

**P6. Agents work from a written spec, then check the diff against it.** Three skills: write a product spec (`PRODUCT.md`: user stories plus "product invariants" that can be verified), write a tech spec (`TECH.md`), then `/validate-changes-match-specs`, which asks the agent to recheck its work and report inconsistencies; the author reviews each. Specs are Markdown checked into the same PR. Source: "Three skills you need for spec-driven development", 11 Jun 2026, https://www.warp.dev/blog/three-skills-for-spec-driven-development.

**P7. Review feedback is anchored and batched.** Comments attach to a file and line, many are collected, and the agent fixes them in one iteration and returns a new diff. Works with Claude Code and Codex output too. Source: https://docs.warp.dev/agents/local-agents/interactive-code-review/ (read 25 Nov 2026, undated).

**P8. Improvement is two small skills and a human filter.** An inner skill does the task; an outer improver skill runs on a schedule, compares the output with human responses, and proposes small edits as plain-file PRs. Feedback is taken where work already happens, with reasons ("Low friction is what keeps signal flowing"). Skills are small, use progressive disclosure, state principles with reasons, and are separate from memory (skills change deliberately; memory changes during use). Where a domain is verifiable, build the verification harness first. Source: Anthropic customer article, 26 Aug 2026, https://claude.com/blog/how-warp-builds-self-improving-agents-on-claude.

**P9. Engineers build the factory; humans handle the exceptions.** "Factory engineers" treat each interactive human session as a failure to learn from. A triage agent decides if a task is automatable, a spec agent drafts, a human reviews the spec before implementation, then review and verification agents, then a human reviews code and verification output. The platform records each human intervention so improvement agents can reduce it. Metrics: share of fully automated tasks, cost, factory efficiency. Source: "We are now factory engineers, not product engineers", 18 Jun 2026, https://www.warp.dev/blog/we-are-now-factory-engineers-not-product-engineers. Open-source pipeline details (labels `ready-to-spec`, `ready-to-implement`; human sets the second after spec review): Warp README and docs as reported by a search summary, [unsourced beyond that]; not fetched directly.

Also read, used for context only:
- The "coding mandate" (10 Jul 2025, possibly stale): engineers own what they submit ("AI is a tool, not a responsible party on our software team"), ask for a plan first, avoid one-shotting large changes, share failed prompts. https://www.warp.dev/blog/warp-ai-coding-mandate
- Docs agents (4 May 2026): a PR-review agent comments but "None of it blocks a merge". https://warp.dev/blog/open-sourcing-our-docs-and-the-agents-that-maintain-them
- Handoff is "best-effort": if changes cannot be applied, the agent reports which failed and continues. https://docs.warp.dev/platform/handoff/ (read 25 Nov 2026).
- Agent Management Panel statuses: Working, Blocked, Canceled, Failed, Success; an unattended run that needs input ends as Blocked "instead of waiting indefinitely". https://docs.warp.dev/platform/managing-cloud-agents/ (read 25 Nov 2026).
- Claude Code inside Warp gets notifications through a "Warp notification plugin". https://docs.warp.dev/agents/cli-agents/overview/ (read 25 Nov 2026).
- Oz multi-harness (19 May 2026): one control plane for Claude Code, Codex and Warp Agent. https://www.warp.dev/blog/multi-harness-cloud-agent-orchestration

## (B) Per principle: toolkit status

| Principle | Status | Where |
|---|---|---|
| P1 Human is the reviewer | Already done, with a twist | Toolkit uses a cross-model reviewer that runs probes (`engineering-method` `references/review-loop.md`) and keeps "a declined permission means stop". The human still holds go/no-go. |
| P2 Plan as checkpoint | Already done | plan-layer: Planned stage needs a plan doc with verifiable steps and an out-of-scope list; plan state in git. Versioning is git, not a feature. |
| P3 Deny-wins permission levels | NEW (for the permissions content) | The toolkit states "enforcement over instruction" as a principle but ships no permission profile. The planned settings manifest holds model-per-role and stage map, not permissions. See idea 2. |
| P4 Foreground and auditable | Already done | Evidence-over-assertion rule; plan page; work-log; pause/handoff. |
| P5 Context as repo files, same everywhere | Mostly done; remainder already planned | `SKILL.md` with `references/`, `MAP.md`, hooks. Instruction-file compression and Codex/Cursor manifests are already planned. Nearest-file-wins is Claude Code's own behaviour; nothing to add. |
| P6 Spec then check diff against spec | Half done; check is NEW | Plan doc and out-of-scope list exist; nothing compares the finished diff to them. Invariants exist but cannot be run. See ideas 1 and 4. |
| P7 Anchored, batched review | Already done | Review-loop: "file and line for every verdict", fix round re-reads each cited line. Bounded review loops are already planned. |
| P8 Two-skill improvement loop | Already planned | Session scorer and run metrics; evaluation method (code first, calibrated judges, pass^k); evals in CI. Skill-size and principle-with-reason style is already the toolkit's design rule. |
| P9 Factory engineer; humans as exceptions | Partly planned; one slice NEW | Run metrics already planned (human touchpoints per task). Human sign-off before building is not enforced anywhere. See idea 3. Fewer-human-touchpoints as the headline goal is deliberately not adopted (see "not to copy"). |

Other already-planned items that Warp's material also points at: tracker controller and Linear/Jira adapters (Warp triggers from Slack/Linear), marketplace CI gates.

## (C) New ideas, ranked

Ranking: value for the cost, fit with "no over-engineering", smallest blast radius first. Each needs a real gap behind it; where I could not show one from the repo, it says so.

### 1. Plan-conformance check at the Verified stage

- **What to adopt.** Warp's `/validate-changes-match-specs` (P6): before a change is called verified, the agent compares the diff with the active plan item's steps and out-of-scope list, lists mismatches (work done that no step asked for; a step with no change; a change inside the out-of-scope list), and the human rules on each. Findings, not auto-fixes.
- **Extends.** `engineering-method`: a new reference `references/plan-conformance.md`, one line in the stage map for Verified, plus one eval case in `evals/`. Optional later: plan-layer `SKILL.md` names the same step.
- **Why it matters.** Today the Planned stage demands an out-of-scope list but no stage reads it again. A list nobody checks is advisory text; this makes it a check. Scope creep is the failure the list exists for (plan-layer README, cycle table).
- **Smallest first step.** Write the reference and its eval (the eval prompt: a diff that touches a file named in out-of-scope; pass = the agent reports it before saying done). No script, no hook.
- **Do not copy.** The `PRODUCT.md` / `TECH.md` split and `specs/<issue>/` folders: the plan doc is already the spec and a second document type is duplication. The computer-use verifier for UX: Warp-specific and costly.

### 2. A permission profile per stakes tier (deny wins)

- **What to adopt.** P3: a short, copyable permissions snippet per tier (prototype, internal tool, live system) for Claude Code's `settings.json`: allow list of read-only commands, deny list of destructive ones (Warp's defaults name `rm`, `curl`, `wget`, `eval`), and the rule that deny beats allow. The live tier adds: no auto-approve of anything that touches a live host.
- **Extends.** `engineering-method`: `references/permission-profiles.md`, linked from the existing "Live systems and permission" section of `SKILL.md`. It later becomes content for the already-planned settings manifest instead of a second file format.
- **Why it matters.** The toolkit's own rule is "enforcement over instruction", but the tier model is enforced only by prose and hooks that remind. A permission rule is enforced by the harness, so it holds even when the agent skips the skill. Gap shown: engineering-method README lists hooks and evals, no permissions.
- **Smallest first step.** One reference with three snippets, checked by hand against Claude Code's current permissions docs (not read in this pass: [unsourced here]; verify deny-over-allow precedence and the pattern syntax before publishing).
- **Do not copy.** The four-level model with "Agent Decides" (it is a UI feature and its Apply-diffs level currently behaves like Always ask); the profile switcher UI; the name "YOLO mode". No script that edits a user's `settings.json`: print it, let the human paste.

### 3. Approval recorded before building, on live-tier work

- **What to adopt.** P9: a human reviews the spec before implementation starts. In plan-layer, an optional field on an active item (for example `approved: {by, date, plan_sha}`), and a gate rule: an item at `building` or later whose `tier` is live with no approval drifts.
- **Extends.** `plan-layer` `scripts/check.py` and `schema/`, with a line in the README cycle table. Opt-in; silent where not declared (matches the toolkit's "silent where uninvited").
- **Why it matters.** The cycle table says a skipped Planned stage means "scope creep, and no way to tell when it is finished", but nothing records that the human accepted the plan. Gap shown: no `approv*` or sign-off string in plan-layer's README or `check.py` (grepped 25 Nov 2026, zero hits; the pattern could produce hits, tested on the word "invariant", which matched).
- **Smallest first step.** Add the optional field and one drift rule behind a test; do not add a command to set it. The human types it, or the agent writes it only after an explicit yes in the transcript.
- **Do not copy.** GitHub issue labels as a state machine (`ready-to-spec`, `ready-to-implement`) and triage agents: they serve an open-source crowd, and this toolkit serves one owner. Any rule that asks approval on prototypes.

### 4. Invariants that can be run

- **What to adopt.** Warp's `PRODUCT.md` carries "product invariants that can be verified" (P6). plan-layer invariants today are `rule`, `state` (holding, at risk, broken) and `detail`, set by hand. Add an optional `check` (a command whose exit code is the state). `sync.py` runs it only when told (`--run-checks`) and writes the result and the commit measured at.
- **Extends.** `plan-layer`: `schema/`, `scripts/check.py`, `scripts/sync.py`.
- **Why it matters.** A hand-set `holding` is an assertion; the toolkit's design rules say "evidence over assertion". It also lets the gate catch an invariant that quietly broke.
- **Smallest first step.** One invariant in this repo's own plan with a `check`, run by hand. Confirm first that no existing feature already runs invariant commands: I read the schema and `check.py` only for `rule/state/detail`, not every script ([unverified] for `sync.py` and `brief.py`).
- **Do not copy.** Computer-use or UI verification. A default run of arbitrary commands from `plan.json` at session start (a hook running a file's commands on someone else's machine breaks "fail open" and is a security surface; keep it explicit and off by default).

### Ideas considered and dropped

- Notifications and an agent status panel (Working/Blocked/Failed): Claude Code and the Desktop app already notify; plan-layer tasks already have `blocked` with a note.
- Advisory non-blocking PR-review agent on every PR: needs a hosted runner and spend for a solo repo; marketplace CI gates are already planned and cover the real risk.
- A knowledge store of shared prompts (Warp Drive Prompts, "share failed attempts"): the toolkit's skills and decision log are the same job. Warp Drive objects beyond Rules, MCP, Skills and Prompts were not described on the page read (workflows, notebooks, env vars, sharing permissions: not verified).
- Multi-harness control plane (Oz): outside scope; the Codex/Cursor manifests already planned are the in-scope slice.
- "Fewer human touchpoints" as the goal: contradicts the toolkit's deliberate human gates.

## (D) Sources (all read 25 Nov 2026 unless stated)

Warp blog:
- https://www.warp.dev/blog/agents-3-full-terminal-use-plan-code-review-integration (19 Nov 2025)
- https://www.warp.dev/blog/oz-orchestration-platform-cloud-agents (10 Feb 2026)
- https://www.warp.dev/blog/multi-harness-cloud-agent-orchestration (19 May 2026)
- https://www.warp.dev/blog/three-skills-for-spec-driven-development (11 Jun 2026)
- https://www.warp.dev/blog/we-are-now-factory-engineers-not-product-engineers (18 Jun 2026)
- https://warp.dev/blog/the-virtuous-loop-of-open-agentic-development (28 Apr 2026)
- https://warp.dev/blog/open-sourcing-our-docs-and-the-agents-that-maintain-them (4 May 2026)
- https://www.warp.dev/blog/warp-ai-coding-mandate (10 Jul 2025, possibly stale)

Warp docs (undated pages):
- https://docs.warp.dev/agents.md
- https://docs.warp.dev/agents/capabilities/agent-profiles-permissions.md
- https://docs.warp.dev/agents/capabilities/rules.md
- https://docs.warp.dev/agents/capabilities/skills/
- https://docs.warp.dev/agents/capabilities/planning/
- https://docs.warp.dev/agents/local-agents/interactive-code-review/
- https://docs.warp.dev/agents/cli-agents/overview/
- https://docs.warp.dev/platform/managing-cloud-agents/
- https://docs.warp.dev/platform/handoff/
- https://docs.warp.dev/knowledge-and-collaboration/warp-drive/ai-objects/

Third party:
- Anthropic, "How Warp builds self-improving agents on Claude", 26 Aug 2026, https://claude.com/blog/how-warp-builds-self-improving-agents-on-claude

Not verified or not read:
- Warp telemetry and privacy: a search turned up Warp docs whose pages disagree on whether secret redaction is on by default; not fetched, so no privacy claim is made here (`docs.warp.dev/support-and-community/privacy-and-security/privacy/`).
- The Warp open-source README labels (`ready-to-spec`, `ready-to-implement`) and the `oz-for-oss` repo: seen only in a search summary.
- The "Spec and Verify" phrase is in the 28 Apr 2026 virtuous-loop post but that post does not define it; the spec-driven post above is the closest definition.
- Warp's old doc URLs (`/agent-platform/...`) returned 404; the `/agents/...` pages above are the current ones as of this read, and pages are undated so changelog timing is unknown.
- Claude Code's own permission precedence (relevant to idea 2) was not read in this pass.
- Warp's changelog was not read.
- Nothing about Warp's product was tested; all behaviour is as the pages state.
