# Weekly run: set up a Desktop scheduled task

A local scheduled task in Claude Desktop makes last week's sheet every Monday morning, before the
transcripts age out. Steps from the Desktop scheduled tasks page
(code.claude.com/docs/en/desktop-scheduled-tasks.md, read 5 Nov 2026).

## Why a local task

- A local task can read the transcripts on this machine and use the Google Drive connector.
- A cloud task runs on a fresh copy of the repository and cannot see the transcripts.
- `/loop` lasts only one session, so it is not used for this.

## Steps

1. Open Claude Desktop, go to the **Code** tab, then **Scheduled**.
2. Click **New task**. If asked, choose **Set up manually**.
3. **Name**: `work-log-weekly`.
4. **Instructions**: paste this text word for word. The first words are a marker: the plugin uses
   it to recognise the weekly run and to leave the logging run itself out of the log.

   ```
   [work-log weekly run] Using the work-log skill, make the weekly work log sheets for this folder: find the last week already saved in Work Logs/Weekly for this folder's scope and create one sheet for every full Monday-to-Sunday week since, up to last week. Use the default HR style. If a week has no activity, make no sheet for it and say so. Finish with one line per week: the sheet link or the reason none was made.
   ```

5. Choose the permission mode and the model in the instructions box.
6. **Advanced settings → General**: turn **Only on this computer** on.
7. **Local folder**: the folder you want logged. The log covers that folder and everything under it.
   Do not turn on the **Worktree** option: the run only reads transcripts, so a worktree adds nothing.
8. **Trigger**: **Weekly**, **Monday**, **09:00**. Or **Custom** with `0 9 * * 1`.
9. Click **Create**.
10. Click **Run now** once. When it asks for permission, choose **always allow** for `python3` and
    for the Google Drive tools. Scheduled runs need these approvals; without them later runs stall
    waiting for an answer nobody gives.
11. Turn on **Keep computer awake** (**Settings > Desktop app**, or **Settings > This computer >
    System**).

## What to expect

- The task runs only while the Desktop app is open and the computer is awake.
- After missed runs, Desktop starts one catch-up run, for the most recent missed time within the
  last 7 days.
- Each run fills every missing week since the last saved weekly sheet, so a catch-up run also
  covers older misses, as long as their transcripts still exist.
- Claude Code deletes transcripts after `cleanupPeriodDays` (30 days by default). A month with no
  runs cannot be rebuilt; those weeks are listed in the About tab as not rebuilt.
- A weekly sheet you delete from the middle of the series is not made again automatically. Ask for
  that week on request instead ("work log for 12 to 18 October").
- Each run ends with one line per week: the sheet link, or why no sheet was made.
