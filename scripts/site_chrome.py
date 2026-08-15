#!/usr/bin/env python3
"""
The one place the site's navigation and footer are defined.

Every page's nav bar and footer are generated from PAGES below. Nothing else in
this repository may hard-code a list of pages.

Why this exists
---------------
There are nine pages built by seven scripts and four HTML templates, written at
different times by three different agents. Adding a page previously meant editing
nine navigation blocks by hand, and the ninth was always the one that got missed:
by the time it was noticed, the nav bars had converged but the FOOTERS had not --
`rhythm.html` and `invention.html` linked to two different subsets of the site,
five pages had no footer at all, and only two carried a link back to the
repository.

So the fix is not "correct the nine copies again". It is to make nine copies
impossible.

How to use it
-------------
In a template, put the markers where the chrome belongs:

    <!--NAV:rhythm.html-->
    <!--FOOTER:rhythm.html-->

then in the builder, after loading the template:

    from site_chrome import apply_chrome
    html = apply_chrome(html)

`apply_chrome` reads the active page out of the marker itself, so a builder cannot
pass the wrong one, and it raises if a marker is missing or names a page that is
not in PAGES.

Styling
-------
Two palettes. The typographic pages use the shared CSS variables; the three
dark full-screen 3-D pages (nexus, geometry, and their kin) do not define those
variables, so `dark=True` emits the same markup with literal colours. The markup
and the link list are identical either way -- only the colours differ, which is
the one difference worth keeping.
"""

# href, label, and the one-line description used in the footer.
# ORDER MATTERS: this is the order every nav bar and footer renders in.
# Grouped by what the page is about rather than when it was built -- the three
# method pages, then the two about when and why ringing happens, then the three
# exploratory 3-D views.
PAGES = [
    ("index.html",      "Founder Atlas",
     "51,451 attributed bells mapped by the foundry that cast them"),
    ("lineage.html",    "Method Lineage",
     "How methods extend from one stage to the next"),
    ("methods.html",    "Blue Line Atlas",
     "20,679 methods drawn as the path a bell traces"),
    ("invention.html",  "First Rung",
     "Three centuries of method invention, 1684–2026"),
    ("rhythm.html",     "Rhythm of Ringing",
     "The week, the year, and 24 days that carry a fifth of 2021–24"),
    ("ringers.html",    "Ringer Constellation",
     "Who rings with whom, across 70,351 names"),
    ("occasions.html",  "The Occasions Archive",
     "Why bells are rung, from 337,946 footnotes"),
    ("nexus.html",      "The Temporal Nexus",
     "Towers, methods and ringers in one 3-D field"),
    ("geometry.html",   "Sacred Geometry",
     "Method symmetries arranged on a phyllotaxis sphere"),
]

HREFS = [p[0] for p in PAGES]

REPO = "https://github.com/nihilisticiconoclast/change-ringing"

# Page-specific provenance and caveats, rendered above the shared note.
# These live here rather than in each template so that the whole site's
# qualifications can be read in one place -- and so that replacing nine
# hand-written footers with one generated footer could not quietly delete them,
# which is exactly what the first attempt at this refactor did.
NOTES = {
    "index.html": [
        "Built from Dove’s Guide for Church Bell Ringers "
        "(<a href='https://dove.cccbr.org.uk'>dove.cccbr.org.uk</a>) and the CCCBR "
        "Methods Library (<a href='https://methods.cccbr.org.uk'>methods.cccbr.org.uk</a>). "
        "Snapshot 9 August 2026. <strong>Changes made:</strong> column names normalised, "
        "the sources loaded into a relational schema, and first-performance locations "
        "linked to Dove tower IDs by adjudicated name matching.",
        "8,623 of 30,734 first-performance records are <strong>deliberately "
        "unlinked</strong> — mostly handbell peals rung in private houses, which have no "
        "tower to link to.",
    ],
    "lineage.html": [
        "Source: the CCCBR Methods Library, 25,055 methods. Extension relationships are "
        "as published by the library; <code>extension_construction</code> is populated "
        "for only 1,851 of them, so the lineage shown is the documented part of a larger "
        "structure rather than the whole of it.",
    ],
    "methods.html": [
        "Lines are computed from the place notation published by the CCCBR Methods "
        "Library, parsed by <code>scripts/notation.py</code>. <strong>Only methods whose "
        "parse is confirmed against the library’s own published <code>lead_head</code> "
        "are shown</strong> — the rest are excluded rather than drawn unchecked. "
        "Failures concentrate at odd stages; at Minor and Major, the stages drawn here, "
        "the parser agrees with the library on over 99.7% of methods.",
        "Blue line diagrams are standard in ringing software. What is new here is drawing "
        "the whole collection at once, so families can be compared side by side.",
    ],
    "invention.html": [
        "<strong>“First rung”, not “invented”.</strong> No column in any of the four "
        "corpora records who devised a method. What the CCCBR library records is the "
        "first performance, and a method enters the collection by being rung and named, "
        "so that is the date used here. A method can be worked out on paper years before "
        "a band attempts it, and that gap is invisible in this data.",
        "Each method is counted <strong>once</strong>, at its own earliest dated "
        "performance. <code>method_performances</code> holds up to fifteen "
        "first-performance event types per method, so counting rows instead would answer "
        "a different question — and did, in an earlier draft of this page.",
    ],
    "rhythm.html": [
        "<strong>This page is deliberately restricted to 2021–24, while the corpus now "
        "runs 2012–24.</strong> Every figure here — the 24 days, the 21%, the weekday "
        "profile — is of that four-year window, which was the whole corpus when the "
        "analysis was done. Widening it is real work rather than a rebuild: the anomaly "
        "rule compares each day against its own neighbourhood, so thirteen years changes "
        "which days qualify, and 2020 would enter as a year of almost no ringing. There "
        "is good reason to expect the answer to move — the same widening took “81.6% of "
        "Major methods are never rung” down to 53.9% — which is exactly why the window "
        "is stated rather than quietly extended.",
        "The anomaly rule and both of its thresholds are command-line flags, and the "
        "build prints the days that fell just below the cut, so the boundary can be "
        "argued with rather than taken on trust.",
        "Footnote text is quoted only where the same words were written independently by "
        "many bands on the same day. <strong>No individual is named anywhere on this "
        "page.</strong>",
    ],
    "occasions.html": [
        "Occasions are keyword patterns over footnote text, so the categories "
        "<strong>overlap and must not be summed</strong> — a large minority of footnotes "
        "match more than one, and a larger one matches none. Both figures are computed "
        "and stated on the page above; they are deliberately not repeated here, because "
        "an earlier version of this note kept its own copy of those percentages and "
        "went wrong twice as the corpus grew. The unit is footnotes, not performances.",
        "Only aggregate counts leave the database. <strong>No footnote text and no names "
        "are published</strong> — many footnotes are funeral tributes written by people "
        "who did not anticipate republication.",
    ],
    "ringers.html": [
        "Ringer identity is resolved by name across the whole corpus, 2012–24. Names are "
        "not unique and the corpus has no person identifier, so two ringers sharing a "
        "name are one node here. Treat the structure as indicative rather than as a "
        "register of people.",
    ],
    "nexus.html": [
        "Positions are a force layout, not a map projection: distance between nodes "
        "reflects the layout’s convergence, not geography or similarity.",
    ],
    "geometry.html": [
        "The sphere is a phyllotaxis arrangement by rank, not a measurement. Position "
        "encodes how often a method is rung; the threads between nodes encode shared "
        "lead-head codes, which is a real structural relationship.",
    ],
}

_FOOTER_NOTE = (
    "Built from <code>data/change-ringing.db</code> by the scripts in "
    "<code>scripts/</code>; the SQL behind each page is in <code>queries/</code>, "
    "read at build time rather than copied, so the recorded queries are the ones "
    "that ran. Data derived from Dove’s Guide, the CCCBR Methods Library and "
    "BellBoard — <strong>CC BY-SA 4.0</strong>, see <code>data/LICENCE-DATA.md</code> "
    "before reusing it. The code is MIT."
)


def nav_html(active, dark=False, indent="  "):
    """The nav bar. `active` must be one of HREFS."""
    if active not in HREFS:
        raise ValueError(f"{active!r} is not a page; expected one of {HREFS}")
    links = "\n".join(
        f'{indent}    <a href="{href}"'
        + (' class="active"' if href == active else "")
        + f">{label}</a>"
        for href, label, _ in PAGES
    )
    btn = (f'\n{indent}  <button class="theme-btn" id="themeToggle">Dark Mode</button>'
           if not dark else "")
    return (f'{indent}<div class="nav-bar">\n'
            f'{indent}  <div class="nav-links">\n{links}\n{indent}  </div>'
            f'{btn}\n{indent}</div>')


def footer_html(active, dark=False, indent="  "):
    """The footer: every other page, with a one-line description, plus the repo.

    The active page is listed too, marked, rather than omitted -- so the footer is
    the same shape on every page and a reader can see the whole site from any of
    them.
    """
    if active not in HREFS:
        raise ValueError(f"{active!r} is not a page; expected one of {HREFS}")
    rows = "\n".join(
        f'{indent}    <li><a href="{href}"'
        + (' aria-current="page"' if href == active else "")
        + f'>{label}</a> <span>{desc}</span></li>'
        for href, label, desc in PAGES
    )
    style = (' style="color:#cbd5e1"' if dark else "")
    notes = "".join(
        f'{indent}  <p class="site-note">{n}</p>\n' for n in NOTES.get(active, [])
    )
    return (f'{indent}<footer class="site-footer"{style}>\n'
            f'{indent}  <ul class="site-map">\n{rows}\n{indent}  </ul>\n'
            f'{notes}'
            f'{indent}  <p class="site-note">{_FOOTER_NOTE}</p>\n'
            f'{indent}  <p class="site-note"><a href="{REPO}">Repository</a></p>\n'
            f'{indent}</footer>')


# Shared chrome CSS. Appended by apply_chrome so that pages which never had a
# footer get one that looks like the others.
FOOTER_CSS = """
/* The last <section> on the typographic pages already draws a bottom rule, so
   the footer's own top rule made a doubled line with a dead 56px band between
   them. Suppress the section's, keep the footer's, and every page gets exactly
   one separator whether or not it has sections at all. */
section:last-of-type{border-bottom:none}
.site-footer{border-top:1px solid var(--rule,rgba(255,255,255,.14));
  margin-top:24px;padding:36px 24px 72px;font-size:14px;
  color:var(--ink-3,#8b93a3);max-width:1200px;margin-left:auto;margin-right:auto}
.site-map{list-style:none;margin:0 0 22px;padding:0;display:grid;
  grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:4px 28px}
.site-map li{padding:5px 0;line-height:1.45}
.site-map a{color:var(--bronze,#38bdf8);text-decoration:none;font-weight:500}
.site-map a:hover{text-decoration:underline}
.site-map a[aria-current="page"]{color:var(--ink-2,#e2e8f0);font-weight:600}
.site-map a[aria-current="page"]::after{content:" — you are here";
  font-size:11px;font-weight:400;opacity:.7}
.site-map span{display:block;font-size:12.5px;opacity:.78}
.site-note{max-width:78ch;margin:12px 0 0;font-size:13px;line-height:1.6}
.site-note a{color:var(--bronze,#38bdf8)}
.site-note code{font-size:.92em}
"""

NAV_MARK = "<!--NAV:"
FOOTER_MARK = "<!--FOOTER:"


def _one(html, mark, render, dark):
    """Replace every `<!--MARK:page.html-->` with its rendered chrome."""
    out, count = [], 0
    i = 0
    while True:
        j = html.find(mark, i)
        if j < 0:
            out.append(html[i:])
            break
        k = html.find("-->", j)
        if k < 0:
            raise ValueError(f"unterminated {mark} marker")
        page = html[j + len(mark):k]
        indent = html[:j].rsplit("\n", 1)[-1]
        out.append(html[i:j])
        out.append(render(page, dark=dark, indent=indent).lstrip())
        i = k + 3
        count += 1
    return "".join(out), count


def apply_chrome(html, dark=False):
    """Expand the NAV and FOOTER markers. Raises unless both are present exactly once.

    Strict on purpose. A page that silently builds without a footer is how the
    inconsistency happened the first time.
    """
    html, n_nav = _one(html, NAV_MARK, nav_html, dark)
    html, n_foot = _one(html, FOOTER_MARK, footer_html, dark)
    if n_nav != 1:
        raise ValueError(f"expected exactly one {NAV_MARK}...--> marker, found {n_nav}")
    if n_foot != 1:
        raise ValueError(f"expected exactly one {FOOTER_MARK}...--> marker, found {n_foot}")
    if "</style>" in html:
        html = html.replace("</style>", FOOTER_CSS + "</style>", 1)
    else:
        html = html.replace("</head>", f"<style>{FOOTER_CSS}</style></head>", 1)
    return html


if __name__ == "__main__":
    for href, label, desc in PAGES:
        print(f"{href:16s} {label:24s} {desc}")
