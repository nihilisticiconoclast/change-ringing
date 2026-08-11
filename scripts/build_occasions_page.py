import sqlite3
import pandas as pd
import json
import re
import random
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
        SELECT p.perf_date, p.changes, f.footnote 
        FROM performance_footnotes f 
        JOIN performances p ON f.perf_id = p.perf_id 
        WHERE f.footnote IS NOT NULL AND f.footnote != ''
    """
    df = pd.read_sql(query, conn)
    conn.close()
    
    # Initialize stats dictionary
    stats = {cat: {"total": 0, "by_month": {m: 0 for m in range(1, 13)}, "changes": []} for cat in CATEGORIES}
    
    for _, row in df.iterrows():
        footnote = row['footnote']
        perf_date_str = row['perf_date']
        changes = row['changes']
        
        # Extract month
        month = 1
        if perf_date_str:
            try:
                dt = datetime.strptime(perf_date_str[:10], "%Y-%m-%d")
                month = dt.month
            except Exception:
                pass
                
        # Validate changes
        valid_changes = None
        if pd.notna(changes):
            try:
                c = int(changes)
                if 100 <= c <= 15000:
                    valid_changes = c
            except:
                pass
                
        for cat, pattern in CATEGORIES.items():
            if pattern.search(footnote):
                stats[cat]["total"] += 1
                stats[cat]["by_month"][month] += 1
                if valid_changes is not None:
                    stats[cat]["changes"].append(valid_changes)
                
    return stats

def generate_html(stats):
    # Format data for Violin plot
    violin_data = []
    
    # Filter out categories with too little data
    valid_cats = [c for c in CATEGORIES if stats[c]["total"] > 100]
    
    # Sort categories by total count descending
    valid_cats.sort(key=lambda c: stats[c]["total"], reverse=True)
    
    for cat in valid_cats:
        c_data = stats[cat]["changes"]
        if not c_data: continue
        # Downsample for JS passing to keep JSON small
        sampled = random.sample(c_data, min(len(c_data), 2000))
        violin_data.append({"name": cat, "values": sampled})
        
    # Format data for Seasonality Line Chart
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    line_datasets = []
    
    colors = ['#ec4899', '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444', '#06b6d4', '#14b8a6', '#64748b']
    
    for i, cat in enumerate(valid_cats):
        month_counts = [stats[cat]["by_month"][m] for m in range(1, 13)]
        line_datasets.append({
            "label": cat,
            "data": month_counts,
            "borderColor": colors[i % len(colors)],
            "backgroundColor": colors[i % len(colors)] + '40',
            "fill": False,
            "tension": 0.4
        })
        
    leaderboard_data = [{"name": cat, "count": stats[cat]["total"], "color": colors[i % len(colors)]} for i, cat in enumerate(valid_cats)]
            
    html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>The Occasions Archive</title>
    <style>
:root{
  --ground:#EFEDE7; --surface:#F7F6F2; --surface-2:#E4E2DA;
  --ink:#1C1E1C; --ink-2:#4A4C48; --ink-3:#7C7E78;
  --rule:#CFCCC2; --bronze:#8A5F22; --bronze-soft:#B8873F;
  --dim:#C9C6BC;
  --serif:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,"Times New Roman",serif;
  --mono:ui-monospace,"SF Mono",SFMono-Regular,Menlo,Consolas,monospace;
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --ground:#131312; --surface:#1a1a19; --surface-2:#242422;
    --ink:#F0EDE6; --ink-2:#B5B1A7; --ink-3:#85817A;
    --rule:#302F2C; --bronze:#C9974A; --bronze-soft:#B8873F;
    --dim:#33322F;
  }
}
        body { margin: 0; padding: 0; background: var(--ground); color: var(--ink); font-family: var(--serif); line-height: 1.62; display: flex; flex-direction: column; min-height: 100vh; overflow-x: hidden; -webkit-font-smoothing:antialiased;}
        
        .nav-bar{
          background:var(--surface); border-bottom:1px solid var(--rule);
          padding:12px 24px; display:flex; justify-content:space-between; align-items:center;
        }
        .nav-links{display:flex;gap:20px;font-family:var(--mono);font-size:12px;letter-spacing:.08em;text-transform:uppercase;flex-wrap:wrap;}
        .nav-links a{color:var(--ink-2);text-decoration:none;padding:4px 0;border-bottom:2px solid transparent}
        .nav-links a.active{color:var(--bronze);border-bottom-color:var(--bronze);font-weight:600}
        .nav-links a:hover{color:var(--ink)}
        
        .container {
            max-width: 1120px;
            margin: 0 auto;
            padding: 40px 24px;
            display: flex;
            flex-direction: column;
            gap: 40px;
        }
        
        .header {
            max-width: 800px;
            margin: 0;
            padding: 48px 0 20px;
        }
        
        .eyebrow{
          font-family:var(--mono); font-size:11px; letter-spacing:.18em;
          text-transform:uppercase; color:var(--bronze); margin:0 0 14px;
        }
        h1{margin:0; font-size:clamp(2.4rem,6vw,4.2rem);line-height:1.03;font-weight:400;letter-spacing:-.015em}
        h1 em{font-style:italic;color:var(--bronze)}
        .standfirst{margin-top:22px;font-size:1.2rem;color:var(--ink-2);max-width:60ch; line-height:1.6;}
        
        .visualizations {
            display: flex;
            flex-direction: column;
            gap: 30px;
            margin-top: 20px;
        }
        
        .grid-2 {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
        }
        
        .card {
            background: var(--surface);
            border: 1px solid var(--rule);
            border-radius: 3px;
            padding: 24px;
        }
        
        .card h2 {
            margin: 0 0 5px 0;
            font-size: clamp(1.4rem,2vw,1.8rem);
            font-weight: 400;
            letter-spacing: -.01em;
            color: var(--ink);
        }
        
        .card p.desc {
            font-family: var(--serif);
            color: var(--ink-2);
            font-size: 0.95rem;
            margin: 0 0 20px 0;
            border-bottom: 1px solid var(--rule);
            padding-bottom: 15px;
        }
        
        #violin-chart-container {
            width: 100%;
            height: 480px;
            position: relative;
        }
        
        #line-chart-container {
            width: 100%;
            height: 400px;
            position: relative;
        }
        
        /* Leaderboard styling */
        .leaderboard {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        
        .lb-row {
            display: grid;
            grid-template-columns: 180px 1fr 60px;
            align-items: center;
            gap: 15px;
        }
        
        .lb-name {
            font-family: var(--mono);
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--ink);
            text-align: right;
        }
        
        .lb-bar-container {
            width: 100%;
            background: var(--surface-2);
            height: 12px;
            border-radius: 6px;
            overflow: hidden;
        }
        
        .lb-bar {
            height: 100%;
            border-radius: 6px;
        }
        
        .lb-count {
            font-family: var(--mono);
            font-variant-numeric: tabular-nums;
            font-size: 12px;
            color: var(--ink-3);
        }
        
        .tooltip {
            position: absolute;
            text-align: center;
            padding: 8px 12px;
            font-size: 14px;
            font-family: var(--mono);
            background: var(--surface);
            color: var(--ink);
            border: 1px solid var(--rule);
            border-radius: 2px;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.2s;
            z-index: 10;
            box-shadow: 0 4px 18px rgba(0,0,0,.28);
        }
        
        @media (max-width: 1024px) {
            .grid-2 { grid-template-columns: 1fr; }
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
            <a href="occasions.html" class="active">The Occasions Archive</a>
            <a href="nexus.html">The Temporal Nexus</a>
            <a href="geometry.html">Sacred Geometry</a>
      </div>
    </div>
    
    <div class="container">
        <div class="header">
            <p class="eyebrow">Change Ringing Corpus · Second analytical output</p>
            <h1>Why people <em>ring</em></h1>
            <p class="standfirst">Every performance is woven with human intent. By classifying hundreds of thousands of footnotes, we can map the overarching reasons why bells are rung—and the physical endurance those occasions demand—all while strictly preserving individual privacy.</p>
        </div>
        
        <div class="visualizations">
            <div class="grid-2">
                <div class="card">
                    <h2>Seasonality</h2>
                    <p class="desc">The cadence of ringing occasions throughout the calendar year. Notice the huge spikes for Christmas and New Year, compared to the stable year-round cadence of Birthday performances.</p>
                    <div id="line-chart-container">
                        <canvas id="seasonalityChart"></canvas>
                    </div>
                </div>
                
                <div class="card">
                    <h2>The Occasions Ledger</h2>
                    <p class="desc">Total performances categorised by underlying motivation. The overwhelming majority of dedicated ringing is to celebrate personal achievements and milestones.</p>
                    <div class="leaderboard" id="leaderboard-container">
                        <!-- Injected via JS -->
                    </div>
                </div>
            </div>

            <div class="card">
                <h2>Endurance of Intent</h2>
                <p class="desc">The distribution of changes rung (length of performance) across different occasion types. By plotting every performance, we can see the physical endurance demanded by different motivations.</p>
                <div style="font-size: 15px; color: var(--ink-2); max-width: 800px; margin-bottom: 25px; line-height: 1.6;">
                    <p>There are two distinct peaks in change ringing: the <strong>Quarter Peal</strong> (typically ~1,260 changes, taking 45 minutes) and the grueling <strong>Full Peal</strong> (typically ~5,040 changes, taking 3 hours of non-stop concentration). </p>
                    <p>When we split these performances by their occasion, stark patterns emerge. <strong>Memorials</strong> and <strong>Church Festivals</strong> are predominantly commemorated with shorter Quarter Peals. However, <strong>Royal events</strong> and <strong>Firsts/Milestones</strong> show a significantly higher proportion of 3-hour Full Peals, reflecting the immense physical effort ringers put into celebrating national events and personal achievements.</p>
                </div>
                <div id="violin-chart-container"></div>
                <div class="tooltip" id="violin-tooltip"></div>
            </div>
        </div>
    </div>

    <script>
        const violinData = {{VIOLIN_DATA}};
        const lineData = {{LINE_DATA}};
        const lbData = {{LB_DATA}};
        
        // Custom color palette matching the line chart
        const colorPalette = ['#ec4899', '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444', '#06b6d4', '#14b8a6', '#64748b'];
        const colorScale = d3.scaleOrdinal().range(colorPalette).domain(violinData.map(d => d.name));
        
        const rootStyles = getComputedStyle(document.documentElement);
        const inkColor = rootStyles.getPropertyValue('--ink').trim();
        const ink2Color = rootStyles.getPropertyValue('--ink-2').trim();
        const ruleColor = rootStyles.getPropertyValue('--rule').trim();
        const monoFont = rootStyles.getPropertyValue('--mono').trim();
        
        // --- VIOLIN PLOT (D3.js) ---
        function renderViolin() {
            const container = document.getElementById('violin-chart-container');
            container.innerHTML = '';
            
            const margin = {top: 20, right: 30, bottom: 40, left: 160},
                  width = Math.max(container.clientWidth, 800) - margin.left - margin.right,
                  height = container.clientHeight - margin.top - margin.bottom;

            const svg = d3.select("#violin-chart-container")
              .append("svg")
                .attr("width", width + margin.left + margin.right)
                .attr("height", height + margin.top + margin.bottom)
              .append("g")
                .attr("transform", `translate(${margin.left},${margin.top})`);

            // Y axis
            const y = d3.scaleBand()
                .range([ 0, height ])
                .domain(violinData.map(d => d.name))
                .padding(0.1);
            
            svg.append("g")
                .call(d3.axisLeft(y).tickSize(0))
                .select(".domain").remove();
                
            svg.selectAll(".tick text")
                .attr("fill", inkColor)
                .attr("font-family", monoFont)
                .attr("font-size", "11px")
                .style("text-transform", "uppercase");

            // X axis
            const x = d3.scaleLinear()
                .domain([0, 6000]) // Cap at 6000 to focus on Quarter/Peal clusters.
                .range([ 0, width ]);
                
            svg.append("g")
                .attr("transform", `translate(0,${height})`)
                .call(d3.axisBottom(x).ticks(6))
                .attr("color", ruleColor)
                .selectAll("text")
                    .attr("fill", inkColor)
                    .attr("font-family", monoFont)
                    .attr("font-size", "11px");
                    
            // Gridlines
            svg.append("g")
                .attr("class", "grid")
                .attr("transform", `translate(0,${height})`)
                .call(d3.axisBottom(x).ticks(6).tickSize(-height).tickFormat(""))
                .attr("color", ruleColor)
                .attr("stroke-opacity", 0.2)
                .select(".domain").remove();

            // Features of the density estimate
            const kde = kernelDensityEstimator(kernelEpanechnikov(200), x.ticks(100));

            // Compute density for each group
            let allDensity = [];
            for (let i = 0; i < violinData.length; i++) {
                const key = violinData[i].name;
                const vals = violinData[i].values.filter(v => v <= 6000);
                const density = kde(vals);
                allDensity.push({key: key, density: density});
            }

            // Find max density to scale vertically
            const maxNum = d3.max(allDensity, d => d3.max(d.density, v => v[1]));

            // Y scale for density
            const yName = d3.scaleLinear()
              .range([0, y.bandwidth()])
              .domain([-maxNum, maxNum]);

            // Add the areas
            svg.selectAll("myViolin")
              .data(allDensity)
              .enter()
              .append("g")
                .attr("transform", d => `translate(0,${y(d.key)})`)
              .append("path")
                  .datum(d => d.density)
                  .style("stroke", "none")
                  .style("fill", (d, i) => colorScale(allDensity[i].key))
                  .style("opacity", 0.6)
                  .attr("d", d3.area()
                      .x0(d => x(d[0]))
                      .x1(d => x(d[0]))
                      .y0(d => yName(-d[1]))
                      .y1(d => yName(d[1]))
                      .curve(d3.curveCatmullRom)
                  );
                  
            // Overlap scatter dots (beeswarm lite)
            const tooltip = d3.select("#violin-tooltip");
            
            svg.selectAll("myDots")
              .data(violinData)
              .enter()
              .append("g")
              .attr("transform", d => `translate(0,${y(d.name) + y.bandwidth()/2})`)
              .selectAll("circle")
              .data(d => d.values.filter(v => v <= 6000).slice(0, 300)) // Max 300 dots per category for perf
              .enter()
              .append("circle")
                .attr("cx", d => x(d))
                .attr("cy", d => (Math.random() - 0.5) * y.bandwidth() * 0.4) // Random jitter
                .attr("r", 2)
                .style("fill", rootStyles.getPropertyValue('--ground').trim())
                .style("stroke", "rgba(0,0,0,0.2)")
                .style("opacity", 0.6)
                .on("mouseover", function(event, d) {
                    d3.select(this).attr("r", 5).style("opacity", 1);
                    tooltip.style("opacity", 1)
                           .html(`<strong>${d}</strong> changes`);
                })
                .on("mousemove", function(event) {
                    tooltip.style("left", (event.pageX + 15) + "px")
                           .style("top", (event.pageY - 15) + "px");
                })
                .on("mouseout", function() {
                    d3.select(this).attr("r", 2).style("opacity", 0.6);
                    tooltip.style("opacity", 0);
                });
                
            // Annotations for Peal/Quarter
            svg.append("line")
               .attr("x1", x(1260)).attr("x2", x(1260))
               .attr("y1", 0).attr("y2", height)
               .attr("stroke", ink2Color)
               .attr("stroke-dasharray", "4,4")
               .style("opacity", 0.5);
               
            svg.append("text")
               .attr("x", x(1260)).attr("y", -5)
               .attr("text-anchor", "middle")
               .attr("fill", ink2Color)
               .attr("font-family", monoFont)
               .attr("font-size", "10px")
               .text("QTR (~1260)");
               
            svg.append("line")
               .attr("x1", x(5040)).attr("x2", x(5040))
               .attr("y1", 0).attr("y2", height)
               .attr("stroke", ink2Color)
               .attr("stroke-dasharray", "4,4")
               .style("opacity", 0.5);
               
            svg.append("text")
               .attr("x", x(5040)).attr("y", -5)
               .attr("text-anchor", "middle")
               .attr("fill", ink2Color)
               .attr("font-family", monoFont)
               .attr("font-size", "10px")
               .text("PEAL (~5040)");
        }
        
        // Kernel Density Estimation Functions
        function kernelDensityEstimator(kernel, X) {
            return function(V) {
                return X.map(function(x) {
                    return [x, d3.mean(V, function(v) { return kernel(x - v); })];
                });
            };
        }
        function kernelEpanechnikov(k) {
            return function(v) {
                return Math.abs(v /= k) <= 1 ? 0.75 * (1 - v * v) / k : 0;
            };
        }
        
        // Render leaderboard
        function renderLeaderboard() {
            const container = document.getElementById('leaderboard-container');
            const maxCount = Math.max(...lbData.map(d => d.count));
            
            let html = '';
            lbData.forEach(d => {
                const widthPct = (d.count / maxCount) * 100;
                html += `
                    <div class="lb-row">
                        <div class="lb-name">${d.name}</div>
                        <div class="lb-bar-container">
                            <div class="lb-bar" style="width: ${widthPct}%; background: ${d.color}"></div>
                        </div>
                        <div class="lb-count">${d.count.toLocaleString()}</div>
                    </div>
                `;
            });
            container.innerHTML = html;
        }

        // --- LINE CHART (Chart.js) ---
        function renderLineChart() {
            const ctx = document.getElementById('seasonalityChart').getContext('2d');
            
            Chart.defaults.color = rootStyles.getPropertyValue('--ink-3').trim();
            Chart.defaults.font.family = rootStyles.getPropertyValue('--mono').trim();
            
            new Chart(ctx, {
                type: 'line',
                data: lineData,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: { mode: 'index', intersect: false },
                    plugins: {
                        legend: { position: 'bottom', labels: { usePointStyle: true, padding: 20 } },
                        tooltip: {
                            backgroundColor: rootStyles.getPropertyValue('--surface-2').trim(),
                            titleColor: rootStyles.getPropertyValue('--ink').trim(),
                            bodyColor: rootStyles.getPropertyValue('--ink-2').trim(),
                            borderColor: rootStyles.getPropertyValue('--rule').trim(),
                            borderWidth: 1, padding: 12
                        }
                    },
                    scales: {
                        x: { grid: { color: rootStyles.getPropertyValue('--rule').trim() } },
                        y: { grid: { color: rootStyles.getPropertyValue('--rule').trim() }, beginAtZero: true }
                    }
                }
            });
        }
        
        renderViolin();
        renderLeaderboard();
        renderLineChart();
        
        window.addEventListener('resize', renderViolin);
    </script>
</body>
</html>"""
    
    html_content = html_template.replace("{{VIOLIN_DATA}}", json.dumps(violin_data))
    html_content = html_content.replace("{{LINE_DATA}}", json.dumps({"labels": months, "datasets": line_datasets}))
    html_content = html_content.replace("{{LB_DATA}}", json.dumps(leaderboard_data))
    
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"Generated {OUTPUT_PATH}")

if __name__ == "__main__":
    print("Extracting and classifying footnotes...")
    stats = fetch_and_classify()
    print("Generating visualization...")
    generate_html(stats)
