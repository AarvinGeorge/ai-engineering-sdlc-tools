---
type: llm
weight: 1
---

Pass when ALL hold:
- Every summary is 30 words or fewer.
- No summary contains `plan/plan.json`, `feat/login`, `doc 133`, `a1b2c3d`, or any other file path, branch name, commit hash or document number.
- `SSO` is either spelled out (single sign-on) or left out.
- Each summary states an outcome in plain language (for example that staff can now sign in with their company account, or that sign-up emails work again).
- The sign-up email problem, if mentioned, is described neutrally.
Fail if any summary keeps one of the codes above or exceeds 30 words.
