# Proposed lines for `~/.claude/CLAUDE.md` (for the controller; not applied)

Each line is checked against the current global file (sections 1-4: header, clock, measurement
table, communication) and is not already there. Proposed as a new short section, e.g.
"## 5. Engineering method".

1. For non-trivial planning, building, reviewing or shipping, invoke the `engineering-method` skill and name the stakes tier (exploration / internal / live) first; ceremony the tier does not need is a defect.
2. A state claim ("deployed", "live", "merged", "parked", "pre-existing") is a measurement: read in the same pass, command shown, never recalled from notes.
3. Vendor docs before vendor claims: cite the tool's official docs or changelog before designing around its behaviour; anything uncited is labelled a hypothesis.
4. The reviewer is never the implementer's model, is at least as strong, and executes probes; an unreproduced finding is a hypothesis.
5. Name the model on every subagent dispatch, chosen by what a mistake costs and whether a test would catch it.
6. A declined permission means stop: no retry, no narrower form, no relocating the action to a path that does not prompt; mark it unverified and report.
7. Never `&&` a commit after a piped test run without `set -o pipefail` or an explicit gate on the summary line.
8. No over-engineering in either direction: build only for a real gap, that nothing existing solves, symmetrically; a guard that stops the work is over-engineering too.

## Recommended set (controller ruling, fix round 1)

- **Keep as a new section "## 5. Engineering method":** lines 1, 2, 6, 8.
- **Line 7 (pipefail):** becomes a row in the global §3 measurement table instead — rule: "A piped test run keeps its exit code (`set -o pipefail` or gate on the summary line) before any chained commit"; why: "a failing suite piped into tail once let a commit through".
- **Drop line 3 (vendor docs):** carried by the skill (principle 3); it matters when designing, which is when the skill loads.
- **Drop line 4 (reviewer model):** only relevant when dispatching reviewers, which is when the skill loads.
- **Drop line 5 (name the model):** Superpowers subagent-driven-development already says it, and it only applies when dispatching.
