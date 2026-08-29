"""
HTML Page Structure Extractor for Golden-File Regression Testing (Roadmap Item R-42 / G-13).

Extracts a semantic, data-invariant structural outline of an HTML page:
- Heading hierarchy (h1-h6 levels and normalized titles with numbers masked)
- Layout containers (header, nav, main, section, article, footer, IDs, classes)
- Table structural shapes (thead column headers, table IDs)
- Interactive controls (inputs, buttons, selects with IDs and types)
- Visualisation and chart containers (svg, canvas, .chart, .map, .network)
- Document element IDs and navigation/footer link targets
"""

from html.parser import HTMLParser
import json
import re
from pathlib import Path
from typing import Dict, Any


def mask_numbers(text: str) -> str:
    """Replaces numbers, years, percentages, and metrics with a '#' placeholder to ensure data invariance."""
    s = re.sub(r"\b[\d,.]+(?:%|k|M|B)?\b", "#", text)
    return " ".join(s.split())


class PageStructureExtractor(HTMLParser):
    """Parses HTML into a structural skeleton invariant to numeric data updates."""

    def __init__(self):
        super().__init__()
        self.structure = {
            "title": "",
            "meta": [],
            "headings": [],
            "sections": [],
            "tables": [],
            "interactive_controls": [],
            "visualisation_containers": [],
            "all_ids": [],
            "nav_links": [],
            "footer_links": [],
        }
        self._in_title = False
        self._in_heading = False
        self._in_th = False
        self._in_nav = False
        self._in_footer = False
        self._current_heading_tag = None
        self._current_heading_text = []
        self._current_th_text = []
        self._current_table = None

    def handle_starttag(self, tag: str, attrs: list):
        attr_dict = dict(attrs)
        elem_id = attr_dict.get("id")
        elem_cls = attr_dict.get("class", "")

        if elem_id and elem_id not in self.structure["all_ids"]:
            self.structure["all_ids"].append(elem_id)

        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            meta_entry = {k: v for k, v in attr_dict.items() if k in ("name", "content", "charset", "http-equiv")}
            if meta_entry:
                self.structure["meta"].append(meta_entry)
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._in_heading = True
            self._current_heading_tag = tag
            self._current_heading_text = []
        elif tag in ("header", "nav", "main", "section", "article", "footer"):
            if tag == "nav":
                self._in_nav = True
            elif tag == "footer":
                self._in_footer = True
            self.structure["sections"].append({
                "tag": tag,
                "id": elem_id,
                "class": elem_cls
            })
        elif tag == "table":
            self._current_table = {"id": elem_id, "class": elem_cls, "headers": []}
            self.structure["tables"].append(self._current_table)
        elif tag == "th" and self._current_table is not None:
            self._in_th = True
            self._current_th_text = []
        elif tag in ("input", "select", "button"):
            self.structure["interactive_controls"].append({
                "tag": tag,
                "id": elem_id,
                "type": attr_dict.get("type"),
                "name": attr_dict.get("name"),
                "class": elem_cls
            })
        elif tag in ("svg", "canvas") or any(c in elem_cls for c in ("chart", "map", "network", "viz", "graph")):
            self.structure["visualisation_containers"].append({
                "tag": tag,
                "id": elem_id,
                "class": elem_cls
            })
        elif tag == "a":
            href = attr_dict.get("href")
            if self._in_nav and href:
                self.structure["nav_links"].append(href)
            elif self._in_footer and href:
                self.structure["footer_links"].append(href)

    def handle_endtag(self, tag: str):
        if tag == "title":
            self._in_title = False
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._in_heading = False
            raw_h_text = " ".join("".join(self._current_heading_text).split())
            masked_h_text = mask_numbers(raw_h_text)
            self.structure["headings"].append({
                "level": self._current_heading_tag,
                "text": masked_h_text
            })
        elif tag == "th" and self._in_th:
            self._in_th = False
            raw_th_text = " ".join("".join(self._current_th_text).split())
            masked_th_text = mask_numbers(raw_th_text)
            if self._current_table is not None:
                self._current_table["headers"].append(masked_th_text)
        elif tag == "table":
            self._current_table = None
        elif tag == "nav":
            self._in_nav = False
        elif tag == "footer":
            self._in_footer = False

    def handle_data(self, data: str):
        if self._in_title:
            self.structure["title"] += data
        elif self._in_heading:
            self._current_heading_text.append(data)
        elif self._in_th:
            self._current_th_text.append(data)


def extract_structure(html_text: str) -> Dict[str, Any]:
    """Extracts the structured skeleton dictionary from raw HTML string."""
    parser = PageStructureExtractor()
    parser.feed(html_text)
    parser.structure["title"] = mask_numbers(parser.structure["title"].strip())
    return parser.structure
