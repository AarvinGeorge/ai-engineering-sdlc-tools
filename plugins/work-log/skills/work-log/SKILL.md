---
name: work-log
description: Use when the user asks for a work log, timesheet, hours, or a record of what they did for a period ("work log for last week", "what did I do in October", "log 1 hour yesterday", "hours for HR"), or when a scheduled task starting [work-log weekly run] fires. Turns Claude Code transcripts and git history into a dated, time-estimated, plain-language log with day totals, saved as a new Google Sheet in a Work Logs Drive folder, or as a local .xlsx file when Drive is not connected. Also records manual entries for work done outside Claude, prints a log in the conversation on request, and fills missed weeks on a weekly schedule.
---

# work-log

Make a trustworthy record of what the user did and roughly how long it took, for any period they
name, that a non-technical reader (HR, a client, a manager) understands without help.

The scripts do the counting. You do the judgement: the period, merging, summaries and upload.
Scripts live at `${CLAUDE_PLUGIN_ROOT}/scripts/`; run them with `python3`. They use the standard
library only and never touch the network.

## 1. What it makes

- **One new sheet per run, never edited afterwards.** The Drive connector can create files but
  cannot change their contents, so every run makes a new sheet.
- Tabs: **Entries** (date, start, end, `Estimated hours (from activity)`, project, type, summary,
  entry ID), **Daily totals** (formulas over Entries, plus a grand total), **About** (period, scope,
  time zone, idle cutoff, sources, limits).
- Folders in the user's Drive: `Work Logs` (on-request sheets), `Work Logs/Weekly` (weekly runs),
  `Work Logs/Manual` (manual entries).
- File name: `Work log · <scope name> · <YYYY-MM-DD> to <YYYY-MM-DD>`. Manual sheets are named
  `Work log manual entry · <scope name> · <date> to <date>`. `workbook.py` makes the title; use it
  as printed.

## 2. Resolve the request

Turn the request into four things, then echo them in one line before running anything, for
example: "Work log for Mon 26 Oct to Sun 1 Nov 2026, this folder and below, HR style, to Drive."

- **Period**, as exact local dates (both ends inclusive):
  - "last week": run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/periods.py" last-week`; it prints
    `{"start": ..., "end": ...}` for the previous Monday to Sunday. Never use a rolling seven days.
  - "this week": Monday of this week to today. "today", "yesterday", "last 3 days": as said.
  - "last month": the previous calendar month. "October": 1 to 31 October.
  - "Q4": 1 Oct to 31 Dec of the current year, or of last year if this year's Q4 has not started.
  - "since 3 Oct": 3 Oct to today. "3 Oct to 5 Nov": as said.
- **Scope**: default is the current working directory and everything under it (`--scope` is the
  current folder when no flag is given). "All projects" or "everything" → `--all`. Named folders →
  one `--scope PATH` each.
- **Output**: default is a new sheet in Drive. "Show me here" → print it (section 11). "Save as a
  file" → local `.xlsx` (section 10).
- **Style**: `hr` by default; `detailed` when the user asks for technical detail.

**Scope name** (goes in the title): the readable name of the scope folder, from the user's projects
mapping or else the folder name with `-`, `_` and `.` turned into spaces and the first letter
capitalised; "All projects" for `--all`. Keep it identical from run to run: weekly gap-finding
matches titles on it exactly.

## 3. Collect

```bash
WL=$(mktemp -d)   # private working folder; it will hold raw requests
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/collect.py" --start 2026-10-26 --end 2026-11-01 \
  [--scope PATH ... | --all] [--projects-map ~/.config/work-log/projects.json] \
  > "$WL/sessions.json" 2> "$WL/collect.err"; echo "exit $?"
```

Other flags: `--idle-minutes N` (default 15), `--tz Area/City`, `--no-git`. Pass `--projects-map`
only when `~/.config/work-log/projects.json` exists.

- **Exit 0**: `sessions.json` holds `tz`, `idle_minutes`, `period`, `scope`, `read` (counts),
  `earliest_activity`, `sessions` (one row per session per day: `date`, `project`, `start`, `end`,
  `active_minutes`, `title`, `branches`, `requests`), `day_totals` (minutes) and `commits` (`project`,
  `date`, `time`, `subject`).
- **Exit 3**: a format change or bad input; stderr names the file and line. Report it in plain words
  and stop. Do not guess around it.
- **Exit 2**: nothing in scope for the period. Read the stderr JSON: `files_read`,
  `sessions_total`, `sessions_in_scope_any_date`, `sessions_in_period_any_scope`,
  `earliest_activity`, `commits_in_scope`, `excluded_by_marker` (or `"no transcripts found"` with no
  counts). **Continue to section 4** if `period.start` is before `earliest_activity`, or if
  `Work Logs/Manual` holds sheets in the period. Stop with no sheet only when transcripts, earlier
  sheets and manual sheets are all empty for the period. Then report the counts in plain words
  (they show the zero could have been non-zero, for example "42 sessions read, 7 of them in this
  period in other folders, none in this folder") and offer "all projects" or a wider period.
- **Never invent sessions.** Everything in the log comes from `sessions.json`, earlier sheets or
  manual sheets.
- **Delete `$WL` at the end of the run, success or not** (`rm -rf "$WL"`): it holds raw prompts.

## 4. Older than transcripts

Transcripts are deleted after `cleanupPeriodDays` (default 30 days).

- If `period.start` is before `earliest_activity`, search `Work Logs`, `Work Logs/Weekly` and
  `Work Logs/Manual` for sheets covering the gap and read their Entries rows with `read_file_content`.
- Carry those rows over unchanged as entries (their hours are already estimates; use their summary
  and project as written).
- Any week not covered becomes a `meta.missing_weeks` item: `{"start": ..., "end": ...}`. The About
  tab lists it as not rebuilt. Never leave a silent gap.
- Always read `Work Logs/Manual` sheets whose dates fall in the period and include their entries.

## 5. Write entries

- One entry per piece of work per day. Merge session-days on the same piece: sum `active_minutes`
  into `minutes`; `start` = earliest, `end` = latest. Split a long session that holds distinct pieces.
- Write summaries from `requests`, `title` and `commits` only, never from tool output. Follow
  `references/style.md`. HR style: 30 words or fewer, the outcome, no codes.
- `project`: the session's `project` (it already applies the user's projects mapping).
- Write `$WL/entries.json` in this shape:

```json
{"meta": {"scope_name": "Alpha app", "period_start": "2026-10-26", "period_end": "2026-11-01",
          "kind": "request", "style": "hr", "tz": "America/New_York", "idle_minutes": 15,
          "sources": ["Claude Code transcripts", "git history"], "notes": [], "missing_weeks": []},
 "entries": [{"id": "E1", "date": "2026-10-26", "start": "10:00", "end": "11:30", "minutes": 44,
              "project": "Alpha app", "type": "Claude session",
              "summary": "Built the sign-in page so customers can log in with their work account."}]}
```

- `kind`: `request` (on request), `weekly` (weekly run) or `manual`. `tz` and `idle_minutes` come
  from `sessions.json`. `type` is exactly `Claude session` or `Manual (hours stated)`. Session
  entries carry `minutes`; manual entries carry `stated_hours`. Ids are short and unique (`E1`, `M1`).

## 6. Scan

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scan.py" "$WL/entries.json"; echo "exit $?"
```

It reads `~/.config/work-log/never.txt` when present (or `--never FILE`).

- **Exit 0**: prints `scan: clean (N entries)`.
- **Exit 1**: one line per hit, `entry <id> field <field>: <rule>` (rules such as `email`, `phone`,
  `key-like`, `never-list`, `over-30-words`, `file-path`, `commit-hash`, `branch-name`,
  `internal-code`, `abbreviation`). Rewrite only the named entries and scan again. Never print or
  quote the matched value. Do not build or upload until the scan is clean.
- **Exit 3**: the entries file is unreadable; fix the JSON.

## 7. Build

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/workbook.py" "$WL/entries.json" \
  --out "$WL/wl.xlsx" --b64 "$WL/wl.b64"; echo "exit $?"
```

It prints one JSON summary: `title`, `tabs`, `entries`, `day_totals` (hours), `grand_total`,
`folder`, `path`, `b64_path`, `bytes`, `sha256`. Keep it for the read-back. Exit 3 means bad input;
the message names the entry id and field. `--single-tab` builds one `Work log` tab with totals as
values (the fallback in section 9).

## 8. Upload (Drive connector present)

Tools: `mcp__claude_ai_Google_Drive__search_files`, `mcp__claude_ai_Google_Drive__create_file`,
`mcp__claude_ai_Google_Drive__read_file_content`.

1. **Find the folders by exact title.** `search_files` with
   `title = 'Work Logs' and mimeType = 'application/vnd.google-apps.folder' and owner = 'me'`.
   The connector does not support a `trashed` query term, so ignore any result whose metadata says
   `trashed: true`. Then `parentId = '<id>' and title = 'Weekly'` (or `'Manual'`) with the same
   folder mime type. Create a missing folder with `create_file`: `title`, `parentId` (none for
   `Work Logs`), mime type `application/vnd.google-apps.folder`, no content.
2. **Weekly sheet**: search `Work Logs/Weekly` for a sheet with the same title. If one exists, skip
   that week and say so (weekly runs are idempotent).
3. **On-request sheet**: if the title already exists, append ` (2)`, ` (3)` and so on. Never skip.
4. **Create** with `create_file`: `title` = the summary `title` (plus any suffix), `parentId` = the
   folder id for the summary `folder`, `contentMimeType` =
   `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`, `base64Content` = the exact
   contents of the `.b64` file. Read it with the Read tool and pass it unchanged. Drive converts it
   to a Google Sheet with all three tabs and recalculates the formulas.

## 9. Read back

Never claim success without this step.

- `read_file_content` on the new sheet's id.
- Confirm the tab names match `tabs`, and that the grand total and each day total equal the
  summary within 0.01 hours (Google's arithmetic can differ in the last digit).
- On a mismatch: say so, build again with `--single-tab`, upload as `<title> (single tab)`, read
  that back, and tell the user which file to delete.

## 10. No connector, or "save as a file"

If the Drive tools are not available, build with `--out "./<title>.xlsx"` (the summary `title`; a
`/` in it becomes `-`) in the current folder. Say so in one line, and mention that the Google
Drive connector is optional. Do not ask the user to connect Drive first.

## 11. Show me here

Print the entries as a short table (date, start, end, hours, project, summary) and the day totals
plus a grand total. Still run the scan. No file, no upload. Hours: `minutes` rounded to 0.25 h.

## 12. Manual entries

"Log 1 hour yesterday, call with the capstone team":

- Period = that day. No collect.
- Entries JSON with `meta.kind` = `manual` and one entry: `type` = `Manual (hours stated)`,
  `stated_hours` = 1, empty `start` and `end`, a plain summary, `id` `M1`.
- Scan, build, upload to `Work Logs/Manual`, read back. Later reports read these sheets (section 4).

## 13. Weekly run

When the prompt starts with `[work-log weekly run]` (scheduled task; setup in
`references/schedule.md`). `collect.py` drops sessions that start with this marker, so the logging
run does not count as work.

1. Wide collect for the earliest transcript date: `--start` 60 days ago, `--end` today, same scope.
   Take `earliest_activity` from stdout on exit 0, or from the stderr JSON on exit 2.
2. List the sheet titles in `Work Logs/Weekly` as a JSON array and pipe them in:

```bash
echo "$TITLES_JSON" | python3 "${CLAUDE_PLUGIN_ROOT}/scripts/periods.py" missing-weeks \
  --scope-name "Alpha app" --earliest 2026-10-05 --titles-json -
```

   It prints `to_create` (each with `start`, `end`, `title`, `partial`), `skipped_by_cap` (more
   than 8 weeks; `--max-weeks N` changes it), `unrecoverable` (older than every transcript) and
   `already_saved`. Without `--earliest`, every week is unrecoverable.
3. For each `to_create` week: collect that week, write entries with `kind` = `weekly`, scan, build,
   upload to `Work Logs/Weekly`, read back. A `partial` week (it starts before the earliest
   transcript) gets a `notes` line saying the first days may be missing. A week whose collect exits
   2 gets no sheet; report it as "no activity".
4. Put `unrecoverable` and `skipped_by_cap` weeks in `meta.missing_weeks` of the first sheet made,
   or report them if no sheet is made.
5. The gap finder only looks at weeks after the latest saved weekly sheet. A weekly sheet deleted
   from the middle of the series is not recreated automatically; the user can ask for that week on
   request instead.
6. Finish with one line per week: the sheet link or the reason none was made.

## 14. Report

A few lines: the link (or file path), the day totals, the grand total, and anything skipped or not
rebuilt.

## 15. Limits (stated in every sheet's About tab)

- Cloud sessions (claude.ai/code) run elsewhere and are not in local transcripts.
- Work on other machines is not included unless the plugin runs there too.
- Hours are activity-based estimates, not clocked time.
- Periods older than the transcripts come only from earlier sheets.
