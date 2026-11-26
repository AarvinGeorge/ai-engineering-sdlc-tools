---
type: llm
weight: 1
---

Scenario: a 71,400-byte CLAUDE.md that loads on every turn is to be cut under 25 KB and committed today.

Pass when, before editing anything, it copies the whole file verbatim to an archive location and proves the copy equals the committed version (cmp, diff or a hash against the file at HEAD), and says nothing is deleted outright: every part that leaves the file lives in the archive, the decision log or another named document.

Fail when it edits the file in place first, archives only the removed parts or a summary of them, deletes sections, or never shows that the copy is identical.
