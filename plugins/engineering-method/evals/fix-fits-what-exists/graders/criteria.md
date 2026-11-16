---
type: llm
weight: 1
---

Pass when ALL hold:
1. Before fixing, it gives the system the case: replay the conversation (or a test with that exact message) through the agent, and it calls any cause a hypothesis until that has run.
2. The plan has a "fit with what exists" step or section: it inventories every mechanism on this concept (the adapter's branches, the tool set and its descriptions, any confirmation step), extends the smallest one, says what the fix unlocks beyond this one case (calling the 15th branch a patch because it fixes only this phrasing), and checks the fix against each of goals (a), (b) and (c).
3. It rejects enumerating meaning in code: code enforces only the safety floor (confirmation before an irreversible cancel, authority over the account), while the order-versus-subscription meaning goes to the model as tools and facts (e.g. a separate `cancel_order` tool, an order lookup, clear tool descriptions), and the model asks the customer when unsure.
Fail if it approves the 15th branch as the fix, or proposes more keyword branches.
