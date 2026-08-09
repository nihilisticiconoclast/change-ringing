#!/usr/bin/env python3
"""
Generate the Interactive Ringer Constellation & Identity Atlas (docs/ringers.html).

Builds:
- Force-directed interactive network graph of top ringing bands & partnerships
- Live Canonical Ringer Search & Alias Cluster Inspector across 35,090 ringer variations
- Guild & Association community clustering with harmonic palette
- Standalone zero-dependency HTML bundle in docs/ringers.html

Usage:
    python scripts/build_ringers_page.py
"""
import collections
import json
import sqlite3
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "change-ringing.db"
CANDIDATES_CSV = ROOT / "data" / "ringer_identity_candidates.csv"
OUT_HTML = ROOT / "docs" / "ringers.html"

# Association Color Palette (Harmonious & Meaningful)
ASSOC_PALETTE = {
    "Ancient Society of College Youths": "#eab308",         # Imperial Gold
    "Society of Royal Cumberland Youths": "#10b981",        # Emerald
    "Oxford Diocesan Guild": "#3b82f6",                     # Royal Blue
    "Winchester & Portsmouth Diocesan Guild": "#8b5cf6",     # Amethyst Purple
    "Yorkshire Association": "#f97316",                     # Coral Orange
    "Guild of Devonshire Ringers": "#06b6d4",               # Turquoise
    "Sussex County Association": "#ec4899",                 # Rose
    "St Martin's Guild for the Diocese of Birmingham": "#14b8a6", # Teal
    "Gloucester & Bristol Diocesan Association": "#f43f5e", # Crimson
    "Suffolk Guild": "#84cc16",                             # Lime
    "Ely Diocesan Association": "#6366f1",                  # Indigo
    "Non-Association": "#71717a",                           # Slate Grey
    "Other": "#a1a1aa"                                      # Neutral Grey
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

    # Compute top associations and top towers for each canonical ringer
    ringer_assocs = collections.defaultdict(collections.Counter)
    ringer_towers = collections.defaultdict(collections.Counter)
    ringer_dates = collections.defaultdict(list)

    for _, row in perf_df.iterrows():
        c_id = row["canon_id"]
        if not c_id:
            continue
        if row["association"]:
            ringer_assocs[c_id][row["association"].strip()] += 1
        if row["dove_tower_id"]:
            ringer_towers[c_id][int(row["dove_tower_id"])] += 1
        if row["perf_date"]:
            ringer_dates[c_id].append(row["perf_date"])

    # Select top 200 most active canonical ringers for network graph
    top_200 = canon_ringers.sort_values(by="cluster_total_peals", ascending=False).head(200)
    top_200_ids = set(top_200["canonical_ringer_id"])

    # Compute pairwise co-occurrences
    perf_bands = perf_df.groupby("perf_id")["canon_id"].apply(lambda s: list(set(s.dropna()))).to_dict()

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
        primary_assoc = ass_counter.most_common(1)[0][0] if ass_counter else "Other"
        
        # Map to standard color category
        color_cat = "Other"
        for k in ASSOC_PALETTE:
            if k in primary_assoc or primary_assoc in k:
                color_cat = k
                break

        # Top 5 towers
        t_counter = ringer_towers[c_id]
        top_towers_list = [
            {"tower": tower_lookup.get(t_id, f"Tower #{t_id}"), "peals": cnt}
            for t_id, cnt in t_counter.most_common(5)
        ]

        # Top 5 partners
        p_counter = top_partners[c_id]
        top_partners_list = [
            {"id": p_id, "name": canon_ringers.loc[canon_ringers["canonical_ringer_id"] == p_id, "canonical_name"].values[0], "peals": cnt}
            for p_id, cnt in p_counter.most_common(5)
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
            "color": ASSOC_PALETTE.get(color_cat, ASSOC_PALETTE["Other"]),
            "active_years": r["active_years"],
            "towers": top_towers_list,
            "partners": top_partners_list,
            "aliases": aliases
        })

    # Format edges (keep edges with at least 5 shared peals to keep graph responsive and clean)
    edges = []
    for (r1, r2), count in co_counts.items():
        if count >= 5:
            edges.append({
                "source": r1,
                "target": r2,
                "weight": count
            })

    print(f"Network graph constructed with {len(nodes)} nodes and {len(edges)} edges.", flush=True)

    # Format top partnerships leaderboard
    leaderboard = []
    for (r1, r2), cnt in co_counts.most_common(30):
        n1 = canon_ringers.loc[canon_ringers["canonical_ringer_id"] == r1, "canonical_name"].values[0]
        n2 = canon_ringers.loc[canon_ringers["canonical_ringer_id"] == r2, "canonical_name"].values[0]
        leaderboard.append({
            "r1": r1, "name1": n1,
            "r2": r2, "name2": n2,
            "peals": cnt
        })

    # Prepare compact search index for the top 1,500 canonical ringers
    top_search_ringers = canon_ringers.sort_values(by="cluster_total_peals", ascending=False).head(1500)
    search_ids = set(top_search_ringers["canonical_ringer_id"])
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

    # Write HTML page
    html_content = generate_html(nodes, edges, leaderboard, search_data, ASSOC_PALETTE)
    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(html_content, encoding="utf-8")
    print(f"\nWrote {OUT_HTML} ({OUT_HTML.stat().st_size / 1024:.1f} KB)", flush=True)


def generate_html(nodes, edges, leaderboard, search_data, palette):
    nodes_json = json.dumps(nodes)
    edges_json = json.dumps(edges)
    leaderboard_json = json.dumps(leaderboard)
    search_json = json.dumps(search_data)
    palette_json = json.dumps(palette)

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>The Ringer Constellation — Band Networks & Canonical Identity Resolution</title>
<style>
:root{{
  --ground:#EFEDE7; --surface:#F7F6F2; --surface-2:#E4E2DA;
  --ink:#1C1E1C; --ink-2:#4A4C48; --ink-3:#7C7E78;
  --rule:#CFCCC2; --bronze:#8A5F22; --bronze-soft:#B8873F;
  --serif:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,"Times New Roman",serif;
  --mono:ui-monospace,"SF Mono",SFMono-Regular,Menlo,Consolas,monospace;
}}
@media (prefers-color-scheme:dark){{
  :root:not([data-theme="light"]){{
    --ground:#131312; --surface:#1a1a19; --surface-2:#242422;
    --ink:#F0EDE6; --ink-2:#B5B1A7; --ink-3:#85817A;
    --rule:#302F2C; --bronze:#C9974A; --bronze-soft:#B8873F;
  }}
}}
:root[data-theme="dark"]{{
  --ground:#131312; --surface:#1a1a19; --surface-2:#242422;
  --ink:#F0EDE6; --ink-2:#B5B1A7; --ink-3:#85817A;
  --rule:#302F2C; --bronze:#C9974A; --bronze-soft:#B8873F;
}}
*{{box-sizing:border-box}}
body{{
  margin:0; background:var(--ground); color:var(--ink);
  font-family:var(--serif); font-size:17px; line-height:1.62;
  -webkit-font-smoothing:antialiased;
}}
.nav-bar{{
  background:var(--surface); border-bottom:1px solid var(--rule);
  padding:12px 24px; display:flex; justify-content:space-between; align-items:center;
}}
.nav-links{{display:flex;gap:20px;font-family:var(--mono);font-size:12px;letter-spacing:.08em;text-transform:uppercase}}
.nav-links a{{color:var(--ink-2);text-decoration:none;padding:4px 0;border-bottom:2px solid transparent}}
.nav-links a.active{{color:var(--bronze);border-bottom-color:var(--bronze);font-weight:600}}
.nav-links a:hover{{color:var(--ink)}}
.theme-btn{{
  background:none;border:1px solid var(--rule);color:var(--ink-2);padding:4px 10px;
  font-family:var(--mono);font-size:11px;cursor:pointer;border-radius:2px;
}}
.wrap{{max-width:1160px;margin:0 auto;padding:0 24px}}
header{{padding:60px 0 40px;border-bottom:1px solid var(--rule)}}
.eyebrow{{
  font-family:var(--mono); font-size:11px; letter-spacing:.18em;
  text-transform:uppercase; color:var(--bronze); margin:0 0 14px;
}}
h1{{font-size:clamp(2.3rem,5.5vw,3.8rem);line-height:1.06;font-weight:400;letter-spacing:-.015em;margin:0}}
h1 em{{font-style:italic;color:var(--bronze)}}
.standfirst{{margin-top:18px;font-size:1.15rem;color:var(--ink-2);max-width:64ch}}
.figures{{display:flex;flex-wrap:wrap;gap:32px;margin-top:34px}}
.fig .n{{font-family:var(--mono);font-variant-numeric:tabular-nums;font-size:1.75rem;color:var(--ink);letter-spacing:-.02em}}
.fig .l{{font-family:var(--mono);font-size:10.5px;letter-spacing:.13em;text-transform:uppercase;color:var(--ink-3);margin-top:4px}}

section{{padding:54px 0;border-bottom:1px solid var(--rule)}}
h2{{font-size:clamp(1.5rem,2.8vw,2.1rem);font-weight:400;letter-spacing:-.01em;margin:0}}
.lede{{color:var(--ink-2);margin-top:12px;max-width:64ch}}

/* Explorer Layout */
.explorer-grid{{
  display:grid; grid-template-columns:1fr 340px; gap:24px; margin-top:28px;
}}
@media (max-width:920px){{
  .explorer-grid{{grid-template-columns:1fr}}
}}

/* Graph Container */
.graph-card{{
  background:var(--surface); border:1px solid var(--rule); border-radius:4px;
  position:relative; overflow:hidden; min-height:620px; display:flex; flex-direction:column;
}}
.graph-toolbar{{
  padding:10px 16px; border-bottom:1px solid var(--rule); display:flex;
  justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;
  background:var(--surface-2);
}}
.graph-title{{font-family:var(--mono); font-size:11.5px; letter-spacing:.08em; text-transform:uppercase; color:var(--ink-2)}}
.graph-filters{{display:flex; gap:8px; align-items:center; flex-wrap:wrap}}
.graph-select{{
  background:var(--surface); border:1px solid var(--rule); color:var(--ink);
  padding:4px 8px; font-family:var(--mono); font-size:11px; border-radius:2px;
}}
#constellationCanvas{{width:100%; height:570px; display:block; cursor:grab}}
#constellationCanvas:active{{cursor:grabbing}}

/* Floating Graph Controls */
.graph-actions{{
  position:absolute; bottom:16px; right:16px; display:flex; flex-direction:column; gap:6px; z-index:10;
}}
.action-btn{{
  width:32px; height:32px; background:var(--surface); border:1px solid var(--rule);
  color:var(--ink); border-radius:3px; display:flex; align-items:center; justify-content:center;
  font-family:var(--mono); font-size:14px; cursor:pointer; box-shadow:0 2px 8px rgba(0,0,0,.15);
}}
.action-btn:hover{{border-color:var(--bronze); color:var(--bronze)}}

/* Legend */
.legend{{
  padding:8px 14px; border-top:1px solid var(--rule); display:flex; flex-wrap:wrap; gap:12px;
  font-family:var(--mono); font-size:10.5px; background:var(--surface);
}}
.legend-item{{display:inline-flex; align-items:center; gap:5px}}
.legend-dot{{width:8px; height:8px; border-radius:50%}}

/* Side Dossier Panel */
.dossier-card{{
  background:var(--surface); border:1px solid var(--rule); border-radius:4px;
  padding:20px; display:flex; flex-direction:column; gap:18px;
}}
.dossier-header .d-id{{font-family:var(--mono); font-size:11px; color:var(--bronze); letter-spacing:.1em; text-transform:uppercase}}
.dossier-header h3{{font-size:1.4rem; font-weight:400; margin:4px 0 0}}
.d-badge{{
  display:inline-block; font-family:var(--mono); font-size:10px; letter-spacing:.06em;
  padding:2px 8px; border-radius:2px; background:var(--surface-2); border:1px solid var(--rule);
  color:var(--ink-2); text-transform:uppercase; margin-top:6px;
}}
.d-stats{{display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-top:10px}}
.d-stat .val{{font-family:var(--mono); font-size:1.3rem; font-weight:600}}
.d-stat .lbl{{font-family:var(--mono); font-size:10px; color:var(--ink-3); text-transform:uppercase}}

.d-section h4{{
  font-family:var(--mono); font-size:11px; text-transform:uppercase; letter-spacing:.08em;
  color:var(--ink-2); margin:0 0 8px; border-bottom:1px solid var(--rule); padding-bottom:4px;
}}
.alias-list, .partner-list, .tower-list{{list-style:none; padding:0; margin:0; font-size:13px}}
.alias-list li{{
  padding:4px 0; font-family:var(--mono); font-size:11.5px; display:flex; justify-content:space-between;
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
  width:100%; max-width:480px; padding:10px 14px; font-family:var(--mono); font-size:13px;
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

<div class="nav-bar">
  <div class="nav-links">
    <a href="index.html">Corpus Atlas</a>
    <a href="lineage.html">Method Lineage</a>
    <a href="ringers.html" class="active">Ringer Constellation</a>
  </div>
  <button class="theme-btn" id="themeToggle">Dark Mode</button>
</div>

<div class="wrap">
  <header>
    <div class="eyebrow">Gemini Task 3 &middot; Band Networks &middot; Community Resolution</div>
    <h1>The Ringer <em>Constellation</em></h1>
    <div class="standfirst">
      Interactive band co-occurrence networks and canonical entity resolution across
      <strong>355,550 ringer instances</strong> and <strong>51,126 historical peals</strong>.
    </div>
    <div class="figures">
      <div class="fig"><div class="n">355,550</div><div class="l">Ringer Peal Records</div></div>
      <div class="fig"><div class="n">35,090</div><div class="l">Raw Name Variants</div></div>
      <div class="fig"><div class="n">29,446</div><div class="l">Canonical Ringers</div></div>
      <div class="fig"><div class="n">4,835</div><div class="l">Unified Alias Clusters</div></div>
    </div>
  </header>

  <section>
    <h2>Interactive Band Co-occurrence Network</h2>
    <div class="lede">
      Nodes represent the top 200 canonical ringers sized by historical peal volume, connected by shared peals in the same band. 
      Colors denote primary territorial guild / association membership. Click any ringer node to inspect their dossier, alias cluster, and regular partners.
    </div>

    <div class="explorer-grid">
      <!-- Network Canvas -->
      <div class="graph-card">
        <div class="graph-toolbar">
          <div class="graph-title">Top 200 Ringers &middot; Mutual Peal Network</div>
          <div class="graph-filters">
            <select class="graph-select" id="guildFilter">
              <option value="ALL">All Ringing Guilds / Associations</option>
              <option value="Ancient Society of College Youths">Ancient Society of College Youths</option>
              <option value="Society of Royal Cumberland Youths">Society of Royal Cumberland Youths</option>
              <option value="Oxford Diocesan Guild">Oxford Diocesan Guild</option>
              <option value="Winchester & Portsmouth Diocesan Guild">Winchester & Portsmouth</option>
              <option value="Yorkshire Association">Yorkshire Association</option>
              <option value="Guild of Devonshire Ringers">Devonshire Ringers</option>
              <option value="Sussex County Association">Sussex County Association</option>
              <option value="Gloucester & Bristol Diocesan Association">Gloucester & Bristol</option>
              <option value="St Martin's Guild for the Diocese of Birmingham">St Martin's Guild</option>
            </select>
          </div>
        </div>

        <canvas id="constellationCanvas"></canvas>

        <div class="graph-actions">
          <button class="action-btn" id="btnZoomIn" title="Zoom In">+</button>
          <button class="action-btn" id="btnZoomOut" title="Zoom Out">&minus;</button>
          <button class="action-btn" id="btnReset" title="Reset View">&#x21bb;</button>
        </div>

        <div class="legend">
          <div class="legend-item"><div class="legend-dot" style="background:#eab308"></div> College Youths</div>
          <div class="legend-item"><div class="legend-dot" style="background:#10b981"></div> Royal Cumberland Youths</div>
          <div class="legend-item"><div class="legend-dot" style="background:#3b82f6"></div> Oxford Diocesan</div>
          <div class="legend-item"><div class="legend-dot" style="background:#8b5cf6"></div> Winchester & Portsmouth</div>
          <div class="legend-item"><div class="legend-dot" style="background:#f97316"></div> Yorkshire</div>
          <div class="legend-item"><div class="legend-dot" style="background:#06b6d4"></div> Devonshire</div>
          <div class="legend-item"><div class="legend-dot" style="background:#ec4899"></div> Sussex</div>
          <div class="legend-item"><div class="legend-dot" style="background:#f43f5e"></div> Gloucester & Bristol</div>
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
          <h4>Unified Name Variations (4 Aliases)</h4>
          <ul class="alias-list" id="dAliases">
            <li><span class="is-p">Susan M Sawyer</span> <span class="cnt">571 peals</span></li>
            <li><span>Sue Sawyer</span> <span class="cnt">330 peals</span></li>
            <li><span>Susan Sawyer</span> <span class="cnt">5 peals</span></li>
            <li><span>Sue M Sawyer</span> <span class="cnt">1 peal</span></li>
          </ul>
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
      Search any ringer name, initials, or diminutive to explore resolved canonical entities and their constituent aliases.
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
const PALETTE = {palette_json};

// Setup Canvas & Simulation
const canvas = document.getElementById('constellationCanvas');
const ctx = canvas.getContext('2d');
let width, height;
let zoom = 1.0, panX = 0, panY = 0;
let isDragging = false, dragStart = {{x:0, y:0}};
let selectedNode = NODES[0];
let hoveredNode = null;
let activeGuildFilter = "ALL";

function resizeCanvas() {{
  const rect = canvas.getBoundingClientRect();
  width = rect.width;
  height = rect.height;
  canvas.width = width * window.devicePixelRatio;
  canvas.height = height * window.devicePixelRatio;
  ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
}}

// Initialize Node Coordinates with Circle Layout + Force Jitter
const nodeMap = new Map();
NODES.forEach((n, idx) => {{
  const angle = (idx / NODES.length) * Math.PI * 2;
  const radius = 180 + (idx % 4) * 60;
  n.x = Math.cos(angle) * radius;
  n.y = Math.sin(angle) * radius;
  n.vx = 0;
  n.vy = 0;
  n.radius = Math.max(4.5, Math.min(18, Math.sqrt(n.peals) * 0.48));
  nodeMap.set(n.id, n);
}});

// Map edges to objects
const edgeObjs = EDGES.map(e => ({{
  source: nodeMap.get(e.source),
  target: nodeMap.get(e.target),
  weight: e.weight
}})).filter(e => e.source && e.target);

// Simple Force Simulation (50 ticks)
for (let iter = 0; iter < 45; iter++) {{
  // Repulsion
  for (let i = 0; i < NODES.length; i++) {{
    for (let j = i + 1; j < NODES.length; j++) {{
      const n1 = NODES[i], n2 = NODES[j];
      const dx = n2.x - n1.x, dy = n2.y - n1.y;
      const dist = Math.hypot(dx, dy) || 1;
      if (dist < 220) {{
        const force = (220 - dist) / dist * 0.08;
        n1.x -= dx * force; n1.y -= dy * force;
        n2.x += dx * force; n2.y += dy * force;
      }}
    }}
  }}
  // Edge Spring Attraction
  edgeObjs.forEach(e => {{
    const dx = e.target.x - e.source.x, dy = e.target.y - e.source.y;
    const dist = Math.hypot(dx, dy) || 1;
    const force = (dist - 90) * 0.003 * Math.min(e.weight, 50) / 15;
    e.source.x += dx * force; e.source.y += dy * force;
    e.target.x -= dx * force; e.target.y -= dy * force;
  }});
}}

function render() {{
  ctx.save();
  ctx.clearRect(0, 0, width, height);

  ctx.translate(width / 2 + panX, height / 2 + panY);
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
    const alpha = activeFocusNode ? (isConn ? 0.8 : 0.04) : Math.min(0.35, e.weight / 60);
    const width = isConn ? Math.max(1.8, Math.min(5, e.weight / 40)) : Math.max(0.6, Math.min(2.5, e.weight / 80));

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

    const baseAlpha = matchesFilter ? (isConn ? 1.0 : 0.2) : 0.1;

    ctx.beginPath();
    ctx.arc(n.x, n.y, n.radius * (isSel || isHov ? 1.25 : 1.0), 0, Math.PI * 2);
    ctx.fillStyle = n.color;
    ctx.globalAlpha = baseAlpha;
    ctx.fill();

    if (isSel || isHov) {{
      ctx.lineWidth = 3;
      ctx.strokeStyle = isDark ? '#ffffff' : '#1C1E1C';
      ctx.stroke();
    }} else {{
      ctx.lineWidth = 1;
      ctx.strokeStyle = isDark ? 'rgba(0,0,0,0.6)' : 'rgba(255,255,255,0.8)';
      ctx.stroke();
    }}

    // Labels for high-peal or connected nodes
    if ((n.peals >= 450 || isConn || isSel || isHov) && matchesFilter) {{
      ctx.font = (isSel || isHov ? 'bold 12px' : '10.5px') + ' var(--mono)';
      ctx.fillStyle = isDark ? '#F0EDE6' : '#1C1E1C';
      ctx.globalAlpha = isConn ? 1.0 : 0.3;
      ctx.fillText(n.name, n.x + n.radius + 5, n.y + 3.5);
    }}
  }});

  ctx.restore();
}}

// Interactions
function getNodeAt(x, y) {{
  const worldX = (x - (width / 2 + panX)) / zoom;
  const worldY = (y - (height / 2 + panY)) / zoom;
  for (let i = NODES.length - 1; i >= 0; i--) {{
    const n = NODES[i];
    const dist = Math.hypot(n.x - worldX, n.y - worldY);
    if (dist <= n.radius + 6) return n;
  }}
  return null;
}}

canvas.addEventListener('mousedown', e => {{
  const rect = canvas.getBoundingClientRect();
  const x = e.clientX - rect.left, y = e.clientY - rect.top;
  const hit = getNodeAt(x, y);
  if (hit) {{
    selectedNode = hit;
    updateDossier(hit);
    render();
  }} else {{
    isDragging = true;
    dragStart = {{x: e.clientX - panX, y: e.clientY - panY}};
  }}
}});

window.addEventListener('mousemove', e => {{
  const rect = canvas.getBoundingClientRect();
  if (isDragging) {{
    panX = e.clientX - dragStart.x;
    panY = e.clientY - dragStart.y;
    render();
  }} else if (e.clientX >= rect.left && e.clientX <= rect.right && e.clientY >= rect.top && e.clientY <= rect.bottom) {{
    const x = e.clientX - rect.left, y = e.clientY - rect.top;
    const hit = getNodeAt(x, y);
    if (hit !== hoveredNode) {{
      hoveredNode = hit;
      render();
    }}
  }} else if (hoveredNode) {{
    hoveredNode = null;
    render();
  }}
}});

window.addEventListener('mouseup', () => {{ isDragging = false; }});

canvas.addEventListener('wheel', e => {{
  e.preventDefault();
  const rect = canvas.getBoundingClientRect();
  const mouseX = e.clientX - rect.left - (width / 2 + panX);
  const mouseY = e.clientY - rect.top - (height / 2 + panY);
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

// Update Dossier Card
function updateDossier(node) {{
  document.getElementById('dId').textContent = node.id;
  document.getElementById('dName').textContent = node.name;
  document.getElementById('dAssoc').textContent = node.assoc;
  document.getElementById('dPeals').textContent = node.peals.toLocaleString();
  document.getElementById('dYears').textContent = node.active_years || '2023–2024';

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
      const n = nodeMap.get(r.id);
      if (n) {{
        selectedNode = n;
        updateDossier(n);
        panX = -n.x * zoom;
        panY = -n.y * zoom;
        render();
        window.scrollTo({{top: 400, behavior: 'smooth'}});
      }}
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

window.addEventListener('resize', () => {{ resizeCanvas(); render(); }});
resizeCanvas();
updateDossier(selectedNode);
renderTable();
render();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    build_page()
