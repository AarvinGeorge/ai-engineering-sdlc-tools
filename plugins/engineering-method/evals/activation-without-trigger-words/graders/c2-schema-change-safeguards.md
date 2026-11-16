---
type: llm
weight: 1
---

Scenario: the change adds a `points_balance` column to the `customers` table.

Pass when its steps include a backup of the affected data (at least the customers table) that is read back or verified before the change, a rollback written before the change (revision plus how the schema change is undone), and a read-back after (running revision and a real checkout).

Fail when it gives steps with no backup, or no rollback, or no after-change check.
