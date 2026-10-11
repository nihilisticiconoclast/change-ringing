# Dashboard page source

The page behind the corpus dashboard described in `docs/dashboard.md`. These files
are the page documents of a claude.ai Dashboard artifact and run only inside it:
the artifact supplies `d3` and the `dash` API that the scripts read their data
through, and `index.html` is a fragment placed inside the artifact's own page, not
a standalone document. Opening it directly shows nothing.

| File | What it does |
| --- | --- |
| `index.html` | Styles, the three tab panels, and each page's markup in a `<template>`, so a page's data loads only when it is first opened |
| `common.js` | Formatting, marks, tooltips, and the chart and table helpers the pages share |
| `activity.js` | Ringing activity: the setting and year filters, tiles, charts and tables |
| `health.js` | Corpus health |
| `project.js` | Project tracker, including the calculations that count roadmap states and verdicts |
| `app.js` | Tabs, links, and the one `dash.onData` that redraws whichever page is showing |

Every figure the page shows comes from a dataset, never from the markup: the
eighteen JSON files `scripts/build_dashboard_data.py` writes, attached to the
artifact. To refresh it after the corpus or the docs change, rebuild those files
and re-attach the ones that changed. Claude, which holds the artifact, can do
both.
