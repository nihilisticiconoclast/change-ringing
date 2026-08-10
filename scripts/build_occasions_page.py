import sqlite3
import pandas as pd
import json
import re
from datetime import datetime

DB_PATH = "data/change-ringing.db"
OUTPUT_PATH = "docs/occasions.html"

# Define regex patterns for classification
CATEGORIES = {
    "Memorial / Funeral": re.compile(r'\b(memory|memorial|funeral|life of|passed away|remembering|died|late|tribute|commemorating|requiem|thanksgiving for the life)\b', re.IGNORECASE),
    "Birthday": re.compile(r'\b(birthday|b\'day|bday)\b', re.IGNORECASE),
    "Wedding / Anniversary": re.compile(r'\b(wedding|anniversary|married|marriage|ruby|golden|diamond|silver)\b', re.IGNORECASE),
    "Firsts / Milestones": re.compile(r'\b(first|1st|circled|milestone)\b', re.IGNORECASE),
    "Church Service / Festival": re.compile(r'\b(thanksgiving|dedication|service|festival|evensong|matins|patronal|centenary|easter|christmas|advent|lent)\b', re.IGNORECASE),
    "Royal / National": re.compile(r'\b(jubilee|coronation|queen|king|royal|majesty|accession|platinum|remembrance|armistice)\b', re.IGNORECASE),
    "Farewell / Welcome": re.compile(r'\b(farewell|leaving|welcome|retiring|retirement|induction)\b', re.IGNORECASE),
    "Compliment / Celebration": re.compile(r'\b(celebrate|celebration|compliment|congratulations|birth of)\b', re.IGNORECASE)
}

def fetch_and_classify():
    conn = sqlite3.connect(DB_PATH)
    
    query = """
        SELECT p.perf_date, f.footnote 
        FROM performance_footnotes f 
        JOIN performances p ON f.perf_id = p.perf_id 
        WHERE f.footnote IS NOT NULL AND f.footnote != ''
    """
    # Fetch all footnotes
    df = pd.read_sql(query, conn)
    conn.close()
    
    # Initialize stats dictionary
    stats = {cat: {"total": 0, "by_month": {m: 0 for m in range(1, 13)}} for cat in CATEGORIES}
    stats["Unclassified"] = {"total": 0, "by_month": {m: 0 for m in range(1, 13)}}
    
    for _, row in df.iterrows():
        footnote = row['footnote']
        perf_date_str = row['perf_date']
        
        # Extract month
        month = 1
        if perf_date_str:
            try:
                dt = datetime.strptime(perf_date_str[:10], "%Y-%m-%d")
                month = dt.month
            except Exception:
                pass
                
        matched = False
        for cat, pattern in CATEGORIES.items():
            if pattern.search(footnote):
                stats[cat]["total"] += 1
                stats[cat]["by_month"][month] += 1
                matched = True
        
        if not matched:
            stats["Unclassified"]["total"] += 1
            stats["Unclassified"]["by_month"][month] += 1
            
    return stats

def generate_html(stats):
    # Format data for Bubble Chart (D3 Pack)
    children = []
    for cat, data in stats.items():
        if cat != "Unclassified" and data["total"] > 0:
            children.append({"name": cat, "value": data["total"]})
            
    bubble_data = {"name": "Occasions", "children": children}
    
    # Format data for Seasonality Line Chart (Chart.js)
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    datasets = []
    colors = [
        '#ec4899', '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444', '#06b6d4', '#14b8a6', '#64748b'
    ]
    
    i = 0
    for cat, data in stats.items():
        if cat != "Unclassified" and data["total"] > 0:
            month_counts = [data["by_month"][m] for m in range(1, 13)]
            datasets.append({
                "label": cat,
                "data": month_counts,
                "borderColor": colors[i % len(colors)],
                "backgroundColor": colors[i % len(colors)] + '40',
                "fill": False,
                "tension": 0.4
            })
            i += 1
            
    html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>The Occasions Archive</title>
    <style>
        body { margin: 0; padding: 0; background-color: #030308; font-family: 'Inter', sans-serif; color: #fff; display: flex; flex-direction: column; min-height: 100vh; overflow-x: hidden; }
        
        .nav-bar {
            width: 100%;
            background: rgba(5, 8, 20, 0.9);
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            padding: 12px 24px;
            display: flex;
            justify-content: flex-start;
            z-index: 10;
            backdrop-filter: blur(12px);
            box-sizing: border-box;
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
            transition: all 0.2s;
        }
        .nav-links a.active {
            color: #ec4899;
            border-bottom-color: #ec4899;
            font-weight: 600;
        }
        .nav-links a:hover { color: #fff; }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px 20px;
            display: flex;
            flex-direction: column;
            gap: 40px;
        }
        
        .header {
            text-align: center;
            max-width: 800px;
            margin: 0 auto;
        }
        
        h1 { margin: 0 0 15px 0; font-size: 2.5rem; font-weight: 700; background: linear-gradient(135deg, #ec4899, #8b5cf6, #3b82f6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        p { margin: 0 0 15px 0; font-size: 1.1rem; color: #94a3b8; line-height: 1.6; }
        
        .visualizations {
            display: grid;
            grid-template-columns: 1fr 1.2fr;
            gap: 30px;
        }
        
        .card {
            background: rgba(15, 20, 40, 0.5);
            border: 1px solid rgba(255, 255, 255, 0.05);
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }
        
        .card h2 {
            margin-top: 0;
            font-size: 1.2rem;
            color: #f8fafc;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            padding-bottom: 15px;
            margin-bottom: 20px;
        }
        
        #bubble-chart-container {
            width: 100%;
            height: 500px;
            position: relative;
        }
        
        #line-chart-container {
            width: 100%;
            height: 500px;
            position: relative;
        }
        
        .tooltip {
            position: absolute;
            text-align: center;
            padding: 8px 12px;
            font-size: 14px;
            font-family: 'Inter', sans-serif;
            background: rgba(0, 0, 0, 0.85);
            color: #fff;
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 8px;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.2s;
            z-index: 10;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
            margin-top: 20px;
        }
        .stat-box {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.05);
            padding: 15px;
            border-radius: 10px;
            text-align: center;
        }
        .stat-val { font-size: 1.8rem; font-weight: 700; color: #ec4899; }
        .stat-lbl { font-size: 0.8rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px; margin-top: 5px; }
        
        @media (max-width: 1024px) {
            .visualizations { grid-template-columns: 1fr; }
            .stats-grid { grid-template-columns: repeat(2, 1fr); }
        }
    </style>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <div class="nav-bar">
      <div class="nav-links">
        <a href="index.html">Founder Atlas</a>
        <a href="lineage.html">Method Lineage</a>
        <a href="ringers.html">Ringer Constellation</a>
        <a href="nexus.html">The Temporal Nexus</a>
        <a href="geometry.html">Sacred Geometry</a>
        <a href="occasions.html" class="active">The Occasions Archive</a>
      </div>
    </div>
    
    <div class="container">
        <div class="header">
            <h1>Why People Ring</h1>
            <p>Every performance is woven with human intent. By classifying hundreds of thousands of footnotes, we can map the overarching reasons why bells are rung—from profound memorials to jubilant celebrations—all while strictly preserving individual privacy.</p>
        </div>
        
        <div class="visualizations">
            <div class="card">
                <h2>The Occasions Constellation</h2>
                <div id="bubble-chart-container"></div>
                <div class="tooltip" id="bubble-tooltip"></div>
            </div>
            
            <div class="card">
                <h2>Seasonality of Intent</h2>
                <div id="line-chart-container">
                    <canvas id="seasonalityChart"></canvas>
                </div>
            </div>
        </div>
        
        <div class="card" style="margin-bottom: 40px;">
            <h2>Aggregate Insights</h2>
            <div class="stats-grid" id="stats-container">
                <!-- Injected via JS -->
            </div>
        </div>
    </div>

    <script>
        const bubbleData = {{BUBBLE_DATA}};
        const lineData = {{LINE_DATA}};
        
        // --- BUBBLE CHART (D3.js) ---
        const container = document.getElementById('bubble-chart-container');
        const width = container.clientWidth;
        const height = container.clientHeight;
        
        const svg = d3.select("#bubble-chart-container")
            .append("svg")
            .attr("width", width)
            .attr("height", height)
            .attr("viewBox", [0, 0, width, height])
            .attr("style", "max-width: 100%; height: auto;");
            
        const pack = d3.pack()
            .size([width - 10, height - 10])
            .padding(8);
            
        const root = pack(d3.hierarchy(bubbleData).sum(d => d.value).sort((a, b) => b.value - a.value));
        
        // Custom color palette matching the line chart
        const colorPalette = ['#ec4899', '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444', '#06b6d4', '#14b8a6', '#64748b'];
        const colorScale = d3.scaleOrdinal().range(colorPalette);
        
        const tooltip = d3.select("#bubble-tooltip");
        
        const node = svg.selectAll("g")
            .data(root.leaves())
            .join("g")
            .attr("transform", d => `translate(${d.x},${d.y})`);
            
        node.append("circle")
            .attr("r", d => d.r)
            .attr("fill", (d, i) => {
                // Find matching color from chart data for consistency
                const ds = lineData.datasets.find(ds => ds.label === d.data.name);
                return ds ? ds.borderColor : colorScale(i);
            })
            .attr("fill-opacity", 0.7)
            .attr("stroke", (d, i) => {
                const ds = lineData.datasets.find(ds => ds.label === d.data.name);
                return ds ? ds.borderColor : colorScale(i);
            })
            .attr("stroke-width", 2)
            .style("cursor", "pointer")
            .on("mouseover", function(event, d) {
                d3.select(this).attr("fill-opacity", 1);
                tooltip.style("opacity", 1)
                       .html(`<strong>${d.data.name}</strong><br/>${d.data.value.toLocaleString()} performances`);
            })
            .on("mousemove", function(event) {
                const containerRect = document.getElementById('bubble-chart-container').getBoundingClientRect();
                tooltip.style("left", (event.clientX - containerRect.left + 15) + "px")
                       .style("top", (event.clientY - containerRect.top - 15) + "px");
            })
            .on("mouseout", function() {
                d3.select(this).attr("fill-opacity", 0.7);
                tooltip.style("opacity", 0);
            });
            
        node.append("text")
            .attr("text-anchor", "middle")
            .attr("dy", "-0.2em")
            .style("fill", "#fff")
            .style("font-size", d => Math.min(d.r / 3, 14) + "px")
            .style("font-weight", "600")
            .style("pointer-events", "none")
            .text(d => d.r > 25 ? d.data.name : "");
            
        node.append("text")
            .attr("text-anchor", "middle")
            .attr("dy", "1.2em")
            .style("fill", "rgba(255,255,255,0.7)")
            .style("font-size", d => Math.min(d.r / 4, 12) + "px")
            .style("pointer-events", "none")
            .text(d => d.r > 35 ? d.data.value.toLocaleString() : "");
            
        // --- LINE CHART (Chart.js) ---
        const ctx = document.getElementById('seasonalityChart').getContext('2d');
        
        Chart.defaults.color = '#94a3b8';
        Chart.defaults.font.family = "'Inter', sans-serif";
        
        new Chart(ctx, {
            type: 'line',
            data: lineData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            usePointStyle: true,
                            padding: 20
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0, 0, 0, 0.8)',
                        titleColor: '#fff',
                        bodyColor: '#cbd5e1',
                        borderColor: 'rgba(255,255,255,0.1)',
                        borderWidth: 1,
                        padding: 12
                    }
                },
                scales: {
                    x: {
                        grid: { color: 'rgba(255,255,255,0.05)' }
                    },
                    y: {
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        beginAtZero: true
                    }
                }
            }
        });
        
        // --- STATS CARDS ---
        const statsContainer = document.getElementById('stats-container');
        
        // Sort by value
        const topStats = bubbleData.children.slice(0, 4);
        
        let html = '';
        topStats.forEach(stat => {
            html += `
                <div class="stat-box">
                    <div class="stat-val">${stat.value.toLocaleString()}</div>
                    <div class="stat-lbl">${stat.name}</div>
                </div>
            `;
        });
        statsContainer.innerHTML = html;
        
    </script>
</body>
</html>"""
    
    html_content = html_template.replace("{{BUBBLE_DATA}}", json.dumps(bubble_data))
    html_content = html_content.replace("{{LINE_DATA}}", json.dumps({"labels": months, "datasets": datasets}))
    
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"Generated {OUTPUT_PATH}")

if __name__ == "__main__":
    print("Extracting and classifying footnotes...")
    stats = fetch_and_classify()
    print("Generating visualization...")
    generate_html(stats)
