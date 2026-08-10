import sqlite3
import pandas as pd
import json
import os
import math

DB_PATH = "data/change-ringing.db"
OUTPUT_PATH = "docs/nexus.html"

def fetch_nexus_data():
    conn = sqlite3.connect(DB_PATH)
    
    # Get a sample of performances from 2024
    perfs_query = """
        SELECT p.perf_id, p.bb_id, p.place, p.method, p.perf_date, t.Lat, t.Long, m.stage
        FROM performances p
        LEFT JOIN towers t ON p.dove_tower_id = t.TowerID
        LEFT JOIN methods m ON p.method = m.title
        WHERE p.perf_date LIKE '2024%' 
        AND p.method IS NOT NULL
        AND p.method != ''
        LIMIT 1000
    """
    perfs = pd.read_sql(perfs_query, conn)
    perf_ids = perfs['perf_id'].tolist()
    
    if not perf_ids:
        print("No 2024 performances found. Taking 1000 most recent.")
        perfs_query = """
            SELECT p.perf_id, p.bb_id, p.place, p.method, p.perf_date, t.Lat, t.Long, m.stage
            FROM performances p
            LEFT JOIN towers t ON p.dove_tower_id = t.TowerID
            LEFT JOIN methods m ON p.method = m.title
            WHERE p.method IS NOT NULL
            AND p.method != ''
            ORDER BY p.perf_date DESC
            LIMIT 1000
        """
        perfs = pd.read_sql(perfs_query, conn)
        perf_ids = perfs['perf_id'].tolist()

    placeholders = ','.join('?' for _ in perf_ids)
    
    # Get ringers for these performances
    ringers_query = f"""
        SELECT perf_id, name, bell
        FROM performance_ringers
        WHERE perf_id IN ({placeholders})
    """
    ringers = pd.read_sql(ringers_query, conn, params=perf_ids)
    conn.close()
    
    # Build Graph
    nodes = {}
    links = []
    
    # Process Towers and Methods and Performances
    for _, row in perfs.iterrows():
        perf_node_id = f"P_{row['perf_id']}"
        tower_id = f"T_{row['place']}"
        method_id = f"M_{row['method']}"
        
        # Add Performance Node
        nodes[perf_node_id] = {
            "id": perf_node_id,
            "group": "performance",
            "name": f"Performance on {row['perf_date']} at {row['place']}",
            "val": 1,
            "date": row['perf_date'],
            "tower": str(row['place']),
            "method": str(row['method']),
            "ringers": []
        }
        
        # Add Tower Node
        if tower_id not in nodes:
            nodes[tower_id] = {
                "id": tower_id, 
                "group": "tower", 
                "name": str(row['place']), 
                "val": 3,
                "lat": row['Lat'] if pd.notnull(row['Lat']) else None,
                "long": row['Long'] if pd.notnull(row['Long']) else None
            }
        nodes[tower_id]["val"] += 0.5
        
        # Add Method Node
        if method_id not in nodes:
            nodes[method_id] = {
                "id": method_id, 
                "group": "method", 
                "name": str(row['method']), 
                "val": 3,
                "stage": row['stage'] if pd.notnull(row['stage']) else None
            }
        nodes[method_id]["val"] += 0.5
        
        # Create links from Performance to Tower and Method
        links.append({"source": perf_node_id, "target": tower_id, "type": "perf_tower", "date": row['perf_date']})
        links.append({"source": perf_node_id, "target": method_id, "type": "perf_method", "date": row['perf_date']})

    # Process Ringers
    for _, row in ringers.iterrows():
        perf_node_id = f"P_{row['perf_id']}"
        ringer_id = f"R_{row['name']}"
        
        # Add Ringer Node
        if ringer_id not in nodes:
            nodes[ringer_id] = {"id": ringer_id, "group": "ringer", "name": str(row['name']), "val": 2}
        nodes[ringer_id]["val"] += 0.2
        
        # Create link from Performance to Ringer
        # Get date from performance node
        if perf_node_id in nodes:
            p_date = nodes[perf_node_id]["date"]
            links.append({"source": perf_node_id, "target": ringer_id, "type": "perf_ringer", "date": p_date, "bell": row['bell']})
            nodes[perf_node_id]["ringers"].append({"name": str(row['name']), "bell": row['bell']})

    # Sort ringers by bell for side panel
    for node in nodes.values():
        if node["group"] == "performance":
            # Attempt to sort naturally by bell if possible (sometimes bell is a letter like 'T' or '0')
            def parse_bell(b):
                try: return int(b)
                except: return 999
            node["ringers"].sort(key=lambda x: parse_bell(x["bell"]))

    node_list = list(nodes.values())
    return {"nodes": node_list, "links": links}

def generate_html(graph_data):
    html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>The Temporal Nexus</title>
    <style>
        body { margin: 0; overflow: hidden; background-color: #050510; font-family: 'Inter', sans-serif; color: #fff; }
        #3d-graph { width: 100vw; height: 100vh; }
        
        .overlay {
            position: absolute;
            top: 60px;
            left: 20px;
            pointer-events: none;
            background: rgba(10, 15, 30, 0.75);
            padding: 20px;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.15);
            backdrop-filter: blur(10px);
            max-width: 380px;
            z-index: 5;
        }
        
        #side-panel {
            position: absolute;
            top: 60px;
            right: -400px;
            width: 350px;
            bottom: 120px;
            background: rgba(10, 15, 30, 0.85);
            border-left: 1px solid rgba(255, 255, 255, 0.15);
            border-top: 1px solid rgba(255, 255, 255, 0.15);
            border-bottom: 1px solid rgba(255, 255, 255, 0.15);
            border-top-left-radius: 12px;
            border-bottom-left-radius: 12px;
            padding: 24px;
            box-sizing: border-box;
            transition: right 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            overflow-y: auto;
            backdrop-filter: blur(10px);
            z-index: 5;
            box-shadow: -5px 0 20px rgba(0,0,0,0.5);
        }
        
        #side-panel.visible {
            right: 0;
        }
        
        #side-panel h2 { margin: 0 0 5px 0; font-size: 1.3rem; color: #fff; }
        #side-panel .node-type { font-family: ui-monospace, monospace; font-size: 0.75rem; color: #94a3b8; letter-spacing: 0.1em; margin-bottom: 20px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 10px; }
        #side-panel p { font-size: 0.9rem; line-height: 1.5; color: #cbd5e1; margin-bottom: 10px; }
        #side-panel ul { padding-left: 20px; margin-top: 5px; font-size: 0.9rem; color: #e2e8f0; }
        #side-panel li { margin-bottom: 4px; }
        #side-panel strong { color: #f8fafc; }
        
        h1 { margin: 0 0 10px 0; font-size: 1.5rem; font-weight: 600; background: linear-gradient(90deg, #a78bfa, #38bdf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        p { margin: 0 0 15px 0; font-size: 0.9rem; color: #cbd5e1; line-height: 1.5; }
        
        .legend { display: flex; flex-direction: column; gap: 8px; font-size: 0.85rem; margin-top: 20px; }
        .legend-item { display: flex; align-items: center; gap: 10px; }
        .dot { width: 12px; height: 12px; border-radius: 50%; }
        .dot.tower { background-color: #fbbf24; }
        .dot.method { background-color: #f472b6; }
        .dot.ringer { background-color: #38bdf8; }
        .dot.perf { background-color: #ffffff; box-shadow: 0 0 8px #ffffff; width: 6px; height: 6px; margin: 0 3px; }
        
        .timeline-container {
            position: absolute;
            bottom: 40px;
            left: 50%;
            transform: translateX(-50%);
            width: 80%;
            max-width: 800px;
            background: rgba(10, 15, 30, 0.7);
            padding: 15px 25px;
            border-radius: 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            display: flex;
            flex-direction: column;
            align-items: center;
            z-index: 5;
        }
        
        .nav-bar {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            background: rgba(10, 15, 30, 0.8);
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            padding: 12px 24px;
            display: flex;
            justify-content: flex-start;
            z-index: 10;
            backdrop-filter: blur(10px);
        }
        .nav-links {
            display: flex;
            gap: 20px;
            font-family: ui-monospace, "SF Mono", SFMono-Regular, Menlo, Consolas, monospace;
            font-size: 12px;
            letter-spacing: .08em;
            text-transform: uppercase;
        }
        .nav-links a {
            color: #cbd5e1;
            text-decoration: none;
            padding: 4px 0;
            border-bottom: 2px solid transparent;
        }
        .nav-links a.active {
            color: #38bdf8;
            border-bottom-color: #38bdf8;
            font-weight: 600;
        }
        .nav-links a:hover {
            color: #fff;
        }
        
        #timeline-slider {
            width: 100%;
            margin-bottom: 10px;
            accent-color: #38bdf8;
        }
        
        #date-display {
            font-size: 1.2rem;
            font-weight: 600;
            color: #38bdf8;
            letter-spacing: 1px;
        }
        
        .controls-hint {
            position: absolute;
            bottom: 20px;
            right: 20px;
            font-size: 0.8rem;
            color: #64748b;
            text-align: right;
            z-index: 5;
            pointer-events: none;
        }
    </style>
    <!-- Use 3d-force-graph via CDN -->
    <script src="https://unpkg.com/3d-force-graph"></script>
    <script src="https://unpkg.com/three"></script>
</head>
<body>
    <div class="nav-bar">
      <div class="nav-links">
        <a href="index.html">Founder Atlas</a>
        <a href="lineage.html">Method Lineage</a>
        <a href="ringers.html">Ringer Constellation</a>
        <a href="nexus.html" class="active">The Temporal Nexus</a>
      </div>
    </div>
    
    <div id="3d-graph"></div>
    
    <div class="overlay">
        <h1>The Temporal Nexus</h1>
        <p>A multi-dimensional view of change ringing. <strong>Nodes cluster mathematically based on shared history.</strong></p>
        <p>The dense center represents the most interconnected hub of 2024. The outer edges represent isolated or unique events.</p>
        <p><em>Click any node to fly to it and view its narrative.</em></p>
        <p style="margin-top: 15px; font-size: 0.85rem; color: #38bdf8;"><em>✨ Click any legend item below to isolate its nodes and reveal special spatial layouts!</em></p>
        <div class="legend">
            <div class="legend-item" style="cursor:pointer;" onclick="highlightGroup('tower')" title="Click to highlight and view map mode"><div class="dot tower"></div> Towers (size reflects activity)</div>
            <div class="legend-item" style="cursor:pointer;" onclick="highlightGroup('method')" title="Click to highlight"><div class="dot method"></div> Methods (size reflects frequency)</div>
            <div class="legend-item" style="cursor:pointer;" onclick="highlightGroup('ringer')" title="Click to highlight"><div class="dot ringer"></div> Ringers (size reflects activity)</div>
            <div class="legend-item" style="cursor:pointer;" onclick="highlightGroup('performance')" title="Click to highlight"><div class="dot perf"></div> Performances</div>
        </div>
    </div>
    
    <div id="side-panel">
        <!-- Content injected via JS -->
    </div>
    
    <div class="timeline-container">
        <input type="range" id="timeline-slider" min="0" max="100" value="100" step="1">
        <div id="date-display">All Time</div>
    </div>
    
    <div class="controls-hint">
        Left-click to focus<br>
        Drag to rotate<br>
        Scroll to zoom
    </div>

    <script>
        const graphData = {{GRAPH_DATA}};
        
        // Setup Date processing for timeline
        const dates = graphData.nodes
            .filter(n => n.group === 'performance' && n.date)
            .map(n => new Date(n.date).getTime());
            
        let minTime = Math.min(...dates);
        let maxTime = Math.max(...dates);
        
        if (!isFinite(minTime)) {
            minTime = Date.now() - 31536000000;
            maxTime = Date.now();
        }
        
        const slider = document.getElementById('timeline-slider');
        const dateDisplay = document.getElementById('date-display');
        const sidePanel = document.getElementById('side-panel');
        
        const timeWindow = 14 * 24 * 60 * 60 * 1000; 
        let currentTime = maxTime;
        
        let highlightedGroup = null;
        let isMapMode = false;
        
        function highlightGroup(group) {
            if (highlightedGroup === group) {
                highlightedGroup = null;
                if (isMapMode) {
                    isMapMode = false;
                    graphData.nodes.forEach(n => {
                        n.fx = undefined;
                        n.fy = undefined;
                        n.fz = undefined;
                    });
                    Graph.d3Force('charge').strength(-30);
                    Graph.d3AlphaTarget(0.3).restart();
                    setTimeout(() => { Graph.d3AlphaTarget(0); }, 3000);
                }
            } else {
                highlightedGroup = group;
                if (group === 'tower') {
                    isMapMode = true;
                    let lats = graphData.nodes.filter(n => n.group === 'tower' && n.lat != null).map(n => n.lat);
                    let longs = graphData.nodes.filter(n => n.group === 'tower' && n.long != null).map(n => n.long);
                    
                    if (lats.length > 0) {
                        let minLat = Math.min(...lats); let maxLat = Math.max(...lats);
                        let minLong = Math.min(...longs); let maxLong = Math.max(...longs);
                        
                        // Map onto X and Y plane (Y is latitude so we don't invert it here if we just want it to lay flat, 
                        // though normally north is positive Y. We'll set long to X and lat to Y.
                        graphData.nodes.forEach(n => {
                            if (n.group === 'tower') {
                                if (n.lat != null && n.long != null) {
                                    // Scale to a nice 3D spread
                                    n.fx = ((n.long - minLong) / (maxLong - minLong) - 0.5) * 4000;
                                    n.fy = ((n.lat - minLat) / (maxLat - minLat) - 0.5) * 4000;
                                    n.fz = 0;
                                } else {
                                    n.fz = 0; // Drop missing to the plane
                                }
                            }
                        });
                        
                        Graph.d3AlphaTarget(0.3).restart();
                        
                        // Move camera to look down at the map (Z-axis)
                        Graph.cameraPosition({ x: 0, y: 0, z: 4500 }, { x: 0, y: 0, z: 0 }, 2000);
                    }
                } else if (group === 'method') {
                    isMapMode = true;
                    // Group methods by stage in concentric circles
                    let methods = graphData.nodes.filter(n => n.group === 'method');
                    let stages = [...new Set(methods.map(n => n.stage).filter(s => s != null))].sort((a,b) => a-b);
                    
                    let stageRadii = {};
                    stages.forEach((s, i) => {
                        stageRadii[s] = 400 + (i * 300); // 400, 700, 1000...
                    });
                    
                    let methodCounts = {};
                    methods.forEach(n => {
                        let s = n.stage || 'unknown';
                        if (!methodCounts[s]) methodCounts[s] = 0;
                        methodCounts[s]++;
                    });
                    
                    let methodIndices = {};
                    
                    graphData.nodes.forEach(n => {
                        if (n.group === 'method') {
                            let s = n.stage || 'unknown';
                            if (!methodIndices[s]) methodIndices[s] = 0;
                            let idx = methodIndices[s]++;
                            let count = methodCounts[s];
                            let r = stageRadii[n.stage] || 2500; // unknown stage gets outer ring
                            let angle = (idx / count) * Math.PI * 2;
                            
                            n.fx = Math.cos(angle) * r;
                            n.fy = Math.sin(angle) * r;
                            n.fz = 0;
                        }
                    });
                    
                    Graph.d3AlphaTarget(0.3).restart();
                    Graph.cameraPosition({ x: 0, y: -2000, z: 3000 }, { x: 0, y: 0, z: 0 }, 2000);
                } else {
                    if (isMapMode) {
                        isMapMode = false;
                        graphData.nodes.forEach(n => { n.fx = undefined; n.fy = undefined; n.fz = undefined; });
                        Graph.d3AlphaTarget(0.3).restart();
                    }
                }
            }
            
            Graph.nodeColor(Graph.nodeColor());
            Graph.linkColor(Graph.linkColor());
        }
        
        const elem = document.getElementById('3d-graph');
        const Graph = ForceGraph3D()(elem)
            .graphData(graphData)
            .nodeLabel('name')
            .nodeColor(node => {
                let opacity = (highlightedGroup && node.group !== highlightedGroup) ? 0.15 : 1.0;
                switch(node.group) {
                    case 'tower': return `rgba(251, 191, 36, ${opacity})`;
                    case 'method': return `rgba(244, 114, 182, ${opacity})`;
                    case 'ringer': return `rgba(56, 189, 248, ${opacity})`;
                    case 'performance': return `rgba(255, 255, 255, ${opacity})`;
                    default: return `rgba(204, 204, 204, ${opacity})`;
                }
            })
            .nodeRelSize(4)
            .nodeVal(node => {
                if (node.group === 'performance') return 0.5;
                // Since 3d-force-graph uses cbrt(val) for radius, we cube the value
                // so that the radius scales exactly linearly with activity!
                return Math.pow(node.val, 3) / 5;
            })
            .nodeResolution(16)
            .linkWidth(link => 0.5)
            .linkColor(link => {
                let baseOpacity = (highlightedGroup) ? 0.05 : 0.3;
                let ringerOpacity = (highlightedGroup) ? 0.05 : 0.2;
                if (link.type === 'perf_tower') return `rgba(251, 191, 36, ${baseOpacity})`;
                if (link.type === 'perf_method') return `rgba(244, 114, 182, ${baseOpacity})`;
                return `rgba(56, 189, 248, ${ringerOpacity})`;
            })
            .linkDirectionalParticles(link => {
                if (!link.date) return 0;
                const linkTime = new Date(link.date).getTime();
                
                if (slider.value === slider.max) {
                    return 0; // All time
                }
                
                if (Math.abs(linkTime - currentTime) < timeWindow) {
                    return link.type === 'perf_tower' ? 3 : (link.type === 'perf_method' ? 2 : 1);
                }
                return 0;
            })
            .linkDirectionalParticleSpeed(0.005)
            .linkDirectionalParticleWidth(2)
            .linkDirectionalParticleColor(link => {
                if (link.type === 'perf_tower') return '#fbbf24';
                if (link.type === 'perf_method') return '#f472b6';
                return '#38bdf8';
            })
            .linkVisibility(link => {
                if (slider.value === slider.max) return true;
                if (!link.date) return true;
                const linkTime = new Date(link.date).getTime();
                return linkTime <= currentTime;
            })
            .nodeVisibility(node => {
                if (slider.value === slider.max) return true;
                if (node.group === 'performance' && node.date) {
                    const nodeTime = new Date(node.date).getTime();
                    return nodeTime <= currentTime;
                }
                return true; 
            })
            .onNodeClick(node => {
                // Fly camera to node
                const distance = 400; // Distance to keep from the node
                const distRatio = 1 + distance/Math.hypot(node.x, node.y, node.z);
                
                Graph.cameraPosition(
                    { x: node.x * distRatio, y: node.y * distRatio, z: node.z * distRatio }, // new position
                    node, // lookAt
                    2000  // ms transition duration
                );
                
                // Populate Narrative Panel
                let html = `<h2>${node.name}</h2>`;
                html += `<p class="node-type">${node.group.toUpperCase()}</p>`;
                
                if (node.group === 'performance') {
                    html += `<p>This performance took place at <strong>${node.tower}</strong>, ringing <strong>${node.method}</strong>.</p>`;
                    html += `<p><strong>Why is it here?</strong> Its position is determined by the combined gravity of its Tower, Method, and Ringers. Highly active towers and common methods pull performances tightly toward the dense center. Isolated or unique performances drift toward the outer edges.</p>`;
                    html += `<p><strong>Ringers:</strong></p><ul>`;
                    if (node.ringers && node.ringers.length > 0) {
                        node.ringers.forEach(r => {
                            html += `<li>Bell ${r.bell}: ${r.name}</li>`;
                        });
                    } else {
                        html += `<li>No ringers recorded</li>`;
                    }
                    html += `</ul>`;
                } else if (node.group === 'ringer') {
                    html += `<p>The glowing links connecting to this node represent the specific performances that <strong>${node.name}</strong> participated in.</p>`;
                    html += `<p>This ringer is pulled mathematically closer to the methods they ring often and the towers they frequent.</p>`;
                } else if (node.group === 'tower') {
                    html += `<p>The glowing links connecting to this node represent the specific performances that occurred at <strong>${node.name}</strong>.</p>`;
                    html += `<p>This tower is pulled mathematically closer to the ringers who ring here often and the methods commonly rung.</p>`;
                } else if (node.group === 'method') {
                    html += `<p>The glowing links connecting to this node represent the specific performances where <strong>${node.name}</strong> was rung.</p>`;
                    html += `<p>This method is pulled mathematically closer to the ringers who specialize in it and the towers where it is popular.</p>`;
                }
                
                sidePanel.innerHTML = html;
                sidePanel.classList.add('visible');
            })
            .onBackgroundClick(() => {
                sidePanel.classList.remove('visible');
            });
            
        // Expand camera far plane
        Graph.camera().far = 100000;
        Graph.camera().updateProjectionMatrix();
            
        // Add highly visible Axes and Grids instead of faint Torus geometry
        const scene = Graph.scene();
        
        // Massive coordinate axes (Red=X, Green=Y, Blue=Z)
        const axesHelper = new THREE.AxesHelper(5000);
        scene.add(axesHelper);
        
        // A highly visible flat equatorial grid plane to provide depth (opacity 0.6)
        const gridHelper = new THREE.GridHelper(6000, 40, 0x38bdf8, 0x111122);
        gridHelper.material.opacity = 0.6;
        gridHelper.material.transparent = true;
        scene.add(gridHelper);
            
        // Setup slider interaction
        slider.addEventListener('input', (e) => {
            const val = parseInt(e.target.value);
            if (val === parseInt(slider.max)) {
                dateDisplay.innerText = "All Time (Cumulative)";
            } else {
                const percent = val / (slider.max - 1);
                currentTime = minTime + percent * (maxTime - minTime);
                const d = new Date(currentTime);
                dateDisplay.innerText = d.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
            }
            
            // Trigger update
            Graph.nodeVisibility(Graph.nodeVisibility()); 
            Graph.linkVisibility(Graph.linkVisibility());
            Graph.linkDirectionalParticles(Graph.linkDirectionalParticles());
        });
        
    </script>
</body>
</html>"""
    
    graph_json = json.dumps(graph_data)
    html_content = html_template.replace("{{GRAPH_DATA}}", graph_json)
    
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"Generated {OUTPUT_PATH} with {len(graph_data['nodes'])} nodes and {len(graph_data['links'])} links.")

if __name__ == "__main__":
    print("Fetching data...")
    data = fetch_nexus_data()
    print("Generating HTML...")
    generate_html(data)
