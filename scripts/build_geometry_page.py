import sqlite3
import pandas as pd
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from site_chrome import apply_chrome  # noqa: E402

DB_PATH = "data/change-ringing.db"
OUTPUT_PATH = "docs/geometry.html"

def fetch_geometry_data():
    conn = sqlite3.connect(DB_PATH)
    
    query = """
        SELECT m.title, m.stage, m.classification, m.lead_head_code, COUNT(p.perf_id) as perf_count
        FROM performances p
        JOIN methods m ON p.method = m.title
        WHERE p.method IS NOT NULL AND p.method != ''
        GROUP BY m.title
        ORDER BY perf_count DESC
        LIMIT 3000
    """
    df = pd.read_sql(query, conn)
    conn.close()
    
    nodes = []
    links = []
    
    # Track the last seen method for a specific stage+lead_head_code combo to form chains
    last_seen_by_symmetry = {}
    
    for idx, row in df.iterrows():
        method_id = f"M_{idx}" # use index to ensure uniqueness and sorted order
        stage = row['stage'] if pd.notnull(row['stage']) else 0
        classification = row['classification'] if pd.notnull(row['classification']) else "Unknown"
        lhc = row['lead_head_code'] if pd.notnull(row['lead_head_code']) else "Unknown"
        
        nodes.append({
            "id": method_id,
            "name": row['title'],
            "stage": stage,
            "classification": classification,
            "lhc": lhc,
            "perf_count": row['perf_count'],
            "rank": idx
        })
        
        # Link to the previous method with the same symmetry
        if lhc != "Unknown":
            sym_key = f"{stage}_{lhc}"
            if sym_key in last_seen_by_symmetry:
                links.append({
                    "source": last_seen_by_symmetry[sym_key],
                    "target": method_id,
                    "type": "symmetry"
                })
            last_seen_by_symmetry[sym_key] = method_id

    return {"nodes": nodes, "links": links}

def generate_html(graph_data):
    html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>The Sphere of Symmetries</title>
    <style>
        /* html as well as body. #side-panel is parked at right:-400px until it
           slides in, and with overflow only on body the documentElement still
           scrolled 400px sideways -- which also widened the containing block, so
           .nav-bar resolved to 100% of 1328px rather than of the viewport. */
        /* overflow-x hidden, overflow-y auto -- not `overflow: hidden`.
           Hidden on both axes clipped the side panel parked at right:-400px, but
           it also made the footer unreachable: the page is 100vh of canvas and
           there was no way to scroll past it. The footer carries this page's only
           provenance, so it has to be reachable. */
        html { overflow-x: hidden; overflow-y: auto; }
        body { margin: 0; overflow-x: hidden; background-color: #030308; font-family: 'Inter', sans-serif; color: #fff; }
        #3d-graph { width: 100vw; height: 100vh; }
        
        .overlay {
            position: absolute;
            top: 60px;
            left: 20px;
            pointer-events: none;
            background: rgba(5, 8, 20, 0.85);
            padding: 24px;
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(12px);
            max-width: 400px;
            z-index: 5;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }
        
        #side-panel {
            position: absolute;
            top: 60px;
            right: -400px;
            width: 350px;
            bottom: 60px;
            background: rgba(5, 8, 20, 0.9);
            border-left: 1px solid rgba(255, 255, 255, 0.1);
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            border-top-left-radius: 12px;
            border-bottom-left-radius: 12px;
            padding: 24px;
            box-sizing: border-box;
            transition: right 0.4s cubic-bezier(0.16, 1, 0.3, 1);
            overflow-y: auto;
            backdrop-filter: blur(12px);
            z-index: 5;
            box-shadow: -5px 0 30px rgba(0,0,0,0.6);
        }
        
        #side-panel.visible {
            right: 0;
        }
        
        #side-panel h2 { margin: 0 0 5px 0; font-size: 1.4rem; color: #fff; line-height: 1.3; }
        #side-panel .node-type { font-family: ui-monospace, monospace; font-size: 0.75rem; color: #eab308; letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: 20px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 10px; }
        #side-panel p { font-size: 0.9rem; line-height: 1.6; color: #cbd5e1; margin-bottom: 15px; }
        #side-panel strong { color: #f8fafc; }
        
        h1 { margin: 0 0 10px 0; font-size: 1.6rem; font-weight: 700; background: linear-gradient(135deg, #fbbf24, #f59e0b, #d97706); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        p { margin: 0 0 15px 0; font-size: 0.9rem; color: #cbd5e1; line-height: 1.6; }
        
        .legend { display: flex; flex-direction: column; gap: 8px; font-size: 0.85rem; margin-top: 20px; pointer-events: auto; }
        .legend-item { display: flex; align-items: center; gap: 10px; transition: opacity 0.2s; cursor: pointer; }
        .legend-item:hover { opacity: 0.8; }
        .dot { width: 12px; height: 12px; border-radius: 50%; }
        
        /* Classification Colors */
        .dot.surprise { background-color: #ec4899; }
        .dot.bob { background-color: #3b82f6; }
        .dot.treble-bob { background-color: #10b981; }
        .dot.delight { background-color: #8b5cf6; }
        .dot.other { background-color: #94a3b8; }
        
        .nav-bar {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            background: rgba(5, 8, 20, 0.9);
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            padding: 12px 24px;
            display: flex;
            justify-content: flex-start;
            z-index: 10;
            backdrop-filter: blur(12px);
        }
        .nav-links {
            display: flex;
            flex-wrap: wrap;
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
            transition: all 0.2s;
        }
        .nav-links a.active {
            color: #fbbf24;
            border-bottom-color: #fbbf24;
            font-weight: 600;
        }
        .nav-links a:hover {
            color: #fff;
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
        
        .equation {
            font-family: "Cambria Math", "Times New Roman", serif;
            font-size: 1.1rem;
            color: #fbbf24;
            text-align: center;
            margin: 15px 0;
            font-style: italic;
        }
    </style>
    <script src="vendor/3d-force-graph-1.80.0.min.js"></script>
    <script src="vendor/three-0.160.0.min.js"></script>
</head>
<body>
    <!--NAV:geometry.html-->
    <div id="3d-graph"></div>
    
    <div class="overlay">
        <h1>The Sphere of Symmetries</h1>
        <p>A mapping of change ringing's inherent mathematics onto universal geometric patterns.</p>
        <p>The 3,000 most popular methods form a perfect 3D <strong>phyllotaxis sphere</strong>. Their coordinates are calculated using the <strong>Golden Angle</strong>:</p>
        <div class="equation">&phi; = 137.508&deg;</div>
        <p>The most popular methods sit at the North Pole, spiraling down mathematically to the South Pole.</p>
        <p>Glowing threads connect methods that share identical permutation structures (<strong>Lead Head Codes</strong>), weaving a geometric web of mathematical symmetries.</p>
        
        <p style="margin-top: 15px; font-size: 0.85rem; color: #fbbf24;"><em>✨ Click any classification below to isolate its symmetric threads!</em></p>
        
        <div class="legend">
            <div class="legend-item" onclick="highlightClass('Surprise')"><div class="dot surprise"></div> Surprise</div>
            <div class="legend-item" onclick="highlightClass('Bob')"><div class="dot bob"></div> Bob</div>
            <div class="legend-item" onclick="highlightClass('Treble Bob')"><div class="dot treble-bob"></div> Treble Bob</div>
            <div class="legend-item" onclick="highlightClass('Delight')"><div class="dot delight"></div> Delight</div>
            <div class="legend-item" onclick="highlightClass('Other')"><div class="dot other"></div> Other</div>
        </div>
    </div>
    
    <div id="side-panel">
        <!-- Content injected via JS -->
    </div>
    
    <div class="controls-hint">
        Left-click to focus<br>
        Drag to rotate<br>
        Scroll to zoom
    </div>

    <script>
        const graphData = {{GRAPH_DATA}};
        
        // Calculate Phyllotaxis 3D Sphere Coordinates
        // This is not a force simulation, we hardcode the mathematically perfect positions!
        const N = graphData.nodes.length;
        const goldenAngle = 2.39996322972865332; // radians (137.508 degrees)
        const radius = 2500;
        
        graphData.nodes.forEach((node, i) => {
            // y goes from 1 to -1 linearly based on index
            let y = 1 - (i / (N - 1)) * 2; 
            // r at this y (circle radius at this latitude)
            let r_lat = Math.sqrt(1 - y * y); 
            // theta advances by golden angle each step
            let theta = goldenAngle * i;
            
            node.fx = Math.cos(theta) * r_lat * radius;
            node.fy = y * radius;
            node.fz = Math.sin(theta) * r_lat * radius;
        });

        let highlightedClass = null;
        
        function highlightClass(cls) {
            if (highlightedClass === cls) {
                highlightedClass = null;
            } else {
                highlightedClass = cls;
            }
            Graph.nodeVisibility(Graph.nodeVisibility());
            Graph.linkVisibility(Graph.linkVisibility());
        }
        
        const getColor = (classification) => {
            if (classification.includes('Surprise')) return '#ec4899';
            if (classification.includes('Bob')) return '#3b82f6';
            if (classification.includes('Treble Bob')) return '#10b981';
            if (classification.includes('Delight')) return '#8b5cf6';
            return '#94a3b8';
        };
        
        const sidePanel = document.getElementById('side-panel');

        const elem = document.getElementById('3d-graph');
        const Graph = ForceGraph3D()(elem)
            .graphData(graphData)
            .nodeLabel('name')
            .nodeColor(node => getColor(node.classification))
            // Size based on performance count, but using log/cbrt to smooth extreme outliers
            .nodeVal(node => Math.cbrt(node.perf_count) * 2)
            .nodeResolution(16)
            .linkWidth(link => 1.5)
            .linkColor(link => {
                let sourceNode = graphData.nodes.find(n => n.id === link.source.id || n.id === link.source);
                if (sourceNode) return getColor(sourceNode.classification);
                return 'rgba(255, 255, 255, 0.4)';
            })
            // Highly glowing directional particles for the symmetry threads
            .linkDirectionalParticles(2)
            .linkDirectionalParticleSpeed(0.005)
            .linkDirectionalParticleWidth(3)
            .linkDirectionalParticleColor(link => '#ffffff')
            
            // Visibility filters
            .nodeVisibility(node => {
                if (!highlightedClass) return true;
                if (highlightedClass === 'Other') {
                    return !node.classification.includes('Surprise') && 
                           !node.classification.includes('Bob') && 
                           !node.classification.includes('Treble Bob') && 
                           !node.classification.includes('Delight');
                }
                return node.classification.includes(highlightedClass);
            })
            .linkVisibility(link => {
                if (!highlightedClass) return true;
                // Links are between methods of the same class anyway since lhc implies class roughly,
                // but we check source node just in case
                let sourceNode = graphData.nodes.find(n => n.id === link.source.id || n.id === link.source);
                if (!sourceNode) return false;
                
                if (highlightedClass === 'Other') {
                    return !sourceNode.classification.includes('Surprise') && 
                           !sourceNode.classification.includes('Bob') && 
                           !sourceNode.classification.includes('Treble Bob') && 
                           !sourceNode.classification.includes('Delight');
                }
                return sourceNode.classification.includes(highlightedClass);
            })
            
            // Interaction
            .onNodeClick(node => {
                const distance = 1000; // Distance to keep from the node
                const distRatio = 1 + distance/Math.hypot(node.x, node.y, node.z);
                
                Graph.cameraPosition(
                    { x: node.x * distRatio, y: node.y * distRatio, z: node.z * distRatio }, // new position
                    node, // lookAt
                    2000  // ms transition duration
                );
                
                let html = `<h2>${node.name}</h2>`;
                html += `<p class="node-type">Rank #${node.rank + 1} | ${node.classification.toUpperCase()} on ${node.stage} BELLS</p>`;
                html += `<p><strong>Performances:</strong> ${node.perf_count}</p>`;
                html += `<p><strong>Lead Head Code:</strong> ${node.lhc}</p>`;
                html += `<p>This method sits at index ${node.rank} on the Golden Spiral.</p>`;
                html += `<p>The glowing threads shooting out from this node connect it to other methods that share the exact same <strong>${node.lhc}</strong> symmetry group, representing a fundamental mathematical kinship in their permutation structure.</p>`;
                
                sidePanel.innerHTML = html;
                sidePanel.classList.add('visible');
            })
            .onBackgroundClick(() => {
                sidePanel.classList.remove('visible');
            });
            
        // Stop the force engine entirely! We don't need it because we hardcoded fx/fy/fz
        Graph.d3Force('charge').strength(0);
        Graph.d3Force('link').distance(0).strength(0);
        Graph.d3Force('center', null);
        // cooldownTicks(0), not d3AlphaTarget(0).restart(): d3AlphaTarget is a
        // d3-force simulation method that force-graph does not re-export, so the
        // original line threw "Graph.d3AlphaTarget is not a function" and every
        // statement after it -- including the camera position -- never ran. It went
        // unnoticed because the page was blank for an unrelated reason (see
        // docs/vendor/README.md); fixing the libraries surfaced this one.
        Graph.cooldownTicks(0);
        
        // Setup initial camera view
        Graph.cameraPosition({ x: 0, y: 1500, z: 6000 });
        
        // Slowly auto-rotate the entire scene to give it a celestial feel
        let angle = 0;
        setInterval(() => {
            if (!sidePanel.classList.contains('visible')) {
                // Only rotate if we aren't zoomed in on a node
                angle += Math.PI / 2000;
                Graph.cameraPosition({
                    x: 6000 * Math.sin(angle),
                    z: 6000 * Math.cos(angle)
                });
            }
        }, 30);
            
    </script>
<!--FOOTER:geometry.html-->
</body>
</html>"""
    
    graph_json = json.dumps(graph_data)
    html_content = html_template.replace("{{GRAPH_DATA}}", graph_json)
    
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        # One nav bar and one footer for the whole site: scripts/site_chrome.py
        html_content = apply_chrome(html_content, dark=True)
        f.write(html_content)
    
    print(f"Generated {OUTPUT_PATH} with {len(graph_data['nodes'])} nodes and {len(graph_data['links'])} links.")

if __name__ == "__main__":
    print("Fetching sacred geometry data...")
    data = fetch_geometry_data()
    print("Generating HTML...")
    generate_html(data)
