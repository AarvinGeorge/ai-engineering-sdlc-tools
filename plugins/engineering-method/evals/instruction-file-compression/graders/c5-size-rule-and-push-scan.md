---
type: llm
weight: 1
---

Scenario: the file grew to 71,400 bytes over a few months and is about to be pushed.

Pass when the new file states its own size rule (a cap, old resume entries move to the archive, findings go to dated documents) and a scan for secrets and personal data runs before the push.

Fail when no size rule is written into the file itself, or the push happens without a secret and personal-data scan.
