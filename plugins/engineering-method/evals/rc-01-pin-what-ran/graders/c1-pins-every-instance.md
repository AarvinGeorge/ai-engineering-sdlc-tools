---
type: llm
weight: 1
---

Scenario: a room-booking assistant fails on the North instance and works on South and East; the committed instance.yaml files show one image digest and differing org_display_name and calendar_mode.

Pass when before comparing the instances it sets out, for each of the three instances (North and both working ones), what is actually running now: revision or image digest, model id, and the configuration and data values that shape what the model is given (such as org_display_name and calendar_mode), each with the command or source that reads it from the running instance rather than from the committed file, or requests, with the exact command per instance.

Fail when it compares from the committed files or the shared tag alone, covers only North, or omits the model id and the per-instance data values.
