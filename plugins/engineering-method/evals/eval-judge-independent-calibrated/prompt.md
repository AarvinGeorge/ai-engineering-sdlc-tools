---
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
description: "contamination strings: meeting-summary; flags decisions; disagreed twice"
---

Our meeting-summary skill was written with Claude Opus, and its evals run on Opus too. Set up the eval judging. My idea: use Opus as the judge as well, since it's our strongest model, and for the cheap criteria just leave `--judge-model` at its default. One criterion, "flags decisions that have no owner", the judge and I disagreed on twice last week. We have no labelled examples yet.
