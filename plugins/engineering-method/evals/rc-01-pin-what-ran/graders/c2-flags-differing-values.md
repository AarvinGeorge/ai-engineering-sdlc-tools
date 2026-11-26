---
type: llm
weight: 1
---

Scenario: the teammate blames the model; the committed instance.yaml files show one image digest and do not show which model each instance runs.

Pass when it does not rule the model in or out until each instance's model id (and the values it is given, such as org_display_name and calendar_mode) has been read from the running instance, and it flags those per-instance values as candidate confounders rather than assuming they match the committed files.

Fail when it rules the model out (or in) by argument, for example that a shared image means a shared model or that a model problem would show on all three instances, without reading each instance's model id; or it takes the committed files as what is running.
