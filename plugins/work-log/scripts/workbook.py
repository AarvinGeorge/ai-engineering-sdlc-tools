#!/usr/bin/env python3
"""Entries JSON -> .xlsx work log, standard library only (zipfile + XML).

Usage: workbook.py ENTRIES.json [--out PATH.xlsx] [--b64 PATH] [--single-tab]

Input is the entries JSON shape checked by scan.py: {"meta": {...}, "entries": [...]}.
Default: three tabs (Entries, Daily totals with live SUMIFS/SUM formulas that also
carry cached values, About). --single-tab: one "Work log" tab, totals as values.
Default --out is ./<title>.xlsx. Prints one JSON summary object on stdout.
Exit 0 ok, 3 bad input (message names the entry id and field) or output not writable.
"""
import argparse
import base64
import hashlib
import json
import math
import os
import re
import sys
import zipfile
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wl_common import local_zone, plugin_version  # noqa: E402

SESSION = "Claude session"
MANUAL = "Manual (hours stated)"
TYPES = (SESSION, MANUAL)
HEADERS = ["Date", "Start", "End", "Estimated hours (from activity)",
           "Project", "Type", "Summary", "Entry ID"]
ENTRY_WIDTHS = [12, 10, 10, 16, 22, 16, 70, 12]
LIMITS = [
    "Cloud sessions (claude.ai/code) run elsewhere and are not in local transcripts.",
    "Work on other machines is not included unless the plugin runs there too.",
    "Hours are activity-based estimates, not clocked time.",
    "Periods older than the transcripts come only from earlier sheets.",
]
HOW = ("Active time from message timestamps, minus gaps longer than the idle cutoff; "
       "parallel sessions counted once; rounded to 0.25 h. Manual entries carry the hours stated.")
BACKGROUND = "Waiting on a long background job with no messages is not counted."
FORMAT_NOTE = "Single tab with totals written as values (fallback)."
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ILLEGAL = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f￾￿\ud800-\udfff]")
ZIP_TIME = (1980, 1, 1, 0, 0, 0)

NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
XML_DECL = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'


class BadInput(Exception):
    pass


# ---------- validation and numbers ----------

def parse_day(value, what):
    if not isinstance(value, str) or not ISO.match(value):
        raise BadInput("%s: date must be YYYY-MM-DD, got %r" % (what, value))
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise BadInput("%s: date is not a real date: %r" % (what, value))


def is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def hours_of(e):
    if e["type"] == SESSION:
        return math.floor(e["minutes"] / 15 + 0.5) / 4
    return float(e["stated_hours"])


def validate(data):
    if not isinstance(data, dict) or not isinstance(data.get("meta"), dict):
        raise BadInput("input must be an object with a meta object")
    meta = data["meta"]
    entries = data.get("entries")
    if not isinstance(entries, list) or not entries:
        raise BadInput("no entries: the entries list is empty or missing")
    for k in ("scope_name", "period_start", "period_end"):
        if not isinstance(meta.get(k), str) or not meta[k]:
            raise BadInput("meta.%s is missing" % k)
    start = parse_day(meta["period_start"], "meta.period_start")
    end = parse_day(meta["period_end"], "meta.period_end")
    if end < start:
        raise BadInput("meta.period_end is before meta.period_start")
    seen = set()
    for i, e in enumerate(entries):
        if not isinstance(e, dict):
            raise BadInput("entry #%d: not an object" % (i + 1))
        eid = e.get("id")
        if not isinstance(eid, str) or not eid:
            raise BadInput("entry #%d: id is missing" % (i + 1))
        if eid in seen:
            raise BadInput("%s: duplicate id" % eid)
        seen.add(eid)
        d = parse_day(e.get("date"), eid)
        if not start <= d <= end:
            raise BadInput("%s: date %s is outside the period %s to %s"
                           % (eid, e["date"], meta["period_start"], meta["period_end"]))
        if e.get("type") not in TYPES:
            raise BadInput("%s: type must be one of %s, got %r" % (eid, " / ".join(TYPES), e.get("type")))
        if e["type"] == SESSION:
            if not is_number(e.get("minutes")) or e["minutes"] < 0:
                raise BadInput("%s: minutes must be a number >= 0" % eid)
        elif not is_number(e.get("stated_hours")) or e["stated_hours"] < 0:
            raise BadInput("%s: stated_hours must be a number >= 0" % eid)
        if not isinstance(e.get("project"), str) or not e["project"].strip():
            raise BadInput("%s: project is missing or empty" % eid)
        for k in ("start", "end", "summary"):
            if e.get(k) is not None and not isinstance(e[k], str):
                raise BadInput("%s: %s must be text" % (eid, k))
    return meta, entries


def num(x):
    x = round(float(x), 10)
    return str(int(x)) if x.is_integer() else repr(x)


def clean_total(x):
    return round(x, 10)


# ---------- naming ----------

def title_of(meta):
    lead = "Work log manual entry" if meta.get("kind") == "manual" else "Work log"
    return "%s · %s · %s to %s" % (lead, meta["scope_name"], meta["period_start"], meta["period_end"])


def folder_of(meta):
    return {"weekly": "Work Logs/Weekly", "manual": "Work Logs/Manual"}.get(meta.get("kind"), "Work Logs")


def file_name(title):
    # A '/' in a scope name would turn the name into a path; keep the name, swap the separator.
    for sep in {os.sep, "/", os.altsep or "/"}:
        title = title.replace(sep, "-")
    return title + ".xlsx"


# ---------- rows (lists of cells; a cell is None, str, number, or ("f", formula, cached)) ----------

def sorted_rows(entries):
    # Sort by (date, start, id); an entry with no start time (manual) goes after the timed ones that day.
    rows = []
    for e in sorted(entries, key=lambda e: (e["date"], not e.get("start"), e.get("start") or "", e["id"])):
        rows.append((e, hours_of(e)))
    return rows


def entry_cells(e, h):
    return [e["date"], e.get("start") or None, e.get("end") or None, h,
            e["project"], e["type"], e.get("summary") or "", e["id"]]


def totals(rows):
    by_day, by_day_proj = {}, {}
    for e, h in rows:
        by_day[e["date"]] = by_day.get(e["date"], 0.0) + h
        k = (e["date"], e["project"])
        by_day_proj[k] = by_day_proj.get(k, 0.0) + h
    return by_day, by_day_proj


def about_rows(meta):
    try:
        zone, zone_name = local_zone(meta.get("tz"))
    except Exception:  # unknown IANA name: say so, fall back to this machine's zone
        zone, zone_name = local_zone(None)
        print("workbook: note: unknown time zone %r, using %s" % (meta.get("tz"), zone_name), file=sys.stderr)
    created = meta.get("created") or "%s %s" % (datetime.now(zone).strftime("%Y-%m-%dT%H:%M"), zone_name)
    idle = meta.get("idle_minutes", 15)
    rows = [
        ["Period covered", "%s to %s" % (meta["period_start"], meta["period_end"])],
        ["Scope", meta["scope_name"]],
        ["Time zone", zone_name],
        ["Idle cutoff", "%s minutes" % num(idle) if is_number(idle) else "15 minutes"],
        ["Sources used", ", ".join(str(s) for s in meta.get("sources") or [])],
        ["Created", created],
        ["Plugin version", plugin_version()],
        ["How hours are estimated", HOW],
        ["Background work", BACKGROUND],
    ]
    rows += [["Limit", line] for line in LIMITS]
    rows += [["Note", str(n)] for n in meta.get("notes") or []]
    for w in meta.get("missing_weeks") or []:
        rows.append(["Not rebuilt", "%s to %s: transcripts no longer exist and no earlier sheet covers it"
                     % (w.get("start"), w.get("end"))])
    return rows


def sheet_ref(name):
    if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
        return name + "!"
    return "'%s'!" % name.replace("'", "''")


def three_tabs(meta, rows):
    by_day, by_day_proj = totals(rows)
    entries = [HEADERS] + [entry_cells(e, h) for e, h in rows]
    E = sheet_ref("Entries")
    daily = [["Date", "Project", "Hours"]]
    for d in sorted(by_day):
        projects = sorted({p for (dd, p) in by_day_proj if dd == d}, key=lambda p: (p.lower(), p))
        for p in projects:
            r = len(daily) + 1
            f = "SUMIFS({E}$D:$D,{E}$A:$A,$A{r},{E}$E:$E,$B{r})".format(E=E, r=r)
            daily.append([d, p, ("f", f, by_day_proj[(d, p)])])
        r = len(daily) + 1
        f = "SUMIFS({E}$D:$D,{E}$A:$A,$A{r})".format(E=E, r=r)
        daily.append([d, "All projects (day total)", ("f", f, by_day[d])])
    grand = sum(h for _, h in rows)
    daily.append(["Grand total", None, ("f", "SUM({E}$D$2:$D${n})".format(E=E, n=len(rows) + 1), grand)])
    about = [["Item", "Detail"]] + about_rows(meta)
    return [
        ("Entries", entries, ENTRY_WIDTHS, {6}),
        ("Daily totals", daily, [12, 26, 12], set()),
        ("About", about, [24, 90], {1}),
    ], by_day, grand


def single_tab(meta, rows):
    by_day, _ = totals(rows)
    out = [HEADERS]
    for i, (e, h) in enumerate(rows):
        out.append(entry_cells(e, h))
        if i + 1 == len(rows) or rows[i + 1][0]["date"] != e["date"]:
            out.append([e["date"], None, None, by_day[e["date"]], "Day total"])
    grand = sum(h for _, h in rows)
    out.append(["Grand total", None, None, grand])
    out.append([])
    out.append(["Item", "Detail"])
    out += about_rows(meta)
    out.append(["Format", FORMAT_NOTE])
    return [("Work log", out, ENTRY_WIDTHS, {6})], by_day, grand


# ---------- XML ----------

def esc(s):
    s = ILLEGAL.sub("", str(s))
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def col_letter(i):
    s = ""
    i += 1
    while i:
        i, rem = divmod(i - 1, 26)
        s = chr(65 + rem) + s
    return s


def cell_xml(ref, v, style):
    s = ' s="%d"' % style if style else ""
    if isinstance(v, tuple):
        return '<c r="%s"%s><f>%s</f><v>%s</v></c>' % (ref, s, esc(v[1]), num(v[2]))
    if is_number(v):
        return '<c r="%s"%s><v>%s</v></c>' % (ref, s, num(v))
    return '<c r="%s"%s t="inlineStr"><is><t xml:space="preserve">%s</t></is></c>' % (ref, s, esc(v))


def sheet_xml(rows, widths, wrap_cols, header_rows):
    max_col = max(len(r) for r in rows)
    last_ref = "%s%d" % (col_letter(max_col - 1), len(rows))
    parts = [XML_DECL, '<worksheet xmlns="%s" xmlns:r="%s">' % (NS_MAIN, NS_R),
             '<dimension ref="A1:%s"/>' % last_ref,
             '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" '
             'activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>',
             '<sheetFormatPr defaultRowHeight="15"/>', "<cols>"]
    for i, w in enumerate(widths):
        parts.append('<col min="%d" max="%d" width="%d" customWidth="1"/>' % (i + 1, i + 1, w))
    parts.append("</cols><sheetData>")
    for ri, row in enumerate(rows, start=1):
        cells = []
        for ci, v in enumerate(row):
            if v is None or v == "":
                continue
            style = 1 if ri in header_rows else (2 if ci in wrap_cols else 0)
            cells.append(cell_xml("%s%d" % (col_letter(ci), ri), v, style))
        if cells:
            parts.append('<row r="%d">%s</row>' % (ri, "".join(cells)))
    parts.append("</sheetData></worksheet>")
    return "".join(parts)


STYLES = (XML_DECL + '<styleSheet xmlns="%s">' % NS_MAIN +
          '<fonts count="2"><font><sz val="11"/><name val="Calibri"/><family val="2"/></font>'
          '<font><b/><sz val="11"/><name val="Calibri"/><family val="2"/></font></fonts>'
          '<fills count="2"><fill><patternFill patternType="none"/></fill>'
          '<fill><patternFill patternType="gray125"/></fill></fills>'
          '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
          '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
          '<cellXfs count="3">'
          '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
          '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/>'
          '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1">'
          '<alignment vertical="top" wrapText="1"/></xf>'
          '</cellXfs>'
          '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
          '</styleSheet>')


def package(tabs):
    n = len(tabs)
    ct = [XML_DECL, '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
          '<Default Extension="xml" ContentType="application/xml"/>',
          '<Override PartName="/xl/workbook.xml" '
          'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
          '<Override PartName="/xl/styles.xml" '
          'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>']
    for i in range(1, n + 1):
        ct.append('<Override PartName="/xl/worksheets/sheet%d.xml" '
                  'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' % i)
    ct.append("</Types>")
    root_rels = (XML_DECL + '<Relationships xmlns="%s">' % NS_PKG_REL +
                 '<Relationship Id="rId1" Type="%s/officeDocument" Target="xl/workbook.xml"/>' % NS_R +
                 "</Relationships>")
    wb = [XML_DECL, '<workbook xmlns="%s" xmlns:r="%s">' % (NS_MAIN, NS_R),
          '<bookViews><workbookView activeTab="0"/></bookViews><sheets>']
    rels = [XML_DECL, '<Relationships xmlns="%s">' % NS_PKG_REL]
    for i, (name, _, _, _) in enumerate(tabs, start=1):
        wb.append('<sheet name="%s" sheetId="%d" r:id="rId%d"/>' % (esc(name), i, i))
        rels.append('<Relationship Id="rId%d" Type="%s/worksheet" Target="worksheets/sheet%d.xml"/>'
                    % (i, NS_R, i))
    wb.append('</sheets><calcPr calcId="191029" fullCalcOnLoad="1"/></workbook>')
    rels.append('<Relationship Id="rId%d" Type="%s/styles" Target="styles.xml"/>' % (n + 1, NS_R))
    rels.append("</Relationships>")
    parts = [("[Content_Types].xml", "".join(ct)), ("_rels/.rels", root_rels),
             ("xl/workbook.xml", "".join(wb)), ("xl/_rels/workbook.xml.rels", "".join(rels)),
             ("xl/styles.xml", STYLES)]
    for i, (_, rows, widths, wrap) in enumerate(tabs, start=1):
        headers = {1} | {ri for ri, r in enumerate(rows, start=1) if r == ["Item", "Detail"]}
        parts.append(("xl/worksheets/sheet%d.xml" % i, sheet_xml(rows, widths, wrap, headers)))
    return parts


def write_zip(path, parts):
    with zipfile.ZipFile(path, "w") as z:
        for name, text in parts:
            info = zipfile.ZipInfo(name, date_time=ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, text.encode("utf-8"))


# ---------- CLI ----------

def main(argv=None):
    ap = argparse.ArgumentParser(description="Build the work-log .xlsx from entries JSON.")
    ap.add_argument("entries")
    ap.add_argument("--out")
    ap.add_argument("--b64")
    ap.add_argument("--single-tab", action="store_true")
    a = ap.parse_args(argv)
    try:
        with open(a.entries, encoding="utf-8") as fh:
            data = json.load(fh)
        meta, entries = validate(data)
    except (OSError, ValueError) as exc:
        print("workbook: cannot read %s: %s" % (a.entries, exc), file=sys.stderr)
        return 3
    except BadInput as exc:
        print("workbook: bad input: %s" % exc, file=sys.stderr)
        return 3
    rows = sorted_rows(entries)
    tabs, by_day, grand = (single_tab if a.single_tab else three_tabs)(meta, rows)
    title = title_of(meta)
    out = a.out or os.path.join(".", file_name(title))
    try:
        write_zip(out, package(tabs))
        with open(out, "rb") as fh:
            blob = fh.read()
        if a.b64:
            with open(a.b64, "w", encoding="ascii", newline="") as fh:
                fh.write(base64.b64encode(blob).decode("ascii"))
    except OSError as exc:
        print("workbook: cannot write output: %s" % exc, file=sys.stderr)
        return 3
    summary = {"path": os.path.abspath(out), "title": title, "bytes": len(blob),
               "sha256": hashlib.sha256(blob).hexdigest(), "tabs": [t[0] for t in tabs],
               "entries": len(rows), "day_totals": {d: clean_total(by_day[d]) for d in sorted(by_day)},
               "grand_total": clean_total(grand), "folder": folder_of(meta)}
    if a.b64:
        summary["b64_path"] = os.path.abspath(a.b64)
    sys.stdout.buffer.write((json.dumps(summary, ensure_ascii=False) + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
