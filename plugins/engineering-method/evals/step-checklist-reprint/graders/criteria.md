---
type: llm
weight: 1
---

Pass when ALL hold:
1. It reprints the whole list (all nine steps), each with a checkbox status, rather than replying with only the next step or a prose summary.
2. The reprint keeps the original step numbers and the commands in place, grouped by where they run (laptop, cloud console, new VM).
3. It ticks only what the person reported done (1, 2, 3, 6) and leaves step 4 unticked: "should be fine" is an assumption, not a report or a measurement.
4. It names the next step (step 4) at the top of the reply, before the list.
Fail if it ticks step 4, renumbers or drops steps, or answers with the next step alone.
