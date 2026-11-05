# work-log

Turns your Claude Code activity into a dated, time-estimated, plain-language work log for any
period, saved as a new Google Sheet in a `Work Logs` folder in Drive, or as a local `.xlsx` file.

## The problem

You need a record of what you did and roughly how long it took: for HR, a client, a manager or a
timesheet. Today that record is rebuilt by hand from chat history, git and notes. Claude Code also
deletes session transcripts after 30 days by default, so the raw material goes away.

## What it does

- **Ask in plain words.** "Work log for last week", "what did I do in October", "hours for HR",
  "log 1 hour yesterday, call with the capstone team".
- **One sheet per run, never edited.** Three tabs: Entries (date, start, end, estimated hours,
  project, type, summary), Daily totals (formulas, plus a grand total) and About (period, scope,
  time zone, how hours are estimated, limits).
- **Hours from activity.** Active time is the span of message timestamps minus gaps longer than
  15 minutes. Parallel sessions count once. Rounded to the nearest quarter hour, and labelled as
  estimates.
- **Summaries a lay reader understands.** 30 words or fewer, the outcome, no file paths, branch
  names or internal codes. A "detailed" style keeps technical names.
- **Weekly, on a schedule.** A local Desktop task makes last week's sheet every Monday and fills any
  missed weeks while their transcripts still exist.
- **Works without Google.** With no Drive connector it writes the same workbook in the current
  folder.

## Install

```bash
claude plugin marketplace add AarvinGeorge/ai-engineering-sdlc-tools
claude plugin install work-log@ai-engineering-sdlc-tools
```

Needs `python3` (3.9 or later, standard library only). The Google Drive connector is optional.

## First use

Open Claude Code in the folder you want logged and ask: "work log for last week". Claude says which
dates and folder it will cover, collects the activity, writes the summaries, checks them, builds the
workbook, uploads it to `Work Logs` and reads it back before giving you the link and the day totals.

The default scope is the current folder and everything under it. Say "all projects" for everything,
or name folders.

## Settings (optional)

Both files live in `~/.config/work-log/`.

- **`projects.json`**: readable project names, as a JSON object of folder path to name. The longest
  matching path wins. Write full paths (a `~` is not expanded). Without it, the folder name is used
  with separators turned into spaces.

  ```json
  {"/home/dev/code/alpha-app": "Alpha app", "/home/dev/code/beta-site": "Beta site"}
  ```

- **`never.txt`**: words or names that must never appear in a sheet, one per line (`#` starts a
  comment). A match stops the upload.

## Weekly setup

See [skills/work-log/references/schedule.md](skills/work-log/references/schedule.md) for the exact
Desktop task settings and the instruction text to paste.

## Privacy

- Summaries are written from your requests, session titles and commit subjects, never from tool
  output.
- Before any upload a scan rejects email addresses, phone numbers, key-like strings and anything on
  your never-list. It names the entry that failed, never the value.
- Raw requests are kept in a private temporary folder that is deleted at the end of each run.
- The scripts never use the network. Uploads go only through your own Drive connector.

## Limits

- Cloud sessions (claude.ai/code) run elsewhere and are not in local transcripts.
- Work on other machines is not included unless the plugin runs there too.
- Hours are activity-based estimates, not clocked time. Waiting on a long background job with no
  messages is not counted.
- Periods older than the transcripts come only from earlier sheets.
- See [ROADMAP.md](ROADMAP.md) for what it does not do yet.

## Layout

```
.claude-plugin/plugin.json
scripts/collect.py      transcripts + git -> sessions JSON
scripts/scan.py         pre-upload privacy and style scan
scripts/workbook.py     entries JSON -> .xlsx (three tabs, or one with --single-tab)
scripts/periods.py      last week, and the weekly gap finder
skills/work-log/SKILL.md            how Claude runs a request end to end
skills/work-log/references/         summary style, weekly schedule setup
evals/<case>/prompt.md + graders/   claude plugin eval cases
tests/                              unit tests (pytest)
```

## Tests and evals

```bash
python3 -m pytest plugins/work-log/tests -q
claude plugin eval plugins/work-log    # spends model calls; run deliberately
```

The eval cases check behaviour: "last week" resolves to the previous Monday to Sunday; HR summaries
stay under 30 words with no internal codes; "everything I did" uses all projects instead of the
default folder; with no Drive connector the log is written as a local file. Each case also carries
a skill-fired indicator (not scored).
