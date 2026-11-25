# Root-cause investigation

Superpowers' `superpowers:systematic-debugging` owns the procedure: its iron law, its four phases
and its tracing technique are not restated here. This file adds the investigation steps it does
not name, most of them for systems where a model makes the decision, and specialises two of its
steps (RC-5, RC-7) for those systems. SKILL.md principle 17 owns the fit check; RC-6 fills its
Exists line and RC-8 calls it by name.

## Using the steps

- **By name, at the trigger.** Invoke each step by name when its trigger fires, and report one
  line per step: `RC-n done: <evidence>` or `RC-n skipped: <reason>`.
- **Scaled by stakes.** Tier a: systematic-debugging plus RC-8's labels. Tier b: every step that
  applies, each reported done or skipped. Tier c: the same, and RC-8's record gate and RC-9 are
  required.
- **Order.** RC-1 → RC-2 → RC-3 → RC-4 → RC-5 → RC-6 → RC-7 → RC-8 → RC-9. RC-10 at every
  hand-off. RC-8's labels apply from the first claim, not only at the end.
- **Model-specific steps.** RC-3 and RC-4 read the model's input and reasoning. RC-5 and RC-7
  specialise systematic-debugging's Phase 2 and Phase 1 for model-driven systems. For a bug with
  no model decision in it, RC-3 and RC-4 are reported `skipped: not a model decision`, RC-5 and
  RC-7 fall back to systematic-debugging's generic phases, and the other steps apply unchanged.

## The steps

### RC-1 Pin what ran
**Rule.** Before comparing any two cases, read for every instance involved (the failing one, its
siblings, and every population the reporter calls working) the revision, image digest, model id,
and the configuration and data values that shape what the model is given (names, roles, modes,
switches), each with its command, now.
- **Trigger:** first, whenever an investigation compares instances or someone says "it works
  elsewhere".
- **Input:** the instance list. **Output:** one row per instance, one column per value, each cell
  with its command and time.
- **Prevents:** "same image, so same behaviour"; a recalled version; a per-instance value that
  makes one instance work by coincidence.
- **Evidence:** the table; each differing value flagged as a candidate confounder.

*Why:* every instance in the source case was on one build; the working ones worked because a
per-instance name happened to resemble the sender's address. *Test:* the table exists before the
first comparison, covers the populations the reporter named, and holds data values, not only the
build.

### RC-2 Read the decision record
**Rule.** Read what deterministic code decided for the failing event (identity, permission level,
route, outcome) from its own logs. A line someone pasted is a lead, not the record: pull every
line the code logged for that event before reading the decision from it. Then map every logged
size or count to the block or item it stands for. A number you cannot account for is the lead.
- **Trigger:** the start of every behaviour bug, after RC-1.
- **Input:** the event id or time window. **Output:** every logged line for the event, quoted;
  the decision read from them; a size map (logged number → block it represents → present or
  absent).
- **Prevents:** confusing what the code decided with what the model did; one quoted line taken
  for the whole record; a clue on screen left undecoded.
- **Evidence:** the query that pulled the event's lines and the quoted lines with timestamps; the
  size map with no unexplained row.

*Why:* the decisive number was on screen in the source case's first minute and decoded an hour
later; it showed an expected block was never sent. *Test:* the report pulls the event's full log
rather than reasoning from the pasted line alone, and every number in the quoted lines has a row
in the size map.

### RC-3 Read the full input (LLM)
**Rule.** Before naming any root for a model decision, read the exact input the model received on
that turn (system prompt, messages, tool schemas, tool results) from the most complete store (the
tracing backend before a local transcript). Check the size of the copy you rely on against the
original length the record states, and note every truncation flag, before naming a cause; a copy
shorter than the original is a fragment, and the part it is missing is where to look. Rebuilding
the input from code, log lengths or the model's own quotes is not reading it.
- **Trigger:** before any claim about why a model acted; whenever a record shows a truncation
  flag, a character limit, or a size smaller than the one logged.
- **Input:** the run id and the stores available. **Output:** the input as sent, or a statement
  that it cannot be read, naming where you looked.
- **Prevents:** theorising from fragments; "reconstructed from code"; a root recorded on an input
  nobody read.
- **Evidence:** the store and query used; the size of the copy read against the original size;
  truncation flags shown false, or the untruncated source named. If no store holds it, every root
  stays [hypothesis] (RC-8) and the missing trace is reported as an observability gap.

*Why:* two investigators in the source case reasoned from a local copy cut to about two thirds of
its length; the full input in the trace store showed the missing fact at once. *Test:* the report
names the store, the size match and the flags before the first root is named.

### RC-4 Quote the objection (LLM)
**Rule.** Quote the model's own stated reason (reasoning text, final reply) and its tool calls on
the failing turn, and name the exact input fact it objected to. Keep three lines apart: what the
code **decided** (RC-2), what the model was **told** about it (RC-3), and what the model then
**judged**.
- **Trigger:** after RC-3, on the failing run and at least one working run.
- **Input:** run ids. **Output:** the quotes and the decided / told / judged lines.
- **Prevents:** guessing the model's motive; placing the break at the model when the told line is
  where the fact went missing.
- **Evidence:** quotes with run ids; each of the three lines cites its source.

*Why:* the source case's first hypothesis blamed the message's wording; the model's own reasoning
named a different fact, and the code's decision was right while the text sent to the model left
out its basis. *Test:* the three lines exist, each with a source.

### RC-5 Diff the served inputs
**Rule.** This specialises systematic-debugging's Phase 2 ("list every difference") for a model
decision. When one instance or run works and another fails, find the working case first and diff
the two served inputs: the working case is evidence, not an anecdote. Diff the **rendered model
inputs** block by block, a failing run against a working run from each population the reporter
named, and run the identical input N times and report k of N. A decision that flips on an
identical input is evidence that the input is ambiguous or missing a fact; it is not an
explanation.
- **Trigger:** "it works elsewhere", "it worked yesterday", or a model decision that varies.
- **Input:** one failing run, working runs, RC-1's table. **Output:** the block diff; k of N;
  each difference sorted as mechanism candidate or correlate.
- **Prevents:** randomness as the explanation; a correlate (a name, a phrasing) taken for the
  mechanism; comparing only the nearest sibling; the working instance waved off as luck.
- **Evidence:** the working run's id, named before any cause; the diff with run ids; N and k.

*Why:* "the model is not deterministic" closed the source case's inquiry for an hour; a diff of
served inputs would have shown that no instance received the fact and that only names and
phrasing varied. *Test:* the working run is named before any cause is offered, the report shows
the block diff and k of N, and it never gives randomness as a cause.

### RC-6 Inventory the concept
**Rule.** Before proposing any new fact, tool, rule, prompt text or principle, list every
mechanism that already touches the concept (proofs, records, rendered lines, lookups, learned
data, earlier fixes): what it computes, where it is rendered, the condition that suppresses it,
and whether it **fired** on this event. For an earlier fix, "fired" needs two readings: its
revision is in what runs (`git merge-base --is-ancestor <fix> <running>`) and its code path
executed on the failing event (a log line, a trace span, a served field). Deployed is not fired.
The table fills principle 17's **Exists** line from the running code.
- **Trigger:** before any remedy; whenever someone says "this was fixed"; whenever a new principle
  seems to explain everything.
- **Input:** the concept (for example "who sent this") and the running revision. **Output:** the
  table, with suppression and fired columns.
- **Prevents:** a new mechanism beside an existing one that is switched off on this path;
  re-fixing what works; tool-text and prompt patches.
- **Evidence:** file and line for each mechanism; the ancestor command and its exit for each
  earlier fix; the line, span or field that shows each one fired.

*Why:* the source case's remedies proposed a new fact, then a tool-description edit, then a
general principle, while a mechanism that already rendered the missing fact sat switched off on
that path; the earlier fixes were present and fired, which, proven early, would have moved the
search to what they did not cover. *Test:* the table exists before the first remedy, with its
suppression and fired columns filled.

### RC-7 Trace the dropped fact
**Rule.** This specialises systematic-debugging's Phase 1 boundary instrumentation for a
model-driven system, where the boundary that matters is context assembly. For a fact the code
knows (RC-2) that the model was not told (RC-3, RC-4), name the hop where it is dropped (computed
→ gated → rendered → sent), the guard on that hop and the assumption the guard states, find when
the guard arrived (`git log -S '<guard text>'`) and the test that pins it. A code reading of where
the fact is dropped stays a [hypothesis] until the input actually sent on the failing turn is read
(RC-3), or requested when you cannot read it yourself. The remedy extends that mechanism and
changes that test.
- **Trigger:** RC-4's decided and told lines differ.
- **Input:** the fact and the rendered input. **Output:** the hop with file and line; the guard,
  its stated assumption and why it no longer holds; its commit and its pinning test; the sent
  input that confirms the drop, or the request for it.
- **Prevents:** blaming the model for not re-checking what the code proved; asking the model to
  re-verify a safety-floor fact (principle 22); a drop point read from code reported as traced.
- **Evidence:** file and line; the `git log -S` output; the test name; the sent input read, or
  the request for it with the claim still labelled [hypothesis].

*Why:* the source case's root was a guard that returned nothing on one-to-one messages because
"there is nothing to add"; for the sender's identity there was. *Test:* the report names the
guard's file and line, its assumption, its commit and its test, and calls the drop traced only
after the sent input is read.

### RC-8 Label the root, then fit the fix
**Rule.** Every claim carries the labels the method already uses (measurement-and-state-claims.md):
[measured] with its source, [documented] with its citation, or [hypothesis]; a claim inferred from
code but not observed is a [hypothesis] with its basis stated. "Root" or "traced" is written only
after RC-3 and RC-7; until then a durable record (incident log, observation row, commit message)
says hypothesis. Then classify the root (setup or data, code suppression, model judgement),
separate it from contributing conditions, keep a ledger of rejected hypotheses with the evidence
that refuted each, and run principle 17's fit check. A fleet count (with its instrument shown
matching a sample) explains variance, not the root. A workaround for a deadline is offered once,
labelled a workaround, apart from the diagnosis.
- **Trigger:** before every write to a durable record and every summary; before recommending a
  fix.
- **Input:** the candidate root and remedy. **Output:** labelled claims, the class, root versus
  contributing, the ledger, the fit check.
- **Prevents:** confident roots pushed and then rewritten; a challenger's framing adopted as
  proven; a workaround repeated as advice; a wording or tool-text patch called a fix; a frequency
  count offered as the cause.
- **Evidence:** a label and source on each claim; the ledger.

*Why:* in the source case one record row was rewritten three times in under an hour, each time as
the root, and a manual workaround was repeated in five replies. *Test:* each claim has a label,
the record says hypothesis until RC-3 and RC-7 are done, and the workaround appears once.

### RC-9 Close the loop
**Rule.** When an investigation ends, write its stage table (stage, who opened it, the conclusion,
the evidence used, what was wrong or missing, the move that unlocked the next stage) into the
project's record, map each lesson to RC-1 to RC-10, and record any lesson they do not cover in the
project's own method record, stated generally.
- **Trigger:** the root is measured and the fix planned, or the investigation is stopped.
- **Input:** the session's record. **Output:** the stage table; the lesson → step map; the
  uncovered lessons recorded.
- **Prevents:** the same investigation mistakes in the next session; a lesson that lives only in
  one transcript.
- **Evidence:** the table, the map, the record entry for each uncovered lesson.

*Why:* this reference was written from such a table; without one the source case's lessons would
have stayed in one session. *Test:* the table exists and every lesson maps to a step or to a
recorded uncovered lesson.

### RC-10 Brief the investigator blind
**Rule.** A brief to a second investigator or reviewer carries the symptom, the evidence locations
and the constraints, never your hypothesis or conclusion. It requires the reply to state
`full input read: yes/no, from <store>`, the model id it ran as, and a label on each claim. Your
hypothesis is tested against its independent findings afterwards.
- **Trigger:** whenever investigation work is handed off (principle 10, review-loop.md briefs).
- **Input:** symptom, evidence locations, constraints. **Output:** the brief.
- **Prevents:** an anchored investigator returning your hypothesis confirmed.
- **Evidence:** the brief as sent.

*Why:* the source case's independent investigator was handed the controller's hypothesis ("test
this") and reported that it held, after reconstructing the input instead of reading it. *Test:*
the brief holds no hypothesis and asks for the input line and the model id.

## Where this departs from systematic-debugging

1. **A flip is the finding.** Phase 1 says an issue that does not reproduce needs more data, not
   a guess. For a model decision, a flip on an identical input is itself the finding (RC-5): the
   input is ambiguous or missing a fact.
2. **One mechanism, not every layer.** `defense-in-depth.md` validates at every layer once the
   root is found. For a fact dropped before the model, the remedy extends the one mechanism where
   the fact is dropped (RC-7; review-loop.md: a check in one branch is usually the wrong shape).
3. **Rejected hypotheses are kept.** Phase 3 keeps one hypothesis at a time; RC-8 also keeps the
   rejected ones with the evidence that refuted each, so a later reader does not re-argue them.

## What stays in each project

The steps name what an executor must do, not how; each project supplies its own:
- **Full-input fetch (RC-3):** a run id in; the input as sent, its size and its truncation flags
  out.
- **Decision-record query (RC-2):** an event id in; every line logged for it, quoted, out.

Project detail (trace-store queries, hosts, log locations), investigation stage tables and
incident records stay in the project's own record.
