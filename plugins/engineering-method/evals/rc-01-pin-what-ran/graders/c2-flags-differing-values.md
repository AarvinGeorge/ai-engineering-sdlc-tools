---
type: llm
weight: 1
---

Scenario: the teammate argues that one shared image 2.4.1 means the code is not involved.

Pass when it flags the values that differ between North and the working instances (org_display_name, calendar_mode, and any other it finds) as candidate confounders to test, and says a shared image does not mean the instances were given the same inputs.

Fail when it concludes from the shared image that the code is ruled out and blames the model, or ignores the per-instance differences.
