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
      height: 900px;
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
      display: flex;
      flex-direction: column;
      position: relative;
      min-width: 0;
    }
    
    #blank-state {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      text-align: center;
      padding: 32px;
      color: var(--ink-2);
    }
    #blank-state h3 { color: var(--bronze); font-weight: 500; font-size: 1.5rem; margin-bottom: 8px; }
    
    #viz-container {
      flex: 1;
      display: none;
      flex-direction: column;
      min-width: 0;
    }
    
    #mynetwork-wrapper {
      flex: 1;
      position: relative;
      border-bottom: 1px solid var(--rule);
    }
    #mynetwork {
      position: absolute;
      top: 0; left: 0; right: 0; bottom: 0;
      background: var(--ground);
    }
    
    .bottom-panels {
      height: 380px;
      display: flex;
      background: var(--surface);
      min-width: 0;
    }
    .text-panel {
      width: 250px;
      border-right: 1px solid var(--rule);
      display: flex;
      flex-direction: column;
      min-width: 0;
    }
    .svg-panel {
      flex: 1;
      display: flex;
      flex-direction: column;
      min-width: 0;
    }
    .panel-header {
      padding: 8px 16px;
      border-bottom: 1px solid var(--rule);
      display: flex;
      justify-content: space-between;
      align-items: center;
      background: var(--surface-2);
      flex: none;
    }
    .panel-header h4 { margin: 0; font-family: var(--mono); font-size: 11px; text-transform: uppercase; letter-spacing: .1em; color: var(--bronze); }
    .copy-btn {
      background: transparent; border: 1px solid var(--rule); color: var(--ink); border-radius: 4px; cursor: pointer; font-size: 11px; padding: 2px 6px;
    }
    .copy-btn:hover { background: var(--rule); }
    
    #text-output {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
      font-family: var(--mono);
      font-size: 13px;
      line-height: 1.6;
    }
    #text-output table { width: 100%; border-collapse: collapse; }
    #text-output th, #text-output td { padding: 4px; text-align: left; border-bottom: 1px dashed var(--rule); }
    #text-output th { color: var(--bronze); font-size: 11px; text-transform: uppercase; letter-spacing: .05em; font-weight: normal; }
    
    #svg-container {
      flex: 1;
      overflow: auto;
      padding: 16px;
    }
    
    .control-select {
      background: var(--surface);
      color: var(--ink);
      border: 1px solid var(--rule);
      border-radius: 4px;
      padding: 8px;
      font-size: 14px;
      font-family: inherit;
      cursor: pointer;
    }
    .control-select:hover { border-color: var(--bronze); }
    
    #controls {
      position: absolute;
      top: 16px;
      right: 24px;
      z-index: 10;
      display: flex;
      gap: 8px;
    }
    
    .play-btn {
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
    <div id="controls">
      <select id="speed-select" class="control-select">
        <option value="fast">Fast-Forward</option>
        <option value="realtime">Real-Time (Audio)</option>
      </select>
      <button class="play-btn" onclick="playAnimation()">▶ Compose</button>
    </div>
    
    <div id="blank-state">
      <h3>Visualizer Ready</h3>
      <p>Select a composition from the sidebar and click <strong>▶ Compose</strong> to begin the visualization.</p>
    </div>
    
    <div id="viz-container">
      <div id="mynetwork-wrapper">
        <div id="mynetwork"></div>
      </div>
      
      <div class="bottom-panels">
        <div class="text-panel">
          <div class="panel-header">
            <h4>Output</h4>
            <button class="copy-btn" onclick="copyText()">📋 Copy</button>
          </div>
          <div id="text-output"></div>
        </div>
        <div class="svg-panel">
          <div class="panel-header"><h4>Blue Line (Treble & Tenor)</h4></div>
          <div id="svg-container"></div>
        </div>
      </div>
    </div>
  </div>
</div>

<!--FOOTER:invention.html-->
<script>
  // Global state
  const compositions = __DATA_JSON__;
  let activeIdx = 0;
  
  let animationState = {
    timer: null,
    step: 0,
    currentRowIdx: 0,
    isPlaying: false
  };

  let network = null;
  let visNodes = null;
  let visEdges = null;

  // Web Audio Context & Synthesizer
  let audioCtx = null;
  
  function initAudio() {
    if (!audioCtx) {
      audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (audioCtx.state === 'suspended') {
      audioCtx.resume();
    }
  }

  // Frequencies for a C Major scale
  const bellFrequencies = {
    '8': 261.63, // C4
    '7': 293.66, // D4
    '6': 329.63, // E4
    '5': 349.23, // F4
    '4': 392.00, // G4
    '3': 440.00, // A4
    '2': 493.88, // B4
    '1': 523.25  // C5
  };

  function playBell(bellChar, time) {
    if (!audioCtx) return;
    const baseFreq = bellFrequencies[bellChar];
    if (!baseFreq) return;

    // Additive synthesis partials for a bell
    const partials = [
      { ratio: 0.5, gain: 0.6, decay: 4.0 },  // Hum
      { ratio: 1.0, gain: 1.0, decay: 2.0 },  // Prime
      { ratio: 1.2, gain: 0.7, decay: 1.5 },  // Tierce (minor 3rd)
      { ratio: 1.5, gain: 0.5, decay: 1.0 },  // Quint
      { ratio: 2.0, gain: 0.8, decay: 0.8 },  // Nominal
      { ratio: 2.6, gain: 0.4, decay: 0.5 }   // Extra metallic brightness
    ];

    const masterGain = audioCtx.createGain();
    masterGain.connect(audioCtx.destination);
    masterGain.gain.value = 0.4; // Global volume

    partials.forEach(p => {
      const osc = audioCtx.createOscillator();
      const gainNode = audioCtx.createGain();
      
      osc.type = 'sine';
      osc.frequency.value = baseFreq * p.ratio;
      
      osc.connect(gainNode);
      gainNode.connect(masterGain);
      
      // Fast attack, exponential decay
      gainNode.gain.setValueAtTime(0, time);
      gainNode.gain.linearRampToValueAtTime(p.gain, time + 0.02);
      gainNode.gain.exponentialRampToValueAtTime(0.001, time + p.decay);
      
      osc.start(time);
      osc.stop(time + p.decay);
    });
  }

  // Theme toggler
  const tb = document.getElementById('themeToggle');
  const setTheme = t => { 
    document.documentElement.setAttribute('data-theme', t); 
    localStorage.setItem('cr-theme', t); 
  };
  if (tb) tb.onclick = () =>
    setTheme(document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');
  else {
    let t = null; try { t = localStorage.getItem('cr-theme'); } catch (e) {}
    if (t) setTheme(t);
  }

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
    animationState.isPlaying = false;
    if (animationState.timer) clearTimeout(animationState.timer);
    
    activeIdx = idx;
    document.querySelectorAll('.comp-card').forEach(el => el.classList.remove('active'));
    document.getElementById('comp-' + idx).classList.add('active');
    
    document.getElementById('blank-state').style.display = 'flex';
    document.getElementById('viz-container').style.display = 'none';
    if (network) {
      network.destroy();
      network = null;
    }
  }
  
  function copyText() {
    const comp = compositions[activeIdx];
    if (!comp) return;
    let txt = `Score: ${comp.score.toFixed(1)}
Call\tCourse Head
-\t${comp.path[0]}
`;
    for(let i=0; i<comp.calls.length; i++) {
      txt += `${comp.calls[i]}\t${comp.path[i+1]}\n`;
    }
    navigator.clipboard.writeText(txt).then(() => {
      const btn = document.querySelector('.copy-btn');
      btn.textContent = "✅ Copied";
      setTimeout(() => btn.textContent = "📋 Copy", 2000);
    });
  }
  
  function generateSVG(rowsSubset) {
    if (!rowsSubset || rowsSubset.length === 0) return "";
    const stage = 8;
    const dx = 9.2, dy = 20.0, pad = 12.0;
    const w = pad * 2 + (rowsSubset.length - 1) * dx;
    const h = pad * 2 + (stage - 1) * dy;
    
    let svg = `<svg viewBox="0 0 ${w} ${h}" style="width: ${w}px; height: ${h}px;" role="img">`;
    
    for (let i = 0; i < rowsSubset.length; i += 32) {
      let x = pad + i * dx;
      svg += `<line x1="${x}" y1="${pad-6}" x2="${x}" y2="${h-pad+6}" stroke="var(--rule, #ccc)" stroke-width="1" opacity=".7"/>`;
    }
    
    const bells = rowsSubset[0].split('');
    const highlight = { 
      '1': { color: 'var(--bar, #2F6D53)', width: 2.4 }, 
      '8': { color: 'var(--bronze, #8A5F22)', width: 2.4 } 
    };
    
    bells.forEach(b => {
      if (!highlight[b]) {
        let pts = rowsSubset.map((row, i) => `${pad + i*dx},${pad + row.indexOf(b)*dy}`).join(' ');
        svg += `<polyline points="${pts}" fill="none" stroke="var(--ink-3, #aaa)" stroke-width="1" opacity=".38" stroke-linejoin="round"/>`;
      }
    });
    
    Object.keys(highlight).forEach(b => {
      if (!bells.includes(b)) return;
      let pts = rowsSubset.map((row, i) => `${pad + i*dx},${pad + row.indexOf(b)*dy}`).join(' ');
      let style = highlight[b];
      svg += `<polyline points="${pts}" fill="none" stroke="${style.color}" stroke-width="${style.width}" stroke-linecap="round" stroke-linejoin="round"/>`;
    });
    
    svg += `</svg>`;
    return svg;
  }

  function setupVisuals() {
    const comp = compositions[activeIdx];
    
    document.getElementById('blank-state').style.display = 'none';
    document.getElementById('viz-container').style.display = 'flex';
    
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    const rdColor = isDark ? "#63A579" : "#2F6D53";
    const hlColor = isDark ? "#C9974A" : "#8A5F22";
    
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
    
    animationState.nodeIds = new Set();
    visNodes.add({
      id: comp.path[0], label: comp.path[0], shape: 'box',
      color: { background: rdColor, border: hlColor, highlight: hlColor },
      font: { color: "#FFF", face: "monospace" }
    });
    animationState.nodeIds.add(comp.path[0]);
    
    const textOut = document.getElementById('text-output');
    textOut.innerHTML = `<table><tr><th>Call</th><th>Course Head</th></tr><tr><td>-</td><td>${comp.path[0]}</td></tr></table>`;
    
    const svgCont = document.getElementById('svg-container');
    svgCont.innerHTML = generateSVG(comp.rows.slice(0, 1));
  }

  function advanceGraph(step) {
    const comp = compositions[activeIdx];
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    const bgColor = isDark ? "#1a1a19" : "#F7F6F2";
    const fgColor = isDark ? "#F0EDE6" : "#1C1E1C";
    const hlColor = isDark ? "#C9974A" : "#8A5F22";
    
    const call = comp.calls[step].toUpperCase();
    const nextNode = comp.path[step+1];
    
    if (!animationState.nodeIds.has(nextNode)) {
      visNodes.add({
        id: nextNode, label: nextNode, shape: 'box',
        color: { background: bgColor, border: hlColor, highlight: hlColor },
        font: { color: fgColor, face: "monospace" }
      });
      animationState.nodeIds.add(nextNode);
    }
    visEdges.add({
      from: comp.path[step], to: nextNode, label: call, arrows: 'to',
      color: { color: fgColor }, font: { color: fgColor, strokeWidth: 0, size: 12, face: "monospace" }
    });
    network.fit({ animation: true });
    
    const textOut = document.getElementById('text-output');
    const table = textOut.querySelector('table');
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${call}</td><td>${nextNode}</td>`;
    table.appendChild(tr);
    textOut.scrollTop = textOut.scrollHeight;
  }

  function playRealTimeLoop() {
    if (!animationState.isPlaying) return;
    const comp = compositions[activeIdx];
    
    if (animationState.currentRowIdx >= comp.rows.length) {
      animationState.isPlaying = false;
      network.fit({ animation: true });
      return;
    }
    
    const row = comp.rows[animationState.currentRowIdx];
    const isHandstroke = (animationState.currentRowIdx % 2 === 0);
    const strikeInterval = 0.25; // 250ms per strike
    const rowDuration = 8 * strikeInterval;
    const gap = isHandstroke ? 0 : strikeInterval; 
    
    // Schedule Audio
    const now = audioCtx.currentTime;
    const bells = row.split('');
    bells.forEach((b, i) => {
      playBell(b, now + (i * strikeInterval));
    });
    
    // Update SVG row-by-row
    const svgCont = document.getElementById('svg-container');
    svgCont.innerHTML = generateSVG(comp.rows.slice(0, animationState.currentRowIdx + 1));
    svgCont.scrollLeft = svgCont.scrollWidth;
    
    // Check if we hit a course head boundary
    if (animationState.step < comp.calls.length && row === comp.path[animationState.step + 1]) {
      advanceGraph(animationState.step);
      animationState.step++;
    }
    
    animationState.currentRowIdx++;
    
    const timeUntilNextRow = (rowDuration + gap) * 1000;
    animationState.timer = setTimeout(playRealTimeLoop, timeUntilNextRow);
  }

  function playFastForwardLoop() {
    if (!animationState.isPlaying) return;
    const comp = compositions[activeIdx];
    
    if (animationState.step >= comp.calls.length) {
      animationState.isPlaying = false;
      network.fit({ animation: true });
      return;
    }
    
    const nextNode = comp.path[animationState.step+1];
    advanceGraph(animationState.step);
    
    // Update SVG in chunks
    let currentRows = animationState.currentRowIdx;
    if (comp.rows && comp.rows.length > 0) {
      let nextIndex = comp.rows.indexOf(nextNode, currentRows + 1);
      if (nextIndex !== -1) currentRows = nextIndex;
      else currentRows += 32;
      
      const svgCont = document.getElementById('svg-container');
      svgCont.innerHTML = generateSVG(comp.rows.slice(0, currentRows + 1));
      svgCont.scrollLeft = svgCont.scrollWidth;
      animationState.currentRowIdx = currentRows;
    }
    
    animationState.step++;
    animationState.timer = setTimeout(playFastForwardLoop, 400);
  }

  function playAnimation() {
    if (animationState.timer) clearTimeout(animationState.timer);
    animationState.isPlaying = true;
    
    setupVisuals();
    
    const speedMode = document.getElementById('speed-select').value;
    if (speedMode === 'realtime') {
      initAudio();
      animationState.currentRowIdx = 0;
      animationState.step = 0;
      playRealTimeLoop();
    } else {
      animationState.currentRowIdx = 0;
      animationState.step = 0;
      playFastForwardLoop();
    }
  }

  window.onload = () => {
    if (compositions && compositions.length > 0) {
      renderList();
      selectComp(0);
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
