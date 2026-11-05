# Roadmap

## Not in 0.1.0

- Editing or appending to existing sheets. Every run makes a new sheet.
- Other destinations: Toggl, Harvest, Jira, Notion or Excel Online.
- Activity from cloud sessions (claude.ai/code).
- Activity from other machines.
- Hooks.
- Billing rates.
- Approval workflows.
- A dashboard.

Each can follow once 0.1.0 is in use.

## Known gaps

- **Work done from a parent folder is not counted for the child folder.** A session belongs to the
  folder it started in (the working folder of its first message). A session started in a parent
  folder that edits a child folder by its full path counts for the parent, not the child. Found while
  planning: a folder with real work in October 2026 showed 0 sessions for that month, because the work
  was done from its parent folder. A fix would attribute sessions by the paths they edit, not only
  where they started.
- **A weekly sheet deleted from the middle of the series is not recreated.** The weekly gap finder
  only looks at weeks after the latest saved weekly sheet. Ask for that week on request instead. A
  later version could check the whole series back to the earliest transcript.
