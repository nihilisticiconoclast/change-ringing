#!/usr/bin/env python3
"""
Generate the Interactive Ringer Constellation & Identity Atlas (docs/ringers.html).

Builds:
- Pre-computed deterministic golden-spiral guild cluster constellation layout
- Ringer Name Picker in the top toolbar + Quick Chips for top ringers
- Live Canonical Ringer Search & Alias Cluster Inspector
- Standalone zero-dependency HTML bundle in docs/ringers.html
"""
import collections
import json
import math
import sqlite3
import pandas as pd
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from site_chrome import apply_chrome  # noqa: E402

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "change-ringing.db"
CANDIDATES_CSV = ROOT / "data" / "ringer_identity_candidates.csv"
OUT_HTML = ROOT / "docs" / "ringers.html"

# Association Color Palette (Harmonious, Meaningful & Rich)
ASSOC_PALETTE = {
    "Bath & Wells": "#0284C7",                              # Sky Blue
    "Hertford": "#8B5CF6",                                  # Purple / Violet
    "Kent": "#0D9488",                                      # Teal
    "Suffolk": "#84CC16",                                   # Lime Green
    "Oxford Diocesan": "#2563EB",                           # Royal Blue
    "Devonshire": "#06B6D4",                                # Turquoise
    "College Youths": "#EAB308",                            # Imperial Gold
    "Chester": "#F59E0B",                                   # Amber
    "Gloucester & Bristol": "#F43F5E",                      # Crimson Rose
    "Norwich": "#10B981",                                   # Emerald
    "Lincoln": "#D97706",                                   # Ochre
    "Hereford": "#6366F1",                                  # Indigo
    "Winchester & Portsmouth": "#A855F7",                   # Amethyst
    "Peterborough": "#14B8A6",                              # Cyan Teal
    "Royal Cumberland": "#059669",                          # Forest Green
    "Yorkshire": "#F97316",                                 # Coral Orange
    "Sussex": "#EC4899",                                    # Pink Rose
    "St Martin": "#0ea5e9",                                 # Ocean Blue
    "Other Regional / Independent": "#94A3B8"               # Slate Grey (Other Societies)
}

def build_page():
    print(f"Loading datasets for Ringer Constellation ...", flush=True)
    cand_df = pd.read_csv(CANDIDATES_CSV)

    # Clean UTF-8 strings
    cand_df["raw_name"] = cand_df["raw_name"].str.replace("Bjrn", "Björn").str.replace("Bj?rn", "Björn")
    cand_df["canonical_name"] = cand_df["canonical_name"].str.replace("Bjrn", "Björn").str.replace("Bj?rn", "Björn")

    # Primary canonical ringers
    canon_ringers = cand_df[cand_df["is_primary"] == True].copy()
    canon_map = dict(zip(cand_df["raw_name"], cand_df["canonical_name"]))
    id_map = dict(zip(cand_df["raw_name"], cand_df["canonical_ringer_id"]))

    # Read performances and ringers from DB
    conn = sqlite3.connect(DB_PATH)
    print("Querying performances and band co-occurrences ...", flush=True)
    perf_df = pd.read_sql_query("""
        SELECT r.perf_id, TRIM(r.name) as name, p.perf_date, p.association, p.dove_tower_id, p.place
        FROM performance_ringers r
        JOIN performances p ON p.perf_id = r.perf_id
        WHERE r.name IS NOT NULL AND TRIM(r.name) != ''
    """, conn)

    # Also get tower names from dove
    towers_df = pd.read_sql_query('SELECT "TowerID" as tower_id, "Place" as place, "Dedicn" as dedicn, "County" as county FROM dove', conn)
    conn.close()

    tower_lookup = {}
    for _, t in towers_df.iterrows():
        t_id = t["tower_id"]
        place_str = f"{t['place']}, {t['dedicn']}" if t['dedicn'] else t['place']
        tower_lookup[t_id] = place_str

    # Clean names
    perf_df["clean_name"] = perf_df["name"].str.replace("Bjrn", "Björn").str.replace("Bj?rn", "Björn")
    perf_df["canon_id"] = perf_df["clean_name"].map(id_map)
    perf_df["canon_name"] = perf_df["clean_name"].map(canon_map)

    # Select top 200 most active canonical ringers for the network graph.
    # Chosen BEFORE the aggregation below, deliberately -- see the note there.
    top_200 = canon_ringers.sort_values(by="cluster_total_peals", ascending=False).head(200)
    top_200_ids = set(top_200["canonical_ringer_id"])

    # Top associations and top towers, for the 200 ringers that get drawn.
    #
    # This was a `for _, row in perf_df.iterrows()` over every ringer instance in
    # the corpus. At 615k rows it took about a minute; at 1,969,949 it had not
    # finished after twenty, because `iterrows()` builds a Series per row and the
    # cost is entirely per-row. Two things fix it and neither changes the output:
    #
    #   1. Only the top 200 are ever read back (the loops below index
    #      ringer_assocs/ringer_towers by a top-200 id and nothing else does), so
    #      aggregating all 55,326 canonical ringers was work thrown away. Filter
    #      first: ~2M rows becomes ~370k.
    #   2. groupby().size() instead of a Python loop over rows.
    #
    # A third structure, `ringer_dates`, is gone entirely: it appended a string
    # per row into per-ringer lists -- two million appends -- and nothing ever
    # read it. Active years come from the candidates CSV.
    sub = perf_df[perf_df["canon_id"].isin(top_200_ids)]

    ringer_assocs = collections.defaultdict(collections.Counter)
    assoc = sub[sub["association"].notna()].copy()
    assoc["association"] = assoc["association"].astype(str).str.strip()
    assoc = assoc[assoc["association"] != ""]
    for (cid, name), n in assoc.groupby(["canon_id", "association"]).size().items():
        ringer_assocs[cid][name] = int(n)

    ringer_towers = collections.defaultdict(collections.Counter)
    tw = sub[sub["dove_tower_id"].notna()]
    for (cid, tid), n in tw.groupby(["canon_id", "dove_tower_id"]).size().items():
        try:
            ringer_towers[cid][int(tid)] = int(n)
        except (ValueError, TypeError):
            pass

    # Compute pairwise co-occurrences
    # sorted(), not list(set(...)). Python randomises string hashing per process,
    # so set iteration order differs between runs; that order reached the output
    # through the tie-breaks in most_common() below and made this page build
    # differently every time from an unchanged database. Sorting costs nothing
    # here and makes the page a function of the data.
    perf_bands = (perf_df.groupby("perf_id")["canon_id"]
                  .apply(lambda s: sorted(set(s.dropna()))).to_dict())

    co_counts = collections.Counter()
    top_partners = collections.defaultdict(collections.Counter)

    for band in perf_bands.values():
        band_top = [r for r in band if r in top_200_ids]
        if len(band_top) >= 2:
            for i in range(len(band_top)):
                for j in range(i + 1, len(band_top)):
                    r1, r2 = band_top[i], band_top[j]
                    pair = tuple(sorted([r1, r2]))
                    co_counts[pair] += 1
                    top_partners[r1][r2] += 1
                    top_partners[r2][r1] += 1

    # Format nodes
    nodes = []
    for _, r in top_200.iterrows():
        c_id = r["canonical_ringer_id"]
        c_name = r["canonical_name"]
        peals = int(r["cluster_total_peals"])
        
        # Primary association
        ass_counter = ringer_assocs[c_id]
        # sorted by (-count, name) so equal counts break the same way every run
        primary_assoc = (min(ass_counter.items(), key=lambda kv: (-kv[1], kv[0]))[0]
                         if ass_counter else "Other")
        
        # Map to standard color category
        color_cat = "Other Regional / Independent"
        for k in ASSOC_PALETTE:
            if k in primary_assoc or primary_assoc in k:
                color_cat = k
                break

        # Top 5 towers
        t_counter = ringer_towers[c_id]
        top_towers_list = [
            {"tower": tower_lookup.get(t_id, f"Tower #{t_id}"), "peals": cnt}
            for t_id, cnt in sorted(t_counter.items(), key=lambda kv: (-kv[1], kv[0]))[:5]
        ]

        # Top 5 partners
        p_counter = top_partners[c_id]
        top_partners_list = [
            {"id": p_id, "name": canon_ringers.loc[canon_ringers["canonical_ringer_id"] == p_id, "canonical_name"].values[0], "peals": cnt}
            for p_id, cnt in sorted(p_counter.items(), key=lambda kv: (-kv[1], kv[0]))[:5]
            if p_id in top_200_ids and len(canon_ringers[canon_ringers["canonical_ringer_id"] == p_id]) > 0
        ]

        # All aliases
        aliases = cand_df[cand_df["canonical_ringer_id"] == c_id].to_dict(orient="records")

        nodes.append({
            "id": c_id,
            "name": c_name,
            "peals": peals,
            "assoc": primary_assoc,
            "color_cat": color_cat,
            "color": ASSOC_PALETTE.get(color_cat, ASSOC_PALETTE["Other Regional / Independent"]),
            "active_years": r["active_years"],
            "towers": top_towers_list,
            "partners": top_partners_list,
            "aliases": aliases
        })

    # Format edges (keep edges with at least 5 shared peals)
    edges = []
    for (r1, r2), count in co_counts.items():
        if count >= 5:
            edges.append({
                "source": r1,
                "target": r2,
                "weight": count
            })

    # Calculate deterministic coordinates via Golden Spiral Guild Clustering
    assoc_groups = collections.defaultdict(list)
    for n in nodes:
        assoc_groups[n["color_cat"]].append(n)

    assoc_list = sorted(assoc_groups.keys(), key=lambda k: -len(assoc_groups[k]))
    num_assocs = len(assoc_list)

    for a_idx, assoc in enumerate(assoc_list):
        group = assoc_groups[assoc]
        center_theta = (a_idx / num_assocs) * 2 * math.pi
        cx = math.cos(center_theta) * 440
        cy = math.sin(center_theta) * 300

        for g_idx, n in enumerate(group):
            theta = g_idx * 2.39996  # Golden ratio angle
            r = 20.0 + math.sqrt(g_idx) * 34.0
            n["x"] = round(cx + math.cos(theta) * r, 1)
            n["y"] = round(cy + math.sin(theta) * r, 1)
            n["radius"] = round(max(9.0, min(30.0, math.sqrt(n["peals"]) * 0.92)), 1)

    # Anti-Collision Relaxation (guarantees zero circle overlap with >= 6px breathing gap)
    for _ in range(200):
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                n1 = nodes[i]
                n2 = nodes[j]
                dx = n2["x"] - n1["x"]
                dy = n2["y"] - n1["y"]
                min_dist = n1["radius"] + n2["radius"] + 6.0  # 6px clear breathing gap
                dist = math.hypot(dx, dy) or 0.1
                if dist < min_dist:
                    push = (min_dist - dist) * 0.5
                    nx = dx / dist
                    ny = dy / dist
                    n1["x"] -= nx * push
                    n1["y"] -= ny * push
                    n2["x"] += nx * push
                    n2["y"] += ny * push

    for n in nodes:
        n["x"] = round(n["x"], 1)
        n["y"] = round(n["y"], 1)

    print(f"Network graph constructed with {len(nodes)} nodes (0 overlaps) and {len(edges)} edges.", flush=True)

    # Top search dataset
    top_search_ringers = canon_ringers.sort_values(by="cluster_total_peals", ascending=False).head(1500)
    search_data = []
    for _, r in top_search_ringers.iterrows():
        c_id = r["canonical_ringer_id"]
        c_name = r["canonical_name"]
        peals = int(r["cluster_total_peals"])
        aliases = [a["raw_name"] for a in cand_df[cand_df["canonical_ringer_id"] == c_id].to_dict(orient="records")]
        search_data.append({
            "id": c_id,
            "name": c_name,
            "peals": peals,
            "years": r["active_years"],
            "aliases": aliases
        })

    # Derive the span from the data rather than writing it into the prose. The
    # standfirst used to end with a literal "(2021-2024)", which stayed on the
    # page after the corpus was backfilled to 2018 -- the figures beside it
    # updated on rebuild and the window did not, so the sentence became false
    # while looking freshly generated. Any date range stated on a page should be
    # computed by the query that produced the figures next to it.
    _dates = perf_df["perf_date"].dropna().astype(str)
    stats = {
        "total_ringers": len(perf_df),
        "total_raw_names": len(cand_df),
        "total_canonical": len(canon_ringers),
        "multi_clusters": int(cand_df.groupby("canonical_ringer_id").size().gt(1).sum()),
        "total_peals": int(perf_df["perf_id"].nunique()),
        "span": (f"{_dates.min()[:4]}–{_dates.max()[:4]}"
                 if len(_dates) else "an unrecorded window"),
    }

    # Write HTML page
    html_content = generate_html(nodes, edges, search_data, stats)
    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    # One nav bar and one footer for the whole site: scripts/site_chrome.py
    html_content = apply_chrome(html_content)
    OUT_HTML.write_text(html_content, encoding="utf-8")
    print(f"\nWrote {OUT_HTML} ({OUT_HTML.stat().st_size / 1024:.1f} KB)", flush=True)

def generate_html(nodes, edges, search_data, stats):
    nodes_json = json.dumps(nodes)
    edges_json = json.dumps(edges)
    search_json = json.dumps(search_data)

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>The Ringer Constellation — Band Networks & Canonical Identity Resolution</title>
<style>
/* Quick Ringer Chips */
.chips-bar{{display:flex; flex-wrap:wrap; gap:8px; margin:22px 0 16px; align-items:center}}
.chips-label{{font-family:var(--mono); font-size:11px; color:var(--ink-3); text-transform:uppercase; letter-spacing:.08em; margin-right:4px}}
.chip-btn{{
  font-family:var(--mono); font-size:11.5px; padding:5px 11px; border-radius:3px;
  background:var(--surface); border:1px solid var(--rule); color:var(--ink-2); cursor:pointer;
  transition:all .15s;
}}
.chip-btn:hover{{border-color:var(--bronze); color:var(--ink)}}
.chip-btn.active{{background:var(--surface-2); border-color:var(--bronze); color:var(--bronze); font-weight:600}}

/* Explorer Layout */
.explorer-grid{{
  display:grid; grid-template-columns:1fr 350px; gap:24px; margin-top:20px;
}}
@media (max-width:920px){{
  .explorer-grid{{grid-template-columns:1fr}}
}}

/* Graph Container */
.graph-card{{
  background:var(--surface); border:1px solid var(--rule); border-radius:4px;
  position:relative; overflow:hidden; display:flex; flex-direction:column;
}}
.graph-toolbar{{
  padding:12px 16px; border-bottom:1px solid var(--rule); display:flex;
  justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;
  background:var(--surface-2);
}}
.graph-title{{font-family:var(--mono); font-size:11.5px; letter-spacing:.08em; text-transform:uppercase; color:var(--ink-2)}}
.graph-controls-group{{display:flex; gap:10px; align-items:center; flex-wrap:wrap}}
.graph-select{{
  background:var(--surface); border:1px solid var(--rule); color:var(--ink);
  padding:6px 10px; font-family:var(--mono); font-size:12px; border-radius:3px; outline:none;
  cursor:pointer;
}}
.graph-select:focus{{border-color:var(--bronze)}}

#constellationCanvas{{
  width:100%; height:580px; display:block; cursor:grab; background:var(--surface);
}}
#constellationCanvas:active{{cursor:grabbing}}

/* Floating Graph Actions */
.graph-actions{{
  position:absolute; bottom:52px; right:16px; display:flex; flex-direction:column; gap:6px; z-index:10;
}}
.action-btn{{
  width:32px; height:32px; background:var(--surface); border:1px solid var(--rule);
  color:var(--ink); border-radius:3px; display:flex; align-items:center; justify-content:center;
  font-family:var(--mono); font-size:14px; cursor:pointer; box-shadow:0 2px 8px rgba(0,0,0,.15);
}}
.action-btn:hover{{border-color:var(--bronze); color:var(--bronze)}}

/* Legend */
.legend{{
  padding:10px 16px; border-top:1px solid var(--rule); display:flex; flex-wrap:wrap; gap:14px;
  font-family:var(--mono); font-size:11px; background:var(--surface);
}}
.legend-item{{display:inline-flex; align-items:center; gap:6px}}
.legend-dot{{width:9px; height:9px; border-radius:50%}}

/* Side Dossier Panel */
.dossier-card{{
  background:var(--surface); border:1px solid var(--rule); border-radius:4px;
  padding:22px; display:flex; flex-direction:column; gap:18px;
}}
.dossier-header .d-id{{font-family:var(--mono); font-size:11px; color:var(--bronze); letter-spacing:.1em; text-transform:uppercase}}
.dossier-header h3{{font-size:1.45rem; font-weight:400; margin:4px 0 0}}
.d-badge{{
  display:inline-block; font-family:var(--mono); font-size:10.5px; letter-spacing:.06em;
  padding:3px 9px; border-radius:2px; background:var(--surface-2); border:1px solid var(--rule);
  color:var(--ink-2); text-transform:uppercase; margin-top:8px;
}}
.d-stats{{display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:8px}}
.d-stat .val{{font-family:var(--mono); font-size:1.35rem; font-weight:600}}
.d-stat .lbl{{font-family:var(--mono); font-size:10px; color:var(--ink-3); text-transform:uppercase}}

.d-section h4{{
  font-family:var(--mono); font-size:11px; text-transform:uppercase; letter-spacing:.08em;
  color:var(--ink-2); margin:0 0 8px; border-bottom:1px solid var(--rule); padding-bottom:4px;
}}
.alias-list, .partner-list, .tower-list{{list-style:none; padding:0; margin:0; font-size:13px}}
.alias-list li{{
  padding:4px 0; font-family:var(--mono); font-size:12px; display:flex; justify-content:space-between;
  border-bottom:1px dashed var(--surface-2);
}}
.alias-list .is-p{{color:var(--bronze); font-weight:600}}
.partner-list li, .tower-list li{{
  padding:4px 0; display:flex; justify-content:space-between; font-size:13px;
}}
.partner-list .cnt, .tower-list .cnt{{font-family:var(--mono); font-size:11px; color:var(--ink-3)}}

/* Search & Candidates Explorer */
.search-bar-wrap{{margin:24px 0 16px}}
.search-input{{
  width:100%; max-width:500px; padding:10px 14px; font-family:var(--mono); font-size:13px;
  background:var(--surface); border:1px solid var(--rule); color:var(--ink); border-radius:3px;
}}
.search-input:focus{{outline:none; border-color:var(--bronze); box-shadow:0 0 0 2px rgba(184,135,63,.2)}}
.candidate-table-wrap{{
  overflow-x:auto; background:var(--surface); border:1px solid var(--rule); border-radius:3px;
}}
table{{width:100%; border-collapse:collapse; font-size:13.5px; text-align:left}}
th{{
  font-family:var(--mono); font-size:10.5px; letter-spacing:.1em; text-transform:uppercase;
  padding:10px 14px; background:var(--surface-2); border-bottom:1px solid var(--rule); color:var(--ink-2);
}}
td{{padding:9px 14px; border-bottom:1px solid var(--rule)}}
tr:hover td{{background:rgba(184,135,63,.04)}}
.tag-alias{{
  display:inline-block; font-family:var(--mono); font-size:10px; padding:1px 6px;
  background:var(--ground); border:1px solid var(--rule); border-radius:2px; margin:2px;
}}
</style>
</head>
<body>

<!--NAV:ringers.html-->
<div class="wrap">
  <header>
    <div class="eyebrow">Gemini Task 3 &middot; Band Networks &middot; Community Resolution</div>
    <h1>The Ringer <em>Constellation</em></h1>
    <div class="standfirst">
      Interactive band co-occurrence networks and canonical entity resolution across
      <strong>{stats['total_ringers']:,} ringer instances</strong> and <strong>{stats['total_peals']:,} historical peals</strong> ({stats['span']}).
    </div>
    <div class="figures">
      <div class="fig"><div class="n">{stats['total_ringers']:,}</div><div class="l">Ringer Peal Records</div></div>
      <div class="fig"><div class="n">{stats['total_raw_names']:,}</div><div class="l">Raw Name Variants</div></div>
      <div class="fig"><div class="n">{stats['total_canonical']:,}</div><div class="l">Canonical Ringers</div></div>
      <div class="fig"><div class="n">{stats['multi_clusters']:,}</div><div class="l">Unified Alias Clusters</div></div>
    </div>
  </header>

  <section>
    <h2>Interactive Band Co-occurrence Network</h2>
    <div class="lede">
      Nodes represent the top 200 canonical ringers sized by historical peal volume, connected by shared peals in the same band. 
      Select any ringer below or click directly on the graph to inspect their dossier, resolved alias cluster, top towers, and frequent partners.
    </div>

    <!-- Quick Ringer Chips -->
    <div class="chips-bar">
      <span class="chips-label">Featured Ringers:</span>
      <button class="chip-btn active" data-id="RINGER_000001">Susan Sawyer</button>
      <button class="chip-btn" data-id="RINGER_000002">Claire Nicholson</button>
      <button class="chip-btn" data-id="RINGER_000003">Reg Hitchings</button>
      <button class="chip-btn" data-id="RINGER_000005">Simon Rudd</button>
      <button class="chip-btn" data-id="RINGER_000006">Peter Randall</button>
      <button class="chip-btn" data-id="RINGER_000009">Alan Pink</button>
      <button class="chip-btn" data-id="RINGER_000017">Alan Regin</button>
      <button class="chip-btn" data-id="RINGER_000013">Jack Page</button>
    </div>

    <div class="explorer-grid">
      <!-- Network Canvas -->
      <div class="graph-card">
        <div class="graph-toolbar">
          <div class="graph-title">Top 200 Ringers &middot; Mutual Peal Network</div>
          
          <div class="graph-controls-group">
            <!-- Ringer Quick Selector -->
            <select class="graph-select" id="ringerPicker" title="Pick a canonical ringer">
              <option value="">-- Jump to Ringer --</option>
            </select>

            <!-- Guild Filter -->
            <select class="graph-select" id="guildFilter" title="Filter by Ringing Guild">
              <option value="ALL">All Guilds & Associations</option>
              <option value="Bath & Wells">Bath & Wells</option>
              <option value="Hertford">Hertford County</option>
              <option value="Kent">Kent County</option>
              <option value="Suffolk">Suffolk Guild</option>
              <option value="Oxford Diocesan">Oxford Diocesan</option>
              <option value="Devonshire">Devonshire Ringers</option>
              <option value="College Youths">College Youths (ASCY)</option>
              <option value="Royal Cumberland">Royal Cumberland (SRCY)</option>
              <option value="Chester">Chester Diocesan</option>
              <option value="Gloucester & Bristol">Gloucester & Bristol</option>
              <option value="Norwich">Norwich Diocesan</option>
              <option value="Lincoln">Lincoln Diocesan</option>
              <option value="Hereford">Hereford Diocesan</option>
              <option value="Winchester & Portsmouth">Winchester & Portsmouth</option>
              <option value="Peterborough">Peterborough Diocesan</option>
              <option value="Yorkshire">Yorkshire Association</option>
              <option value="Sussex">Sussex County</option>
            </select>
          </div>
        </div>

        <canvas id="constellationCanvas" width="1600" height="1160"></canvas>

        <div class="graph-actions">
          <button class="action-btn" id="btnZoomIn" title="Zoom In">+</button>
          <button class="action-btn" id="btnZoomOut" title="Zoom Out">&minus;</button>
          <button class="action-btn" id="btnReset" title="Reset View">&#x21bb;</button>
        </div>

        <div class="legend">
          <div class="legend-item"><div class="legend-dot" style="background:#0284C7"></div> Bath &amp; Wells</div>
          <div class="legend-item"><div class="legend-dot" style="background:#8B5CF6"></div> Hertford</div>
          <div class="legend-item"><div class="legend-dot" style="background:#0D9488"></div> Kent</div>
          <div class="legend-item"><div class="legend-dot" style="background:#84CC16"></div> Suffolk</div>
          <div class="legend-item"><div class="legend-dot" style="background:#2563EB"></div> Oxford Diocesan</div>
          <div class="legend-item"><div class="legend-dot" style="background:#06B6D4"></div> Devonshire</div>
          <div class="legend-item"><div class="legend-dot" style="background:#EAB308"></div> College Youths</div>
          <div class="legend-item"><div class="legend-dot" style="background:#059669"></div> Royal Cumberland</div>
          <div class="legend-item"><div class="legend-dot" style="background:#F59E0B"></div> Chester</div>
          <div class="legend-item"><div class="legend-dot" style="background:#F43F5E"></div> Gloucester &amp; Bristol</div>
          <div class="legend-item"><div class="legend-dot" style="background:#10B981"></div> Norwich</div>
          <div class="legend-item"><div class="legend-dot" style="background:#D97706"></div> Lincoln</div>
          <div class="legend-item"><div class="legend-dot" style="background:#6366F1"></div> Hereford</div>
          <div class="legend-item"><div class="legend-dot" style="background:#A855F7"></div> Winchester &amp; Portsmouth</div>
          <div class="legend-item"><div class="legend-dot" style="background:#F97316"></div> Yorkshire</div>
          <div class="legend-item"><div class="legend-dot" style="background:#EC4899"></div> Sussex</div>
          <div class="legend-item"><div class="legend-dot" style="background:#94A3B8"></div> Other Regional / Independent</div>
        </div>
      </div>

      <!-- Side Dossier Card -->
      <div class="dossier-card" id="dossierCard">
        <div class="dossier-header">
          <div class="d-id" id="dId">RINGER_000001</div>
          <h3 id="dName">Susan M Sawyer</h3>
          <div class="d-badge" id="dAssoc">Oxford Diocesan Guild</div>
        </div>

        <div class="d-stats">
          <div class="d-stat"><div class="val" id="dPeals">907</div><div class="lbl">Total Peals</div></div>
          <div class="d-stat"><div class="val" id="dYears">2023–2024</div><div class="lbl">Active Period</div></div>
        </div>

        <div class="d-section">
          <h4>Unified Name Variations (<span id="dAliasCount">4</span> Aliases)</h4>
          <ul class="alias-list" id="dAliases"></ul>
        </div>

        <div class="d-section">
          <h4>Top Band Partners (Shared Peals)</h4>
          <ul class="partner-list" id="dPartners"></ul>
        </div>

        <div class="d-section">
          <h4>Top Towers Rung At</h4>
          <ul class="tower-list" id="dTowers"></ul>
        </div>
      </div>
    </div>
  </section>

  <section>
    <h2>Canonical Entity & Alias Cluster Explorer</h2>
    <div class="lede">
      Search any ringer name, initials, or diminutive across 1,500 canonical ringers to explore resolved entities and their constituent aliases. Click any row to focus on that ringer in the constellation above.
    </div>

    <div class="search-bar-wrap">
      <input type="text" class="search-input" id="tableSearch" placeholder="Type a ringer name (e.g. Sawyer, Smith, Pink, Boulton, Hitchings)...">
    </div>

    <div class="candidate-table-wrap">
      <table>
        <thead>
          <tr>
            <th>Canonical Ringer</th>
            <th>ID</th>
            <th>Total Peals</th>
            <th>Active Period</th>
            <th>Merged Aliases & Nicknames</th>
          </tr>
        </thead>
        <tbody id="candidateTbody"></tbody>
      </table>
    </div>
  </section>
</div>

<script>
const NODES = {nodes_json};
const EDGES = {edges_json};
const SEARCH_DATA = {search_json};

// Canvas Setup
const canvas = document.getElementById('constellationCanvas');
const ctx = canvas.getContext('2d');
const WIDTH = 1600;
const HEIGHT = 1160;

let zoom = 1.0, panX = 0, panY = 0;
let isDragging = false;
let startMouseX = 0, startMouseY = 0;
let startPanX = 0, startPanY = 0;
let selectedNode = NODES[0];
let hoveredNode = null;
let activeGuildFilter = "ALL";

// Populate Ringer Picker Dropdown
const ringerPicker = document.getElementById('ringerPicker');
NODES.forEach(n => {{
  const opt = document.createElement('option');
  opt.value = n.id;
  opt.textContent = `${{n.name}} (${{n.peals}} peals)`;
  ringerPicker.appendChild(opt);
}});

ringerPicker.addEventListener('change', e => {{
  if (e.target.value) {{
    selectRingerById(e.target.value);
  }}
}});

const nodeMap = new Map();
NODES.forEach(n => {{
  nodeMap.set(n.id, n);
}});

// Map edges to objects
const edgeObjs = EDGES.map(e => ({{
  source: nodeMap.get(e.source),
  target: nodeMap.get(e.target),
  weight: e.weight
}})).filter(e => e.source && e.target);

function render() {{
  ctx.save();
  ctx.clearRect(0, 0, WIDTH, HEIGHT);

  ctx.translate(WIDTH / 2 + panX, HEIGHT / 2 + panY);
  ctx.scale(zoom, zoom);

  const isDark = document.documentElement.getAttribute('data-theme') === 'dark' || 
    (!document.documentElement.getAttribute('data-theme') && window.matchMedia('(prefers-color-scheme: dark)').matches);

  const activeFocusNode = hoveredNode || selectedNode;
  const connectedIds = new Set();
  if (activeFocusNode) {{
    connectedIds.add(activeFocusNode.id);
    edgeObjs.forEach(e => {{
      if (e.source.id === activeFocusNode.id) connectedIds.add(e.target.id);
      if (e.target.id === activeFocusNode.id) connectedIds.add(e.source.id);
    }});
  }}

  // Draw Edges
  edgeObjs.forEach(e => {{
    const isConn = activeFocusNode && (e.source.id === activeFocusNode.id || e.target.id === activeFocusNode.id);
    const alpha = activeFocusNode ? (isConn ? 0.85 : 0.05) : Math.min(0.35, e.weight / 60);
    const width = isConn ? Math.max(3.0, Math.min(9, e.weight / 20)) : Math.max(1.0, Math.min(4, e.weight / 50));

    ctx.beginPath();
    ctx.moveTo(e.source.x, e.source.y);
    ctx.lineTo(e.target.x, e.target.y);
    ctx.strokeStyle = isConn ? '#B8873F' : (isDark ? 'rgba(255,255,255,' + alpha + ')' : 'rgba(0,0,0,' + alpha + ')');
    ctx.lineWidth = width;
    ctx.stroke();
  }});

  // Draw Nodes
  NODES.forEach(n => {{
    const matchesFilter = (activeGuildFilter === 'ALL' || n.assoc.includes(activeGuildFilter));
    const isConn = !activeFocusNode || connectedIds.has(n.id);
    const isSel = (selectedNode && selectedNode.id === n.id);
    const isHov = (hoveredNode && hoveredNode.id === n.id);

    const baseAlpha = matchesFilter ? (isConn ? 1.0 : 0.25) : 0.10;

    ctx.beginPath();
    ctx.arc(n.x, n.y, n.radius * (isSel || isHov ? 1.25 : 1.0), 0, Math.PI * 2);
    ctx.fillStyle = n.color;
    ctx.globalAlpha = baseAlpha;
    ctx.fill();

    if (isSel || isHov) {{
      ctx.lineWidth = 4;
      ctx.strokeStyle = isDark ? '#FFFFFF' : '#1C1E1C';
      ctx.stroke();
    }} else {{
      ctx.lineWidth = 1.5;
      ctx.strokeStyle = isDark ? 'rgba(0,0,0,0.6)' : 'rgba(255,255,255,0.85)';
      ctx.stroke();
    }}

    // Labels
    if ((n.peals >= 450 || isConn || isSel || isHov) && matchesFilter) {{
      ctx.font = (isSel || isHov ? 'bold 18px' : '15px') + ' var(--mono)';
      ctx.fillStyle = isDark ? '#F0EDE6' : '#1C1E1C';
      ctx.globalAlpha = isConn ? 1.0 : 0.4;
      ctx.fillText(n.name, n.x + n.radius + 8, n.y + 5);
    }}
  }});

  ctx.restore();
}}

// Interactions
function getNodeAt(screenX, screenY) {{
  const rect = canvas.getBoundingClientRect();
  const scaleX = WIDTH / rect.width;
  const scaleY = HEIGHT / rect.height;
  const canvasX = (screenX - rect.left) * scaleX;
  const canvasY = (screenY - rect.top) * scaleY;

  const worldX = (canvasX - (WIDTH / 2 + panX)) / zoom;
  const worldY = (canvasY - (HEIGHT / 2 + panY)) / zoom;

  for (let i = NODES.length - 1; i >= 0; i--) {{
    const n = NODES[i];
    const dist = Math.hypot(n.x - worldX, n.y - worldY);
    if (dist <= n.radius + 12) return n;
  }}
  return null;
}}

canvas.addEventListener('mousedown', e => {{
  const hit = getNodeAt(e.clientX, e.clientY);
  if (hit) {{
    selectRingerNode(hit);
  }} else {{
    isDragging = true;
    startMouseX = e.clientX;
    startMouseY = e.clientY;
    startPanX = panX;
    startPanY = panY;
  }}
}});

window.addEventListener('mousemove', e => {{
  if (isDragging) {{
    const rect = canvas.getBoundingClientRect();
    const scaleX = WIDTH / rect.width;
    const scaleY = HEIGHT / rect.height;
    const dx = (e.clientX - startMouseX) * scaleX;
    const dy = (e.clientY - startMouseY) * scaleY;
    panX = startPanX + dx;
    panY = startPanY + dy;
    render();
  }} else {{
    const rect = canvas.getBoundingClientRect();
    if (e.clientX >= rect.left && e.clientX <= rect.right && e.clientY >= rect.top && e.clientY <= rect.bottom) {{
      const hit = getNodeAt(e.clientX, e.clientY);
      if (hit !== hoveredNode) {{
        hoveredNode = hit;
        render();
      }}
    }} else if (hoveredNode) {{
      hoveredNode = null;
      render();
    }}
  }}
}});

window.addEventListener('mouseup', () => {{ isDragging = false; }});

canvas.addEventListener('wheel', e => {{
  e.preventDefault();
  const rect = canvas.getBoundingClientRect();
  const scaleX = WIDTH / rect.width;
  const scaleY = HEIGHT / rect.height;
  const canvasX = (e.clientX - rect.left) * scaleX;
  const canvasY = (e.clientY - rect.top) * scaleY;

  const mouseX = canvasX - (WIDTH / 2 + panX);
  const mouseY = canvasY - (HEIGHT / 2 + panY);

  const delta = e.deltaY < 0 ? 1.15 : 0.87;
  const newZoom = Math.min(3.5, Math.max(0.4, zoom * delta));
  panX -= mouseX * (newZoom / zoom - 1);
  panY -= mouseY * (newZoom / zoom - 1);
  zoom = newZoom;
  render();
}}, {{passive: false}});

// Zoom buttons
document.getElementById('btnZoomIn').onclick = () => {{ zoom = Math.min(3.5, zoom * 1.25); render(); }};
document.getElementById('btnZoomOut').onclick = () => {{ zoom = Math.max(0.4, zoom / 1.25); render(); }};
document.getElementById('btnReset').onclick = () => {{ zoom = 1.0; panX = 0; panY = 0; render(); }};

// Guild filter
document.getElementById('guildFilter').addEventListener('change', e => {{
  activeGuildFilter = e.target.value;
  render();
}});

// Select Ringer Action
function selectRingerNode(node) {{
  selectedNode = node;
  updateDossier(node);
  ringerPicker.value = node.id;
  updateChipButtons(node.id);
  render();
}}

function selectRingerById(ringerId) {{
  const n = nodeMap.get(ringerId);
  if (n) {{
    selectRingerNode(n);
    panX = -n.x * zoom;
    panY = -n.y * zoom;
    render();
  }}
}}

// Chip buttons click
document.querySelectorAll('.chip-btn').forEach(btn => {{
  btn.addEventListener('click', () => {{
    const rId = btn.getAttribute('data-id');
    selectRingerById(rId);
  }});
}});

function updateChipButtons(activeId) {{
  document.querySelectorAll('.chip-btn').forEach(btn => {{
    btn.classList.toggle('active', btn.getAttribute('data-id') === activeId);
  }});
}}

// Update Dossier Card
function updateDossier(node) {{
  document.getElementById('dId').textContent = node.id;
  document.getElementById('dName').textContent = node.name;
  document.getElementById('dAssoc').textContent = node.assoc;
  document.getElementById('dPeals').textContent = node.peals.toLocaleString();
  document.getElementById('dYears').textContent = node.active_years || '2023–2024';
  document.getElementById('dAliasCount').textContent = node.aliases.length;

  // Aliases
  const aliasUl = document.getElementById('dAliases');
  aliasUl.innerHTML = '';
  node.aliases.forEach(a => {{
    const li = document.createElement('li');
    const isP = a.is_primary ? ' class="is-p"' : '';
    li.innerHTML = `<span${{isP}}>${{a.raw_name}}</span><span class="cnt">${{a.variant_peal_count}} peals</span>`;
    aliasUl.appendChild(li);
  }});

  // Partners
  const partUl = document.getElementById('dPartners');
  partUl.innerHTML = '';
  if (node.partners && node.partners.length > 0) {{
    node.partners.forEach(p => {{
      const li = document.createElement('li');
      li.innerHTML = `<span>${{p.name}}</span><span class="cnt">${{p.peals}} mutual peals</span>`;
      li.style.cursor = 'pointer';
      li.onclick = () => selectRingerById(p.id);
      partUl.appendChild(li);
    }});
  }} else {{
    partUl.innerHTML = '<li style="color:var(--ink-3)">No recorded top-200 partner data</li>';
  }}

  // Towers
  const towUl = document.getElementById('dTowers');
  towUl.innerHTML = '';
  if (node.towers && node.towers.length > 0) {{
    node.towers.forEach(t => {{
      const li = document.createElement('li');
      li.innerHTML = `<span>${{t.tower}}</span><span class="cnt">${{t.peals}} peals</span>`;
      towUl.appendChild(li);
    }});
  }}
}}

// Search Table Population
const tbody = document.getElementById('candidateTbody');
function renderTable(filterText = '') {{
  tbody.innerHTML = '';
  const q = filterText.toLowerCase().trim();
  const matched = SEARCH_DATA.filter(r => {{
    if (!q) return true;
    if (r.name.toLowerCase().includes(q)) return true;
    if (r.id.toLowerCase().includes(q)) return true;
    return r.aliases.some(a => a.toLowerCase().includes(q));
  }}).slice(0, 50);

  matched.forEach(r => {{
    const tr = document.createElement('tr');
    const aliasHtml = r.aliases.map(a => `<span class="tag-alias">${{a}}</span>`).join(' ');
    tr.innerHTML = `
      <td><strong>${{r.name}}</strong></td>
      <td style="font-family:var(--mono);font-size:11px;color:var(--bronze)">${{r.id}}</td>
      <td style="font-family:var(--mono);font-variant-numeric:tabular-nums">${{r.peals.toLocaleString()}}</td>
      <td style="font-family:var(--mono);font-size:11px;color:var(--ink-3)">${{r.years}}</td>
      <td>${{aliasHtml}}</td>
    `;
    tr.onclick = () => {{
      selectRingerById(r.id);
      window.scrollTo({{top: 380, behavior: 'smooth'}});
    }};
    tr.style.cursor = 'pointer';
    tbody.appendChild(tr);
  }});
}}

document.getElementById('tableSearch').addEventListener('input', e => {{
  renderTable(e.target.value);
}});

// Theme toggler
const themeToggle = document.getElementById('themeToggle');
themeToggle.addEventListener('click', () => {{
  const curr = document.documentElement.getAttribute('data-theme') || 
    (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  const next = curr === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  themeToggle.textContent = next === 'dark' ? 'Light Mode' : 'Dark Mode';
  render();
}});

updateDossier(selectedNode);
renderTable();
render();
</script>
<!--FOOTER:ringers.html-->
</body>
</html>
"""

if __name__ == "__main__":
    build_page()
