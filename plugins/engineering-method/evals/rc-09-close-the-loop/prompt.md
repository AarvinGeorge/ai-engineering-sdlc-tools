---
description: "Contamination strings: vat_region ; render_tax_line"
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
---

Wrap-up of this week's investigation. Our invoicing agent (an LLM) put the wrong VAT rate on invoices for some customers.

- Monday: support reported it. On-call assumed the model had made the rate up and edited the prompt to "always use the rate from the tax table". No change.
- Tuesday: we compared the failing customer's instance with a working one. Both ran the same build, so we ruled out configuration. Later we found the working one had `vat_region` set per customer and the failing one did not.
- Wednesday: we read the local transcript of a failing turn and reasoned from it all day. It turned out to be cut off before the tax section.
- Thursday morning: we pulled the full input from the trace store. The customer's VAT region line was missing. We found `if customer.country == company.country: return ""` in `render_tax_line`, added when all customers were domestic.
- Thursday afternoon: fix planned and reviewed: always render the region line, and change the test that pinned the empty return. Root measured.

One more thing: the alert that should have caught wrong-rate invoices posts to a channel that has been muted since a team reorganisation, so we heard about this from the customer three days late.

Anything else before we close this?
