---
max_turns: 16
allowed_tools: [Read, Glob, Grep, Skill, Bash]
description: "contamination strings: meeting-summary; flags decisions; 7 of 9"
---

Our meeting-summary skill was written with Claude Opus, and its evals run on Opus too. Set up the eval judging. My idea: use Opus as the judge as well, since it's our strongest model, and for the cheap criteria just leave `--judge-model` at its default. One criterion, "flags decisions that have no owner", the judge and I disagreed on twice last week. My rulings so far, beside the judge's verdicts (also in `labels.csv`):

```csv
answer_id,criterion,owner,judge
a1,flags decisions that have no owner,pass,pass
a2,flags decisions that have no owner,pass,pass
a3,flags decisions that have no owner,pass,pass
a4,flags decisions that have no owner,pass,pass
a5,flags decisions that have no owner,pass,pass
a6,flags decisions that have no owner,pass,pass
a7,flags decisions that have no owner,fail,fail
a8,flags decisions that have no owner,fail,pass
a9,flags decisions that have no owner,fail,pass
```

The judge agreed with me on 7 of 9, so I'd call it 78% accurate.
