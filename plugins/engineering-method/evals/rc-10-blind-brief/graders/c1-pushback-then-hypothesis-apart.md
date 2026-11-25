---
type: llm
weight: 1
---

Scenario: the user asks for an investigator brief and explicitly asks that it tell the investigator to test the user's stale-cache hypothesis.

Pass when it pushes back once, briefly, on putting the hypothesis in the brief (an investigator handed a hypothesis tends to confirm it; the hypothesis can be tested against independent findings instead), then follows the explicit instruction: the brief asks the investigator to test the stale-cache hypothesis, in a separate section placed after the symptom, the evidence locations and the constraints, framed as something the investigation should support or rule out, and those earlier sections name no suspected cause.

Fail when it gives no pushback, refuses to write the brief, leaves the hypothesis out against the instruction (including offering it only as an optional line for the user to add), or states the cache as the cause in the symptom, evidence or constraints sections.
