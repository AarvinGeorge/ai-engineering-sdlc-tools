#!/usr/bin/env python3
"""Render plan.json into a self-contained HTML page.

Data and presentation stay separate on purpose: the agent edits plan.json,
this renders it, the human reads the HTML. Nobody hand-edits the HTML -- it is
generated output and will be overwritten. If this script ever breaks, the JSON
is still readable on its own, which is the point.

Every section is optional. A project that only fills in `plans` gets a page
with only plans on it, and nothing looks broken. Sections are assembled as a
list rather than substituted into one large format string -- a positional
format string with thirty slots silently scrambles the whole page the first
time someone inserts a section in the middle.

The output is fully self-contained: no scripts, no fonts, no external
requests. Open it locally, host it anywhere, publish it as an artifact.

Usage:
  render.py            write the page
  render.py --check    exit 1 if the page is stale relative to plan.json
"""
import hashlib
import html
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plan_lib as L  # noqa: E402

BUILD = {
    "done": ("Done", "s-done"),
    "active": ("In progress", "s-active"),
    "partial": ("Partial", "s-partial"),
    "not-started": ("Not started", "s-none"),
}
PLAN = {
    "planned": ("Planned", "s-done"),
    "partial": ("Partial", "s-partial"),
    "none": ("No plan", "s-gap"),
}
# Defaults are overridable per project via meta.headings, because "systems"
# means something different in every codebase.
HEADINGS = {
    "figures": ("The plan in pictures", "the shape of the work, before the detail"),
    "systems": ("Systems", "where we came from, where we are, where we are going"),
    "capabilities": ("Capabilities", "what exists — and whether a plan covers it"),
    "cycle": ("The development cycle", "every unit of work moves through these stages"),
    "done": ("Plans completed", "the historical record"),
    "now": ("Active now", ""),
    "next": ("Next", "agreed direction; each still needs a written plan before work starts"),
    "parked": ("Parked", "deferred by decision, not oversight"),
    "invariants": ("Invariants", "things that must stay true"),
    "glossary": ("Glossary", ""),
}


def e(x):
    return html.escape(str(x), quote=True)


def fingerprint(src):
    return hashlib.sha256(open(src, "rb").read()).hexdigest()[:12]


def is_stale(src, out):
    """True when the page was rendered from a different plan.json.

    Lets the page SAY it is stale rather than quietly showing old data -- the
    failure mode this whole tool exists to avoid.
    """
    if not os.path.exists(out):
        return True
    try:
        return ('data-fingerprint="%s"' % fingerprint(src)) not in \
            open(out, encoding="utf-8").read()
    except Exception:
        return True


def pill(mapping, key):
    label, cls = mapping.get(key, (key, "s-none"))
    return '<span class="pill %s">%s</span>' % (cls, e(label))


def h2(d, key):
    title, hint = d.get("meta", {}).get("headings", {}).get(key) or HEADINGS[key]
    return '<h2>%s%s</h2>' % (
        e(title), ' <span class="hint">%s</span>' % e(hint) if hint else "")


# --------------------------------------------------------------------------
# Section builders. Each returns "" when its data is absent, so the page
# contains exactly the sections the project actually filled in.
# --------------------------------------------------------------------------
def sec_figures(d, mod):
    """Figures come as a (markup, css) pair.

    Markup alone is not enough and shipping it alone was a real bug: an SVG
    <rect> with no stylesheet defaults to solid black fill, so a figure whose
    styles went missing renders as a row of black boxes with invisible text --
    worse than no figure, because it looks like the page is broken rather than
    the styles. A figures module may define a module-level CSS string, which is
    appended to the page stylesheet.
    """
    if not mod:
        return "", ""
    try:
        body = mod.build(d)
    except Exception as exc:
        print("  warning: figures.build() raised (%s); skipping figures" % exc)
        return "", ""
    if not body:
        return "", ""
    css = getattr(mod, "CSS", "") or ""
    if not css:
        print("  note: figures supply no CSS. If the markup uses classes, they will be "
              "unstyled — an SVG rect with no fill rule renders solid black.")
    return h2(d, "figures") + body, css


def sec_systems(d):
    items = d.get("systems") or []
    if not items:
        return ""
    cards = "".join(
        '<article class="sys sys--%s"><header><h3>%s</h3>%s%s</header><dl>%s</dl></article>' % (
            e(s.get("id", "")), e(s.get("label", "")),
            '<p class="serves">%s</p>' % e(s["serves"]) if s.get("serves") else "",
            '<p class="sysnote">%s</p>' % e(s["note"]) if s.get("note") else "",
            "".join('<div class="fact"><dt>%s</dt><dd>%s</dd></div>' % (e(k), e(v))
                    for k, v in s.get("facts", [])))
        for s in items)
    return h2(d, "systems") + '<div class="systems">%s</div>' % cards


def sec_capabilities(d):
    caps = d.get("capabilities") or []
    if not caps:
        return ""
    rows = "".join(
        '<tr><td class="num">%s</td><td><div class="capname">%s</div>%s</td>'
        '<td>%s</td><td>%s</td><td class="where">%s</td><td class="evidence">%s</td></tr>' % (
            e(c.get("id", "")), e(c.get("name", "")),
            '<div class="capwhat">%s</div>' % e(c["what"]) if c.get("what") else "",
            pill(BUILD, c.get("build")), pill(PLAN, c.get("plan")),
            e(c.get("where", "")), e(c.get("evidence", "")))
        for c in caps)
    return h2(d, "capabilities") + (
        '<div class="tablewrap"><table><thead><tr><th></th><th>Capability</th>'
        '<th>Built</th><th>Planned</th><th>Where defined</th><th>Evidence</th></tr></thead>'
        '<tbody>%s</tbody></table></div>' % rows)


def sec_cycle(d):
    cyc = d.get("cycle") or L.DEFAULT_CYCLE
    stages = cyc.get("stages") or []
    if not stages:
        return ""
    items = "".join(
        '<li class="cyst"><span class="cyn">%d</span><div><b>%s</b>%s%s%s</div></li>' % (
            i + 1, e(st.get("name", "")),
            '<span class="cywho">%s</span>' % e(st["who"]) if st.get("who") else "",
            '<p class="cydone">%s</p>' % e(st["done_when"]) if st.get("done_when") else "",
            '<p class="cyskip"><b>Skipped, it looks like:</b> %s</p>' % e(st["skipped_looks_like"])
            if st.get("skipped_looks_like") else "")
        for i, st in enumerate(stages))
    intro = '<p class="cyintro">%s</p>' % e(cyc["what"]) if cyc.get("what") else ""
    return h2(d, "cycle") + intro + '<ol class="cycle">%s</ol>' % items


def stagechip(d, p):
    """Where this item sits on the cycle. Absent is worth showing, not hiding."""
    names = {s["id"]: s.get("name", s["id"])
             for s in (d.get("cycle") or L.DEFAULT_CYCLE).get("stages", [])}
    sid = p.get("stage")
    if not sid:
        return ""
    return '<span class="stage stage--%s">%s</span>' % (e(sid), e(names.get(sid, sid)))


def capchip(d, p):
    """Which capability this work serves.

    Without it, the capabilities table and the plan lists are two documents
    that happen to share a page: a reader cannot tell that "tenant identity in
    traces" IS the observability row. Naming the link makes the page one
    argument instead of several.
    """
    cid = p.get("capability")
    if cid is None:
        return ""
    cap = next((c for c in d.get("capabilities", []) if str(c.get("id")) == str(cid)), None)
    return '<span class="capref">%s %s</span>' % (
        e(cid), e(cap["name"]) if cap else "unknown capability")


def planlink(p):
    """A pointer to the executable plan, or an honest statement that none exists."""
    return ('<code class="planfile">%s</code>' % e(p["plan_file"])) if p.get("plan_file") \
        else '<span class="pill s-gap">No plan written yet</span>'


def sec_done(d):
    items = (d.get("plans") or {}).get("done") or []
    if not items:
        return ""
    li = "".join(
        '<li class="plan plan--done"><div class="planhead"><span class="planname">%s</span>'
        '<span class="planmeta">%s</span></div>%s%s%s</li>' % (
            e(p.get("name", "")),
            e(" · ".join(str(p[k]) for k in ("period", "tasks") if p.get(k))),
            '<p class="planout">%s</p>' % e(p["outcome"]) if p.get("outcome") else "",
            '<p class="plannote"><b>What it taught us:</b> %s</p>' % e(p["notable"])
            if p.get("notable") else "",
            '<code class="planfile">%s</code>' % e(p["file"]) if p.get("file") else "")
        for p in items)
    return h2(d, "done") + '<ul class="plans">%s</ul>' % li


def sec_now(d):
    items = (d.get("plans") or {}).get("now")
    if items is None:
        return ""
    li = "".join(
        '<li class="plan plan--active"><div class="planhead"><span class="planname">%s</span>'
        '%s%s%s%s</div>%s</li>' % (
            e(p.get("name", "")), stagechip(d, p), capchip(d, p), planlink(p),
            '<span class="planmeta">updated %s</span>' % e(p["updated"]) if p.get("updated") else "",
            '<p class="planout">%s</p>' % e(p["status"]) if p.get("status") else "")
        for p in items) or '<li class="plan plan--idle"><p class="planout">Nothing active.</p></li>'
    return h2(d, "now") + '<ul class="plans">%s</ul>' % li


def sec_next(d):
    items = (d.get("plans") or {}).get("next") or []
    if not items:
        return ""
    li = "".join(
        '<li class="plan plan--next"><div class="planhead"><span class="planname">%s</span>'
        '%s%s%s</div>%s%s</li>' % (
            e(p.get("name", "")), stagechip(d, p), capchip(d, p), planlink(p),
            '<p class="planout">%s</p>' % e(p["why"]) if p.get("why") else "",
            '<p class="unblocks"><b>Unblocks:</b> %s</p>' % e(p["unblocks"])
            if p.get("unblocks") else "")
        for p in items)
    return h2(d, "next") + '<ul class="plans">%s</ul>' % li


def sec_parked(d):
    items = d.get("parked") or []
    if not items:
        return ""
    li = "".join(
        '<li><div class="pk"><code>%s</code>%s</div>%s%s</li>' % (
            e(p.get("id", "")),
            '<span class="trigger">%s</span>' % e(p["trigger"]) if p.get("trigger") else "",
            '<p class="pq">%s</p>' % e(p["q"]) if p.get("q") else "",
            '<p class="pn">%s</p>' % e(p["note"]) if p.get("note") else "")
        for p in items)
    return h2(d, "parked") + '<ul class="parked">%s</ul>' % li


def sec_invariants(d):
    items = d.get("invariants") or []
    if not items:
        return ""
    li = "".join(
        '<li class="inv"><span class="invrule">%s</span>'
        '<span class="invstate inv--%s">%s</span><span class="invdetail">%s</span></li>' % (
            e(i.get("rule", "")),
            # An invariant that is not holding must not render in the same green
            # as one that is. A green "at risk" is a quiet lie.
            "ok" if i.get("state") == "holding" else "warn",
            e(i.get("state", "")), e(i.get("detail", "")))
        for i in items)
    return h2(d, "invariants") + '<ul class="invs">%s</ul>' % li


def sec_glossary(d):
    items = d.get("glossary") or []
    if not items:
        return ""
    return h2(d, "glossary") + '<dl class="gloss">%s</dl>' % "".join(
        '<div class="gterm"><dt>%s</dt><dd>%s</dd></div>' % (e(g.get("term", "")), e(g.get("def", "")))
        for g in items)


# Canonical contract keys get a considered label; anything else starting with
# "for_" is rendered too, with the name derived from the key. A project that
# writes `for_aarvin` or `for_the_team` must not have it silently dropped --
# an allow-list of key names is a trap that only shows up as missing text.
CONTRACT_LABELS = {
    "for_agent": "For the agent — read this first, every session",
    "for_claude": "For the agent — read this first, every session",
    "for_human": "For the human",
    "for_owner": "For the human",
}


def sec_contract(d):
    c = d.get("contract") or {}
    parts = [(k, v) for k, v in c.items()
             if k.startswith("for_") and isinstance(v, str) and v.strip()]
    if not parts:
        return ""
    return '<div class="contract">%s</div>' % "".join(
        '<div><b>%s</b><p>%s</p></div>' % (
            e(CONTRACT_LABELS.get(k, "For " + k[4:].replace("_", " ").title())), e(v))
        for k, v in parts)


def sec_orientation(d):
    o = d.get("orientation") or {}
    order = [("what", "What this is"), ("why", "Why it matters"),
             ("shape", "How it is set up"), ("how_to_read", "How to read this page")]
    parts = [(lbl, o[k]) for k, lbl in order if o.get(k)]
    if not parts:
        return ""
    return '<div class="orient">%s</div>' % "".join(
        '<div><b>%s</b><p>%s</p></div>' % (e(lbl), e(v)) for lbl, v in parts)


def sec_northstar(d):
    m = d.get("meta", {})
    if not m.get("north_star"):
        return ""
    owner = m.get("north_star_owner")
    return ('<p class="ns">%s<strong>%s</strong></p>' % (
        '<span class="lock">North star · frozen · owner %s</span><br>' % e(owner) if owner else "",
        e(m["north_star"])))


def metrics(d):
    caps = d.get("capabilities") or []
    nxt = (d.get("plans") or {}).get("next") or []
    out = []
    if caps:
        out.append(('<div class="metric"><b>%d/%d</b><span>capabilities built</span></div>'
                    % (sum(1 for c in caps if c.get("build") == "done"), len(caps))))
    done = (d.get("plans") or {}).get("done") or []
    if done:
        out.append('<div class="metric"><b>%d</b><span>plans complete</span></div>' % len(done))
    gaps = sum(1 for p in nxt if not p.get("plan_file"))
    if nxt:
        out.append('<div class="metric warn"><b>%d</b><span>no plan yet</span></div>' % gaps)
    return '<div class="metrics">%s</div>' % "".join(out) if out else ""


CSS = """
  /* Light-theme --muted and --active were measured at 4.31:1 and 4.09:1 against
     the card ground -- both just under WCAG AA's 4.5:1 for body text, and both
     used for real content (section hints, sub-labels inside diagrams). Darkened
     to 4.89:1 and 4.94:1. The dark palette measured 5.2:1 and up already. */
  :root{--ink:#14171c;--ink-2:#3d4652;--muted:#67727f;--ground:#f6f7f9;--card:#fff;
    --line:#e2e6ea;--accent:#0f6b68;--accent-soft:#e6f0ef;--done:#2f7d5d;--active:#a26105;
    --gap:#a03232;--partial:#5b6f8a;--radius:6px}
  @media(prefers-color-scheme:dark){:root{--ink:#e8ecf1;--ink-2:#b9c3ce;--muted:#8794a3;
    --ground:#12151a;--card:#191d24;--line:#2a313a;--accent:#4fb3ac;--accent-soft:#12302f;
    --done:#5cb98c;--active:#d9a04a;--gap:#d97070;--partial:#8aa2bf}}
  :root[data-theme="dark"]{--ink:#e8ecf1;--ink-2:#b9c3ce;--muted:#8794a3;--ground:#12151a;
    --card:#191d24;--line:#2a313a;--accent:#4fb3ac;--accent-soft:#12302f;--done:#5cb98c;
    --active:#d9a04a;--gap:#d97070;--partial:#8aa2bf}
  :root[data-theme="light"]{--ink:#14171c;--ink-2:#3d4652;--muted:#67727f;--ground:#f6f7f9;
    --card:#fff;--line:#e2e6ea;--accent:#0f6b68;--accent-soft:#e6f0ef;--done:#2f7d5d;
    --active:#a26105;--gap:#a03232;--partial:#5b6f8a}
  *{box-sizing:border-box}
  body{margin:0;background:var(--ground);color:var(--ink);
    font-family:system-ui,-apple-system,"Segoe UI",sans-serif;font-size:15px;line-height:1.55;
    -webkit-font-smoothing:antialiased}
  .wrap{max-width:1180px;margin:0 auto;padding:28px 22px 72px}
  code,.commits,time,.planfile{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
  .bar{display:flex;flex-wrap:wrap;gap:18px 26px;align-items:baseline;padding:16px 18px;
    background:var(--card);border:1px solid var(--line);border-radius:var(--radius);
    border-left:3px solid var(--accent)}
  .bar h1{margin:0;font-size:19px;font-weight:600;letter-spacing:-.01em}
  .bar .sub{color:var(--muted);font-size:13px;margin:2px 0 0}
  .metrics{display:flex;gap:22px;margin-left:auto}
  .metric{text-align:right}
  .metric b{display:block;font-size:20px;font-variant-numeric:tabular-nums;line-height:1.1}
  .metric span{font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:var(--muted)}
  .metric.warn b{color:var(--gap)}
  .stale{margin:14px 0 0;padding:12px 16px;border-radius:var(--radius);
    background:var(--gap);color:#fff;font-size:13.5px;font-weight:600}
  .contract{margin:14px 0 0;padding:14px 18px;background:var(--accent-soft);
    border:1px solid var(--accent);border-radius:var(--radius);display:grid;
    grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px}
  .contract div>b{display:block;font-size:10.5px;text-transform:uppercase;letter-spacing:.07em;
    color:var(--accent);margin-bottom:3px}
  .contract p{margin:0;font-size:12.5px;color:var(--ink-2)}
  .orient{margin:14px 0 0;padding:16px 18px;background:var(--card);border:1px solid var(--line);
    border-radius:var(--radius);display:grid;
    grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px}
  .orient div>b{display:block;font-size:10.5px;text-transform:uppercase;letter-spacing:.07em;
    color:var(--accent);margin-bottom:3px}
  .orient p{margin:0;font-size:13.5px;color:var(--ink-2)}
  .ns{margin:12px 0 0;padding:13px 16px;background:var(--accent-soft);border-radius:var(--radius);
    font-size:13.5px;color:var(--ink-2)}
  .ns strong{color:var(--ink)}
  .lock{font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:var(--accent);
    font-weight:600}
  h2{font-size:12px;text-transform:uppercase;letter-spacing:.09em;color:var(--muted);
    font-weight:600;margin:38px 0 12px;padding-bottom:7px;border-bottom:1px solid var(--line)}
  h2 .hint{text-transform:none;letter-spacing:0;font-weight:400;color:var(--muted);margin-left:8px}
  .systems{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:14px}
  .sys{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);
    padding:16px 17px}
  .sys h3{margin:0;font-size:15px}
  .sys .serves{margin:1px 0 0;font-size:12.5px;color:var(--accent);font-weight:500}
  .sys .sysnote{margin:7px 0 13px;font-size:12.5px;color:var(--muted)}
  .sys dl{margin:0;display:flex;flex-direction:column;gap:8px}
  .fact dt{font-size:10.5px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}
  .fact dd{margin:1px 0 0;font-size:13px;color:var(--ink-2)}
  .sys--target{border-style:dashed}
  .tablewrap{overflow-x:auto;border:1px solid var(--line);border-radius:var(--radius);
    background:var(--card)}
  table{border-collapse:collapse;width:100%;min-width:840px}
  th{text-align:left;font-size:10.5px;text-transform:uppercase;letter-spacing:.06em;
    color:var(--muted);font-weight:600;padding:11px 13px;border-bottom:1px solid var(--line)}
  td{padding:12px 13px;border-bottom:1px solid var(--line);vertical-align:top;font-size:13px}
  tr:last-child td{border-bottom:0}
  .num{font-variant-numeric:tabular-nums;color:var(--muted);width:26px}
  .capname{font-weight:600;font-size:13.5px}
  .capwhat{color:var(--muted);font-size:12.5px;margin-top:2px}
  .where{color:var(--ink-2);font-size:12.5px}
  .evidence{color:var(--muted);font-size:12.5px}
  .pill{display:inline-block;padding:2px 9px;border-radius:20px;font-size:11px;font-weight:600;
    white-space:nowrap;border:1px solid currentColor}
  .s-done{color:var(--done)}.s-active{color:var(--active)}.s-partial{color:var(--partial)}
  .s-gap{color:var(--gap)}.s-none{color:var(--muted)}
  .cyintro{margin:0 0 12px;font-size:13px;color:var(--ink-2)}
  .cycle{list-style:none;margin:0;padding:0;display:grid;
    grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:10px}
  .cyst{display:flex;gap:11px;padding:13px 15px;background:var(--card);
    border:1px solid var(--line);border-radius:var(--radius);border-top:2px solid var(--accent)}
  .cyn{font-variant-numeric:tabular-nums;font-size:11px;font-weight:700;color:var(--accent);
    border:1px solid var(--accent);border-radius:50%;width:20px;height:20px;flex:none;
    display:flex;align-items:center;justify-content:center;margin-top:1px}
  .cyst b{font-size:13.5px}
  .cywho{font-size:10.5px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);
    margin-left:7px}
  .cydone{margin:4px 0 0;font-size:12.5px;color:var(--ink-2)}
  .cyskip{margin:6px 0 0;font-size:11.5px;color:var(--muted)}
  .cyskip b{color:var(--gap);font-weight:600}
  .stage{display:inline-block;padding:2px 8px;border-radius:20px;font-size:10.5px;
    font-weight:600;text-transform:uppercase;letter-spacing:.05em;border:1px solid currentColor;
    white-space:nowrap}
  .stage--intent{color:var(--muted)}
  .stage--grounded{color:var(--partial)}
  .stage--planned{color:var(--accent)}
  .stage--building{color:var(--active)}
  .stage--verified{color:var(--done)}
  .stage--recorded{color:var(--done)}
  .capref{display:inline-block;padding:2px 8px;border-radius:4px;font-size:10.5px;
    font-weight:600;color:var(--accent);background:var(--accent-soft);white-space:nowrap}
  ul.plans{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:9px}
  .plan{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);
    padding:14px 16px;border-left:3px solid var(--muted)}
  .plan--done{border-left-color:var(--done)}
  .plan--active{border-left-color:var(--active)}
  .plan--next{border-left-color:var(--gap)}
  .plan--idle{border-left-color:var(--line)}
  .planhead{display:flex;align-items:center;gap:11px;flex-wrap:wrap}
  .planname{font-weight:600;font-size:14px}
  .planmeta{font-size:11.5px;color:var(--muted);font-family:ui-monospace,monospace}
  .planfile{font-size:11.5px;color:var(--accent)}
  .planout{margin:7px 0 0;font-size:13px;color:var(--ink-2)}
  .plannote,.unblocks{margin:6px 0 0;font-size:12.5px;color:var(--muted)}
  .plannote b,.unblocks b{color:var(--ink-2)}
  ul.parked{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:9px}
  ul.parked>li{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);
    padding:13px 16px}
  .pk{display:flex;gap:11px;align-items:baseline;flex-wrap:wrap}
  .pk code{font-weight:700;color:var(--accent)}
  .trigger{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}
  .pq{margin:5px 0 0;font-size:13.5px;font-weight:500}
  .pn{margin:4px 0 0;font-size:12.5px;color:var(--muted)}
  ul.invs{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:7px}
  .inv{display:grid;grid-template-columns:250px 78px 1fr;gap:12px;align-items:baseline;
    background:var(--card);border:1px solid var(--line);border-radius:var(--radius);
    padding:11px 15px}
  .invrule{font-size:13px;font-weight:600}
  .invstate{font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.05em}
  .inv--ok{color:var(--done)}
  .inv--warn{color:var(--gap)}
  .invdetail{font-size:12.5px;color:var(--muted)}
  .gloss{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:11px;margin:0}
  .gterm dt{font-size:12.5px;font-weight:600;color:var(--accent)}
  .gterm dd{margin:2px 0 0;font-size:12.5px;color:var(--muted)}
  footer{margin-top:44px;padding-top:16px;border-top:1px solid var(--line);
    font-size:11.5px;color:var(--muted)}
  footer ul{margin:9px 0 0;padding-left:17px}
  footer li{margin-bottom:3px}
  @media(max-width:760px){.metrics{margin-left:0;width:100%}
    .inv{grid-template-columns:1fr;gap:3px}}
"""


def build(d, root, fp):
    m = d.get("meta", {})
    figures_html, figures_css = sec_figures(d, L.load_figures(root))
    body = [
        '<div class="wrap" data-fingerprint="%s">' % fp,
        '<div class="bar"><div><h1>%s</h1>%s</div>%s</div>' % (
            e(m.get("project", "Plan")),
            '<p class="sub">%s</p>' % e(m["subtitle"]) if m.get("subtitle") else "",
            metrics(d)),
        sec_contract(d),
        sec_orientation(d),
        sec_northstar(d),
        figures_html,
        sec_systems(d),
        sec_capabilities(d),
        sec_cycle(d),
        sec_done(d),
        sec_now(d),
        sec_next(d),
        sec_parked(d),
        sec_invariants(d),
        sec_glossary(d),
    ]
    changes = "".join('<li><code>%s</code> <time>%s</time> %s</li>' % (
        e(c.get("version", "")), e(c.get("date", "")), e(c.get("note", "")))
        for c in m.get("changelog", []))
    body.append(
        '<footer>%s · rendered from commit <code>%s</code>%s · fingerprint <code>%s</code>'
        '%s<p>Generated from the plan JSON by plan-layer. Do not hand-edit this page — '
        'edit the JSON and re-render.</p></footer>' % (
            'Plan version <code>%s</code>' % e(m["plan_version"]) if m.get("plan_version")
            else "Plan",
            e(L.git(root, "rev-parse", "--short", "HEAD") or "unversioned"),
            ' · data updated <time>%s</time>' % e(m["updated"]) if m.get("updated") else "",
            fp, '<ul>%s</ul>' % changes if changes else ""))
    body.append("</div>")
    return ("<title>%s</title>\n<style>%s%s</style>\n%s"
            % (e(m.get("project", "Plan")), CSS, figures_css,
               "\n".join(x for x in body if x)))


def main():
    if not L.has_plan():
        print("  no plan in this project. Run the plan-layer skill's init to create one.")
        return 0

    p = L.paths()
    if "--check" in sys.argv:
        stale = is_stale(p["src"], p["out"])
        print("  STALE — plan.json changed since last render. Run: render.py"
              if stale else "  in sync — page matches plan.json")
        return 1 if stale else 0

    d = L.load()
    fp = fingerprint(p["src"])
    doc = build(d, p["root"], fp)
    with open(p["out"], "w", encoding="utf-8") as fh:
        fh.write(doc)
    print("  wrote %s (%s bytes)" % (p["out"], format(len(doc), ",")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
