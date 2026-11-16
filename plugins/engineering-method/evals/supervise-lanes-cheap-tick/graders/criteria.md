---
type: llm
weight: 1
---

Pass when ALL hold:
1. It moves the recurring 15-minute check off the main strongest-model session: a cheap agent (or a small script plus a cheap model) reads the lane state and writes the status, and the main session reads only that report.
2. For E-05 (about 46 minutes with no file change, a status ping unanswered): it says to stop the agent, save its uncommitted diff as a patch, and dispatch a fresh agent that inherits the same worktree, rather than waiting longer or re-pinging indefinitely.
3. The brief change: builders take short foreground steps; only the named full suite may run in the background (no ad hoc `nohup … &`); the controller watches file mtimes and processes, pings once after about 30 idle minutes and stops at about 45.
4. Every dispatched agent reports the model id it actually ran as, and the plan/ledger disagreement is settled from that report, not by picking one of the notes.
Fail if it runs the tick in the main session, or picks one of the conflicting notes as the answer.
