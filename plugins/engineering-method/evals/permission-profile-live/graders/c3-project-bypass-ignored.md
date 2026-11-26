---
# Judged: a documented behaviour must be stated, not merely avoided.
type: llm
weight: 1
---

Scenario: the user sets defaultMode bypassPermissions in the committed project file.

Pass when the answer says bypassPermissions set as defaultMode in a project (or local) settings file does not take effect, and recommends permissions.disableBypassPermissionsMode set to "disable" for a live system.

Fail when it keeps bypassPermissions, or only removes it without saying it would not have applied, or omits disableBypassPermissionsMode.
