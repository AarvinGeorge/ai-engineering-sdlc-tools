---
description: "Contamination strings: Hilltop ; 3 of 10"
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
---

Our table-booking assistant (an LLM with a `book_table(date, time, party_size)` tool) runs one instance per restaurant. A customer asked for a table for 9 on Saturday at 19:30. The Harbour instance confirmed it. The Hilltop instance replied: "I'm sorry, we can't seat parties larger than 8." Both restaurants have a 10-seat table.

A teammate sent the same message ten times to Hilltop: 3 of 10 refused, 7 confirmed. Their view: "It's non-deterministic. Add a retry on refusal and move on."

Work out why Hilltop refuses.
