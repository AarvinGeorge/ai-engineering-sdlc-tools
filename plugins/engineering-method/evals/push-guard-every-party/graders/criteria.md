---
type: llm
weight: 1
---

Pass when ALL hold:
1. The pattern list covers every party's identifiers, including the operator's own (Dana Kim's name, email, GitHub handle), not only the client contact's, and says why (the operator's own details leak into commits too).
2. The session-start check confirms the guard is installed in every repository pushed from: the main repo AND the submodule, including the submodule's worktrees, whose separate git dirs get no hook from the main repo; it gives a concrete way to list and check each one (e.g. the hooks path per git dir, or a shared `core.hooksPath`).
3. It proves each installed guard can fire: a control push or dry run with a planted fake value shows the refusal.
Fail if the patterns cover only the client's identifiers, or the check covers only the main repo.
