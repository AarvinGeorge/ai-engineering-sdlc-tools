#!/usr/bin/env python3
"""Look at the figures, rather than reasoning about their coordinates.

A project supplies its own diagrams in plan/figures.py. Nothing about the
drawing generalises, but two ways of getting it wrong do, and both are
invisible in the source: a label that runs off the right edge of the drawing,
and two labels that land on the same line and print over each other. Both were
found in a figure that had already been read carefully, by a screenshot.

So this does two things:

  1. Extracts every <figure> from the rendered page into its own standalone
     HTML file carrying the page's own stylesheet, and screenshots each one
     into plan/.figures/NN.png with a headless browser, so a person or an
     agent can LOOK at it.
  2. Estimates the width of every text run and reports any run that crosses
     the right edge of its SVG, and any two runs that overlap on the same
     baseline.

Exit 1 on a page-edge crossing, a same-baseline overlap or an SVG that does
not parse. A label that may spill its own box is printed as "check" rather
than failing, because a label deliberately placed beside a box trips the same
estimate, and a check people learn to dismiss is worse than no check.

Whether a figure tells the truth about the system is the part no script can
do. Read the screenshots.

  figcheck.py              # check and screenshot
  figcheck.py --no-shots   # geometry only, no browser needed
"""
import html as _html
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import plan_lib as L  # noqa: E402

# Average glyph width as a fraction of the font size, calibrated against
# rendered pages in the system sans the page ships. Deliberately generous: a
# pass has to mean a pass.
EM = 0.50
DEFAULT_SIZE = 12.0

# Where a headless browser usually lives, per platform, plus whatever is on
# PATH. No browser is not an error: the geometry checks still run.
BROWSERS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser",
    "/usr/bin/microsoft-edge",
]


def find_browser():
    for name in ("google-chrome", "chromium", "chromium-browser", "chrome",
                 "microsoft-edge", "brave-browser"):
        p = shutil.which(name)
        if p:
            return p
    for p in BROWSERS:
        if os.path.exists(p):
            return p
    return None


def font_sizes(css):
    """class name -> font size in px, read from the page's own stylesheet.

    The sizes belong to the project's figures, so asking the stylesheet is the
    only way to know them without the checker carrying a copy that goes stale
    the first time a figure is restyled.
    """
    out = {}
    for block in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        sel, body = block.group(1), block.group(2)
        m = re.search(r"font-size:\s*([\d.]+)px", body)
        if not m:
            continue
        for cls in re.findall(r"\.([A-Za-z0-9_-]+)", sel):
            out[cls] = float(m.group(1))
    return out


def size_for(classes, sizes):
    """The most specific size we know about, else the default.

    Longest class name first, because a modifier like dg-lbl-b is written
    after the base class it refines and is the one that carries the size.
    """
    for cls in sorted(classes, key=len, reverse=True):
        if cls in sizes:
            return sizes[cls]
    return DEFAULT_SIZE


def runs(svg, sizes):
    """Every text run as (left, right, baseline, text)."""
    out = []
    for t in re.finditer(r'<text x="([\d.]+)" y="([\d.]+)"([^>]*)>([^<]*)</text>', svg):
        x, y, attrs, txt = float(t.group(1)), float(t.group(2)), t.group(3), \
            _html.unescape(t.group(4))
        cls = (re.search(r'class="([^"]*)"', attrs) or [None, ""])[1].split()
        anchor = (re.search(r'text-anchor="([^"]*)"', attrs) or [None, "middle"])[1]
        w = len(txt) * size_for(cls, sizes) * EM
        x0 = x if anchor == "start" else x - w if anchor == "end" else x - w / 2
        out.append((x0, x0 + w, y, txt))
    return out


def boxes(svg):
    return [(float(a), float(b), float(c), float(d)) for a, b, c, d in
            re.findall(r'<rect x="([\d.]+)" y="([\d.]+)" '
                       r'width="([\d.]+)" height="([\d.]+)"', svg)]


def check_figure(n, name, svg, sizes, say):
    problems = 0
    vb = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg)
    width = float(vb.group(1)) if vb else 1020.0
    try:
        ET.fromstring(svg.replace("&nbsp;", " "))
    except ET.ParseError as exc:
        say("FAIL  figure %d (%s): the SVG does not parse: %s" % (n, name, exc))
        problems += 1
    rects = boxes(svg)
    texts = runs(svg, sizes)

    for x0, x1, y, txt in texts:
        if x1 > width + 1:
            say("FAIL  figure %d (%s): text crosses the page edge: %r"
                % (n, name, txt[:60]))
            problems += 1
            continue
        holding = [r for r in rects
                   if r[0] <= x0 + 1 and r[1] <= y and r[0] + r[2] >= x0
                   and r[1] + r[3] >= y - 12]
        if holding:
            b = min(holding, key=lambda r: r[2] * r[3])
            if x1 > b[0] + b[2] + 2:
                say("check figure %d (%s): may spill its box: %r (~%dpx)"
                    % (n, name, txt[:60], int(x1 - (b[0] + b[2]))))

    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            a, b = texts[i], texts[j]
            if abs(a[2] - b[2]) < 4 and a[0] < b[1] - 2 and b[0] < a[1] - 2:
                say("FAIL  figure %d (%s): overlapping text: %r / %r"
                    % (n, name, a[3][:40], b[3][:40]))
                problems += 1
    return problems


def main():
    if not L.has_plan():
        print("  no plan in this project — nothing to check")
        return 0
    P = L.paths()
    page = P["out"]
    if not os.path.exists(page):
        print("  no page yet. Run render.py first.")
        return 0
    doc = open(page, encoding="utf-8").read()
    style = "".join(re.findall(r"<style[^>]*>(.*?)</style>", doc, re.S))
    sizes = font_sizes(style)
    figs = re.findall(r"<figure.*?</figure>", doc, re.S)
    if not figs:
        print("  the page has no figures")
        return 0

    out_dir = os.path.join(P["dir"], ".figures")
    os.makedirs(out_dir, exist_ok=True)
    browser = None if "--no-shots" in sys.argv else find_browser()
    problems = 0
    for n, fig in enumerate(figs, 1):
        label = re.search(r'aria-label="([^"]*)"', fig)
        name = (label.group(1) if label else "figure %d" % n)[:70]
        svg = re.search(r"<svg.*?</svg>", fig, re.S)
        if svg:
            problems += check_figure(n, name, svg.group(0), sizes, print)
        else:
            print("skip  figure %d (%s): no SVG, probably a table" % (n, name))
        shot = ('<!doctype html><html><head><meta charset="utf-8"><style>%s</style>'
                '<style>body{background:var(--ground);margin:0;padding:16px;width:1080px}'
                '</style></head><body><div class="wrap">%s</div></body></html>'
                % (style, fig))
        hp = os.path.join(out_dir, "%02d.html" % n)
        L.atomic_write(hp, shot)
        if browser:
            subprocess.run([browser, "--headless=new", "--disable-gpu",
                            "--hide-scrollbars", "--window-size=1120,900",
                            "--screenshot=%s" % os.path.join(out_dir, "%02d.png" % n),
                            "file://" + hp],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if not browser and "--no-shots" not in sys.argv:
        print("  no headless browser found, so the HTML for each figure was written "
              "but not screenshotted. Open %s to look." % out_dir)
    print("%d figures checked, %d problems; output in %s" % (len(figs), problems, out_dir))
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
