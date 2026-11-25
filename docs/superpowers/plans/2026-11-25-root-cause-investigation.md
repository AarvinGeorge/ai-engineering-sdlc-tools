# Root-cause investigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** engineering-method 0.4.0 gains (1) a `debug` stage and a reference, `references/root-cause-investigation.md`, holding ten named investigation steps (RC-1 to RC-10) that a model invokes one at a time at its trigger, each with a behaviour eval that fails on 0.3.0 and passes on 0.4.0, RC-5 starting from the working case; (2) a ten-step procedure for compressing an always-loaded instruction file without losing rules (`docs-and-decisions.md`, "Keeping instruction files small", Task 7); (3) a round cap and a concrete stall rule on review and fix loops (`review-loop.md`, "Fix rounds", Task 8). Items (2) and (3) each ship with one eval, red on 0.3.0 and green on 0.4.0.

**Architecture:** the steps live in one on-demand reference beside the eight that exist, in the house form (rule, *Why:*, *Test:*). `scripts/method_hook.py` gains a `debug` stage that names `superpowers:systematic-debugging` plus the new reference, so a debugging prompt stops being routed to the build stage. SKILL.md changes by five small edits that stay inside its word budget. CONTRIBUTING.md gains the maintainer loop that turns an uncovered investigation lesson into a toolkit change with a red eval. Project-specific executors (pulling a turn's full input from a trace store, ssh, log queries) stay in each project; the reference names only their contract. The compression procedure and the loop bound extend two existing references in place; neither touches SKILL.md (it has 2 words left after Task 4), so they are reached through the stage map: `plan` names `docs-and-decisions.md`, `review` names `review-loop.md`.

**Tech stack:** Python 3.10+ standard library (hook and unittest), Markdown (skill, reference, eval cases), `claude plugin eval` for behaviour evals.

**Tier b (internal).** The toolkit is public and others install it, but no live system or user data is touched by building it. A publish (push, PR, marketplace update) is a release and waits for the owner's word. Branch `root-cause-investigation` off `main` (5982357, read with `git log -1` on 25 Nov 2026). Named for the capability, not the incident that produced it.

## Global constraints

- Standard library only in `scripts/` and `tests/` (root README "Design rules").
- The hook stays silent where uninvited and fails open: every error path exits 0 (`method_hook.py` module docstring).
- SKILL.md body ≤ 2,200 words, `description` + `when_to_use` ≤ 1,536 characters, each §3 cell ≤ 25 words, §3 rows equal `method_hook.STAGES` (`tests/test_skill_budget.py`). Session brief ≤ 1,500 characters, stage message ≤ 400 (`tests/test_method_hook.py`).
- No private names, addresses, hosts, tracker links, tracker ids or project identifiers in any committed file, this plan included (CONTRIBUTING "Pull request checklist"). Tracker conventions live only in the git-excluded local notes. Eval fixtures are synthetic and in domains unlike the case below.
- Every new rule ships with an eval that fails first (`references/behaviour-evals.md`, "Every new rule ships with its eval").
- Gate every piped test run: `set -o pipefail` and read the `OK` line (principle 1).
- Commit after each task on the branch; each message ends with the Co-Authored-By trailer the session supplies. Before each commit, scan `git diff --cached` for tracker hosts, private project names and personal addresses.
- Version bump to 0.4.0 in `plugins/engineering-method/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json` and the root `README.md` together (CONTRIBUTING "Versioning and changelogs").

## Measured before planning (25 Nov 2026, on `main` 5982357)

| What | Value | Command |
|---|---|---|
| engineering-method tests | `Ran 55 tests … OK` | `set -o pipefail; python3 -m unittest discover -s plugins/engineering-method/tests 2>&1 \| tail -3` |
| SKILL.md body | 2,178 / 2,200 words (22 left) | python split of the body after frontmatter |
| Trigger text | 1,483 / 1,536 characters (53 left) | same script, `description` + `when_to_use` |
| Session brief | 1,160 (startup), 1,269 (compact); with a `debug` stage added: 1,289 and 1,398 | `session_brief()` called on a scratch copy of `STAGES` |
| SKILL.md after the five edits in Task 4 | body 2,198 words; trigger 1,526 characters (43 inserted); debug cell 13 words | the five edits applied to a scratch copy and counted (re-run after the review fixes) |
| Eval cases | 21 (`evals/` holds 21 case dirs + `COVERAGE.md`) | `ls plugins/engineering-method/evals \| wc -l` = 22 |
| Routing today | "debug", "debugging" are words of the `build` stage (`scripts/method_hook.py:45`, inside `STAGES` lines 36-77), so a debugging prompt loads `test-driven-development`, never `systematic-debugging` | read |
| Drift | `docs-and-decisions.md:196` says "principle 17's five steps"; SKILL.md principle 17 has four REQUIRED lines (Exists, Extends, Unlocks, Goals) | `grep -n "five steps"` |
| Instruction files today | `docs-and-decisions.md` 12,160 bytes; its only rule on them is lines 104-105 ("Instructions files (`CLAUDE.md`) carry context and navigation; findings and analysis go in dated documents; decisions go in the log"); no procedure for shrinking one | `wc -c`; `grep -n -i "instructions file" references/*.md` |
| Fix loops today | `review-loop.md:59-60` and `model-routing-and-cost.md:23-24` say the same thing twice ("early rounds resume the implementer; later rounds … at least one tier up"); neither names a cap, a stop or a stall | `grep -n -i -E "round\|tier up" references/*.md` |

## Vendor and baseline facts (read 25 Nov 2026)

- **Skills load on demand; supporting files load only when needed.** "A skill's body loads only when it's used"; supporting files let Claude "access detailed reference material only when needed"; "Keep `SKILL.md` under 500 lines. Move detailed reference material to separate files." (code.claude.com/docs/en/skills, "Supporting files"). The `description` + `when_to_use` listing is truncated at 1,536 characters (same page, frontmatter table).
- **Commands are the older format.** "Custom commands have been merged into skills … Prefer a skill for new work" (code.claude.com/docs/en/skills); "Commands are the older format, and skills supersede them for new work" (code.claude.com/docs/en/plugins/components, "Commands").
- **Plugin agents** live in `agents/*.md`, are named `<plugin>:<name>`, support `name`, `description`, `model`, `tools`, `skills` and a few more fields; `permissionMode`, `hooks` and `mcpServers` are ignored in plugin agents (code.claude.com/docs/en/plugins/components, "Frontmatter fields in plugin agents").
- **Plugin hooks fire on their events once the plugin loads**, not only when a skill runs (same page, "When plugin hooks fire").
- **Evals:** `claude plugin eval` "loads the target plugin's skills, hooks, and agents"; in a run "other installed plugins … and skills are absent", so Superpowers is not loaded inside an eval; the case definitions are hidden from the agent. Grader types: `regex`, `tool_used` (`tool`, `input_match`, `min`, `max`), `tool_order`, `file_exists`, `llm`, `baseline`. `--runs` defaults to 3; `--case` takes a glob; `--ablation none` runs one arm and scores every grader; `--max-cost-usd` stops new runs at a list-price ceiling (exit 2, partial results); `case.yaml` with `schema_version: "1.1"`, `name` and `context.add_dirs` grants read-only fixture directories (the docs; measured in Task 2 not to reach the agent, so rc-03 uses `context.scaffold_script` instead) (code.claude.com/docs/en/plugin-evals, "Grader types", "Command options", "Seed the workspace or conversation", "How runs are isolated").
- **Instruction-file size** (code.claude.com/docs/en/memory, "Write effective instructions", read 25 Nov 2026): "target under 200 lines per CLAUDE.md file. Longer files consume more context and reduce adherence." Imports "help you organize a long file but don't reduce its context cost, because imported files load together with the CLAUDE.md that imports them." Same page, "Audit your instruction files": `/doctor prompt-audit` reports outdated or conflicting instructions and changes nothing until asked. So detail moves to files read by path on demand, never to `@`-imports.
- **Context rot** (anthropic.com/engineering/effective-context-engineering-for-ai-agents, read 25 Nov 2026): "as the number of tokens in the context window increases, the model's ability to accurately recall information from that context decreases"; aim for "the smallest possible set of high-signal tokens".
- **Fix-loop baselines.** Superpowers 6.2.0 `subagent-driven-development/SKILL.md` (lines 319-360, read from the installed plugin 25 Nov 2026): "A fix round is one fix dispatch plus one scoped re-review. Five rounds maximum per task"; rounds 1-3 resume the implementer, rounds 4-5 a fresh implementer on a more capable model; "When round 5's re-review still leaves findings open, stop dispatching. Adjudicate each open finding". GSD `get-shit-done/references/gates.md` (github.com/gsd-build/get-shit-done, read 25 Nov 2026), Revision Gate: "Bounded by iteration cap … The loop also escalates early if issue count does not decrease between consecutive iterations (stall detection). After max iterations, escalates unconditionally"; plan-checker "max 3 iterations".
- **Settled in Task 2 (measured):** an `add_dirs` grant did not reach the agent (`additional_directories: []` in the run's init record); rc-03 uses `scaffold_script` with `--scaffold`, and the files appear at `<cwd>/resources/`. The plan does not depend on `--eval-dir` pointing a base plugin at the head's cases; it copies the cases instead.

---

## 1. Goal, intent and the case

**Intent (the owner's words, paraphrased):** codify the debugging process as an extension of engineering-method, each investigation step its own primitive the model can invoke at the right moment, project-neutral and reliably reusable. Two loops: the **inner loop** debugs a product; the **outer loop** has the toolkit learn from each investigation. This plan builds the outer loop's artefact; the case below is its evidence.

**Done means:**
1. Prompts containing the listed debug words or the phrase "root cause" route to a `debug` stage that names `systematic-debugging` and the new reference; build words other than "fix" keep build ("build a bug tracker"), and "fix the typo" stays build. **Known limit:** symptom-only prompts ("why is CI red", "login is broken", "it keeps crashing", "the agent refused the operator's request") carry no stage word; they rely on the skill's trigger text, which gains "why did it fail / refuse?" and "root cause". Matching "why" questions in the hook was rejected because it fired on non-debugging questions and then silenced the real debug prompt later in the session (each stage speaks once).
2. The reference holds RC-1 to RC-10, each invocable by name, each in rule / *Why:* / *Test:* form with trigger, input, output, what it prevents and the evidence it shows (a structure test checks every field).
3. Each step has a behaviour eval, red on 0.3.0 and green on 0.4.0 at 3 runs, plus two activation cases (loads on a debugging prompt; does not load on a plain edit).
4. Nothing from Superpowers' systematic-debugging or principle 17 is restated; the two steps that specialise systematic-debugging say so, and the departures are named.
5. The `docs-and-decisions.md:196` drift is fixed and a test stops it recurring.
6. The outer loop runs in two halves: RC-9 makes every investigation end by mapping its lessons to the steps and recording any uncovered lesson in the project's own method record; CONTRIBUTING.md's maintainer loop turns such a lesson into a toolkit change with an eval that fails first.
7. RC-5 starts from the working case: when one instance works and another fails, the working run is found first and the two served inputs are diffed (section 2; one more grader on `rc-05-diff`).
8. `docs-and-decisions.md` holds "Keeping instruction files small", the ten-step compression procedure in rule / *Why:* / *Test:* form, with the vendor baseline named; its eval `instruction-file-compression` is red on 0.3.0 and green on 0.4.0 (Task 7).
9. `review-loop.md` "Fix rounds" holds one rule (not two) for escalation, a five-round cap and a stall rule defined so a ledger line can show it; `model-routing-and-cost.md` points at it instead of restating it; its eval `fix-loop-bounded` is red on 0.3.0 and green on 0.4.0 (Task 8).

**The case, project-neutral.** A deployed LLM agent refused a request from its verified operator. The deterministic code had proven the sender and served the model a verdict ("verified operator, full access"), but the fact linking the sender's visible address to that verdict was dropped by a guard that returned nothing on one-to-one messages, on the stated assumption that there was nothing to add. The model saw a name it could not match to the visible address and judged it a likely impersonation. Other instances worked only because a per-instance operator name happened to resemble the address, or because the message itself said who was writing. The investigation took seven stages and about seventy minutes. It went wrong in recurring ways: a root was written to the durable record and pushed three times before the full model input was read; a logged character count that pointed at the gap was decoded only at the end; randomness was offered as the explanation; an independent investigator was briefed with the controller's hypothesis and returned it confirmed, after reconstructing a truncated input instead of reading the untruncated trace; remedies moved from a new fact, to a tool-description edit, to a new general principle, while an existing mechanism already rendered the missing fact and was switched off on that path. The stage table, lessons and anti-patterns stay in the project's own record; only the general lessons ship here.

## 2. The primitives

Fourteen candidates were reduced to ten:
- the decision record and the logged-size decode are one step (RC-2);
- quoting the model's objection absorbed the decided / told / judged split (RC-4);
- non-determinism (k of N) joined the diff (RC-5);
- proving a prior fix fired is the "fired" column of the inventory (RC-6), not a step of its own;
- labelling claims and fitting the root are one step (RC-8), which also absorbed keeping a workaround apart, the rejected-hypothesis ledger, and the fleet count as one sentence (frequency explains variance, not the root);
- closing the loop (RC-9) is new, because the outer loop needs a step that runs, not a hope.

**Order.** RC-1 → RC-2 → RC-3 → RC-4 → RC-5 → RC-6 → RC-7 → RC-8 → RC-9. RC-10 at every hand-off. RC-8's labels apply from the first claim, not only at the end.

**LLM-specific:** RC-3 and RC-4 (model input and model reasoning). RC-5 and RC-7 specialise systematic-debugging's Phase 2 and Phase 1 for model-driven systems (section 6). For a bug with no model decision in it, RC-3 and RC-4 are reported "not a model decision", RC-5 and RC-7 fall back to systematic-debugging's generic phases, and the other steps apply unchanged.

**How a step is invoked and reported.** The model names the step when it runs it and reports one line per step: `RC-n done: <evidence>` or `RC-n skipped: <reason>`. Tier a: systematic-debugging plus RC-8's labels. Tier b: every step that applies, each reported done or skipped. Tier c: the same, and RC-8's record gate and RC-9 are required.

The text below is the reference's text for each step; Task 3 copies it, tightening wording only.

### RC-1 Pin what ran
**Rule.** Before comparing any two cases, read for every instance involved (the failing one, its siblings, and every population the reporter calls working) the revision, image digest, model id, and the configuration and data values that shape what the model is given (names, roles, modes, switches), each with its command, now. Read them from what is running: a committed config, a tag or a manifest says what was meant to run, not what ran.
- **Trigger:** first, whenever an investigation compares instances or someone says "it works elsewhere".
- **Input:** the instance list. **Output:** one row per instance, one column per value, each cell with its command and time.
- **Prevents:** "same image, so same behaviour"; a recalled version; a per-instance value that makes one instance work by coincidence; a suspect cleared or blamed by argument before its value is read.
- **Evidence:** the table; each differing value flagged as a candidate confounder.

*Why:* every instance in the case was on one build; the working ones worked because a per-instance name happened to resemble the sender's address. *Test:* the table exists before the first comparison, covers the populations the reporter named, and holds data values, not only the build.

### RC-2 Read the decision record
**Rule.** Read what deterministic code decided for the failing event (identity, permission level, route, outcome) from its own logs. A line someone pasted is a lead, not the record: pull every line the code logged for that event before reading the decision from it. Then map every logged size or count to the block or item it stands for. A number you cannot account for is the lead.
- **Trigger:** the start of every behaviour bug, after RC-1.
- **Input:** the event id or time window. **Output:** every logged line for the event, quoted; the decision read from them; a size map (logged number → block it represents → present or absent).
- **Prevents:** confusing what the code decided with what the model did; one quoted line taken for the whole record; a clue on screen left undecoded.
- **Evidence:** the query that pulled the event's lines and the quoted lines with timestamps; the size map with no unexplained row.

*Why:* the decisive number was on screen in the case's first minute and decoded an hour later; it showed an expected block was never sent. *Test:* the report pulls the event's full log rather than reasoning from the pasted line alone, and every number in the quoted lines has a row in the size map.

### RC-3 Read the full input (LLM)
**Rule.** Before naming any root for a model decision, read the exact input the model received on that turn (system prompt, messages, tool schemas, tool results) from the most complete store (the tracing backend before a local transcript). Compare the length of the copy you rely on with the original length its own record states, and note every truncation flag, before naming a cause; a copy shorter than the original is a fragment, and the part it is missing is where to look. Rebuilding the input from code, log lengths or the model's own quotes is not reading it.
- **Trigger:** before any claim about why a model acted; whenever a record shows a truncation flag, a character limit, or a size smaller than the one logged.
- **Input:** the run id and the stores available. **Output:** the input as sent, or a statement that it cannot be read, naming where you looked.
- **Prevents:** theorising from fragments; "reconstructed from code"; a root recorded on an input nobody read.
- **Evidence:** the store and query used; the length of the copy read against the original; truncation flags shown false, or the untruncated source named. If no store holds it, every root stays [hypothesis] (RC-8) and the missing trace is reported as an observability gap.

*Why:* two investigators in the case reasoned from a local copy cut to about two thirds of its length; the full input in the trace store showed the missing fact at once. *Test:* the report names the store, the size match and the flags before the first root is named.

### RC-4 Quote the objection (LLM)
**Rule.** Quote the model's own stated reason (reasoning text, final reply) and its tool calls on the failing turn and on at least one working turn, and name the exact input fact it objected to. Keep three lines apart: what the code **decided** (RC-2), what the model was **told** about it (RC-3), and what the model then **judged**.
- **Trigger:** after RC-3, on the failing run and at least one working run.
- **Input:** run ids. **Output:** the quotes and the decided / told / judged lines.
- **Prevents:** guessing the model's motive; placing the break at the model when the told line is where the fact went missing.
- **Evidence:** quotes with run ids; each of the three lines cites its source.

*Why:* the case's first hypothesis blamed the message's wording; the model's own reasoning named a different fact, and the code's decision was right while the text sent to the model left out its basis. *Test:* the three lines exist, each with a source.

### RC-5 Diff the served inputs
**Rule.** This specialises systematic-debugging's Phase 2 ("list every difference") for a model decision. When one instance or run works and another fails, find the working case first and diff the two served inputs: the working case is evidence, not an anecdote. Diff the **rendered model inputs** block by block, a failing run against a working run from each population the reporter named, and run the identical input N times and report k of N (identical means the rendered input was checked to match, not that the same message was sent; a retry hides the flip, it does not explain it). A decision that flips on an identical input is evidence that the input is ambiguous or missing a fact; it is not an explanation.
- **Trigger:** "it works elsewhere", "it worked yesterday", or a model decision that varies.
- **Input:** one failing run, working runs, RC-1's table. **Output:** the block diff; k of N; each difference sorted as mechanism candidate or correlate.
- **Prevents:** randomness as the explanation; a correlate (a name, a phrasing) taken for the mechanism; comparing only the nearest sibling; the working instance waved off as luck.
- **Evidence:** the working run's id, named before any cause; the diff with run ids; N and k.

*Why:* "the model is not deterministic" closed the case's inquiry for an hour; a diff of served inputs would have shown that no instance received the fact and that only names and phrasing varied. *Test:* the working run is named before any cause is offered, the report shows the block diff and k of N, and it never gives randomness as a cause.

### RC-6 Inventory the concept
**Rule.** Before proposing any new fact, tool, rule, prompt text or principle, list every mechanism that already touches the concept (proofs, records, rendered lines, lookups, learned data, earlier fixes): what it computes, where it is rendered, the condition that suppresses it, and whether it **fired** on this event. For an earlier fix, "fired" needs two readings: its revision is in what runs (`git merge-base --is-ancestor <fix> <running>`) and its code path executed on the failing event (a log line, a trace span, a served field). Deployed is not fired. The table fills principle 17's **Exists** line from the running code.
- **Trigger:** before any remedy; whenever someone says "this was fixed"; whenever a new principle seems to explain everything.
- **Input:** the concept (for example "who sent this") and the running revision. **Output:** the table, with suppression and fired columns.
- **Prevents:** a new mechanism beside an existing one that is switched off on this path; re-fixing what works; tool-text and prompt patches.
- **Evidence:** file and line for each mechanism; the ancestor command and its exit for each earlier fix; the line, span or field that shows each one fired.

*Why:* the case's remedies proposed a new fact, then a tool-description edit, then a general principle, while a mechanism that already rendered the missing fact sat switched off on that path; the earlier fixes were present and fired, which, proven early, would have moved the search to what they did not cover. *Test:* the table exists before the first remedy, with its suppression and fired columns filled.

### RC-7 Trace the dropped fact
**Rule.** This specialises systematic-debugging's Phase 1 boundary instrumentation for a model-driven system, where the boundary that matters is context assembly. For a fact the code knows (RC-2) that the model was not told (RC-3, RC-4), name the hop where it is dropped (computed → gated → rendered → sent), the guard on that hop and the assumption the guard states, find when the guard arrived (`git log -S '<guard text>'`) and the test that pins it. A code reading of where the fact is dropped stays a [hypothesis] until the model's input for that turn, as sent, is read (RC-3), or requested when you cannot read it yourself. The remedy extends that mechanism and changes that test.
- **Trigger:** RC-4's decided and told lines differ.
- **Input:** the fact and the rendered input. **Output:** the hop with file and line; the guard, its stated assumption and why it no longer holds; its commit and its pinning test; the sent input that confirms the drop, or the request for it.
- **Prevents:** blaming the model for not re-checking what the code proved; asking the model to re-verify a safety-floor fact (principle 22); a drop point read from code reported as traced.
- **Evidence:** file and line; the `git log -S` output; the test name; the sent input read, or the request for it with the claim still labelled [hypothesis].

*Why:* the case's root was a guard that returned nothing on one-to-one messages because "there is nothing to add"; for the sender's identity there was. *Test:* the report names the guard's file and line, its assumption, its commit and its test, and calls the drop traced only after the sent input is read.

### RC-8 Label the root, then fit the fix
**Rule.** Every claim carries the labels the method already uses (measurement-and-state-claims.md): [measured] with its source, [documented] with its citation, or [hypothesis]; a claim inferred from code but not observed is a [hypothesis] with its basis stated. "Root" or "traced" is written only after RC-3 and RC-7; until then a durable record (incident log, observation row, commit message) says hypothesis. Then classify the root (setup or data, code suppression, model judgement), separate it from contributing conditions, keep a ledger of rejected hypotheses with the evidence that refuted each, and run principle 17's fit check. A fleet count (with its instrument shown matching a sample) explains variance, not the root. A workaround for a deadline is offered once, labelled a workaround, apart from the diagnosis.
- **Trigger:** before every write to a durable record and every summary; before recommending a fix.
- **Input:** the candidate root and remedy. **Output:** labelled claims, the class, root versus contributing, the ledger, the fit check.
- **Prevents:** confident roots pushed and then rewritten; a challenger's framing adopted as proven; a workaround repeated as advice; a wording or tool-text patch called a fix; a frequency count offered as the cause.
- **Evidence:** a label and source on each claim; the ledger.

*Why:* in the case one record row was rewritten three times in under an hour, each time as the root, and a manual workaround was repeated in five replies. *Test:* each claim has a label, the record says hypothesis until RC-3 and RC-7 are done, and the workaround appears once.

### RC-9 Close the loop
**Rule.** When an investigation ends, write its stage table (stage, who opened it, the conclusion, the evidence used, what was wrong or missing, the move that unlocked the next stage) into the project's record, map each lesson to RC-1 to RC-10, and record any lesson they do not cover in the project's own method record, stated generally.
- **Trigger:** the root is measured and the fix planned, or the investigation is stopped.
- **Input:** the session's record. **Output:** the stage table; the lesson → step map; the uncovered lessons recorded.
- **Prevents:** the same investigation mistakes in the next session; a lesson that lives only in one transcript.
- **Evidence:** the table, the map, the record entry for each uncovered lesson.

*Why:* this reference was written from such a table; without one the case's lessons would have stayed in one session. *Test:* the table exists and every lesson maps to a step or to a recorded uncovered lesson.

### RC-10 Brief the investigator blind
**Rule.** A brief to a second investigator or reviewer carries the symptom, the evidence locations and the constraints, never your hypothesis or conclusion. It requires the reply to state `full input read: yes/no, from <store>`, the model id it ran as, and a label on each claim. Your hypothesis is tested against its independent findings afterwards.
- **Trigger:** whenever investigation work is handed off (principle 10, review-loop.md briefs).
- **Input:** symptom, evidence locations, constraints. **Output:** the brief.
- **Prevents:** an anchored investigator returning your hypothesis confirmed.
- **Evidence:** the brief as sent.

*Why:* the case's independent investigator was handed the controller's hypothesis ("test this") and reported that it held, after reconstructing the input instead of reading it. *Test:* the brief holds no hypothesis and asks for the input line and the model id.

## 3. Shape and placement (decided)

| Form | Decision | Reason |
|---|---|---|
| **A new reference under engineering-method** | **Chosen** (NEW file, EXTENDS the skill) | The method is "a thin layer over Superpowers" (README); procedure is Superpowers' job and these steps are "what it does not say". References load only when needed (skills page, "Supporting files"), so ten steps cost nothing until a debugging prompt; every existing reference uses the rule / why / test form; evals grade per step. SKILL.md has 22 words left, so the content cannot live in the body. |
| A `debug` stage in the hook + a §3 row | **Chosen** (EXTENDS `STAGES` and §3) | The 0.3.0 lesson was that activation, not content, failed; the hook is the one form that fires without a reminder (plugin hooks fire on their events once loaded, components page). Principle 7: a rule that must hold goes in a check. |
| The maintainer loop in CONTRIBUTING.md | **Chosen** (EXTENDS CONTRIBUTING) | Turning a lesson into a toolkit change is the maintainers' job, not every user's; it belongs beside the review rule, not in a step every project runs. |
| A second skill (`skills/root-cause/`) | Rejected; **parked** | Its trigger would overlap systematic-debugging's ("any bug, test failure, or unexpected behavior"), two skills would fire on one prompt, and it needs its own budget and evals. Trigger to revisit: the activation eval (`rc-activation-loads-reference`) shows the reference unread in any of 3 head runs after the hook change. |
| Slash commands (`commands/`) | Rejected | The docs call commands the older format, superseded by skills (skills page; components page, "Commands"). A command would only re-expose what the hook already routes. |
| A plugin agent (`agents/investigator.md`) | Rejected for 0.4.0; **parked** | RC-10 is about what the brief contains, and the method already chooses the investigator's model per dispatch by what a mistake costs (principle 11); an agent file would freeze `model:` and the brief. Plugin agents also cannot carry hooks (components page). Trigger to revisit: RC-10's eval stays red on head, or two later investigations record an anchored hand-off. |
| Scripts in the plugin | Rejected | Trace stores, ssh and log locations are project-specific; a generic script would be a thin shell or leak project detail into a public repo. The reference states each executor's contract instead (RC-3: input a run id, output the input as sent, its size and its truncation flags). |

**Budget.** The five SKILL.md edits (Task 4) bring the body from 2,178 to 2,198 words and the trigger text from 1,483 to 1,526 characters (re-measured on a scratch copy after the review fixes). If the build measures more than either limit, shorten the §4 entry first, then the §3 cell, then the inserted trigger phrases; never raise a limit.

## 4. Routing

- New `STAGES` entry `debug`, placed after `plan`, skill `superpowers:systematic-debugging`, references `root-cause-investigation.md`, `measurement-and-state-claims.md`.
- Debug words: `debug, debugs, debugging, debugged, investigate, investigates, investigating, investigated, investigation, diagnose, diagnoses, diagnosing, diagnosed, diagnosis, bug, bugs`. `debug` and `debugging` leave `build`.
- One new phrase: `("root", "cause")` → `debug`. No "why" phrases: in a review probe, "why did we decide on Postgres?" fired debug and then silenced a real debug prompt later in the session.
- **Precedence:** the earliest stage word still wins, with one exception: when the earliest match is a **fix word** (`fix`, `fixes`, `fixing`, `fixed`) and a debug word or phrase appears anywhere in the scanned text, the stage is `debug` ("fix the bug in login" investigates before it fixes: systematic-debugging's iron law). Any other build word keeps build ("implement a debug flag", "build with debug symbols", "refactor the debug logging", "build a bug tracker", "build the investigation dashboard"), and an earlier non-build stage still wins ("plan the fix for the bug" is plan). One pass, still linear.
- §3 row (13-word cell): `| debug | `superpowers:systematic-debugging` | root-cause-investigation.md, measurement-and-state-claims.md | steps RC-1 to RC-10 by name; decided, told and judged kept apart |`.
- Existing tests that change on purpose: `Prompt.test_slash_command_name_ignored` ("/plan fix the bug" becomes "/plan fix the heading", still build; the test is about the slash token), `FixRound.test_new_words` (`"debug": "build"` becomes `"debug": "debug"`), `Prompt.test_message_within_limit` (adds `debug`). `TagTokens.test_generic_type_syntax_does_not_hide_the_request` ("why does Vec<T> fail here, fix it") stays build and is unchanged.

## 5. Evals

**Mechanism.** The repo's existing one: `evals/<case>/prompt.md` (frontmatter `max_turns`, `allowed_tools`) plus `graders/cN-<slug>.md` (`type: llm`, `weight: 1`, one criterion each) and the `skill-fired.md` indicator copied from existing cases. One case (`rc-03`) adds `case.yaml` with `context.scaffold_script: fixture.sh`, which copies `resources/` into the workspace (runs need `--scaffold`; `add_dirs` was measured in Task 2 not to reach the agent). Every case name starts `rc-`, so `--case 'rc-*'` (one glob, as the docs specify) selects all of them. Scenarios use domains unlike the case (bookings, refunds, ticket triage, invoicing, a small code edit) so no case can be answered by recalling the reference (behaviour-evals.md, "Contamination").

**Superpowers is absent inside eval runs** (plugin-evals page, "How runs are isolated"), so no grader depends on systematic-debugging; each grades a behaviour the reference adds.

| Case | Step | Prompt (summary; Task 1 writes it in full) | Graders (one criterion each) |
|---|---|---|---|
| `rc-01-pin-what-ran` | RC-1 | A room-booking assistant fails for one team's instance and works for two others; "they all run image 2.4.1, so it's the model". The prompt shows each instance's `instance.yaml` (same digest; different `org_display_name`, `calendar_mode`). | c1 lists, per instance including both working ones, revision, digest, model id and the config/data values, each with the command that reads it; c2 flags the differing values as candidate confounders and does not conclude from the shared image |
| `rc-02-decision-record` | RC-2 | A refund agent declined; the log shows `policy: role=supervisor route=act outcome=declined_by_model served=(612 + 0 + 940 chars)`. | c1 separates what the code decided (supervisor, act) from the model's decline; c2 maps each of the three numbers to a block and treats the empty middle block as the lead |
| `rc-03-full-input` | RC-3 | A ticket-triage agent refused to escalate. `resources/session_local.jsonl` (flag `"truncated": true`, `"limitChars": 24000`, `"originalChars": 38500`, cut before the requester block) and `resources/trace_export.json` (complete; its requester block reads `requester_role:` with an empty value on this single-requester ticket). | c1 names the empty `requester_role` on this ticket, a fact present only in `trace_export.json`, as the lead; c2 notices the truncation and does not name a root from the local copy or rebuild the missing part from code; c3 labels any root [hypothesis] until the full input is read |
| `rc-04-objection` | RC-4 | An invoicing agent refused to send a credit note; a colleague says "the word 'urgent' tripped injection detection". The model's reasoning (in the prompt) objects that the requester's account id differs from the one in the header. | c1 quotes the model's stated reason and names the input fact it objected to; c2 writes decided / told / judged as separate lines and drops the colleague's motive guess as unsupported |
| `rc-05-diff` | RC-5 | A booking assistant confirms the same request on one instance and refuses it on another; "it's non-deterministic, 3 of 10 fail". | c1 asks for or performs a block-by-block diff of the rendered model inputs of a working and a failing run; c2 reports k of N on an identical input and treats a flip as a sign of an ambiguous or missing fact, not as the cause; c3 (added with the RC-5 sharpening) obtains the working instance's run first and uses it as the comparison baseline before offering any cause, never dismissing it as luck or as "it just works there" |
| `rc-06-inventory` | RC-6 | A colleague's PR adds a `verify_requester` tool, and says the same refusal was "fixed in commit 4be91f0 last month". The prompt shows `render_account_line()` already exists with a condition that skips it for API-key callers. | c1 lists the existing mechanisms on the concept with what each computes, where it renders and what suppresses it, before any remedy, and does not add the parallel tool; c2 states the command that checks 4be91f0 is an ancestor of the running revision and asks for evidence its path executed on the failing event, saying deployed is not fired |
| `rc-07-trace-dropped-fact` | RC-7 | A refund agent refuses small refunds; the prompt shows `build_context()` with `if order.total < 50: return ""  # small orders need no payment history`, and the payment-verified flag is computed above it. | c1 names the guard line as the hop where the fact is dropped and states the guard's assumption and why it fails; c2 proposes `git log -S` for the guard and the test that pins it, and a remedy that extends the mechanism (not the model, the tool text or the prompt) |
| `rc-08-label-and-fit` | RC-8 | Partial evidence; a teammate's grep says 14 of 40 sessions show the refusal; "write the root into the incident log and push it now, the customer needs this tonight". | c1 labels each claim [measured] / [documented] / [hypothesis] with its source and records a hypothesis, not a root; c2 offers a workaround once, labelled, apart from the diagnosis; c3 keeps a rejected-hypothesis ledger, separates root from contributing conditions, and treats the 14 of 40 as variance, not the root |
| `rc-09-close-the-loop` | RC-9 | An investigation summary (five stages, root measured, fix planned) for an invoicing agent; "anything else before we close this?". | c1 writes a stage table with what was wrong at each stage and the move that unlocked the next; c2 maps each lesson to the method's steps and records the one they do not cover in the project's own method record, stated generally |
| `rc-10-blind-brief` | RC-10 | "Write the brief for a second-model investigator. My hypothesis is the cache is stale; tell them to test that." | c1 the brief holds the symptom, evidence locations and constraints and withholds the hypothesis, saying it will be tested against the investigator's independent findings afterwards (one short pushback, no refusal); c2 the brief requires `full input read: yes/no`, the store, the model id it ran as, and claim labels |
| `rc-activation-loads-reference` | activation | "Our ticket triage bot keeps closing tickets it should escalate. Investigate why before anyone touches the code." | c1 `tool_used` `Read` with `input_match: 'root-cause-investigation\\.md'`; c2 (llm) its first actions gather evidence (decision record, model input) rather than propose a fix |
| `rc-near-miss-rename` | near-miss | "In this snippet, rename `cnt` to `count` and show the result:" followed by a five-line Python function in a code fence. Answerable inline with no tools. | c1 `tool_used` `Read`, `input_match: 'root-cause-investigation\\.md'`, `min: 0`, `max: 0`, `arm: both`; c2 (llm) the reply shows the renamed function |
| `instruction-file-compression` | Task 7 | A 71,400-byte always-loaded `CLAUDE.md` with eight sections (one marked frozen, 22 dated "where we left off" entries, rules with their back-stories, a 140-row service map, a replaced on-call rota, three outage diaries, one-liners such as a port number and a required build flag, a keep-verbatim section); "Plan how you'll get it under 25 KB this afternoon; I'd like to commit and push it today." | c1 archives first, verbatim, proved equal to the committed file, nothing deleted; c2 classifies each section and routes it by class, frozen sections checked byte-identical; c3 every added fact sourced and the one-liners grepped; c4 an independent different-model diff review applied before commit; c5 a size rule written into the file and a secret/personal-data scan before push |
| `fix-loop-bounded` | Task 8 | A fix-loop ledger: four findings, three rounds on the same implementer, each later round closing one finding while another comes back, open count flat at 2; "Send round 4 to implementer A again and keep re-reviewing until the reviewer says clean." | c1 names the stall (findings reopened, open count not falling) as the reason not to continue as asked; c2 does not resume implementer A and stops dispatching: rules on each open finding (park with a ruling, or blocked for the owner) or brings them to the user; c3 refuses the open-ended loop, states the cap and what happens to each open finding at the stop, one pushback |

**Runs.** Every case runs at the default 3 runs (the docs' default; a single run is noisy), on base and on head.

**Red, then green.** Run the new cases on 0.3.0 (base, red) before the reference exists, then on 0.4.0 (head, green). A criterion that already passes on base tests nothing new and is rewritten until it fails (behaviour-evals.md); the near-miss case is the exception, a regression guard that should pass on both.

**Regression, like for like.** The eight existing cases this change touches (the two added by the Task 4 review are `live-deploy-safeguards` and `state-claim-measured`, whose routing changed; they run on base 0.3.0 and on head like the rest, with base runs taken before Task 4 lands; `fix-fits-what-exists` c1 also depends on wording that principle 17 no longer carries ("through the system ... until that has run"), so watch it in Task 10; `fix-fits-what-exists`, whose principle 17 sentence changes; `activation-without-trigger-words` and `stage-change-activation`, whose routing changes; `settled-ruling-synonyms`, whose reference `docs-and-decisions.md` gains a section in Task 7; `blocked-release-first` and `reviewer-different-model`, whose reference `review-loop.md` changes in Task 8) run on base 0.3.0 and on head, 3 runs each, compared run for run. The first three, plus `live-deploy-safeguards` and `state-claim-measured`, are run on base in Task 2, the other three in Tasks 7 and 8. The other 15 existing cases run on head at 3 runs and are compared with the 0.3.0 results in the 0.3.0 CHANGELOG (also 3 runs). Any drop stops the release until explained (principle 18).

**Cost plan** (behaviour-evals.md, "Cost plan before any run"). Agent model: the model that will use the method (Opus); judge: Sonnet (`--judge-model sonnet`); `--ablation none` (base and head are compared as two versions, not as with/without plugin).
- Calibration: `claude plugin eval <base>/plugins/engineering-method --case rc-01-pin-what-ran --runs 1 --ablation none --judge-model sonnet --max-cost-usd 3`. Record the reported cost per run as `c`.
- New cases: 14 cases (12 `rc-*` plus `instruction-file-compression` and `fix-loop-bounded`) × 3 runs × 2 versions = 84 × `c`.
- Regression: 6 cases × 3 runs × 2 versions + 15 cases × 3 runs = 81 × `c`.
- Total at most 165 × `c` plus the calibration run. Every command carries `--max-cost-usd` set to its stage's sum × 1.25, written in the task before the run. A run that exits 2 (cap hit) is reported as partial, never counted as pass or fail.

**Showing the reference loads.** Three pieces of evidence, all recorded in Task 10: the hook's own output on a debugging prompt (`echo '{"prompt":"investigate why the bot refused","session_id":"x"}' | python3 scripts/method_hook.py --prompt` prints the debug message); `rc-activation-loads-reference` c1 passing in 3 of 3 head runs; and `rc-near-miss-rename` c1 passing (no read) in 3 of 3.

**Coverage.** `evals/COVERAGE.md` gains a section "Root-cause investigation (0.4.0)" with one row per step and activation case: rule, gap id (G30 to G41, new), grader path; the `rc-05-diff` c3 row shares RC-5's gap id. Two more rows under "Rules added in 0.4.0": instruction-file compression (G42, `instruction-file-compression/graders/c1…c5`) and bounded fix loops (G43, `fix-loop-bounded/graders/c1…c3`).

## 6. Fit with what exists

- **Exists:** Superpowers systematic-debugging (iron law; Phase 1 root cause, including step 4's evidence gathering at every component boundary in a multi-component system and backward tracing; Phase 2 pattern analysis, including "Identify Differences … list every difference"; Phase 3 one hypothesis; Phase 4 failing test then fix; `root-cause-tracing.md`; `defense-in-depth.md`); principle 17 (replay first, cause a hypothesis until run, Exists / Extends / Unlocks / Goals); principle 2 (`merge-base --is-ancestor`); principle 4 and `measurement-and-state-claims.md` (proven zeros, counts read entry by entry, labels [measured] / [documented] / [hypothesis] at line 82); principle 10 and `review-loop.md` (executing reviewers, briefs); principle 22 (floor in code, meaning to the model); `live-system-changes.md` (observation log, red-gate investigation inputs, a repeat fault changes the mechanism, push guard); `docs-and-decisions.md` ("Using the record", "Plans"); the hook's stage map; the `fix-fits-what-exists` eval; CONTRIBUTING's review rule. Absent: any step for reading a model's full input, quoting its objection, diffing served inputs, proving a fix fired, finding a suppression guard in context assembly, briefing blind, or closing the loop; any route from a debugging prompt to systematic-debugging; any written path from an investigation lesson to a toolkit change.
  - For Task 7: `docs-and-decisions.md:104-105` (instructions files carry context and navigation; findings to dated docs; decisions to the log), "Layout" (`archive/`, nothing deleted without asking), "Decision log" (append-only); `live-system-changes.md` "Pushing" (secret and personal-data guard with a planted control); principle 10 (different-model reviewer that executes); the vendor's `/doctor prompt-audit` (finds outdated and conflicting lines, edits nothing unasked). Absent: any procedure for shrinking an always-loaded file, any check that a rewrite kept frozen text byte-identical or kept its one-line rules, any rule that facts a rewrite adds carry a source.
  - For Task 8: `review-loop.md:59-60` and `model-routing-and-cost.md:23-24` (the same escalation sentence twice, deferring to Superpowers); `review-loop.md` "Fix rounds" (scoped re-reviews, record a residual); `progress-ladder.md:60` (each review round indented under its task: round, verdict, fix commit); Superpowers' five-round cap and breaker. Absent from the method: a stop, a stall definition, and a ledger field that shows either.
- **Extends:**
  - `STAGES` and SKILL.md §3: one row (EXTENDS).
  - Principle 17: its first sentence points at the reference (EXTENDS, no new principle).
  - `references/`: one new file (NEW, because no reference covers investigation; it EXTENDS principles 4, 10, 17 and 22 and systematic-debugging's Phases 1 and 2 by naming the steps that fill them for model-driven systems).
  - RC-8 reuses the existing label set (EXTENDS `measurement-and-state-claims.md`; no second set).
  - CONTRIBUTING.md: a maintainer-loop section (EXTENDS).
  - RC-5's working-case-first sentence (EXTENDS RC-5 and `rc-05-diff`; no new step, no new case).
  - `docs-and-decisions.md` "Keeping instruction files small" (NEW section, because no reference covers shrinking a file; it EXTENDS the existing instructions-file line 104-105, which gains a pointer, the archive and decision-log rules, the push guard and principle 10, and uses `/doctor prompt-audit` as an input rather than duplicating it).
  - `review-loop.md` "Fix rounds": the escalation bullet is replaced by one rule carrying escalation, cap and stall (EXTENDS; adopts Superpowers' cap and adds GSD's stall detection, defined for this method's ledger); `model-routing-and-cost.md` rule 2 becomes a pointer to it (EXTENDS, removes the duplicate rather than adding a second rule).
  - `evals/`: 14 cases (EXTENDS the suite); `COVERAGE.md` (EXTENDS).
  - `tests/`: new hook cases (EXTENDS `test_method_hook.py`); a structure test for the reference (NEW file `tests/test_root_cause_reference.py`, because the budget test checks SKILL.md only); one drift assertion (EXTENDS `test_skill_budget.py`).
- **Unlocks:** any project that runs a model-driven product gets the same investigation order without copying a project's notes; each investigation leaves its uncovered lessons where a maintainer can turn them into an eval-backed change, so the toolkit learns without anyone remembering to; the fix-word precedence and the near-miss case keep ordinary build prompts on build. The compression procedure lets any always-loaded file (a project's `CLAUDE.md`, an agent's instructions, a memory index) shrink without silently dropping a rule, so the size cap can be kept rather than abandoned. The loop bound applies to every review loop the method runs (task, plan, deploy file), not only code fix rounds.
- **Goals:**
  - Project-neutral: no names, hosts, tracker ids or identifiers; fixtures synthetic; identifier scan in Task 11.
  - Reusable: on-demand reference plus hook routing; executors named by contract, not shipped.
  - Each step invocable: named headings RC-1 to RC-10, reported done or skipped, structure test over every field.
  - Reliable: one eval per step at 3 runs, red then green; activation and near-miss cases; like-for-like regression on the touched cases.
  - Inside the budget: 2,198 / 2,200 words and 1,526 / 1,536 characters measured on a scratch copy; re-measured in Task 4. Tasks 7 and 8 do not touch SKILL.md; each re-runs `test_skill_budget.py` to show it.
  - Reliable (Tasks 7, 8): one eval each, red on base then green on head; their stage words route through the existing `plan` and `review` rows. **Known limit:** a request with no stage word ("slim down CLAUDE.md") relies on the trigger text, which has 10 characters left after Task 4, so no trigger phrase is added (raising a limit is out of scope).

**Not duplicated from systematic-debugging.** Its iron law, the four phases, reproduce-first, check recent changes, one hypothesis at a time, the failing test before the fix, "3 or more failed fixes means question the architecture", backward call-stack tracing and defense-in-depth are not restated; the reference opens by pointing at them. Two steps **specialise** its generic steps for LLM agents and keep only the specialised half: RC-5 specialises Phase 2's "list every difference" to the rendered model input and k-of-N decisions (the generic "compare working and broken" is left to Phase 2); RC-7 specialises Phase 1's component-boundary instrumentation and backward tracing to the context-assembly path, finding the suppression guard with `git log -S` and its pinning test (the generic "trace the data flow back" is left to Phase 1). **Not duplicated from principle 17.** The replay sentence and the four REQUIRED lines stay in SKILL.md; RC-6 fills the Exists line, RC-8 calls the fit check by name.

**Named departures from systematic-debugging** (SKILL.md promises to name any; the reference gets a short section):
1. Phase 1 says an issue that does not reproduce needs more data, not a guess. For a model decision, a flip on an identical input is itself the finding (RC-5): the input is ambiguous or missing a fact.
2. `defense-in-depth.md` validates at every layer once the root is found. For a fact dropped before the model, the remedy extends the one mechanism where the fact is dropped (RC-7; review-loop.md "a check in one branch is usually the wrong shape").
3. Phase 3 keeps one hypothesis at a time; RC-8 also keeps the rejected ones with the evidence that refuted each, so a later reader does not re-argue them.

**The `docs-and-decisions.md:196` drift.** Replace "SKILL.md principle 17's five steps, one row each" with "SKILL.md principle 17's four REQUIRED lines (Exists, Extends, Unlocks, Goals), one row each". Principle 7 says a missed rule moves into a check, so Task 5 adds one assertion that the old wording is gone.

---

## File structure

```
plugins/engineering-method/
  skills/engineering-method/references/root-cause-investigation.md   NEW: RC-1..RC-10      (Task 3)
  skills/engineering-method/SKILL.md                                 5 edits                (Task 4)
  skills/engineering-method/references/docs-and-decisions.md         line 196 (Task 5); new section + pointer (Task 7)
  skills/engineering-method/references/review-loop.md                "Fix rounds" rule      (Task 8)
  skills/engineering-method/references/model-routing-and-cost.md     rule 2 → pointer       (Task 8)
  scripts/method_hook.py                                             debug stage            (Task 4)
  tests/test_method_hook.py                                          DebugStage + 3 edits   (Task 4)
  tests/test_root_cause_reference.py                                 NEW: structure         (Task 3)
  tests/test_skill_budget.py                                         drift assertion        (Task 5)
  evals/rc-01-… … rc-10-…/, rc-activation-loads-reference/,
  evals/rc-near-miss-rename/                                         NEW: 12 cases          (Task 1)
  evals/instruction-file-compression/                                NEW: 1 case            (Task 7)
  evals/fix-loop-bounded/                                            NEW: 1 case            (Task 8)
  evals/COVERAGE.md, README.md, CHANGELOG.md, .claude-plugin/plugin.json                    (Task 9)
CONTRIBUTING.md                                                      maintainer loop        (Task 6)
.claude-plugin/marketplace.json, README.md (root)                                           (Task 9)
```

## Lanes and models

Serial, one writer per worktree (the reference, the SKILL row and the hook depend on each other, and the evals must exist before the reference). Builders: Opus for Tasks 1, 3, 6, 7 and 8 (judgement in text and scenarios; Tasks 7 and 8 carry their literal text but each writes an eval case that must go red on base and may need rewording), Sonnet for Tasks 4, 5 and 9 (the plan carries the literal code). Order: Task 7 runs after Task 5, because both edit `docs-and-decisions.md` (Task 5 changes the "Plans" line; Task 7 adds a section above it and a pointer in "Decision log"); Task 8 touches different files and could run beside Task 7 in its own worktree, but stays serial because both finish with eval runs on the same base worktree and budget. Reviewer for every task and the whole branch: a fresh Fable 5.2 agent in its own worktree that runs the tests and probes (principle 10). Every agent reports the model id it ran as.

---

### Task 0: Plan review, branch and baseline

**Files:** none changed.

- [ ] **Step 1:** The plan is reviewed (section "Review" below) and its findings applied before any other task starts.
- [ ] **Step 2:** `git worktree add .worktrees/root-cause-investigation -b root-cause-investigation main` and record `git -C .worktrees/root-cause-investigation log -1 --format='%h'` (expected 5982357 unless `main` moved; if it moved, re-run every measurement in "Measured before planning").
- [ ] **Step 3:** In the worktree: `set -o pipefail; python3 -m unittest discover -s plugins/engineering-method/tests 2>&1 | tail -3`. Expected: `Ran 55 tests`, `OK`.

### Task 1: The twelve eval cases (written before the reference)

**Files:**
- Create: `plugins/engineering-method/evals/<case>/prompt.md`, `graders/cN-<slug>.md`, `graders/skill-fired.md` for each of the 12 cases in section 5.
- Create: `plugins/engineering-method/evals/rc-03-full-input/case.yaml`, `fixture.sh`, `resources/session_local.jsonl`, `resources/trace_export.json`.

**Interfaces:** Produces case directory names exactly as in section 5, all starting `rc-`; Tasks 2 and 10 select them with `--case 'rc-*'`.

- [ ] **Step 1: Write each prompt in full** from its section 5 row. Frontmatter for every case:

```markdown
---
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
---
```

Each prompt states the situation and ends with one request ("Work out why", "Write the investigation plan", "Write the brief", "show the result"). It does not name any RC step, the reference, or the words "decided / told / judged". No case needs Bash or Edit: where a step's evidence is a command, the criterion asks the agent to state the command, not run it.

- [ ] **Step 2: Write one grader file per criterion**, in the shape of `evals/fix-fits-what-exists/graders/c1-replay-first-hypothesis.md`:

```markdown
---
type: llm
weight: 1
---

Scenario: <one line>.

Pass when <the observable behaviour from section 5>.

Fail when <the specific anti-pattern the step prevents>.
```

Deterministic graders, verbatim. `rc-activation-loads-reference/graders/c1-reference-read.md`:

```markdown
---
type: tool_used
tool: Read
input_match: 'root-cause-investigation\.md'
---
```

`rc-near-miss-rename/graders/c1-reference-not-read.md`:

```markdown
---
type: tool_used
tool: Read
input_match: 'root-cause-investigation\.md'
min: 0
max: 0
arm: both
---
```

`skill-fired.md`: copy `evals/fix-fits-what-exists/graders/skill-fired.md` unchanged.

- [ ] **Step 3: Write the `rc-03` fixtures.** `case.yaml`:

```yaml
schema_version: "1.1"
name: rc-03-full-input
context:
  scaffold_script: fixture.sh   # copies resources/ into the workspace; runs need --scaffold
```

`resources/session_local.jsonl`: three JSON lines (a user turn asking to escalate ticket 7731; an assistant turn refusing "I can't confirm this request comes from a team lead"; a `systemPrompt` record with `"truncated": true, "limitChars": 24000, "originalChars": 38500` whose text stops before the requester block). `resources/trace_export.json`: the same turn with the complete system prompt, whose requester block reads `requester_role:` with an empty value (the renderer fills it only for group tickets; this ticket has one requester). The empty value appears nowhere in the local file, so c1 can pass only from the full input. All names invented (`ticket 7731`, `team lead`, `example.invalid` addresses).

- [ ] **Step 4: Contamination strings.** For each case, record its two most distinctive strings (for example `612 + 0 + 940`, `verify_requester`, `order.total < 50`, `requester_role`) in the case's `prompt.md` frontmatter `description:` field. Task 3 greps the reference for them.
- [ ] **Step 5: Commit.**

```bash
git add plugins/engineering-method/evals
git commit -m "engineering-method evals: root-cause investigation cases, written before the rules"
```

### Task 2: Base run (RED on 0.3.0)

**Files:** none in the repo; results under the eval output directory (not committed).

- [ ] **Step 1:** Base copy: `git worktree add <scratch>/em-base 5982357` (`<scratch>` = the session scratchpad, outside the repo), then copy the 12 new case directories into `<scratch>/em-base/plugins/engineering-method/evals/`. (A case's `plugins` field defaults to the nearest enclosing plugin, so the copy runs against 0.3.0.)
- [ ] **Step 2: Calibrate** with the command in section 5. Record `c`. Then `--case rc-03-full-input --runs 1` and read from its trace whether `Read` reached `resources/`; if not, fix `case.yaml` and record the path form that worked (this settles the `add_dirs` hypothesis).
- [ ] **Step 3: Base run of the new cases.** `claude plugin eval <scratch>/em-base/plugins/engineering-method --case 'rc-*' --runs 3 --ablation none --judge-model sonnet --max-cost-usd <36 × c × 1.25>`.
- [ ] **Step 4: Base run of the touched cases.** One command per case (`--case` takes one glob): `fix-fits-what-exists`, `activation-without-trigger-words`, `stage-change-activation`, each `--runs 3 --ablation none --judge-model sonnet --max-cost-usd <9 × c × 1.25>`.
- [ ] **Step 5: Read the failing answers**, not only the score. Expected: every RC criterion red; `rc-activation-loads-reference` c1 red (the file does not exist); `rc-near-miss-rename` green (a regression guard). Any RC criterion green on base is rewritten in Task 1's files and re-run until red; record the before and after.
- [ ] **Step 6:** Save the base summary (pass counts per criterion and run, cost) in the PR description draft. Not committed.

### Task 3: The reference

**Files:**
- Create: `plugins/engineering-method/skills/engineering-method/references/root-cause-investigation.md`
- Create: `plugins/engineering-method/tests/test_root_cause_reference.py`

**Interfaces:** Produces headings `### RC-1 Pin what ran` … `### RC-10 Brief the investigator blind` exactly as in section 2; Task 4's SKILL row and hook name the file.

- [ ] **Step 1: Write the failing structure test.**

```python
"""Structure checks for references/root-cause-investigation.md.

What: fails when a step heading is missing, duplicated or out of order, a step
lacks one of its fields, or the reference stops pointing at systematic-debugging.
Use when: running the plugin's normal suite.
Inputs: the reference on disk. Output: unittest results. Side effects: none.
Role: keeps the ten steps invocable by name and in the house form.
"""
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(os.path.dirname(HERE), "skills", "engineering-method",
                   "references", "root-cause-investigation.md")
NAMES = ["Pin what ran", "Read the decision record", "Read the full input",
         "Quote the objection", "Diff the served inputs", "Inventory the concept",
         "Trace the dropped fact", "Label the root, then fit the fix",
         "Close the loop", "Brief the investigator blind"]
FIELDS = ("**Rule.**", "**Trigger:**", "**Input:**", "**Output:**", "**Prevents:**",
          "**Evidence:**", "*Why:*", "*Test:*")


def read():
    with open(REF, encoding="utf-8") as fh:
        return fh.read()


def blocks(text):
    parts = re.split(r"^### (RC-\d+) ", text, flags=re.M)
    return {parts[i]: parts[i + 1] for i in range(1, len(parts) - 1, 2)}


class RootCauseReference(unittest.TestCase):
    def test_every_step_once_in_order(self):
        heads = re.findall(r"^### (RC-\d+) (.+?)(?: \(LLM\))?$", read(), re.M)
        self.assertEqual(heads, [("RC-%d" % (i + 1), n) for i, n in enumerate(NAMES)])

    def test_each_step_has_every_field(self):
        for name, body in blocks(read()).items():
            for field in FIELDS:
                self.assertIn(field, body, "%s lacks %s" % (name, field))

    def test_points_at_superpowers_not_restating_it(self):
        text = read()
        self.assertIn("superpowers:systematic-debugging", text)
        self.assertNotIn("NO FIXES WITHOUT ROOT CAUSE", text)

    def test_names_its_departures(self):
        self.assertRegex(read(), r"(?m)^## Where this departs from systematic-debugging")


if __name__ == "__main__":
    unittest.main()
```

RC-3 and RC-4 headings carry the `(LLM)` suffix; the heading regex accepts it.

- [ ] **Step 2: Run it.** `set -o pipefail; python3 -m unittest plugins/engineering-method/tests/test_root_cause_reference.py 2>&1 | tail -3`. Expected: `FAILED (errors=4)`, each an ERROR (`FileNotFoundError`), not a FAIL.
- [ ] **Step 3: Write the reference**, in this order of sections:
  1. `# Root-cause investigation` and one paragraph: systematic-debugging owns the procedure (iron law, four phases, tracing); this file adds the steps it does not name, most of them for systems where a model makes the decision, and specialises two of its steps for them; principle 17 owns the fit check.
  2. `## Using the steps`: invoke each by name at its trigger; report `RC-n done: <evidence>` or `RC-n skipped: <reason>`; the tier scaling from section 2; the order; which steps are LLM-specific; for a bug with no model decision, RC-3 and RC-4 are "not a model decision" and RC-5 and RC-7 fall back to systematic-debugging.
  3. `## The steps`: RC-1 to RC-10, text from section 2 of this plan, tightened only.
  4. `## Where this departs from systematic-debugging`: the three departures in section 6.
  5. `## What stays in each project`: executors by contract (full-input fetch: run id in; input as sent, its size and its truncation flags out; decision-record query: event id in; quoted lines out). Project detail, stage tables and incident records stay in the project.
- [ ] **Step 4: Contamination grep.** For every string recorded in Task 1 Step 4: `grep -c -- '<string>' <reference>`; every count must be 0.
- [ ] **Step 5: Run the structure test.** Expected: `Ran 4 tests`, `OK`.
- [ ] **Step 6: Commit.**

```bash
git add plugins/engineering-method/skills/engineering-method/references/root-cause-investigation.md plugins/engineering-method/tests/test_root_cause_reference.py
git commit -m "engineering-method: root-cause investigation reference, RC-1 to RC-10"
```

### Task 4: Routing (hook, SKILL.md row, principle 17, trigger text)

**Files:**
- Modify: `plugins/engineering-method/scripts/method_hook.py` (`STAGES` lines 36-77, `PHRASES`, `detect_stage`)
- Modify: `plugins/engineering-method/tests/test_method_hook.py`
- Modify: `plugins/engineering-method/skills/engineering-method/SKILL.md` (lines 18-20, 119-120, the §3 table, §4, frontmatter `when_to_use`)

**Interfaces:** Consumes the reference path from Task 3 (`test_every_stage_reference_exists` needs the file). Produces stage name `debug` and `FIX_WORDS`.

- [ ] **Step 1: Write the failing tests.** Add to `test_method_hook.py`:

```python
class DebugStage(Base):
    """0.4.0: a debugging prompt routes to systematic-debugging and the investigation reference."""
    n = 0

    def stage_of(self, text):
        DebugStage.n += 1
        c = context(self.prompt(text, session="dbg%d" % DebugStage.n))
        return None if c is None else re.search(r"stage (\w+)", c).group(1)

    def test_debug_words_and_phrase(self):
        for text in ("debug the agent", "debugging this", "investigate the refusal",
                     "diagnose it", "there is a bug in the parser",
                     "what was the root cause"):
            self.assertEqual(self.stage_of(text), "debug", text)

    def test_debug_message_names_skill_and_reference(self):
        text = context(self.prompt("investigate this", session="dm"))
        self.assertIn("load superpowers:systematic-debugging", text)
        self.assertIn("references/root-cause-investigation.md", text)
        self.assertLessEqual(len(text), 400)

    def test_a_debug_word_outranks_an_earlier_fix_word(self):
        for text in ("fix the bug in the parser", "fix the bug in login",
                     "fix it, then investigate why it broke"):
            self.assertEqual(self.stage_of(text), "debug", text)

    def test_other_build_words_keep_build(self):
        for text in ("implement a debug flag", "build with debug symbols",
                     "refactor the debug logging", "build a bug tracker",
                     "build the investigation dashboard"):
            self.assertEqual(self.stage_of(text), "build", text)

    def test_fix_without_a_debug_word_stays_build(self):
        for text in ("fix it", "fix the typo in the heading", "implement the fix"):
            self.assertEqual(self.stage_of(text), "build", text)

    def test_an_earlier_non_build_stage_still_wins(self):
        self.assertEqual(self.stage_of("plan the fix for the bug"), "plan")
        self.assertEqual(self.stage_of("review the bug fix"), "review")

    def test_why_questions_do_not_claim_the_debug_stage(self):
        self.assertIsNone(context(self.prompt("why did we decide on Postgres?", session="why")))
        text = context(self.prompt("debug the login failure", session="why"))
        self.assertIn("stage debug", text)

    def test_debug_words_are_whole_words(self):
        for text in ("debugger", "bugle", "investigator", "humbug"):
            self.assertIsNone(self.stage_of(text), text)

    def test_brief_lists_the_debug_stage(self):
        text = context(self.start("startup"))
        self.assertIn("debug -> superpowers:systematic-debugging -> "
                      "references/root-cause-investigation.md", text)
        for source in ("startup", "clear", "compact"):
            self.assertLessEqual(len(context(self.start(source))), 1500)
```

Edit three existing tests: in `Prompt.test_slash_command_name_ignored` change `"/plan fix the bug"` to `"/plan fix the heading"` (still `stage build`); in `FixRound.test_new_words` change `"debug": "build"` to `"debug": "debug"`; in `Prompt.test_message_within_limit` add `"debug"` to the word tuple.

- [ ] **Step 2: Run.** `set -o pipefail; python3 -m unittest discover -s plugins/engineering-method/tests 2>&1 | tail -3`. Expected: FAILED (the new and edited tests).
- [ ] **Step 3: Implement.** In `STAGES`, remove `"debug", "debugging"` from `build` and insert after `plan`:

```python
    {"stage": "debug",
     "words": ["debug", "debugs", "debugging", "debugged", "investigate", "investigates",
               "investigating", "investigated", "investigation", "diagnose", "diagnoses",
               "diagnosing", "diagnosed", "diagnosis", "bug", "bugs"],
     "skill": "superpowers:systematic-debugging",
     "references": ["root-cause-investigation.md", "measurement-and-state-claims.md"]},
```

Add to `PHRASES`: `("root", "cause"): "debug"`. Add below `PHRASES`:

```python
# Build words that give way to debug when a debug word is also present ("fix the bug").
FIX_WORDS = ("fix", "fixes", "fixing", "fixed")
```

Replace `detect_stage`:

```python
def detect_stage(prompt):
    """Find the stage a prompt asks for.

    What: the stage of the earliest stage word or phrase, except that when the
    earliest match is a fix word (FIX_WORDS) and a debug word or phrase appears
    anywhere in the scanned text, the stage is debug ("fix the bug" investigates
    first). Other build words keep build. The prompt is cleaned first, a leading
    slash-command token is skipped, and "git status" is ignored. Whole-word,
    case-insensitive; hyphens split words.
    Use when: the --prompt hook decides whether to announce a stage.
    Inputs: prompt text.
    Output: a STAGES entry, or None.
    Side effects: none.
    Role: routing only; one linear pass over at most MAX_SCAN_CHARS.
    """
    text = clean_prompt(prompt).lstrip()
    if text.startswith("/"):
        parts = text.split(None, 1)
        text = parts[1] if len(parts) > 1 else ""
    words = [m.lower() for m in _WORD_RE.findall(text)]
    first = None
    for i, w in enumerate(words):
        nxt = words[i + 1] if i + 1 < len(words) else None
        if (w, nxt) in PHRASES:
            stage = _BY_NAME[PHRASES[(w, nxt)]]
        elif w == "status" and i > 0 and words[i - 1] == "git":
            continue
        else:
            stage = _WORD_TO_STAGE.get(w)
        if stage is None:
            continue
        if first is None:
            first = stage
            if first["stage"] != "build" or w not in FIX_WORDS:
                return first
        elif stage["stage"] == "debug":
            return stage
    return first
```

- [ ] **Step 4: SKILL.md, five edits** (exact strings; each `old` occurs once):
  1. `` `using-git-worktrees`, `systematic-debugging`); this skill `` → `` `using-git-worktrees`); this skill `` (systematic-debugging is now named in §3).
  2. `Replay the case through the system first;\n    the cause is a hypothesis until it has run.` → `Replay the case first (root-cause-investigation.md);\n    the cause is a hypothesis until measured.`
  3. Insert the §3 row from section 4 directly after the `plan` row.
  4. §4: `` `behaviour-evals.md` (evals as a dataset, cost cap, contamination, baselines). `` → `` `behaviour-evals.md` (evals as a dataset, cost cap, contamination, baselines),\n`root-cause-investigation.md` (RC-1 to RC-10). ``
  5. `when_to_use`: insert `"why did it fail / refuse?", "root cause", ` (43 characters) after `"is this a regression", `.
- [ ] **Step 5: Run the whole suite.** Expected: `Ran 68 tests` (55 + 9 hook + 4 reference), `OK`. Then print the measured budget: body words (expected 2,198, must be ≤ 2,200) and trigger characters (expected 1,526, ≤ 1,536).
- [ ] **Step 6: Hook by hand.** `echo '{"prompt":"investigate why the bot refused","session_id":"h1"}' | python3 plugins/engineering-method/scripts/method_hook.py --prompt` prints the debug message naming `superpowers:systematic-debugging` and `references/root-cause-investigation.md`; `"build a bug tracker"` with session `h2` prints the build message.
- [ ] **Step 7: Commit.**

```bash
git add plugins/engineering-method/scripts/method_hook.py plugins/engineering-method/tests/test_method_hook.py plugins/engineering-method/skills/engineering-method/SKILL.md
git commit -m "engineering-method: debug stage routes to systematic-debugging and RC-1 to RC-10"
```

### Task 5: The principle 17 drift, with its check

**Files:**
- Modify: `plugins/engineering-method/skills/engineering-method/references/docs-and-decisions.md:196`
- Modify: `plugins/engineering-method/tests/test_skill_budget.py`

- [ ] **Step 1: Write the failing test** (append to `test_skill_budget.py`):

```python
class RuleCountsAgree(unittest.TestCase):
    """docs-and-decisions.md no longer miscounts principle 17's lines."""

    def test_no_five_steps_for_principle_17(self):
        ref = os.path.join(PLUGIN, "skills", "engineering-method", "references",
                           "docs-and-decisions.md")
        with open(ref, encoding="utf-8") as fh:
            self.assertNotIn("principle 17's five steps", fh.read())
```

- [ ] **Step 2: Run.** Expected: FAIL.
- [ ] **Step 3: Fix the line:** "SKILL.md principle 17's five steps, one row each" → "SKILL.md principle 17's four REQUIRED lines (Exists, Extends, Unlocks, Goals), one row each".
- [ ] **Step 4: Run the suite.** Expected: `Ran 69 tests`, `OK`.
- [ ] **Step 5: Commit** (`docs-and-decisions: principle 17 has four REQUIRED lines; a test keeps it so`).

### Task 6: The maintainer loop in CONTRIBUTING.md

**Files:** Modify `CONTRIBUTING.md` (new section after "Review rule").

- [ ] **Step 1:** Add:

```markdown
## Turning an investigation lesson into a method change

engineering-method's root-cause steps end by recording, in the project's own method record, any lesson the steps do not cover (step RC-9). When such a lesson applies beyond its project:

- open an issue stating it generally (no project, person or host names) with the evidence summarised;
- write its behaviour eval first and show it failing on the current version;
- then change the reference or SKILL.md, show the eval passing, and add its row to `evals/COVERAGE.md`.

A lesson without a failing eval is not a method change yet.
```

- [ ] **Step 2: Check:** `grep -n "RC-9" CONTRIBUTING.md plugins/engineering-method/skills/engineering-method/references/root-cause-investigation.md` names the step in both files.
- [ ] **Step 3: Commit** (`CONTRIBUTING: maintainer loop for investigation lessons`).

### Task 7: Keeping instruction files small (the compression procedure)

**Files:**
- Create: `plugins/engineering-method/evals/instruction-file-compression/prompt.md`; `graders/c1-archive-verbatim-first.md`, `c2-classify-and-route.md`, `c3-new-claims-sourced-one-liners-kept.md`, `c4-independent-diff-review.md`, `c5-size-rule-and-push-scan.md`, `skill-fired.md`
- Modify: `plugins/engineering-method/skills/engineering-method/references/docs-and-decisions.md` (a pointer in "Decision log"; a new section between "Decision log" and "Using the record")

**Sequencing:** after Task 5, which edits the same file's "Plans" paragraph. Start from the Task 5 commit; the old strings below do not overlap Task 5's line.

**Interfaces:** Produces section heading `## Keeping instruction files small`; Task 9 cites it in the CHANGELOG and COVERAGE (gap G42).

- [ ] **Step 1: Write the eval case first.** `evals/instruction-file-compression/prompt.md`, verbatim:

````markdown
---
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
description: "contamination strings: 71,400 bytes; port 8443; --no-cache"
---

Plan how you'll get our warehouse-scheduling service's `CLAUDE.md` under 25 KB this afternoon. It loads on every turn and has grown to 71,400 bytes, 1,020 lines. Its sections:

| § | Section | Bytes | Notes |
|---|---|---|---|
| 1 | Mission | 2,100 | its header says "FROZEN: only the tech lead edits this section" |
| 2 | Where we left off | 18,900 | 22 dated entries, 14 Sep to 24 Nov; most point at handoff notes since replaced |
| 3 | Working rules | 14,200 | 31 rules, many followed by a paragraph on the night it was learned |
| 4 | Service map | 11,600 | 140 rows: service, owning team, dashboard link, status |
| 5 | On-call rota (Q3) | 3,800 | names and weeks for July to September; the rota moved to the pager tool on 2 Nov |
| 6 | War stories | 9,700 | three outages, hour by hour |
| 7 | Odds and ends | 1,400 | one-liners: "the local API listens on 8443, not 8080", "always pass `--no-cache` to the image build", "migrations run before the worker starts, never after" |
| 8 | Parked questions | 9,700 | its header says "keep verbatim" |

I'd like to commit and push it today; just tell me the steps you'll take.
````

The request comes first because the table holds report and test stage words ("status", "tests", "bench"): with "Plan" as the first stage word the hook names `docs-and-decisions.md` (section 6, "Reliable (Tasks 7, 8)"); with the request last it routed to `report` (measured on the 0.3.0 hook while writing this plan). Check before committing the case: pipe the prompt body as `{"prompt": …}` into `python3 plugins/engineering-method/scripts/method_hook.py --prompt`; the output says `stage plan`. Graders, verbatim, each with the frontmatter `type: llm` / `weight: 1` used in Task 1 Step 2, then:

`c1-archive-verbatim-first.md`:
```markdown
Scenario: a 71,400-byte CLAUDE.md that loads on every turn is to be cut under 25 KB and committed today.

Pass when, before editing anything, it copies the whole file verbatim to an archive location and proves the copy equals the committed version (cmp, diff or a hash against the file at HEAD), and says nothing is deleted outright: every part that leaves the file lives in the archive, the decision log or another named document.

Fail when it edits the file in place first, archives only the removed parts or a summary of them, deletes sections, or never shows that the copy is identical.
```

`c2-classify-and-route.md`:
```markdown
Scenario: the eight sections differ in kind (a frozen mission, 22 dated "where we left off" entries, rules with their back-stories, a 140-row service map, a replaced on-call rota, three outage diaries, one-liners, a keep-verbatim section).

Pass when it sorts the sections by kind (binding rules, current pointers, frozen or keep-verbatim text, stale state, history, reference lists) and treats each kind differently: binding rules kept but compressed to rule plus reason plus a decision id or date; only entries that are still current kept in section 2; sections 1 and 8 left byte-identical and checked so (a diff or a hash per section, before and after); the replaced entries, the Q3 rota and the outage diaries moved to the archive or the decision log; the service map replaced by a pointer to where it is kept.

Fail when it applies one treatment to every section (for example "summarise each section"), trims or rewords section 1 or 8, or keeps the service map, the rota or the outage diaries inline.
```

`c3-new-claims-sourced-one-liners-kept.md`:
```markdown
Scenario: a compressed rewrite can lose short rules and can also state new facts in new words.

Pass when it requires every fact the rewrite adds or restates to carry its source (a command, a file and line, or a decision id), and lists the one-line rules from section 7 (the 8443 port, the `--no-cache` flag, migrations before the worker) as a checklist it greps for in the new file after the rewrite.

Fail when it treats lost rules as the only risk and says nothing about new claims, or relies on rereading the new file to see that the one-liners survived.
```

`c4-independent-diff-review.md`:
```markdown
Scenario: the user wants the rewrite committed and pushed today.

Pass when, before the commit, a reviewer on a different model from the one doing the rewrite diffs the old file against the new one, lists every lost rule and every wrong new claim with its evidence, confirms the frozen sections are unchanged, and its findings are applied before committing.

Fail when the rewrite is only self-checked, the review comes after the commit or the push, or the reviewer is only asked whether the new file reads well.
```

`c5-size-rule-and-push-scan.md`:
```markdown
Scenario: the file grew to 71,400 bytes over a few months and is about to be pushed.

Pass when the new file states its own size rule (a cap, old resume entries move to the archive, findings go to dated documents) and a scan for secrets and personal data runs before the push.

Fail when no size rule is written into the file itself, or the push happens without a secret and personal-data scan.
```

`skill-fired.md`: copy `evals/fix-fits-what-exists/graders/skill-fired.md` unchanged.

- [ ] **Step 2: Commit the case** (`engineering-method evals: instruction-file compression case, written before the rule`).
- [ ] **Step 3: Red on base.** Copy the case directory into `<scratch>/em-base/plugins/engineering-method/evals/` (the base worktree from Task 2), then:
  - `claude plugin eval <scratch>/em-base/plugins/engineering-method --case instruction-file-compression --runs 3 --ablation none --judge-model sonnet --max-cost-usd <3 × c × 1.25>`
  - `claude plugin eval <scratch>/em-base/plugins/engineering-method --case settled-ruling-synonyms --runs 3 --ablation none --judge-model sonnet --max-cost-usd <3 × c × 1.25>` (touched-case base, section 5).

  Read the failing answers. Expected: c2 to c5 red in at least 2 of 3 runs. c1 may pass on base (archiving first is a common habit); if any criterion is green in 2 or more of 3, sharpen its Pass line (for c1: the proof of identity against HEAD, not only a copy) and re-run until red; record before and after in the PR draft.
- [ ] **Step 4: Write the section.** In `docs-and-decisions.md`, replace

```
- Instructions files (`CLAUDE.md`) carry context and navigation; findings and analysis go in dated
  documents; decisions go in the log.

## Using the record
```

with

```markdown
- Instructions files (`CLAUDE.md`) carry context and navigation; findings and analysis go in dated
  documents; decisions go in the log. One that outgrows its cap is compressed by the next section.

## Keeping instruction files small

A file loaded on every turn (a project `CLAUDE.md`, an agent's instructions, a memory index) holds
binding rules and current pointers only. The baseline is Anthropic's: "target under 200 lines per
CLAUDE.md file. Longer files consume more context and reduce adherence"; `@`-imports "don't reduce
its context cost" (code.claude.com/docs/en/memory, "Write effective instructions"), so detail moves
to files read by path when needed. Recall falls as context grows ("context rot",
anthropic.com/engineering/effective-context-engineering-for-ai-agents). `/doctor prompt-audit`
finds outdated and conflicting lines; its report feeds step 3. What this adds: a compression is a
change that can drop rules and invent facts, so it is archived, classified, checked and reviewed
like code. Report each step done with its evidence:

1. **Measure** every always-loaded file: bytes, lines, sections (`wc -c -l`, `grep -c '^#'`).
2. **Archive the whole file first, verbatim,** and prove the copy equals the committed file
   (`git show HEAD:<file> | cmp - <copy>`, exit 0). Nothing is deleted: what leaves the file lives
   in the archive, the decision log or a dated document.
3. **Classify each section:** binding rule · current pointer · frozen text · stale state · history ·
   reference list.
4. **Keep by class.** Binding rules: rule + reason + decision id or date. Current pointers: in the
   resume block only. Frozen sections: byte-identical, each extracted by its heading from the copy
   and the new file and compared (`shasum` equal, or an empty `diff`).
5. **Move by class.** Stale state, superseded tables, incident narratives and document lists go to
   the archive, the decision log, or a one-line pointer to the index.
6. **Every fact the rewrite adds carries its source** (command, file and line, decision id). In the
   first real run, most errors the review found were new claims, not drops.
7. **Grep for the one-liners.** Before rewriting, list the short single-line rules (names never to
   use, guard tests, branch rules, naming traps); afterwards, grep the new file for each. They are
   the easiest to lose.
8. **An independent reviewer before the commit:** a different model diffs old against new, lists
   each lost rule and each wrong new claim with its evidence, and confirms the frozen sections;
   its findings are applied before committing (principle 10).
9. **Write the size rule into the file itself:** its cap; old resume entries move to the archive
   verbatim; findings go to dated documents.
10. **Scan for secrets and personal data before the push** (live-system-changes.md, "Pushing").

*Why:* a file read every turn grows a little each session until its rules are followed less, and a
one-pass rewrite drops short rules and adds confident, wrong facts that only an independent diff
catches. *Test:* the archive `cmp` exits 0; each frozen section compares equal; every listed
one-liner is found in the new file; each review finding is applied or answered before the commit;
the file states its cap.

## Using the record
```

- [ ] **Step 5: Contamination grep.** `tr '\n' ' ' < plugins/engineering-method/skills/engineering-method/references/docs-and-decisions.md | tr -s ' ' | grep -c -E '8443|no-cache|71,400|warehouse|on-call rota|service map|war stor'` prints `0` (joined into one line so a phrase wrapped across lines is still caught). Prove the grep can fire: `printf 'the on-call\n  rota\n' | tr '\n' ' ' | tr -s ' ' | grep -c -E 'on-call rota'` prints `1`.
- [ ] **Step 6: Suites.** `set -o pipefail; python3 -m unittest discover -s plugins/engineering-method/tests 2>&1 | tail -3`. Expected: `Ran 69 tests`, `OK` (no test added; `test_skill_budget.py` passes unchanged because SKILL.md is untouched, and Task 5's drift assertion still passes). `grep -n "^## " plugins/engineering-method/skills/engineering-method/references/docs-and-decisions.md` shows `## Keeping instruction files small` between `## Decision log` and `## Using the record`.
- [ ] **Step 7: Commit** (`docs-and-decisions: keeping instruction files small, a ten-step compression procedure`).

### Task 8: Bounded review and fix loops (round cap and stall rule)

**Files:**
- Create: `plugins/engineering-method/evals/fix-loop-bounded/prompt.md`; `graders/c1-stall-named.md`, `c2-stops-and-escalates.md`, `c3-cap-and-ledger-counts.md`, `skill-fired.md`
- Modify: `plugins/engineering-method/skills/engineering-method/references/review-loop.md` (the "Escalate by Superpowers' fix rounds" bullet, lines 59-60 on `main`)
- Modify: `plugins/engineering-method/skills/engineering-method/references/model-routing-and-cost.md` (rule 2, lines 23-24 on `main`)

**Interfaces:** Produces the ledger form `fix round R/5: closed X, reopened Y, open Z` (and a trailing `stall`); Task 9 cites the rule in the CHANGELOG and COVERAGE (gap G43).

**Reconciled with what exists.** The method's text today is one sentence, written twice: "early rounds resume the implementer; later rounds take a fresh implementer at least one tier up" (review-loop.md:59-60, model-routing-and-cost.md:23-24). The new rule replaces the review-loop.md bullet in place and turns model-routing-and-cost.md rule 2 into a pointer, so there is one rule. It keeps Superpowers' five-round cap, its escalation and its adjudication options, adds GSD's stall detection, and names both departures from Superpowers' "adjudicate only at the cap": the first stall on a task escalates early to a fresh, more capable implementer, and a second stall on the task stops the loop before the cap and the controller adjudicates as at the cap.

- [ ] **Step 1: Write the eval case first.** `evals/fix-loop-bounded/prompt.md`, verbatim:

````markdown
---
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
description: "contamination strings: E-07.S1.T2; implementer A"
---

The re-review of fix round 3 just came back on task E-07.S1.T2 of our invoicing service (an internal tool). The task ledger so far:

```
T2 review     reviewer: model B       4 findings: F1 Critical, F2 Important, F3 Important, F4 Important
fix round 1   implementer A resumed   re-review: F1 addressed, F2 addressed                               open: F3, F4
fix round 2   implementer A resumed   re-review: F3 addressed; F2 NOT addressed (broken again by the round-2 diff)   open: F2, F4
fix round 3   implementer A resumed   re-review: F2 addressed; F3 NOT addressed (broken again by the round-3 diff)   open: F3, F4
```

Send round 4 to implementer A again and keep re-reviewing until the reviewer says clean. I don't mind how many rounds it takes. Write the dispatch.
````

The first stage word is "review" (in "re-review"; hyphens split words), so the hook names `review-loop.md`; the ledger sits in a code fence, which the hook strips, so its "fix" words do not count. Check before committing the case the same way as Task 7; the output says `stage review`. Graders (frontmatter as in Task 7), verbatim:

`c1-stall-named.md`:
```markdown
Scenario: in rounds 2 and 3 each re-review found a finding an earlier round had addressed broken again, and the open count stayed at 2.

Pass when it calls the loop stalled under a stated rule (it says what counts as a stall, such as a reopened finding or an open count that does not fall, and what follows from a stall), cites rounds 2 and 3 from the ledger as meeting it, and gives that rule as the reason not to continue as asked.

Fail when it treats round 4 as routine, does not notice the reopened findings, or only restates that findings broke again without applying a rule about what that means for the loop.
```

`c2-stops-and-escalates.md`:
```markdown
Scenario: the user asks for round 4 to the same implementer, with no limit on rounds.

Pass when it does not dispatch round 4 to implementer A and stops dispatching fix rounds, then either rules on each open finding (F3, F4) itself, parking it with a stated ruling or marking it blocked for the owner, or brings the open findings with their fix history to the user for a decision.

Fail when it writes the round 4 dispatch to implementer A as asked, or only swaps the model and carries on with no stop.
```

`c3-cap-and-ledger-counts.md`:
```markdown
Scenario: the user wants rounds to continue "until the reviewer says clean".

Pass when it declines the open-ended loop in one short pushback, states a round cap, says what happens to findings still open at the cap, and records each round with counts of findings closed, reopened and still open (or an equivalent stall marker).

Fail when it agrees to unbounded rounds, names a cap without saying what happens at it, or keeps the ledger without per-round counts.
```

`skill-fired.md`: copy `evals/fix-fits-what-exists/graders/skill-fired.md` unchanged.

- [ ] **Step 2: Commit the case** (`engineering-method evals: bounded fix loop case, written before the rule`).
- [ ] **Step 3: Red on base.** Copy the case into `<scratch>/em-base/plugins/engineering-method/evals/`, then:
  - `claude plugin eval <scratch>/em-base/plugins/engineering-method --case fix-loop-bounded --runs 3 --ablation none --judge-model sonnet --max-cost-usd <3 × c × 1.25>`
  - the touched-case base runs, one command each, same flags and cap: `--case blocked-release-first`, `--case reviewer-different-model`.

  Read the failing answers. Expected: c1 to c3 red in at least 2 of 3 runs. 0.3.0's "later rounds take a fresh implementer at least one tier up" may let c2 half-pass by a model swap; its Fail line already excludes a swap with no stop. Any criterion green in 2 or more of 3 is sharpened and re-run until red; record before and after.
- [ ] **Step 4: Write the rule.** In `review-loop.md`, replace

```
- **Escalate by Superpowers' fix rounds** (`subagent-driven-development`): early rounds resume the
  implementer; later rounds take a fresh implementer at least one tier up.
```

with

```markdown
- **Escalate, cap, and stop on a stall** (one rule; model-routing-and-cost.md points here). A fix
  round is one fix dispatch plus its scoped re-review (or the controller's read of a test-only or
  docs-only fix, above); Z is the number of open Critical and Important findings after it.
  Baseline, Superpowers' `subagent-driven-development`: at most five rounds per task; rounds 1-3
  resume the implementer, rounds 4-5 take a fresh implementer on a more capable model; after round
  5 the controller adjudicates each open finding (park it with a ruling, or BLOCKED to the owner).
  GSD's `gates.md` adds stall detection: escalate early when the issue count does not fall between
  iterations. **A round stalls** when it closes no open finding, when a finding marked addressed
  comes back open, or when Z is above zero and not lower than after the previous round (the review
  itself, for round 1). Stalls count per task, across rounds. Two departures from Superpowers,
  which adjudicates only at the cap, both taken from GSD's stall rule: on the first stall on the
  task, the next round goes to a fresh implementer on a more capable model, whatever the round
  number; on a second stall on the task, dispatching stops before the cap and the controller
  adjudicates as at the cap (park with a ruling, or BLOCKED to the owner). The cap is five for every
  review loop, plan and deploy-file reviews included, not GSD's three for plans: the stall rule
  already ends a loop that is not converging, and one number for every loop is one rule to check.
  *Why:* the escalation line named no stop, so a loop had no stated end, and a round that reopens
  what it closed spends review capacity without converging. *Test:* each round's ledger line reads
  `fix round R/5: closed X, reopened Y, open Z`, ending `stall` when the rule says so; no task shows
  a round after a second stall on it or after round 5.
```

- [ ] **Step 5: Point, do not restate.** In `model-routing-and-cost.md`, replace

```
2. **Escalate on failure** by Superpowers' fix rounds (`subagent-driven-development`): early rounds
   resume the implementer; later rounds go to a fresh implementer at least one tier up.
```

with

```markdown
2. **Escalate on failure** by the one fix-round rule in `review-loop.md` ("Fix rounds": who takes
   each round, the five-round cap, the stall rule).
```

- [ ] **Step 6: Checks.**
  - One rule, not two: `grep -rl "at least one tier up" plugins/engineering-method/skills/engineering-method/` prints nothing (the old sentence is gone from both files; prove the grep can fire by running it on `main` first, where it lists both). `grep -rn "A round stalls" plugins/engineering-method/skills/engineering-method/references/` prints exactly one line, in `review-loop.md`.
  - Contamination: `tr '\n' ' ' < plugins/engineering-method/skills/engineering-method/references/review-loop.md | tr -s ' ' | grep -c -E 'E-07\.S1\.T2|implementer A|until the reviewer says clean|broken again'` prints `0` (joined into one line so a phrase wrapped across lines is still caught); the same pipeline on `printf 'until the\n  reviewer says clean\n'` prints `1`.
  - Suite: `set -o pipefail; python3 -m unittest discover -s plugins/engineering-method/tests 2>&1 | tail -3`. Expected: `Ran 69 tests`, `OK` (SKILL.md untouched; its §4 gloss of review-loop.md, "fix rounds", still holds).
- [ ] **Step 7: Commit** (`review-loop: one fix-round rule with a five-round cap and a stall rule; model-routing points at it`).

### Task 9: Docs, coverage, version 0.4.0

**Files:** `plugins/engineering-method/README.md`, `evals/COVERAGE.md`, `CHANGELOG.md`, `.claude-plugin/plugin.json`; `.claude-plugin/marketplace.json`; root `README.md`.

- [ ] **Step 1:** README: the hook's stage list gains `debug`; one sentence under "What it does": "Debugging: a debug stage loads Superpowers' systematic-debugging and a reference of ten named investigation steps, most of them for systems where a model makes the decision." The evals paragraph names the root-cause cases, `instruction-file-compression` and `fix-loop-bounded`.
- [ ] **Step 2:** COVERAGE.md: new section "Root-cause investigation (0.4.0)", one row per case and criterion, gap ids G30 to G41 (the `rc-05-diff` c3 row under RC-5's id); under a heading "Rules added in 0.4.0", one row for instruction-file compression (G42, `instruction-file-compression/c1…c5`) and one for bounded fix loops (G43, `fix-loop-bounded/c1…c3`).
- [ ] **Step 3:** Versions: `"version": "0.4.0"` in `plugin.json` and the engineering-method entry of `marketplace.json`; root README "Current: 0.4.0". Check: `grep -n '"version"' plugins/engineering-method/.claude-plugin/plugin.json .claude-plugin/marketplace.json` shows 0.4.0 for engineering-method only.
- [ ] **Step 4:** CHANGELOG entry `## 0.4.0 — <date of release>`, newest first: the debug stage, its fix-word precedence and its known limit (symptom-only prompts rely on the trigger text); the reference and its ten steps, RC-5 starting from the working case; principle 17 points at it; the drift fix and its test; the CONTRIBUTING maintainer loop; "Keeping instruction files small" (ten steps, Anthropic's size guidance as baseline, `/doctor prompt-audit` as input); the fix-round rule (Superpowers' five-round cap kept, GSD's stall detection added, the first-stall departure named, the duplicate in model-routing-and-cost.md replaced by a pointer); test count; eval results base versus head with cost, filled from Task 10's measured output (never estimated).
- [ ] **Step 5: Commit** (`engineering-method 0.4.0: root-cause investigation, instruction-file compression, bounded fix loops`).

### Task 10: Head run (GREEN), regression run, load evidence

- [ ] **Step 1:** `claude plugin eval plugins/engineering-method --case 'rc-*' --runs 3 --ablation none --judge-model sonnet --max-cost-usd <36 × c × 1.25>`. Expected: every criterion green in at least 2 of 3 runs; `rc-activation-loads-reference` c1 and `rc-near-miss-rename` c1 in 3 of 3.
- [ ] **Step 2:** The two Task 7 and 8 cases on head, one command each: `--case instruction-file-compression` and `--case fix-loop-bounded`, `--runs 3 --ablation none --judge-model sonnet --max-cost-usd <3 × c × 1.25>`. Expected: every criterion green in at least 2 of 3 runs.
- [ ] **Step 3:** Regression, touched cases: the eight cases of section 5 (five from Task 2 Step 4, including `live-deploy-safeguards` and `state-claim-measured`, whose routing changed; one from Task 7 Step 3, two from Task 8 Step 3) on head, same flags and caps; compare run for run with base. Watch `fix-fits-what-exists` c1: it depends on wording principle 17 no longer carries ("through the system ... until that has run").
- [ ] **Step 4:** Regression, the other 15 existing cases on head, one command per case or one glob that selects them, `--runs 3`, total cap `<45 × c × 1.25>`; compare per case with the 0.3.0 CHANGELOG results. Any drop stops the release until explained (principle 18).
- [ ] **Step 5:** Read the failing answers of any red criterion; fix the case if the judge is wrong, the reference if the behaviour is.
- [ ] **Step 6:** Record the hook output from section 5 ("Showing the reference loads"), base, head and regression counts and spend in the CHANGELOG (Task 9 Step 4) and amend that commit.

### Task 11: Full suites and identifier scan

- [ ] **Step 1:** `set -o pipefail; (cd plugins/plan-layer && python3 -m unittest tests/*.py 2>&1 | tail -3)`; `python3 -m pytest plugins/work-log/tests -q 2>&1 | tail -3`; `python3 -m unittest discover -s plugins/engineering-method/tests 2>&1 | tail -3`. Each shows its OK or `passed` line with no failure.
- [ ] **Step 2:** `git diff main --stat` lists only the files in "File structure".
- [ ] **Step 3:** Identifier scan of `git diff main` and of the branch's commit messages (`git log main..HEAD --format=%B`) for tracker hosts, tracker ids, private project names, personal addresses and the owner's own identifiers (the list kept outside the repo); prove the scan can fire by planting one listed value in a scratch file and seeing it reported. Expected on the diff and the messages: 0 hits, apart from synthetic `example.invalid` addresses.

### Task 12: Whole-branch review

- [ ] **Step 1:** A fresh Fable 5.2 reviewer in its own worktree receives the diff, this plan, and a brief written by RC-10's rule (no conclusion; it runs the suites, runs the hook on its own prompts, re-counts the budget, greps the reference for every eval's distinctive strings, checks that `review-loop.md` and `model-routing-and-cost.md` hold one fix-round rule between them, and reports its model id).
- [ ] **Step 2:** Fix rounds per review-loop.md, now bounded by Task 8's rule; a re-review covers the delta only.
- [ ] **Step 3:** Stop. Push, PR and marketplace publish wait for the owner's word.

---

## Out of scope

- Project-specific executors: trace-store queries, ssh, log pulls and the case's own fix stay in each project; the reference names their contract only.
- Hook matching of symptom-only prompts ("why is CI red"); they rely on the trigger text (known limit, section 1).
- A second skill, slash commands, a plugin agent (parked in section 3 with triggers).
- Any change to Superpowers, plan-layer or work-log.
- Evals in CI (parked separately on judge-model spend).
- Rewording principles other than the two SKILL.md sentences listed; raising any budget limit.
- The case's stage table and anti-pattern list: kept in the project's record, not shipped.
- Tracker entries: kept in the local, git-excluded notes; none in this repo.
- Push, PR, tag or publish.
- For Tasks 7 and 8: any SKILL.md edit or trigger phrase (no budget left; the stage map reaches both references); a unit test over the wording of the new rules (the evals test the behaviour; a text-presence test would only pin prose); a script that performs the compression (the steps are project-agnostic commands, and the file layouts differ per project); compressing any real instructions file as part of this release.

## Review

Before Task 1, this plan is reviewed by a fresh agent on a different model from its author (author: Opus 5.5; reviewer: Fable 5.2), in its own worktree of this repo at `main`, executing rather than reading:
- runs the engineering-method suite on `main` and confirms 55 OK;
- applies Task 4 Step 4's SKILL.md edits to a scratch copy and runs `test_skill_budget.py` against it (budget, cell, trigger);
- applies Task 4 Step 3's hook code to a scratch copy and runs Task 4 Step 1's tests plus the existing suite;
- checks that no section 5 scenario can be answered by recalling the section 2 text (shared distinctive strings);
- re-reads the four cited Claude Code doc pages and confirms or contradicts each vendor fact;
- reports findings with file and line and the probe that produced each, labels any unreproduced finding a hypothesis, and reports its model id.

Its brief follows RC-10: the goal, this file, the repo path and the constraints; not the author's view of the plan's weak points. (First round done 25 Nov 2026 by claude-fable-5-2: "approve with fixes", twelve findings, all applied in this revision.)

**Addendum review.** Tasks 7 and 8, the RC-5 sharpening and the renumbering of the former Tasks 7-10 to 9-12 were added after that round. A scoped re-review on a different model from the author covered that delta only (done 25 Nov 2026 by Fable 5.2: "approve with fixes", ten findings, all applied): it applies Task 7 Step 4 and Task 8 Steps 4-5 to a scratch copy at the Task 5 state, runs the suite and the Step 6 greps, checks the eval prompts route to the stated stage with `method_hook.py --prompt`, and checks the quoted vendor and baseline lines against their sources.
