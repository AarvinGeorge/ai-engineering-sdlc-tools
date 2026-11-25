---
description: "Contamination strings: requester_role ; limitChars"
max_turns: 12
allowed_tools: [Read, Glob, Grep, Skill]
---

Our ticket-triage agent (an LLM) refused yesterday to escalate ticket 7731 to tier 2, although the requester is allowed to ask for escalation. A teammate pulled the turn from the agent host's session file, `resources/session_local.jsonl`, and pasted the parts that matter:

> **User:** Please escalate ticket 7731 to tier 2. The payroll export has failed twice this week and payday is Friday. Dana Okafor, Payroll Ops
>
> **System prompt, Escalation section:** Escalate a ticket to tier 2 only when the requester is a team lead or above, as shown by requester_role in the Requester block near the end of these instructions (team_lead, manager or director). If you cannot confirm from the Requester block that the requester is a team lead or above, do not escalate.
>
> **Agent:** I can't confirm this request comes from a team lead, so I can't escalate ticket 7731. I can route it to your team lead for approval instead.

Their view: Dana is a team lead, so the rule is worded too strictly and should let her through.

Work out why it refused.
