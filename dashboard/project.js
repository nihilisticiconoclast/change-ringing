// Page 3: the project itself. Roadmap, predictions, commits, and figures the docs state.
(() => {
  const CR = window.CR;
  const STATES = ['Open', 'Blocked', 'Held', 'Done', 'Superseded'];
  const VERDICTS = [
    { name: 'Held', slot: 4 },
    { name: 'Wrong in size', slot: 5 },
    { name: 'Wrong', slot: 6 },
    { name: 'Unresolved', slot: null },
  ];
  const WHO = ['Claude Code', 'Gemini', 'Mistral Vibe', 'James'];

  dash.calc('roadmap_states', {
    inputs: ['roadmap'],
    title: 'Roadmap items by state',
    description: 'Counts the roadmap items in each state.',
    fn: (roadmap) => ['Open', 'Blocked', 'Held', 'Done', 'Superseded'].map((state) => ({
      state,
      items: roadmap.filter((r) => r.state === state).length,
    })),
  });

  dash.calc('verdict_tally', {
    inputs: ['hypotheses'],
    title: 'Verdicts on predictions',
    description: 'Counts the hypotheses under each verdict, out of all of them.',
    fn: (hypotheses) => ['Held', 'Wrong in size', 'Wrong', 'Unresolved'].map((verdict) => ({
      verdict,
      entries: hypotheses.filter((h) => h.verdict === verdict).length,
      of: hypotheses.length,
    })),
  });

  dash.calc('doc_drift', {
    inputs: ['doc_claims'],
    title: 'Doc figures that drifted',
    description: 'Counts the recounted doc figures that no longer match the repo.',
    fn: (doc_claims) => [{
      drifted: doc_claims.filter((c) => c.verdict === 'Drifted').length,
      checked: doc_claims.length,
    }],
  });

  dash.calc('commits_by_contributor', {
    inputs: ['commits_daily'],
    title: 'Commits by contributor',
    description: 'Adds up each contributor’s daily commits.',
    fn: (commits_daily) => {
      const totals = {};
      for (const r of commits_daily) totals[r.contributor] = (totals[r.contributor] || 0) + r.commits;
      return Object.keys(totals).map((contributor) => ({ contributor, commits: totals[contributor] }));
    },
  });

  const whoColor = (w) => dash.colors[Math.max(0, WHO.indexOf(w))];
  const verdictColor = (v) => {
    const s = VERDICTS.find((x) => x.name === v);
    return s && s.slot != null ? dash.colors[s.slot] : 'var(--cds-chart-muted)';
  };
  const sorts = {
    roadmap: { field: 'state', dir: 1, then: (a, b) => a.num - b.num },
    hypotheses: { field: 'id', dir: 1 },
    claims: { field: 'verdict', dir: -1, then: (a, b) => a.where.localeCompare(b.where, 'en', { numeric: true }) },
  };
  const wired = new WeakSet();

  function wire(root) {
    if (wired.has(root)) return;
    wired.add(root);
    const redraw = () => draw(root);
    root.querySelector('#roadmap-search').addEventListener('input', redraw);
    CR.sortable(root.querySelector('#table-roadmap'), sorts.roadmap, redraw);
    CR.sortable(root.querySelector('#table-hypotheses'), sorts.hypotheses, redraw);
    CR.sortable(root.querySelector('#table-claims'), sorts.claims, redraw);
  }

  function draw(root) {
    wire(root);
    drawTakeaway(root);
    drawTiles(root);
    drawCommits(root);
    drawRoadmap(root);
    drawVerdicts(root);
    drawHypotheses(root);
    drawClaims(root);
  }

  function drawTakeaway(root) {
    const p = root.querySelector('#project-takeaway');
    const st = CR.state('roadmap_states', 'verdict_tally', 'doc_drift');
    if (st === 'error') {
      p.replaceChildren();
      return;
    }
    if (st !== 'ok') return;
    const states = new Map(CR.rows('roadmap_states').map((r) => [r.state, r.items]));
    const held = CR.rows('verdict_tally').find((r) => r.verdict === 'Held');
    const drift = CR.rows('doc_drift')[0];
    if (!held || !drift) return;
    const s = (state) => ({ text: CR.fmt.n(states.get(state)), source: 'roadmap_states', field: 'items', where: { state } });
    CR.sentence(p, [
      s('Open'), ' roadmap items are open, ', s('Blocked'), ' blocked and ', s('Held'), ' held; ', s('Done'), ' are done. ',
      { text: CR.fmt.n(held.entries), source: 'verdict_tally', field: 'entries', where: { verdict: 'Held' } }, ' of ',
      { text: CR.fmt.n(held.of), source: 'verdict_tally', field: 'of', where: { verdict: 'Held' } }, ' written predictions held. ',
      { text: CR.fmt.n(drift.drifted), source: 'doc_drift', field: 'drifted', where: 0 }, ' of the ',
      { text: CR.fmt.n(drift.checked), source: 'doc_drift', field: 'checked', where: 0 }, ' doc figures recounted here no longer match the repo.',
    ]);
  }

  function drawTiles(root) {
    const rs = CR.state('roadmap_states');
    const states = new Map(CR.rows('roadmap_states').map((r) => [r.state, r.items]));
    if (rs === 'ok') {
      root.querySelectorAll('#project-tiles [data-source="roadmap_states"]').forEach((el) => {
        const state = new URLSearchParams(el.getAttribute('data-where') || '').get('state');
        if (states.has(state)) CR.put(el, CR.fmt.n(states.get(state)));
      });
    }
    CR.settle(root.querySelectorAll('#project-tiles [data-source="roadmap_states"]'), rs);

    const vs = CR.state('verdict_tally');
    const held = CR.rows('verdict_tally').find((r) => r.verdict === 'Held');
    const tHeld = root.querySelector('#tile-held');
    if (vs === 'ok' && held) {
      CR.put(tHeld.querySelector('[data-field="entries"]'), CR.fmt.n(held.entries));
      CR.put(tHeld.querySelector('[data-field="of"]'), CR.fmt.n(held.of));
    }
    CR.settle(tHeld.querySelectorAll('[data-source]'), vs);

    const cs = CR.state('doc_claims');
    const tests = CR.rows('doc_claims').find((r) => r.key === 'tests-readme');
    const tTests = root.querySelector('#tile-tests');
    if (cs === 'ok' && tests) {
      CR.put(tTests.querySelector('[data-field="counted"]'), CR.fmt.n(tests.counted));
      CR.put(tTests.querySelector('[data-field="stated"]'), CR.fmt.n(tests.stated));
    }
    CR.settle(tTests.querySelectorAll('[data-source]'), cs);

    const ss = CR.state('snapshot');
    const snap = CR.rows('snapshot')[0];
    const tCommits = root.querySelector('#tile-commits');
    if (ss === 'ok' && snap) {
      CR.put(tCommits.querySelector('[data-field="commits"]'), CR.fmt.n(snap.commits));
      CR.put(tCommits.querySelector('[data-field="commit_date"]'), CR.fmt.day(snap.commit_date));
    }
    CR.settle(tCommits.querySelectorAll('[data-source]'), ss);
  }

  function drawCommits(root) {
    const box = root.querySelector('#chart-commits');
    const legend = root.querySelector('#commits-legend');
    const totals = new Map(CR.rows('commits_by_contributor').map((r) => [r.contributor, r.commits]));
    CR.legend(legend, WHO.map((w) => ({
      name: w,
      color: whoColor(w),
      value: totals.has(w) ? CR.fmt.n(totals.get(w)) : null,
    })));
    if (!CR.prep(box, CR.state('commits_daily'))) return;
    const rows = CR.rows('commits_daily');
    if (!rows.length) return;
    const first = d3.min(rows, (r) => r.day);
    const last = d3.max(rows, (r) => r.day);
    const days = d3.utcDay.range(new Date(first + 'T00:00:00Z'), d3.utcDay.offset(new Date(last + 'T00:00:00Z'), 1))
      .map((d) => d3.utcFormat('%Y-%m-%d')(d));
    const by = d3.group(rows, (r) => r.day);
    CR.stack(box, {
      label: 'Commits by day and contributor',
      cats: days,
      keys: WHO,
      color: whoColor,
      height: 220,
      pad: 0.25,
      values: (day) => {
        const o = {};
        for (const r of by.get(day) || []) o[r.contributor] = r.commits;
        return o;
      },
      xLabels: (svg, x, yPos) => {
        const labelW = CR.textWidth(svg, ['30 Sep']) + 10;
        const every = Math.max(7, Math.ceil(labelW / x.step() / 7) * 7);
        const g = svg.append('g').attr('class', 'cr-tick');
        days.forEach((d, i) => {
          if (i % every) return;
          g.append('text').attr('x', x(d) + x.bandwidth() / 2).attr('y', yPos).attr('text-anchor', 'middle').text(CR.fmt.dayShort(d));
        });
      },
      tip: (d, total) => ({
        head: CR.fmt.day(d.cat),
        lines: total
          ? WHO.filter((w) => d[w]).map((w) => ({ name: w, value: CR.fmt.n(d[w]), color: whoColor(w) })).concat(
            [{ name: 'Total', value: CR.fmt.n(total) }])
          : [{ name: 'No commits', value: '' }],
      }),
    });
  }

  function drawRoadmap(root) {
    const table = root.querySelector('#table-roadmap');
    const st = CR.state('roadmap');
    if (st !== 'ok') {
      CR.tableState(table, st);
      return;
    }
    CR.table(table, {
      rows: CR.rows('roadmap'),
      rowKey: 'id',
      sort: sorts.roadmap,
      search: root.querySelector('#roadmap-search'),
      columns: [
        { field: 'id', sortVal: (r) => r.num },
        { field: 'title' },
        { field: 'type' },
        { field: 'owner' },
        { field: 'state', sortVal: (r) => STATES.indexOf(r.state) },
      ],
    });
  }

  function drawVerdicts(root) {
    const box = root.querySelector('#chart-verdicts');
    if (!CR.prep(box, CR.state('verdict_tally'))) return;
    const rows = CR.rows('verdict_tally').filter((r) => r.entries > 0);
    const total = d3.sum(rows, (r) => r.entries) || 1;
    box.replaceChildren();
    const tip = CR.tip(box);
    const bar = document.createElement('div');
    bar.className = 'cr-verdict-bar';
    for (const r of rows) {
      const seg = document.createElement('div');
      seg.className = 'cr-verdict-seg';
      seg.style.flex = `${r.entries} 1 0`;
      seg.style.background = verdictColor(r.verdict);
      seg.addEventListener('pointermove', (ev) => {
        const b = box.getBoundingClientRect();
        tip.show(r.verdict, [
          { name: 'Entries', value: CR.fmt.n(r.entries) },
          { name: 'Share', value: CR.fmt.pct(r.entries / total) },
        ], ev.clientX - b.left, ev.clientY - b.top);
      });
      seg.addEventListener('pointerleave', () => tip.hide());
      bar.append(seg);
    }
    const legend = document.createElement('div');
    legend.className = 'cr-legend';
    CR.legend(legend, rows.map((r) => ({ name: r.verdict, color: verdictColor(r.verdict), value: CR.fmt.n(r.entries) })));
    box.append(bar, legend);
  }

  function drawHypotheses(root) {
    const table = root.querySelector('#table-hypotheses');
    const st = CR.state('hypotheses');
    if (st !== 'ok') {
      CR.tableState(table, st);
      return;
    }
    CR.table(table, {
      rows: CR.rows('hypotheses'),
      rowKey: 'id',
      sort: sorts.hypotheses,
      columns: [
        { field: 'id', sortVal: (r) => r.num },
        { field: 'claim' },
        { field: 'section' },
        { field: 'verdict' },
      ],
    });
  }

  function drawClaims(root) {
    const table = root.querySelector('#table-claims');
    const st = CR.state('doc_claims');
    if (st !== 'ok') {
      CR.tableState(table, st);
      return;
    }
    const fmtVal = (v, r) => (r.unit === 'share' ? CR.fmt.pct(v) : CR.fmt.n(v));
    CR.table(table, {
      rows: CR.rows('doc_claims'),
      rowKey: 'key',
      sort: sorts.claims,
      columns: [
        { field: 'where' },
        { field: 'claim' },
        { field: 'stated', fmt: fmtVal },
        { field: 'counted', fmt: fmtVal },
        { field: 'verdict' },
        { field: 'how' },
      ],
    });
  }

  CR.pages.project = { draw };
})();
