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
- **Short body, detail on demand.** `SKILL.md` stays under 150 lines; the detail lives in
  `references/` and loads only when a task needs it.

## Install

```bash
claude plugin marketplace add AarvinGeorge/ai-engineering-sdlc-tools
claude plugin install engineering-method@ai-engineering-sdlc-tools
```

Works best with Superpowers installed (`superpowers@claude-plugins-official` or its own
marketplace). Without it the skill still reads correctly; the pointers name skills that are absent.

## Layout

```
.claude-plugin/plugin.json
skills/engineering-method/SKILL.md          principles, stakes tiers, pointer table
skills/engineering-method/references/       detail, loaded on demand
evals/<case>/prompt.md + graders/           claude plugin eval cases
```

## Evals

```bash
claude plugin eval plugins/engineering-method    # spends model calls; run deliberately
```

The cases check behaviour, not wording: a prototype must not get live-system ceremony; a test
report must show the command and its output; the reviewer must be a different model from the
implementer; a zero must be proven able to be non-zero; a declined permission must stop the action.
