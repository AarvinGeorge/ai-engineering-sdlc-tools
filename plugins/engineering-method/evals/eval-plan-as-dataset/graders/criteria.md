---
type: llm
weight: 1
---

Pass when ALL hold:
1. It states a cost plan with the arithmetic and a hard cap before any run (e.g. the colleague's scheme is 30 x 5 x 2 x $0.40 = $120 per commit) and sets a budget per stage that runs stop at.
2. It shapes the cases as a dataset in layers (a small floor, a core, an extended set) mapped to stages (e.g. floor per commit, core per pull request, extended per release), with repeats only on the floor or where a difference between runs appears, not five repeats of everything.
3. Each of the three new rules gets a case that is run first against today's instructions and fails, then passes with the change; a baseline result is stored per artifact (instructions version) to compare against.
4. It adds controls: contamination (the judge and the agent do not see the expected answer; cases not copied into the instructions) and a fail-closed recipient guard on the email cases (only allow-listed sandbox recipients; anything else blocks the send).
Fail if it adopts the colleague's plan unchanged or runs anything without a stated cap.
