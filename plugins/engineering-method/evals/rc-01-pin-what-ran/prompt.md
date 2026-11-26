---
description: "Contamination strings: sha256:9b2e41c07d ; Aurora"
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
---

Our room-booking assistant (an LLM with calendar tools) runs as one instance per team. Since Monday the North team's instance answers "I can't find a room called Aurora" for rooms that exist; the South and East instances book the same rooms without trouble.

The three `instance.yaml` files, as committed in the config repo:

```yaml
# north/instance.yaml
image: registry.example.invalid/roombot:2.4.1@sha256:9b2e41c07d
org_display_name: "North Ops (Floor 3)"
calendar_mode: delegated

# south/instance.yaml
image: registry.example.invalid/roombot:2.4.1@sha256:9b2e41c07d
org_display_name: "South"
calendar_mode: shared

# east/instance.yaml
image: registry.example.invalid/roombot:2.4.1@sha256:9b2e41c07d
org_display_name: "East"
calendar_mode: shared
```

A teammate's view: "They all run image 2.4.1, so it isn't our code. It's the model having a bad week."

Work out why North fails.
