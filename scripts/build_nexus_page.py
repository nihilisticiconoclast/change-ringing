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
    # We limit to 1000 to keep the WebGL graph at 60fps
    perfs_query = """
        SELECT perf_id, bb_id, place, method, perf_date
        FROM performances 
        WHERE perf_date LIKE '2024%' 
        AND method IS NOT NULL
        AND method != ''
        LIMIT 1000
    """
    perfs = pd.read_sql(perfs_query, conn)
    perf_ids = perfs['perf_id'].tolist()
    
    if not perf_ids:
        print("No 2024 performances found. Taking 1000 most recent.")
        perfs_query = """
            SELECT perf_id, bb_id, place, method, perf_date
            FROM performances 
            WHERE method IS NOT NULL
            AND method != ''
            ORDER BY perf_date DESC
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
            "date": row['perf_date']
        }
        
        # Add Tower Node
        if tower_id not in nodes:
            nodes[tower_id] = {"id": tower_id, "group": "tower", "name": str(row['place']), "val": 3}
        nodes[tower_id]["val"] += 0.5
        
        # Add Method Node
        if method_id not in nodes:
            nodes[method_id] = {"id": method_id, "group": "method", "name": str(row['method']), "val": 3}
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

    # Convert to list
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
            background: rgba(10, 15, 30, 0.7);
            padding: 20px;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            max-width: 350px;
        }
        
        h1 { margin: 0 0 10px 0; font-size: 1.5rem; font-weight: 600; background: linear-gradient(90deg, #a78bfa, #38bdf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        p { margin: 0 0 15px 0; font-size: 0.9rem; color: #cbd5e1; line-height: 1.5; }
        
        .legend { display: flex; flex-direction: column; gap: 8px; font-size: 0.85rem; }
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
        }
    </style>
    <!-- Use 3d-force-graph via CDN -->
    <script src="https://unpkg.com/3d-force-graph"></script>
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
        <p>A multi-dimensional view of change ringing. Stars represent individual performances, forming constellations with Towers, Methods, and Ringers.</p>
        <div class="legend">
            <div class="legend-item"><div class="dot tower"></div> Towers (Sized by activity)</div>
            <div class="legend-item"><div class="dot method"></div> Methods</div>
            <div class="legend-item"><div class="dot ringer"></div> Ringers</div>
            <div class="legend-item"><div class="dot perf"></div> Performances</div>
        </div>
    </div>
    
    <div class="timeline-container">
        <input type="range" id="timeline-slider" min="0" max="100" value="100" step="1">
        <div id="date-display">All Time</div>
    </div>
    
    <div class="controls-hint">
        Left-click & drag to rotate<br>
        Scroll to zoom<br>
        Hover for details
    </div>

    <script>
        const graphData = {{GRAPH_DATA}};
        
        // Setup Date processing for timeline
        // Find min and max dates
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
        
        // Time window in milliseconds (e.g. 14 days)
        const timeWindow = 14 * 24 * 60 * 60 * 1000; 
        
        let currentTime = maxTime;
        
        // Initialize graph
        const elem = document.getElementById('3d-graph');
        const Graph = ForceGraph3D()(elem)
            .graphData(graphData)
            .nodeLabel('name')
            .nodeColor(node => {
                switch(node.group) {
                    case 'tower': return '#fbbf24';
                    case 'method': return '#f472b6';
                    case 'ringer': return '#38bdf8';
                    case 'performance': return '#ffffff';
                    default: return '#cccccc';
                }
            })
            .nodeRelSize(4)
            .nodeVal(node => node.group === 'performance' ? 1 : Math.sqrt(node.val) * 2)
            .nodeResolution(16)
            .linkWidth(link => 0.5)
            .linkColor(link => {
                if (link.type === 'perf_tower') return 'rgba(251, 191, 36, 0.3)';
                if (link.type === 'perf_method') return 'rgba(244, 114, 182, 0.3)';
                return 'rgba(56, 189, 248, 0.2)';
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
            });
            
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
