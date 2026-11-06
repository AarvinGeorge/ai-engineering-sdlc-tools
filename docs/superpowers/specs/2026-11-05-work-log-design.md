---
summary: Design for the work-log plugin, which turns Claude Code activity into dated, time-estimated, plain-language work logs saved as new Google Sheets in a dedicated Drive folder, on request or weekly.
status: draft for review
covers: intent, sources, scope, time estimates, sheet format, run modes, privacy, components, testing, release, out of scope
key_facts: default scope is the current folder and below; idle gap 15 min; weekly run Mondays covers the previous Mon-Sun; create-only sheets in "Work Logs"; transcripts are deleted after 30 days by default
updated: 2026-11-05
---

# work-log: design

## 1. Intent

A person who works with Claude Code needs a trustworthy record of what they did and roughly how long it took, for any period they name. They should be able to hand it to a non-technical reader, such as HR, a client, a manager or a timesheet. Today that record has to be rebuilt by hand from chat history, git and notes. Claude Code also deletes session transcripts after 30 days by default (`cleanupPeriodDays`, official settings reference), so the raw material goes away.

The plugin makes the record in two ways:

- **On request**, in plain words.
- **On a weekly schedule**, so it is saved before the raw material ages out.

Each record is a new Google Sheet in one Drive folder. That folder becomes the lasting record.

**Who it serves:** anyone using this marketplace. The author's own use (logging time for an HR reviewer) is the first case, not the only one.

**Success means:**

- One request ("work log for last week") gives a sheet a non-technical reader understands without help.
- Each entry has a date, times, estimated hours and an outcome of 30 words or fewer.
- Each day has a total.
- Weekly runs keep a gap-free series of sheets with no manual step.

## 2. Requests it understands

Requests come in natural language. Examples are a guide, not a grammar.

- **Periods:**
  - "today", "yesterday", "last 3 days";
  - "this week", "last week", "last two weeks";
  - "last month", "October", "since 3 Oct", "3 Oct to 5 Nov";
  - "Q4", "last few months".
- **Scope:**
  - default is the current working directory and everything under it;
  - "all projects";
  - a named folder, or several.
- **Output:**
  - default is a new sheet in Drive;
  - "show me here" prints the log in the conversation instead;
  - "save as a file" writes a local `.xlsx` file.
- **Manual entries:** "log 1 hour yesterday, call with the capstone team" records work done outside Claude (§6.4).
- **Style:**
  - default is the plain, high-level HR style;
  - "detailed" keeps technical names for a technical reader.

A period is resolved to exact local dates and echoed back in the sheet's title and first row, so the reader sees what was covered. "Last week" means the previous Monday to Sunday.

## 3. Sources

| Source | What it gives | Limit |
|---|---|---|
| Claude Code transcripts, `~/.claude/projects/<slug>/<session>.jsonl` | Per-message timestamps, the working directory (`cwd`) on each entry, the user's requests, Claude's replies, a session title | Deleted after `cleanupPeriodDays` (default 30). The line format is internal and undocumented, so it is read defensively (§8) |
| git history of repositories inside the scope | Commit times and subjects, as evidence of outcomes | Only what was committed |
| Earlier work-log sheets in the Drive folder | Periods older than the transcripts still cover | Only what earlier runs saved |
| Manual entries (§6.4) | Work done outside Claude | Only what the person logs |

Subagent transcripts are not counted as separate time: they run inside a session already counted.

**Scope match:** a session belongs to a folder when the `cwd` of its first user message is that folder or under it. This includes the git worktrees used by sessions that started there, because they belong to the session, not to the worktree's path. The folder-name slug is not used for matching: it isn't reversible (`/`, `.` and `_` all become `-`).

## 4. Time estimates

- **Active time:**
  - A session's active time is the span of its message timestamps, minus every gap longer than the idle cutoff.
  - The default cutoff is 15 minutes; it can be changed per request.
  - This mirrors activity-based trackers such as WakaTime.
- **Dates:**
  - Times are shown in the machine's local time zone, with its name in the header.
  - A session that crosses midnight is split between the two days.
- **Overlaps:** when two sessions overlap, time is counted once per minute of wall clock, so parallel sessions don't double a day.
- **Rounding:** hours are rounded to the nearest 0.25 h.
- **Labels:** every hours column is labelled "Estimated hours (from activity)". Manual entries carry the hours the person gave, labelled "Stated".
- **Background work:** a reply that waits on a long background job is counted only while messages flow. Waiting without activity is not work time in this estimate, and the sheet's notes row says so.

## 5. Summaries

- One entry per piece of work within a day. Several sessions on one piece merge, and one long session with distinct pieces splits.
- **HR style (default):**
  - 30 words or fewer;
  - plain language;
  - the outcome and why it mattered;
  - no internal document numbers, plan codes, branch names, commit hashes, file paths or tool names;
  - an abbreviation is either spelled out or left out.
- **Detailed style:** keeps technical names and is still 30 words or fewer.
- **Incidents and failures are recorded honestly**, in neutral words ("a test reached a real person by mistake; testing was tightened").
- Summaries are written by Claude in the session, from the collected facts. The scripts never write prose.

## 6. Output

### 6.1 The sheet

**One new Google Sheet per run, never edited afterwards.** The Drive connector can create a sheet from uploaded data, but its `update_file` changes only metadata (tool definitions, read 5 Nov 2026). Create-only is the only kind of write the plugin needs.

**Tabs:**

1. **Entries:** date, start, end, estimated hours, project, type (Claude session or manual), summary, entry ID.
2. **Daily totals:** one row per day and project, with hours as formulas over Entries, plus a grand total.
3. **About:** period covered, scope, time zone, idle cutoff, sources used, creation time, plugin version, and the limits in §9.

**Project names:**

- Project names are readable, such as "example agent".
- They come from a small `projects` mapping the person can edit, or else the folder name with separators turned into spaces.
- File paths never appear.

**File and folder:**

- File name: `Work log · <scope name> · <YYYY-MM-DD> to <YYYY-MM-DD>`.
- Folder: `Work Logs` in the connected account's Drive. It is created on first use and found by name afterwards.
- Weekly sheets go in `Work Logs/Weekly`, manual entries in `Work Logs/Manual`, and on-request reports at the top level.

### 6.2 How the file is made

- A script builds an `.xlsx` workbook, with tabs, formulas and column formats, using `openpyxl`.
- Claude then uploads it through the Drive connector's `create_file`, with conversion to a Google Sheet.
- **To verify in the build's first step:** that conversion keeps all three tabs and the formulas.
  - If it doesn't, the fallback is one tab with daily subtotal rows written as values.
  - The About tab then says so.

### 6.3 No Drive connector

The plugin works without the connector. It writes the same `.xlsx` file into the current folder and says so. The connector is recommended, not required, so the plugin is useful to people who don't use Google.

### 6.4 Manual entries

- Each manual entry becomes its own small sheet in `Work Logs/Manual`.
- Later reports read these back.
- This keeps manual entries in Drive without editing any existing file.

## 7. Run modes

### 7.1 On request

Any Claude Code session (terminal, IDE or Desktop) with the plugin installed can run it. Claude:

1. resolves the period and scope;
2. runs the collector;
3. reads earlier sheets for any part of the period older than the transcripts;
4. writes the summaries;
5. builds the workbook and uploads it.

Claude then gives the sheet's link and the day totals in a few lines.

### 7.2 Weekly, on a schedule

- **Mechanism:** a local scheduled task in Claude Desktop, with "Only on this computer" on, pointed at the folder to log.
- **Why local:**
  - local tasks can read local files and use connectors;
  - cloud tasks run on a fresh clone and cannot see `~/.claude` (Desktop scheduled tasks page, official docs).
- **Schedule:** every Monday morning, covering the previous Monday to Sunday.
- **Self-healing:**
  - Desktop runs only while the app is open and the machine awake.
  - After a missed run, Desktop starts one catch-up run, for the most recently missed time within 7 days (same page).
  - So each run does not trust its own date. It lists `Work Logs/Weekly`, finds the last week saved for its scope, and creates a sheet for every full week since.
  - It goes back only as far as transcripts still exist. Any week it can no longer rebuild gets one line in the About tab, never a silent gap.
- **Setup:** the skill's setup guide gives the exact task settings and the instruction text to paste. It also suggests turning on "Keep computer awake".
- **Other ways to schedule:** `/loop` and the `schedule` skill are not used for the weekly run. `/loop` lasts one session; cloud tasks cannot read local transcripts.

## 8. Reliability and honesty rules

- **Fail loudly on zero.** If a transcript file can't be parsed, or a period that should have sessions yields none, the run stops and says what it read. It doesn't write an empty sheet. A zero must be proven possible, for example that the scope matched no session at all.
- **Defensive reading:**
  - The transcript format is not a published contract.
  - Unknown line types are skipped and counted.
  - A missing `timestamp` or `cwd` on a user or assistant line counts as a format change. The run reports it rather than guessing.
- **Idempotent weekly runs:**
  - Before creating a weekly sheet, the run checks for one with the same scope and week.
  - If one exists, it skips that week and says so.
- **No secrets or personal data:**
  - Summaries are written from requests and outcomes, never from tool output.
  - Before upload, a scan rejects email addresses, phone numbers, key-like strings, and anything on an optional local list of names that must never appear.
  - A hit stops the upload and shows which entry failed. It never shows the value.
- **Labels:** estimates are labelled as estimates, and the About tab states the limits in §9.

## 9. Limits, stated in every sheet

- Cloud sessions (claude.ai/code) run elsewhere and are not in local transcripts.
- Work on other machines is not included unless the plugin runs there too.
- Hours are activity-based estimates, not clocked time.
- Periods older than the transcripts come only from earlier sheets.

## 10. Components

```
plugins/work-log/
  .claude-plugin/plugin.json
  README.md
  CHANGELOG.md
  skills/work-log/
    SKILL.md                 how to resolve a request, run the scripts, write summaries, upload
    references/style.md      the HR and detailed styles, with good and bad examples
    references/schedule.md   the Desktop scheduled-task setup, word for word
  scripts/
    collect.py               transcripts + git -> sessions JSON (times, active minutes, requests, titles, commits)
    workbook.py              entries JSON -> .xlsx with the three tabs
    scan.py                  the pre-upload scan
  tests/                     pytest, with fixture transcripts
  evals/                     same shape as engineering-method's evals
```

- The scripts are deterministic and have no network access. Claude does the judgement: periods, merging, summaries.
- The connector calls happen in the session, because hooks can't use connectors.
- No hooks ship in 0.1.0.

## 11. Testing

- **Unit tests (red first, then green):**
  - idle gaps;
  - the midnight split;
  - overlap counting;
  - time-zone handling;
  - scope match by `cwd` (including a subfolder and a worktree);
  - unknown line types;
  - the fail-loud zero;
  - the weekly gap finder;
  - each scan pattern;
  - workbook tabs and formulas.
- **Evals:**
  - a period phrase resolves to the right dates;
  - HR-style summaries keep the 30-word limit and contain no internal codes;
  - "all projects" versus the default scope;
  - a no-connector run writes a file.
- **Live check before release,** on the author's machine:
  - last week's log for one folder, uploaded, opened, tabs and totals read back;
  - one weekly scheduled run observed creating its sheet.
- **Review:** implementer and reviewer are different models; the reviewer runs probes. This is the method the marketplace already uses.

## 12. Release

- **Version 0.1.0:**
  - add it to `.claude-plugin/marketplace.json`;
  - add a row to the README plugins table;
  - add a CHANGELOG entry.
- Merge to `main` only on the author's word; push only when asked.

## 13. Out of scope for 0.1.0

- editing or appending to existing sheets;
- Toggl, Harvest, Jira, Notion or Excel Online destinations;
- cloud-session activity;
- other machines;
- hooks;
- billing rates;
- approvals workflows;
- a dashboard.

Each can follow once 0.1.0 is in use.
