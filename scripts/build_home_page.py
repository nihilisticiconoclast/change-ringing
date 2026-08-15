#!/usr/bin/env python3
"""Build the home page and its table of contents."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from site_chrome import PAGES, apply_chrome  # noqa: E402

TEMPLATE = Path(__file__).parent / "templates" / "home.html"


def build():
    html = TEMPLATE.read_text(encoding="utf-8")
    if "<!--/*TOC*/-->" not in html:
        sys.exit(f"ERROR: {TEMPLATE} has no <!--/*TOC*/--> placeholder")

    toc_items = []
    for href, label, desc in PAGES:
        if href == "index.html":
            continue
        toc_items.append(
            f'      <a href="{href}" class="toc-card">\n'
            f'        <h3 class="toc-title">{label}</h3>\n'
            f'        <p class="toc-desc">{desc}</p>\n'
            f'      </a>'
        )
    
    html = html.replace("<!--/*TOC*/-->", "\n".join(toc_items))
    
    # We want the page to default to dark mode, which we did in the template by 
    # setting <body class="dark-mode">. We also apply chrome.
    final_html = apply_chrome(html, dark=True)
    
    out_path = Path("docs/index.html")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(final_html, encoding="utf-8")
    
    print(f"Wrote {out_path} ({len(final_html):,} bytes)")


if __name__ == "__main__":
    build()
