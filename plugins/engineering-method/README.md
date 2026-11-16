# engineering-method

An engineering method for working with coding agents, carried to every project as one on-demand
skill.

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
- **UserPromptSubmit**: when your prompt moves to a new stage of work (plan, build, review, test, deploy, merge, release, report), injects one line naming the skill and references to load. It stays silent while the stage is unchanged; the memory resets on session start.

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
implementer; a zero must be proven able to be non-zero; a declined permission must stop the action; a live deploy gets in-flight, backup, rollback-first and read-backs; a "deployed" note is measured, not recalled. Each case also carries a skill-fired indicator (not scored).

Every new rule ships with its case, written first: it fails on the skill without the rule and
passes with it (`references/behaviour-evals.md`). `evals/COVERAGE.md` maps each rule to its case.
