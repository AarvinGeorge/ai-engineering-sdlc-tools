---
type: llm
weight: 1
---

Pass when ALL hold:
- It recommends a reviewer that is a DIFFERENT model from the implementer (not Opus reviewing Opus), and at least as strong.
- It explains why in one or two lines (self-preference bias / grading its own homework).
- The brief tells the reviewer to execute: write and run probe scripts or tests against the code, not only read the diff; and labels unreproduced findings as hypotheses.
- The brief asks for file:line evidence and gives a brief plus a diff rather than the whole codebase.
- Bonus (not required): own worktree for the reviewer; a tool-call bound; what must not regress.
Fail if it recommends the same model as the implementer without flagging it, or describes a read-only review with no execution.
