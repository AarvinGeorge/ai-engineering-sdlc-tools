---
type: llm
weight: 1
---

Scenario: the eight sections differ in kind (a frozen mission, 22 dated "where we left off" entries, rules with their back-stories, a 140-row service map, a replaced on-call rota, three outage diaries, one-liners, a keep-verbatim section).

Pass when it sorts the sections by kind (binding rules, current pointers, frozen or keep-verbatim text, stale state, history, reference lists) and treats each kind differently: binding rules kept but compressed to rule plus reason plus a decision id or date; only entries that are still current kept in section 2; sections 1 and 8 left byte-identical and checked so (a diff or a hash per section, before and after); the replaced entries, the Q3 rota and the outage diaries moved to the archive or the decision log; the service map replaced by a pointer to where it is kept.

Fail when it applies one treatment to every section (for example "summarise each section"), trims or rewords section 1 or 8, or keeps the service map, the rota or the outage diaries inline.
