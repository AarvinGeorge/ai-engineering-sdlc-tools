# engineering-method

An engineering method for working with coding agents, carried to every project as one on-demand
skill.

## Use cases

- **You ask "is it deployed?"** The agent measures instead of recalling. It shows the command that
  proves the running version contains the change (for example
  `git merge-base --is-ancestor <sha> <running>`), and says "unverified" when it cannot read the
  running version.
- **You want a quick throwaway script.** The agent names it exploration (tier a) and keeps it light:
  the script, plus one check you can run. No plan, no review pipeline. Ceremony the stakes do not
  need counts as a defect.
- **A search comes back with 0 results.** Before reporting "none", the agent shows the same search
  can find something, so a broken pattern is not mistaken for a real zero.
- **You decline a permission prompt.** The agent stops. It does not retry a narrower form or move
  the action somewhere that does not prompt; it marks the step unverified and tells you.
- **You type "ok, now deploy it to production".** A hook sees the stage change and injects one line
  telling the agent to read `references/live-system-changes.md` before acting: in-flight check,
  verified backup, rollback ready, read-backs after. It stays quiet until the stage changes again.
- **You type "investigate why the assistant refuses on the North site but works on South".** The
  hook sees the debug stage and injects: `engineering-method: stage debug — re-read SKILL.md §3 row 'debug', load superpowers:systematic-debugging, read references/root-cause-investigation.md, references/measurement-and-state-claims.md before acting; evidence first (tier b, c): no cause, suspect list or fix until RC-1 to RC-4 are done, requested or skipped; keep the stakes tier you named.` The
  agent then pins what each instance actually runs before comparing them, reads the model input as
  sent on a failing turn, and calls a cause a hypothesis until that input has been read. A prompt
  that names only the symptom, with none of the stage words, relies on the skill's trigger text
  instead of the hook.
- **Your always-loaded instruction file has grown past what is read.** Ask to compress it and the
  agent follows the ten-step procedure in `references/docs-and-decisions.md`: archive the whole file
  verbatim and prove the copy matches, sort sections by kind, keep binding rules as rule plus reason,
  grep a checklist of one-line rules afterwards, and have a different model diff old against new
  before anything is committed. Nothing is deleted; what leaves the file lives in the archive.
- **You ask for "one more fix round, until the reviewer says clean".** The agent pushes back once and
  applies the fix-round rule in `references/review-loop.md`: a five-round cap and a ledger line per
  round (`fix round R/5: closed X, reopened Y, open Z`). A round stalls when a finding reopens or the
  open count does not fall. After the first stall the next round goes to a fresh implementer on a
  more capable model (the same model at the top tier); after a second stall, or at round 5,
  dispatching stops and the open findings are adjudicated: parked with a ruling, or brought to you.
  If you then say to continue anyway, the agent pushes back once and does as asked.
- **You type "Which graders should this new eval case use?"** The hook sees the test stage and
  injects: `engineering-method: stage test — re-read SKILL.md §3 row 'test', load superpowers:verification-before-completion, read references/measurement-and-state-claims.md, references/behaviour-evals.md before acting; keep the stakes tier you named.` The agent then puts a code check (a pattern over
  the reply, a tool called, a file created) wherever one can decide, keeps an LLM judge for what
  needs reading and says why code cannot decide it, and writes binary pass and fail conditions
  instead of a score to average. It pins the judge by name, on a different model from the one under
  test and the one that wrote the instructions, and calls the judge "uncalibrated, n = …" until
  enough of your own rulings back it.
- **You type "The eval says 2 of 3. Can we call it reliable?"** The hook injects the same test-stage
  line, unless the test stage was already announced in this session. The agent reports k of n per
  criterion, holds a rule that must never break to every run (pass^k), and says how little three runs can prove. A run whose inputs
  never reached the agent is reported apart, as invalid. A new rule's case still red is recorded as
  known red; a drop on an existing case gets more runs and a reading of the answers, then goes to
  you.
- **You type "All tests pass, mark it verified".** The hook injects the same test-stage line. On
  tier b or c the agent first compares the diff with the plan's steps and its out-of-scope list. It
  lists each mismatch with file and line: out of scope, a step with no change, or a change nobody
  asked for. It withholds "verified" until you rule on each one, and fixes nothing on its own. (In the 0.5.0 runs this last part was known red, 0 of 3; see CHANGELOG.) With
  no mismatch it says so with the counts and the command, for example
  `diff matches the plan: 5 steps, 4 out-of-scope lines checked`. On a throwaway script with no plan
  it does none of this.
- **You type "Write the project settings file for our production service".** The hook sees the
  deploy stage and injects: `engineering-method: stage deploy — re-read SKILL.md §3 row 'deploy', read references/live-system-changes.md before acting; keep the stakes tier you named.` That reference's
  standing rules point to `references/permission-profiles.md`, and the agent gives you its live
  profile to paste into the committed `.claude/settings.json`: what must never run under deny, every
  command that can change the live system under ask, and bypass disabled. It explains that deny wins
  over any allow in any settings file, and that a Bash rule matches the command text, not the
  program, so a sandbox or a PreToolUse hook is the hard floor. It never edits your settings file
  itself. (In the 0.5.0 runs the deny-wins part was known red, 0 of 3; see CHANGELOG.)
- **You ask which model should review a change.** The answer is a different model from the one that
  wrote it, at least as strong, and the reviewer runs probes rather than reading the diff.

## The problem

A method learnt on one project lives in that project's instructions file. Open a different
repository and it is gone; copy it everywhere and every copy drifts. And a method written as rigid
procedure makes an agent worse on the small task and no better on the large one.

## What it does

- **Principles, not procedures.** Each rule carries its reason in one line and a test for whether it
  held. They are defaults: the skill tells the agent to propose a better approach when it sees one.
- **Scaled by stakes.** A prototype gets evidence and one review. An internal tool adds tests and a
  cross-model review. A live system with real users gets everything, including a deploy file, an
  in-flight check, a backup and a rollback. Ceremony the stakes do not need is a defect.
- **A thin layer over [Superpowers](https://github.com/obra/superpowers).** Brainstorming, plans,
  TDD, code review, debugging, worktrees and verification are Superpowers' job; this skill points to
  them by name and adds only what they do not say.
- **Debugging.** A debug stage loads Superpowers' systematic-debugging and a reference of ten named
  investigation steps, most of them for systems where a model makes the decision.
- **Short body, detail on demand.** `SKILL.md` stays within 2,200 words, and a test enforces it; the detail lives in
  `references/` and loads only when a task needs it.

## Install

```bash
claude plugin marketplace add AarvinGeorge/ai-engineering-sdlc-tools
claude plugin install engineering-method@ai-engineering-sdlc-tools
```

Works best with Superpowers installed (`superpowers@claude-plugins-official` or its own
marketplace). Without it the skill still reads correctly; the pointers name skills that are absent.

## Hooks

The plugin ships two hooks (`hooks/hooks.json`, script `scripts/method_hook.py`) so the method is re-applied without a reminder:

- **SessionStart** (`startup`, `clear`, `compact`): injects a short brief with the stakes tiers and the stage map. After compaction it adds a line telling the agent to re-read the skill.
- **UserPromptSubmit**: when your prompt moves to a new stage of work (plan, debug, build, review, test, deploy, merge, release, report), injects one line naming the skill and references to load. It stays silent while the stage is unchanged; the memory resets on session start.

Both never fail loudly: on any error they print nothing (or a one-line brief) and exit 0. To turn them off, disable the plugin; there is no separate switch.

## Layout

```
.claude-plugin/plugin.json
skills/engineering-method/SKILL.md          principles, stakes tiers, pointer table
skills/engineering-method/references/       detail, loaded on demand
hooks/hooks.json + scripts/method_hook.py   session-start and per-prompt reminders
tests/test_method_hook.py                   unit tests for the hooks
evals/<case>/prompt.md + graders/           claude plugin eval cases
```

## Evals

```bash
claude plugin eval plugins/engineering-method    # spends model calls; run deliberately
```

The cases check behaviour, not wording: a prototype must not get live-system ceremony; a test
report must show the command and its output; the reviewer must be a different model from the
implementer; a zero must be proven able to be non-zero; a declined permission must stop the action; a live deploy gets in-flight, backup, rollback-first and read-backs; a "deployed" note is measured, not recalled; the root-cause cases (`rc-01` to `rc-10`, plus `rc-activation-loads-reference` and the near-miss guard `rc-near-miss-rename`) check each investigation step at its trigger; `instruction-file-compression` checks that an always-loaded file is shrunk without losing a rule; `fix-loop-bounded` checks the round cap and stall rule; the `eval-*` cases check how evals are graded, repeated, judged, gated and accounted for (with the near-miss guard `eval-near-miss-unit-test`); `verified-matches-plan` checks "verified" against the plan (guard `verified-near-miss-no-plan`); `permission-profile-live` checks the live settings profile (guard `permission-profile-exploration-light`). Each case also carries a skill-fired indicator (not scored).

Every new rule ships with its case, written first: it fails on the skill without the rule, and its
result with the rule is reported beside it (`references/behaviour-evals.md`). `evals/COVERAGE.md` maps each rule to its case.
