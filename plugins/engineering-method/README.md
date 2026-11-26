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
