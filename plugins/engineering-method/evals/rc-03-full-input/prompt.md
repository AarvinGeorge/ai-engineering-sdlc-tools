---
description: "Contamination strings: requester_role ; limitChars"
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
---

Our ticket-triage agent (an LLM) refused yesterday to escalate ticket 7731 to tier 2, although the requester is allowed to ask for escalation. Two exports of that turn are in the `resources/` directory: `session_local.jsonl` (the agent host's own session file) and `trace_export.json` (from the tracing backend).

A teammate has already looked at the local file and thinks the escalation rule in the system prompt is worded too strictly.

Work out why it refused.
