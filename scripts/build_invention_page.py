#!/usr/bin/env python3
"""
Builds the 'invention.html' interactive composition visualizer.
"""

import json
from pathlib import Path
from scripts.site_chrome import apply_chrome

ROOT = Path(__file__).parent.parent
JSON_PATH = ROOT / "data" / "search_results.json"
OUT_PATH = ROOT / "docs" / "invention.html"

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>First Rung: Composition Visualizer</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
  <style>
    :root {
      --ground: #EFEDE7; --surface: #F7F6F2; --surface-2: #E4E2DA;
      --ink: #1C1E1C; --ink-2: #4A4C48; --ink-3: #7C7E78;
      --rule: #CFCCC2; --bronze: #8A5F22; --accent: #38bdf8;
      --mono: ui-monospace, "SF Mono", SFMono-Regular, Menlo, Consolas, monospace;
    }
    @media (prefers-color-scheme: dark) {
      :root:not([data-theme="light"]) {
        --ground: #131312; --surface: #1a1a19; --surface-2: #242422;
        --ink: #F0EDE6; --ink-2: #B5B1A7; --ink-3: #85817A;
        --rule: #302F2C; --bronze: #C9974A; --accent: #38bdf8;
      }
    }
    :root[data-theme="dark"] {
      --ground: #131312; --surface: #1a1a19; --surface-2: #242422;
      --ink: #F0EDE6; --ink-2: #B5B1A7; --ink-3: #85817A;
      --rule: #302F2C; --bronze: #C9974A; --accent: #38bdf8;
    }
    body {
      margin: 0; padding: 0;
      font-family: system-ui, -apple-system, sans-serif;
      background: var(--ground);
      color: var(--ink);
    }
    .layout {
      display: flex;
      height: calc(100vh - 52px); /* Minus nav bar */
      max-width: 1200px;
      margin: 0 auto;
      border-left: 1px solid var(--rule);
      border-right: 1px solid var(--rule);
    }
    .sidebar {
      width: 350px;
      border-right: 1px solid var(--rule);
      overflow-y: auto;
      background: var(--surface);
    }
    .main-view {
      flex: 1;
      display: flex;
      flex-direction: column;
    }
    #mynetwork {
      flex: 1;
      background: var(--ground);
    }
    .comp-card {
      padding: 16px;
      border-bottom: 1px solid var(--rule);
      cursor: pointer;
      transition: background 0.2s;
    }
    .comp-card:hover { background: var(--surface-2); }
    .comp-card.active { background: var(--surface-2); border-left: 4px solid var(--bronze); }
    .comp-score { font-size: 1.2em; font-weight: bold; color: var(--bronze); }
    .comp-meta { font-size: 0.85em; color: var(--ink-2); margin-top: 4px; }
    .novel-badge {
      display: inline-block;
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 0.75em;
      font-weight: bold;
      background: #22c55e;
      color: #000;
      margin-left: 8px;
    }
    .not-novel-badge {
      display: inline-block;
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 0.75em;
      font-weight: bold;
      background: #64748b;
      color: #fff;
      margin-left: 8px;
    }
    .comp-calls {
      margin-top: 8px;
      font-family: var(--mono);
      font-size: 0.85em;
      word-wrap: break-word;
      color: var(--ink-2);
    }
    .header { padding: 16px; border-bottom: 1px solid var(--rule); }
    h1 { margin: 0; font-size: 1.5em; font-weight: 400; color: var(--ink); }
    p { margin: 8px 0 0; font-size: 0.9em; color: var(--ink-3); }
  </style>
</head>
<body>
<!--NAV:invention.html-->

<div class="layout">
  <div class="sidebar">
    <div class="header">
      <h1>Composition Search</h1>
      <p>Results from the Heuristic Beam Search Engine. Select a composition to visualize its directed path.</p>
    </div>
    <div id="comp-list"></div>
  </div>
  <div class="main-view">
    <div id="mynetwork"></div>
  </div>
</div>

<!--FOOTER:invention.html-->

<script>
  // Theme toggler
  const tb = document.getElementById('themeToggle');
  const setTheme = t => { 
    document.documentElement.setAttribute('data-theme', t);
    if (tb) tb.textContent = t === 'dark' ? 'Light Mode' : 'Dark Mode';
    try { localStorage.setItem('cr-theme', t); } catch (e) {}
    if (network) redrawGraph(); // Redraw graph to update colors
  };
  if (tb) tb.onclick = () =>
    setTheme(document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');
  (() => { 
    let t = null; try { t = localStorage.getItem('cr-theme'); } catch (e) {}
    if (!t) t = matchMedia('(prefers-color-scheme:dark)').matches ? 'dark' : 'light';
    setTheme(t); 
  })();

  // Inject JSON data
  const compositions = __DATA_JSON__;
  let network = null;
  let activeIdx = 0;

  function renderList() {
    const list = document.getElementById('comp-list');
    compositions.forEach((comp, idx) => {
      const el = document.createElement('div');
      el.className = 'comp-card';
      el.id = 'comp-' + idx;
      
      const badge = comp.novel ? '<span class="novel-badge">Likely Novel</span>' : '<span class="not-novel-badge">Previously Rung</span>';
      const complete = comp.is_complete ? 'TRUE composition' : 'Partial block';
      
      el.innerHTML = `
        <div class="comp-score">Score: ${comp.score.toFixed(1)}${badge}</div>
        <div class="comp-meta">${complete} · ${comp.length_leads} leads</div>
        <div class="comp-calls">${comp.calls.join(' ')}</div>
      `;
      el.onclick = () => selectComp(idx);
      list.appendChild(el);
    });
  }

  function selectComp(idx) {
    activeIdx = idx;
    document.querySelectorAll('.comp-card').forEach(el => el.classList.remove('active'));
    document.getElementById('comp-' + idx).classList.add('active');
    redrawGraph();
  }
  
  function getComputedColor(varName) {
    return getComputedStyle(document.documentElement).getPropertyValue(varName).trim();
  }

  function redrawGraph() {
    drawGraph(compositions[activeIdx]);
  }

  function drawGraph(comp) {
    const nodes = [];
    const edges = [];
    const nodeIds = new Set();
    
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    const bgColor = isDark ? "#1a1a19" : "#F7F6F2";
    const fgColor = isDark ? "#F0EDE6" : "#1C1E1C";
    const hlColor = isDark ? "#C9974A" : "#8A5F22";
    const rdColor = isDark ? "#63A579" : "#2F6D53";
    
    // Add nodes
    comp.path.forEach((ch, i) => {
      if (!nodeIds.has(ch)) {
        nodes.push({
          id: ch,
          label: ch,
          shape: 'box',
          color: {
            background: ch === "12345678" ? rdColor : bgColor,
            border: hlColor,
            highlight: hlColor
          },
          font: { color: ch === "12345678" ? "#FFF" : fgColor, face: "monospace" }
        });
        nodeIds.add(ch);
      }
    });
    
    // Add edges
    for (let i = 0; i < comp.calls.length; i++) {
      edges.push({
        from: comp.path[i],
        to: comp.path[i+1],
        label: comp.calls[i].toUpperCase(),
        arrows: 'to',
        color: { color: fgColor },
        font: { color: fgColor, strokeWidth: 0, size: 12, face: "monospace" }
      });
    }

    const container = document.getElementById('mynetwork');
    const data = { nodes: nodes, edges: edges };
    const options = {
      physics: {
        solver: 'forceAtlas2Based',
        forceAtlas2Based: {
          gravitationalConstant: -100,
          springLength: 80
        }
      }
    };
    
    if (network) network.destroy();
    network = new vis.Network(container, data, options);
  }

  window.onload = () => {
    if (compositions.length > 0) {
      renderList();
      selectComp(0); // Select first by default
    }
  };
</script>
</body>
</html>
"""

def main():
    print(f"Reading {JSON_PATH}...")
    if not JSON_PATH.exists():
        print(f"Error: {JSON_PATH} not found. Run export_compositions.py first.")
        return 1
        
    with open(JSON_PATH) as f:
        data_json = f.read()
        
    html = HTML_TEMPLATE.replace("__DATA_JSON__", data_json)
    
    print("Applying site chrome...")
    html = apply_chrome(html, dark=False) # Use standard chrome, no dark override
    
    print(f"Writing to {OUT_PATH}...")
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w") as f:
        f.write(html)
        
    print("Done!")
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
