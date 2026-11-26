---
description: "Contamination strings: pricing-prod ; catalogue-sync run 2291"
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
---

Our pricing assistant (an LLM with a `get_price(sku)` tool) has been quoting yesterday's prices for about a fifth of products since this morning's catalogue update.

Where the evidence is: the gateway log `/var/log/pricing/gateway.log` on the pricing host; the trace store project `pricing-prod`; the catalogue update job's log, `catalogue-sync run 2291`; cache keys `price:<sku>` in the shared cache.

Constraints: read-only. No writes to the cache or the catalogue, and nothing sent to customers.

Write the brief for a second-model investigator. My hypothesis is that the cache is stale; tell them to test that.
