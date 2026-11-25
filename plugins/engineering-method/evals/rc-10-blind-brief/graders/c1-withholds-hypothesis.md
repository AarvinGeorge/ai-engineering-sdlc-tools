---
type: llm
weight: 1
---

Scenario: the user asks for an investigator brief that tells the investigator to test the user's stale-cache hypothesis.

Pass when the brief gives the symptom, the evidence locations and the constraints but does not contain the stale-cache hypothesis or any other suspected cause; the answer says briefly why (an investigator handed a hypothesis tends to confirm it) and that the hypothesis will be tested against the investigator's independent findings afterwards, without refusing to write the brief.

Fail when the brief names the cache hypothesis or steers the investigator toward the cache, or the answer refuses to write a brief.
