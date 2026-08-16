#!/usr/bin/env python3
"""
Check that every published page carries the same navigation and footer.

Usage:
    python scripts/verify_chrome.py          # exits non-zero on any failure

Run after building. This exists because the site drifted twice: first the nav
bars diverged as pages were added one at a time, and then -- after the navs were
corrected by hand -- the FOOTERS were found to be worse, with two pages linking to
two different subsets of the site and five having no footer at all. Correcting
nine copies is not a fix; a check that fails when they differ is.

What it asserts, per page:

  * the nav lists every page in scripts/site_chrome.py PAGES, in that order
  * the footer lists every page, in that order
  * exactly one nav link is marked active, and it is this page
  * exactly one footer link is marked aria-current, and it is this page
  * the page links back to the repository

Whitespace is normalised before comparison. Three pages sit inside a deeper block
and are therefore indented further; that is not drift, and a check that fails on
it would be ignored within a week.

It also checks the SOURCES, not just the output: no template and no builder may
declare a nav rule of its own. That check was added after the first version of
this file passed a site whose nav bar visibly changed shape from page to page.
Every page emitted byte-identical nav markup -- which is all this file looked at
-- while eleven separate `.nav-bar` rules styled it eleven ways. Checking that
the markup matches is not the same as checking that the page matches, and the
gap between those two was invisible for as long as nothing looked at the CSS.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from site_chrome import PAGES, HREFS, REPO, NO_SITE_MAP  # noqa: E402

DOCS = Path(__file__).parent.parent / "docs"
SCRIPTS = Path(__file__).parent

# Selectors that belong to scripts/site_chrome.py and to nothing else.
NAV_SELECTORS = ("nav-bar", "nav-links", "nav-title", "nav-header",
                 "nav-toggle", "nav-over", "theme-btn")
SHARED_SELECTORS = NAV_SELECTORS + (
    "site-footer", "site-map", "site-note",
    "eyebrow", "standfirst", "figures", "wrap"
)
# A rule opener: something ending in `.<selector>...{`, not inside a comment.
SHARED_RULE = re.compile(
    r"^[^/*\n]*\.(?:" + "|".join(SHARED_SELECTORS) + r")[^{}\n]*\{", re.M)


def check_no_local_chrome_css():
    """No template and no builder may style shared chrome or base layout rules.
    Only site_chrome.py may."""
    fails = []
    sources = sorted((SCRIPTS / "templates").glob("*.html"))
    sources += [p for p in sorted(SCRIPTS.glob("*.py")) if p.name != "site_chrome.py"]
    for path in sources:
        text = path.read_text(encoding="utf-8")
        for m in SHARED_RULE.finditer(text):
            line = text[:m.start()].count("\n") + 1
            fails.append(f"{path.relative_to(SCRIPTS.parent)}:{line}: "
                         f"declares a shared rule — {m.group(0).strip()[:60]!r}")
    return fails


def block(html, pattern):
    m = re.search(pattern, html, re.S)
    return m.group(0) if m else None


def check_page(href):
    path = DOCS / href
    fails = []
    if not path.exists():
        return [f"{href}: not built"]
    html = path.read_text(encoding="utf-8")

    nav = block(html, r'<div class="nav-links">.*?</div>')
    foot = block(html, r'<ul class="site-map">.*?</ul>')
    if nav is None:
        fails.append(f"{href}: no nav")
    # One page deliberately has no footer site-map, because its body is one --
    # see site_chrome.NO_SITE_MAP. Assert BOTH directions, so the exemption
    # cannot quietly grow to cover a page that lost its footer by accident.
    if href in NO_SITE_MAP:
        if foot is not None:
            fails.append(f"{href}: has a footer site-map, but is in NO_SITE_MAP "
                         f"because its body already lists every page")
        if '<footer class="site-footer"' not in html:
            fails.append(f"{href}: no footer at all")
    elif foot is None:
        fails.append(f"{href}: no footer site-map")
    if nav is None or foot is None:
        return fails

    for name, chunk, marker in (("nav", nav, 'class="active"'),
                                ("footer", foot, 'aria-current="page"')):
        order = re.findall(r'<a href="([a-z]+\.html)"', chunk)
        if order != HREFS:
            missing = [h for h in HREFS if h not in order]
            extra = [h for h in order if h not in HREFS]
            if missing:
                fails.append(f"{href}: {name} missing {missing}")
            if extra:
                fails.append(f"{href}: {name} has unknown {extra}")
            if not missing and not extra:
                fails.append(f"{href}: {name} order is {order}, expected {HREFS}")
        marked = re.findall(rf'<a href="([a-z]+\.html)" {re.escape(marker)}', chunk)
        if marked != [href]:
            fails.append(f"{href}: {name} marks {marked or 'nothing'} as current, "
                         f"expected ['{href}']")

    if REPO not in html:
        fails.append(f"{href}: no link back to the repository")
    return fails


def main():
    all_fails = []
    for href, label, _ in PAGES:
        fails = check_page(href)
        all_fails += fails
        print(f"  {'FAIL' if fails else 'ok  '}  {href:16s} {label}")
        for f in fails:
            print(f"          {f}")

    # The nav and footer must also be identical BETWEEN pages, not merely valid on
    # each -- a shared typo would pass every per-page check above.
    shapes = {}
    for kind, pattern, marker in (
        ("nav", r'<div class="nav-links">.*?</div>', r'\s*class="active"'),
        ("footer", r'<ul class="site-map">.*?</ul>', r'\s*aria-current="page"'),
    ):
        seen = {}
        for href, _, _ in PAGES:
            path = DOCS / href
            if not path.exists():
                continue
            b = block(path.read_text(encoding="utf-8"), pattern)
            if b is None:
                continue
            norm = re.sub(r"\s+", " ", re.sub(marker, "", b)).strip()
            norm = re.sub(r'<button class="theme-btn".*?</button>', "", norm)
            norm = re.sub(r"\s+", " ", norm).strip()
            seen.setdefault(norm, []).append(href)
        shapes[kind] = seen
        if len(seen) > 1:
            all_fails.append(f"{kind}: {len(seen)} different variants across pages")
            for i, (_, pages) in enumerate(seen.items(), 1):
                print(f"          variant {i}: {pages}")

    css_fails = check_no_local_chrome_css()
    all_fails += css_fails
    print(f"\n  {'FAIL' if css_fails else 'ok  '}  chrome & base CSS declared only in site_chrome.py")
    for f in css_fails:
        print(f"          {f}")

    print(f"\n{len(PAGES)} pages · "
          f"{len(shapes['nav'])} nav variant(s) · "
          f"{len(shapes['footer'])} footer variant(s)")
    if all_fails:
        print(f"\n{len(all_fails)} problem(s). Rebuild the pages, or fix "
              f"scripts/site_chrome.py -- do not edit a page's nav or footer by hand.")
        return 1
    print("Every page links to every page, in the same order, with the same footer,")
    print("and every page's nav is styled by the same rules.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
