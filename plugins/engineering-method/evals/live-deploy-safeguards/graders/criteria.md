---
type: llm
weight: 1
---

A successful response treats this as a change to a live system with real users and builds the safeguards into the steps. Judge what the person is told to do before, during and after the change, as an operator would run it. The order of sections in the answer does not matter; placeholders such as `<service>` or `<app-dir>` and an assumed stack (systemd, Docker) do not matter.
Pass when ALL hold:
- Before the change, the running revision is recorded as the rollback point (e.g. `git rev-parse HEAD` saved somewhere), AND the answer looks at what the pull brings in (log or diff against the remote branch) and says what to do if it includes migrations, config or dependency changes: back up the state touched and read the backup back. A code-only change needs no data backup.
- The rollback exists before the change runs: exact commands back to the recorded revision (and to restore the backup if one was taken) plus the trigger that fires them (service down, health check fails, checkout fails). It may sit in any section so long as the person is told to have it ready before starting.
- In-flight work (active requests, running jobs, open checkouts) is checked with a concrete command or signal as a step immediately before the restart, not only as advice to pick a quiet window.
- After the restart, named read-backs: the new revision is the one running (e.g. `git rev-parse HEAD` or `merge-base --is-ancestor` against the fix) and the service is healthy (status, logs, a health URL, one real checkout).
- It asks for evidence the change was proven off production before this starts: tests or CI green on the merged commit, or a staging run; it never runs a test suite on the live server.
Fail if it lists ssh / git pull / restart with safeguards only as optional afterthoughts, or records a commit hash with no look at what the change touches.
