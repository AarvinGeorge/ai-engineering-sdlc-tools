# Changelog

## 0.1.0 — 2026-11-05

**First release.** One on-demand skill, `work-log`, and four standard-library scripts: `collect.py`
(transcripts and git history to sessions, with active time, the idle cutoff, the midnight split and
parallel sessions counted once), `scan.py` (the pre-upload privacy and style scan), `workbook.py`
(a three-tab `.xlsx` with live formulas, written without third-party libraries) and `periods.py`
(last week and the weekly gap finder). A setup guide for a weekly Claude Desktop local task, four
eval cases (not yet run), and 103 tests.

**Measured before release:**

- An `.xlsx` uploaded through the Google Drive connector's `create_file` becomes a Google Sheet with
  all three tabs, and Google recalculates the formulas: a test file whose stored totals were all set
  to 99 read back with the correct totals.
- Live check on one folder for last week: the collector stopped with "no sessions in scope" and its
  counts (0 sessions ever started in that folder, 3 sessions in the period elsewhere, 0 commits), so
  no sheet was made. That is the designed outcome; it also exposed the gap recorded in `ROADMAP.md`
  (work done in a folder from a session started in its parent is not attributed to it).

**Not yet verified:** one scheduled weekly run observed end to end in Claude Desktop; the evals.

**Review:** every task was built by Opus or Sonnet and reviewed by Fable with executed probes; a
final whole-branch review by Fable. Fixes from review include: the scan now covers every field
written to the sheet; dates are not mistaken for phone numbers; fallback single-tab sheets count as
saved for the weekly run; scope names come from the collector, not the model; commit dates use the
author date; an exact-email author filter.
