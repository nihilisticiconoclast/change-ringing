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
      font-family: var(--serif);
      background: var(--ground);
      color: var(--ink);
      line-height: 1.62;
      -webkit-font-smoothing: antialiased;
    }
    
    /* Typography from main site */
    .wrap { max-width: 1200px; margin: 0 auto; padding: 0 24px; }
    h1, h2, h3, h4 { text-wrap: balance; margin: 0; }
    .eyebrow {
      font-family: var(--mono); font-size: 11px; letter-spacing: .18em;
      text-transform: uppercase; color: var(--bronze); margin: 0 0 14px;
    }
    header { padding: 64px 0 44px; }
    h1 { font-size: clamp(2.2rem, 5.5vw, 3.8rem); line-height: 1.04; font-weight: 400; letter-spacing: -.015em; }
    h1 em { font-style: italic; color: var(--bronze); }
    .standfirst { margin-top: 20px; font-size: 1.15rem; color: var(--ink-2); max-width: 64ch; }
    
    .explainer-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 32px;
      margin-top: 40px;
      border-top: 1px solid var(--rule);
      padding-top: 40px;
      margin-bottom: 40px;
    }
    .explainer-grid h4 { font-family: var(--mono); font-size: 13px; text-transform: uppercase; letter-spacing: .1em; margin-bottom: 8px; color: var(--bronze); }
    .explainer-grid p { font-size: 0.95rem; color: var(--ink-2); margin: 0; font-family: system-ui, -apple-system, sans-serif; }

    /* Visualizer App Layout */
    .layout {
      display: flex;
      height: 800px;
      max-width: 1200px;
      margin: 0 auto 64px auto;
      border: 1px solid var(--rule);
      font-family: system-ui, -apple-system, sans-serif;
    }
    .sidebar {
      width: 350px;
      border-right: 1px solid var(--rule);
      overflow-y: auto;
      background: var(--surface);
    }
    .main-view {
      flex: 1;
      position: relative;
    }
    #mynetwork {
      position: absolute;
      top: 0; left: 0; right: 0; bottom: 0;
      background: var(--ground);
    }
    .play-btn {
      position: absolute;
      top: 16px;
      right: 24px;
      z-index: 10;
      background: var(--bronze);
      color: #fff;
      border: none;
      padding: 8px 16px;
      font-size: 14px;
      font-weight: bold;
      border-radius: 4px;
      cursor: pointer;
      box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .play-btn:hover { background: var(--bronze-soft, #B8873F); }
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
    .sidebar-header { padding: 16px; border-bottom: 1px solid var(--rule); }
    .sidebar-header h2 { font-family: system-ui, -apple-system, sans-serif; margin: 0; font-size: 1.5em; font-weight: 500; color: var(--ink); }
    .sidebar-header p { font-family: system-ui, -apple-system, sans-serif; margin: 8px 0 0; font-size: 0.9em; color: var(--ink-3); }
  </style>
</head>
<body>
<!--NAV:invention.html-->

<div class="wrap">
  <header>
    <p class="eyebrow">Beam Search Engine · Composition Discovery</p>
    <h1>The <em>First Rung</em> Visualizer</h1>
    <p class="standfirst">Instead of using legacy depth-first search that brute-forces millions of false combinations, this tool uses a heuristic <strong>beam search</strong> to discover highly musical, previously un-rung compositions.</p>
    
    <div class="explainer-grid">
      <div>
        <h4>How it Searches</h4>
        <p>At every step, the engine evaluates all valid next calls and keeps only the branches with the highest musicality scores. Unmusical branches are aggressively pruned, letting the search reach deep into previously computationally prohibitive search spaces.</p>
      </div>
      <div>
        <h4>Reading the Graph</h4>
        <p>The numbers in the boxes represent <strong>course heads</strong>. The letters on the arrows denote the <strong>calls</strong> used to transition between them (<code>p</code> = plain, <code>b</code> = bob, <code>s</code> = single). The graph originates and terminates at Rounds (12345678).</p>
      </div>
      <div>
        <h4>Scoring & Novelty</h4>
        <p>The <strong>Score</strong> reflects musicality (e.g., counting 56s and 65s off the front and back). <strong>Likely Novel</strong> indicates that the exact sequence of calls was not found anywhere in the historical performance database.</p>
      </div>
      <div>
        <h4>▶ Compose Animation</h4>
        <p>Clicking "Compose" redraws the graph node-by-node in real time. It visually demonstrates exactly how the engine's beam search branches outwards from Rounds, evaluating the path until it finds a true block back to rounds.</p>
      </div>
    </div>
  </header>
</div>

<div class="layout">
  <div class="sidebar">
    <div class="sidebar-header">
      <h2>Top Compositions</h2>
      <p>Results ranked by musicality score. Select one to visualize its directed path.</p>
    </div>
    <div id="comp-list"></div>
  </div>
  <div class="main-view">
    <button class="play-btn" onclick="playAnimation()">▶ Compose</button>
    <div id="mynetwork"></div>
  </div>
</div>

<!--FOOTER:invention.html-->

<script>
  // Global state
  const compositions = __DATA_JSON__;
  let network = null;
  let activeIdx = 0;
  let animationTimer = null;
  let visNodes = null;
  let visEdges = null;

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
    if (animationTimer) clearInterval(animationTimer);
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
    if (animationTimer) clearInterval(animationTimer);
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
    visNodes = new vis.DataSet(nodes);
    visEdges = new vis.DataSet(edges);
    const data = { nodes: visNodes, edges: visEdges };
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

  function playAnimation() {
    if (animationTimer) clearInterval(animationTimer);
    
    const comp = compositions[activeIdx];
    
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    const bgColor = isDark ? "#1a1a19" : "#F7F6F2";
    const fgColor = isDark ? "#F0EDE6" : "#1C1E1C";
    const hlColor = isDark ? "#C9974A" : "#8A5F22";
    const rdColor = isDark ? "#63A579" : "#2F6D53";
    
    // Completely destroy and recreate network so physics resets
    const container = document.getElementById('mynetwork');
    visNodes = new vis.DataSet([]);
    visEdges = new vis.DataSet([]);
    const data = { nodes: visNodes, edges: visEdges };
    const options = {
      physics: {
        solver: 'forceAtlas2Based',
        forceAtlas2Based: { gravitationalConstant: -100, springLength: 80 }
      }
    };
    if (network) network.destroy();
    network = new vis.Network(container, data, options);
    
    const nodeIds = new Set();
    
    // Add just the first node (rounds)
    visNodes.add({
      id: comp.path[0],
      label: comp.path[0],
      shape: 'box',
      color: {
        background: rdColor,
        border: hlColor,
        highlight: hlColor
      },
      font: { color: "#FFF", face: "monospace" }
    });
    nodeIds.add(comp.path[0]);
    
    let step = 0;
    
    animationTimer = setInterval(() => {
      if (step >= comp.calls.length) {
        clearInterval(animationTimer);
        network.fit({ animation: true });
        return;
      }
      
      const nextNode = comp.path[step+1];
      if (!nodeIds.has(nextNode)) {
        visNodes.add({
          id: nextNode,
          label: nextNode,
          shape: 'box',
          color: {
            background: bgColor,
            border: hlColor,
            highlight: hlColor
          },
          font: { color: fgColor, face: "monospace" }
        });
        nodeIds.add(nextNode);
      }
      
      visEdges.add({
        from: comp.path[step],
        to: nextNode,
        label: comp.calls[step].toUpperCase(),
        arrows: 'to',
        color: { color: fgColor },
        font: { color: fgColor, strokeWidth: 0, size: 12, face: "monospace" }
      });
      
      network.fit({ animation: true });
      step++;
    }, 400); // add one step every 400ms
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
        
    with open(JSON_PATH, encoding="utf-8") as f:
        data_json = f.read()
        
    html = HTML_TEMPLATE.replace("__DATA_JSON__", data_json)
    
    print("Applying site chrome...")
    html = apply_chrome(html, dark=False) # Use standard chrome, no dark override
    
    print(f"Writing to {OUT_PATH}...")
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
        
    print("Done!")
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
