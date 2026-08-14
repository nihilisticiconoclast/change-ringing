# Vendored JavaScript libraries

Third-party libraries, pinned and committed, served from this repository rather
than from a CDN. These are **not** covered by the root `LICENSE` (MIT, this
project's code) or by `data/LICENCE-DATA.md` (CC BY-SA 4.0, the corpus). Each
carries its own licence, recorded below.

| File | Package | Version | Licence | SHA-256 |
| --- | --- | --- | --- | --- |
| `3d-force-graph-1.80.0.min.js` | [3d-force-graph](https://github.com/vasturiano/3d-force-graph) | 1.80.0 | MIT | `d96e738e…33a72e42` |
| `three-0.160.0.min.js` | [three.js](https://threejs.org) | 0.160.0 | MIT | `170c6789…ee1d49fa` |
| `d3-7.9.0.min.js` | [D3](https://d3js.org) | 7.9.0 | ISC | `f2094bbf…ceb86539` |
| `chart-4.5.1.min.js` | [Chart.js](https://www.chartjs.org) | 4.5.1 | MIT | `48444a82…05c9f54a` |

Verify with `sha256sum docs/vendor/*.js`.

## Why these are committed rather than fetched

Three pages — `nexus.html`, `geometry.html` and `occasions.html` — loaded these
from `unpkg.com`, `d3js.org` and `cdn.jsdelivr.net`. Three separate problems,
all measured rather than assumed:

**1. The `three` tag never worked.** `https://unpkg.com/three`, with no version,
resolves to `three@0.185.1/build/three.cjs` — a **CommonJS** build. Loaded in a
`<script>` tag it throws `exports is not defined` and never defines
`window.THREE`. `nexus.html` calls `THREE.AxesHelper` and `THREE.GridHelper` to
draw the grid plane and coordinate axes that give its 3D scatter depth, so those
have been silently absent on the published page, which then also threw
`THREE is not defined`. 2.09 MB was being downloaded per visit and discarded.

Reproduced by fetching exactly what the CDN serves and loading the real page
against it: two page errors, one canvas, no grid. Fixed by pinning
**three 0.160.0**, the last release to ship a browser `three.min.js`. Verified
by screenshot that the grid and axes now render; three.js logs a benign
"Multiple instances" warning because `3d-force-graph` bundles its own copy, and
the helper objects work across the two revisions.

**2. Every reference was unversioned.** `unpkg.com/3d-force-graph`,
`unpkg.com/three` and `cdn.jsdelivr.net/npm/chart.js` all resolve to whatever is
latest. A breaking change upstream breaks a published page with no commit here
and no warning — which is how problem 1 arose in the first place.

**3. The pages were not self-contained.** `index.html`, `methods.html`,
`rhythm.html`, `lineage.html` and `ringers.html` inline everything and work
offline. The other three rendered blank behind a proxy that blocks CDNs, or with
no network at all. Every page in this repository should be openable from disk.

## Updating

Fetch the new version, put it here with the version in the filename, update the
table and the SHA-256, and point the builder at it. Do **not** reintroduce a CDN
reference, and do **not** drop the version from a filename — the whole point of
the pin is that the page cannot change without a commit.

The relative path `vendor/…` works identically on GitHub Pages (served from
`main` / `docs`) and from a local file, so no build step or base tag is needed.
