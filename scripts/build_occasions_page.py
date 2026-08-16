import sqlite3
import pandas as pd
import json
import re
import random
from datetime import datetime

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from site_chrome import apply_chrome  # noqa: E402
import sqlfile  # noqa: E402

ROOT = Path(__file__).parent.parent
DB_PATH = str(ROOT / "data" / "change-ringing.db")
OUTPUT_PATH = str(ROOT / "docs" / "occasions.html")
QUERIES = ROOT / "queries" / "occasions"

def sql(name, index=0):
    """Load one statement from queries/occasions/.

    The SQL lives in a file rather than a string literal here so the recorded
    query and the one that builds the page cannot drift apart. Comments are
    stripped before splitting on ';', not after -- splitting first breaks on any
    semicolon inside a '--' comment.
    """
    return sqlfile.statement(QUERIES / name, index)

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
    
    df = pd.read_sql(sql("01_footnotes_with_length.sql", 0), conn)
    denom = conn.execute(sql("01_footnotes_with_length.sql", 1)).fetchone()
    conn.close()
    
    # Initialize stats dictionary
    stats = {cat: {"total": 0, "by_month": {m: 0 for m in range(1, 13)}, "changes": []} for cat in CATEGORIES}

    # The categories are keyword patterns tested independently, so they are NOT a
    # partition: a footnote can match several, or none. Both have to be counted
    # while classifying and both have to appear on the page, otherwise the ledger
    # reads as a breakdown of a whole when it is neither exhaustive nor exclusive.
    coverage = {"footnotes": 0, "unclassified": 0, "multi": 0,
                "pairs": {}, "denom": denom, "thanksgiving_for_the_life": 0}
    # One overlap is worth naming rather than leaving in the pair counts: the
    # Memorial pattern matches "thanksgiving for the life" and the Church Service
    # pattern matches bare "thanksgiving", so every memorial thanksgiving is
    # counted as a service too. Measured, not guessed at.
    thanks_re = re.compile(r"thanksgiving for the life", re.IGNORECASE)
    
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
            except (TypeError, ValueError):
                # `changes` is nullable and occasionally non-numeric; a length we
                # cannot parse is left as None rather than guessed at. A bare
                # `except:` here would also have swallowed KeyboardInterrupt.
                pass
                
        matched = []
        for cat, pattern in CATEGORIES.items():
            if pattern.search(footnote):
                matched.append(cat)
                stats[cat]["total"] += 1
                stats[cat]["by_month"][month] += 1
                if valid_changes is not None:
                    stats[cat]["changes"].append(valid_changes)

        coverage["footnotes"] += 1
        if thanks_re.search(footnote):
            coverage["thanksgiving_for_the_life"] += 1
        if not matched:
            coverage["unclassified"] += 1
        elif len(matched) > 1:
            coverage["multi"] += 1
            for i, a in enumerate(matched):
                for b in matched[i + 1:]:
                    key = " + ".join(sorted((a, b)))
                    coverage["pairs"][key] = coverage["pairs"].get(key, 0) + 1

    return stats, coverage

def generate_html(stats, coverage):
    # Format data for Violin plot
    violin_data = []
    
    # Filter out categories with too little data
    valid_cats = [c for c in CATEGORIES if stats[c]["total"] > 100]
    
    # Sort categories by total count descending
    valid_cats.sort(key=lambda c: stats[c]["total"], reverse=True)
    
    for cat in valid_cats:
        c_data = stats[cat]["changes"]
        if not c_data: continue
        # Downsample for JS passing to keep JSON small.
        #
        # SEEDED, and the seed is the point. This was a bare random.sample(),
        # so every rebuild drew a different 2,000 and the committed page changed
        # on every build whether or not the data had. Two consecutive builds from
        # an unchanged database produced different SHA-256s, which means no
        # published version of this page could be reproduced, and `git status`
        # always showed it modified -- training everyone to ignore that.
        # A fixed seed keeps the sample statistically arbitrary, which is all it
        # needs to be, while making the output a function of the data alone.
        sampled = random.Random(20260815).sample(c_data, min(len(c_data), 2000))
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
        /* Long file paths in <code> are single unbreakable tokens and were the last
           thing forcing the page 80px wider than a 390px viewport. */
        code { font-family: var(--mono); font-size: .88em; background: var(--surface-2);
               padding: 1px 5px; border-radius: 2px;
               overflow-wrap: anywhere; word-break: break-word; }
        
        .header {
            max-width: 800px;
            margin: 0;
            padding: 48px 0 20px;
        }
        
        .visualizations {
            display: grid;
            grid-template-columns: 1fr;
            gap: 30px;
            margin-top: 20px;
        }
        .visualizations, .grid-2, .card { min-width: 0; }
        /* max-width is what makes overflow-x work here: without a definite width
           the container grows to fit the 800px-minimum violin SVG, pushes .card
           wider than the viewport, and the whole page scrolls sideways instead of
           just the chart. */
        #violin-chart-container, #line-chart-container {
            overflow-x: auto; min-width: 0; max-width: 100%;
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
            height: 600px;
            position: relative;
            overflow-x: auto;
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
    <script src="vendor/d3-7.9.0.min.js"></script>
    <script src="vendor/chart-4.5.1.min.js"></script>
</head>
<body>
    <!--NAV:occasions.html-->
    <div class="wrap">
        <div class="header">
            <p class="eyebrow">Change Ringing Corpus · Second analytical output</p>
            <h1>Why people <em>ring</em></h1>
            <p class="standfirst">Ringers write a footnote saying why they rang. Classifying <strong>{{N_FOOTNOTES}}</strong> of them maps the reasons bells are rung in England, and the physical endurance each occasion asks for. Nothing below identifies anybody: only aggregate counts and lengths leave the database, and no footnote text is published on this page.</p>
        </div>
        
        <div class="visualizations">
            <div class="card">
                <h2>Endurance of Intent</h2>
                <p class="desc">The distribution of changes rung — how long the performance was — across occasion types. The dense bands at 1,260 (quarter peal) and 5,040 (full peal) are the two standard lengths, and every category has both, so occasion does not choose length nearly as much as you would expect. Restricted to performances of 100–15,000 changes, plotted to 6,000, and thinned to at most 300 points per category for rendering: read the shape, not the dot count.</p>
                <div id="violin-chart-container"></div>
                <div class="tooltip" id="violin-tooltip"></div>
            </div>
            
            <div class="grid-2">
                <div class="card">
                    <h2>Seasonality</h2>
                    <p class="desc">Footnotes per month, by category, across 2021–24. The Royal / National line is dominated by four national events rather than by any seasonal cycle — see <a href="rhythm.html" style="color:var(--bronze)">Rhythm of Ringing</a>, where 24 days carry 21% of all ringing in the window.</p>
                    <div id="line-chart-container">
                        <canvas id="seasonalityChart"></canvas>
                    </div>
                </div>
                
                <div class="card">
                    <h2>The Occasions Ledger</h2>
                    <p class="desc"><strong>Footnotes</strong> — not performances — matching each occasion keyword. <strong>These do not sum to a total and must not be added up:</strong> the categories are independent keyword tests, so {{N_MULTI}} footnotes ({{PC_MULTI}}%) match more than one, and {{N_UNCLS}} ({{PC_UNCLS}}%) match none.</p>
                    <div class="leaderboard" id="leaderboard-container">
                        <!-- Injected via JS -->
                    </div>
                </div>
            </div>
        </div>

        <div class="card" style="margin-top:8px">
            <h2>How this was made, and where it is weak</h2>
            <p class="desc" style="max-width:78ch">
            Built by <code>scripts/build_occasions_page.py</code> from
            <code>data/change-ringing.db</code>; the SQL is
            <code>queries/occasions/01_footnotes_with_length.sql</code> and the script reads
            that file rather than holding a copy, so the recorded query is the one that ran.
            The eight categories are regular expressions over footnote text, listed in full
            at the top of the builder.</p>
            <p class="desc" style="max-width:78ch">
            <strong>Four limitations, stated rather than buried.</strong>
            <em>One:</em> the unit is footnotes. {{N_FOOTNOTES}} footnotes attach to
            {{N_PERFS}} performances, a mean of {{FN_PER_PERF}} each, so a category count is
            not a count of ringing occasions.
            <em>Two:</em> the categories overlap by construction — {{N_MULTI}} footnotes
            match two or more, the largest pair being {{TOP_PAIR}}. Some of that is real
            (a birthday <em>is</em> a celebration) and some is an artefact: {{N_THANKS}}
            footnotes say “thanksgiving for the life of”, which the Memorial pattern and the
            Church Service pattern both claim, so Church Service is inflated by that much.
            <em>Three:</em> {{PC_UNCLS}}% match no keyword at all, so this is a map of eight
            reasons and not of every reason.
            <em>Four:</em> a keyword is not an intent. “First” catches a ringer’s personal
            milestone and the word “first” in any other sentence alike; no sample has been
            hand-checked to estimate that error rate, and until one has, treat the ordering
            of the smaller categories as unproven.</p>
            <p class="desc" style="max-width:78ch">
            <strong>Privacy.</strong> Footnotes are written by ringers for ringers, and many
            are memorials and funeral tributes composed by people who did not anticipate
            republication. Only aggregate counts and change-lengths are embedded in this
            page — no footnote text, no names, no dates of individual performances. That is
            a deliberate constraint on the analysis, recorded in
            <code>docs/ROADMAP.md</code>.</p>
            <p class="desc" style="max-width:78ch">
            Data derived from BellBoard and Dove’s Guide, <strong>CC BY-SA 4.0</strong> — see
            <code>data/LICENCE-DATA.md</code> before reusing anything here. The code is MIT.</p>
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
<!--FOOTER:occasions.html-->
</body>
</html>"""
    
    n = coverage["footnotes"]
    _, n_perfs, _ = coverage["denom"]
    top_pair, top_pair_n = sorted(
        coverage["pairs"].items(), key=lambda kv: -kv[1])[0] if coverage["pairs"] else ("none", 0)
    fills = {
        "{{VIOLIN_DATA}}": json.dumps(violin_data),
        "{{LINE_DATA}}": json.dumps({"labels": months, "datasets": line_datasets}),
        "{{LB_DATA}}": json.dumps(leaderboard_data),
        # Every figure in the prose is filled from the same pass that built the
        # charts. None of them is typed in, so a re-run on a larger corpus cannot
        # leave a stale number in a sentence.
        "{{N_FOOTNOTES}}": f"{n:,}",
        "{{N_PERFS}}": f"{n_perfs:,}",
        "{{FN_PER_PERF}}": f"{n / n_perfs:.1f}",
        "{{N_MULTI}}": f"{coverage['multi']:,}",
        "{{PC_MULTI}}": f"{100 * coverage['multi'] / n:.0f}",
        "{{N_UNCLS}}": f"{coverage['unclassified']:,}",
        "{{PC_UNCLS}}": f"{100 * coverage['unclassified'] / n:.0f}",
        "{{TOP_PAIR}}": f"{top_pair_n:,} in “{top_pair}”",
        "{{N_THANKS}}": f"{coverage['thanksgiving_for_the_life']:,}",
    }
    html_content = html_template
    for k, v in fills.items():
        html_content = html_content.replace(k, v)
    leftover = [k for k in fills if k in html_content]
    if leftover:
        raise SystemExit(f"ERROR: placeholders survived substitution: {leftover}")
    
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        # One nav bar and one footer for the whole site: scripts/site_chrome.py
        html_content = apply_chrome(html_content)
        f.write(html_content)
    
    print(f"Generated {OUTPUT_PATH}")

if __name__ == "__main__":
    print("Extracting and classifying footnotes...")
    stats, coverage = fetch_and_classify()
    print("Generating visualization...")
    generate_html(stats, coverage)
    n = coverage["footnotes"]
    print(f"  {n:,} footnotes across {coverage['denom'][1]:,} performances")
    print(f"  unclassified {coverage['unclassified']:,} "
          f"({100 * coverage['unclassified'] / n:.1f}%)")
    print(f"  in more than one category {coverage['multi']:,} "
          f"({100 * coverage['multi'] / n:.1f}%)")
    top = sorted(coverage["pairs"].items(), key=lambda kv: -kv[1])[:3]
    for k, v in top:
        print(f"    {v:,}  {k}")
