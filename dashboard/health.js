// Page 2: corpus health. How complete, how linked, and where the known traps are.
(() => {
  const CR = window.CR;

  dash.calc('years_exact', {
    inputs: ['completeness_by_year'],
    title: 'Years matching BellBoard',
    description: 'Counts the years whose committed performances equal BellBoard’s own search count.',
    fn: (completeness_by_year) => [{
      exact: completeness_by_year.filter((r) => r.gap === 0).length,
      years: completeness_by_year.length,
    }],
  });

  const LENGTH = [
    { key: 'peals', name: 'Peal', slot: 4 },
    { key: 'quarters', name: 'Quarter', slot: 5 },
    { key: 'short', name: 'Shorter', slot: 6 },
    { key: 'unknown_length', name: 'Unknown length', slot: null },
  ];
  const lengthColor = (k) => {
    const s = LENGTH.find((x) => x.key === k).slot;
    return s == null ? 'var(--cds-chart-muted)' : dash.colors[s];
  };
  const sorts = {
    inventory: { field: null, dir: 1 },
    completeness: { field: 'year', dir: 1 },
    linkages: { field: null, dir: 1 },
    hazards: { field: null, dir: 1 },
  };
  const wired = new WeakSet();

  function wire(root) {
    if (wired.has(root)) return;
    wired.add(root);
    const redraw = () => draw(root);
    CR.sortable(root.querySelector('#table-inventory'), sorts.inventory, redraw);
    CR.sortable(root.querySelector('#table-completeness'), sorts.completeness, redraw);
    CR.sortable(root.querySelector('#table-linkages'), sorts.linkages, redraw);
    CR.sortable(root.querySelector('#table-hazards'), sorts.hazards, redraw);
  }

  function draw(root) {
    wire(root);
    drawTakeaway(root);
    drawTiles(root);
    drawTable(root, '#table-inventory', 'corpus_tables', 'key', sorts.inventory, [
      { field: 'corpus' },
      { field: 'table' },
      { field: 'rows', fmt: CR.fmt.n },
      { field: 'basis' },
      { field: 'source' },
    ]);
    drawTable(root, '#table-completeness', 'completeness_by_year', 'year', sorts.completeness, [
      { field: 'year' },
      { field: 'performances', fmt: CR.fmt.n },
      { field: 'ringer_rows', fmt: CR.fmt.n },
      { field: 'footnotes', fmt: CR.fmt.n },
      { field: 'flags', fmt: CR.fmt.n },
      { field: 'bellboard_count', fmt: CR.fmt.n },
      { field: 'status' },
    ]);
    drawCoverage(root);
    drawLengthMix(root);
    drawUnlinked(root);
    drawTable(root, '#table-linkages', 'linkages', 'key', sorts.linkages, [
      { field: 'linkage' },
      { field: 'linked', fmt: CR.fmt.n },
      { field: 'of', fmt: CR.fmt.n },
      { field: 'rate', fmt: CR.fmt.pct, bar: 1, color: dash.colors[0] },
      { field: 'basis' },
      { field: 'note' },
    ]);
    drawTable(root, '#table-hazards', 'hazards', 'key', sorts.hazards, [
      { field: 'hazard' },
      { field: 'rows', fmt: CR.fmt.n },
      { field: 'share', fmt: CR.fmt.pct },
      { field: 'state' },
      { field: 'handling' },
    ]);
  }

  function drawTable(root, sel, source, rowKey, sort, columns) {
    const table = root.querySelector(sel);
    const st = CR.state(source);
    if (st !== 'ok') {
      CR.tableState(table, st);
      return;
    }
    CR.table(table, { rows: CR.rows(source), columns, sort, rowKey });
  }

  function drawTakeaway(root) {
    const p = root.querySelector('#health-takeaway');
    const st = CR.state('completeness_by_year', 'activity_yearly', 'linkages');
    if (st === 'error') {
      p.replaceChildren();
      return;
    }
    if (st !== 'ok') return;
    const short = CR.rows('completeness_by_year').filter((r) => r.gap !== 0);
    const all = CR.rows('activity_yearly').find((r) => r.year === 'all' && r.setting === 'all');
    const method = CR.rows('linkages').find((r) => r.key === 'method');
    if (!all || !method) return;
    const parts = [];
    if (short.length) {
      parts.push('Every year matches BellBoard’s own count except ');
      short.forEach((r, i) => {
        if (i) parts.push(i === short.length - 1 ? ' and ' : ', ');
        parts.push(
          { text: r.year, source: 'completeness_by_year', field: 'year', where: { year: r.year } },
          ', ',
          { text: CR.fmt.n(r.gap), source: 'completeness_by_year', field: 'gap', where: { year: r.year } },
          r.gap === 1 ? ' record short' : ' records short',
        );
      });
      parts.push('. ');
    } else {
      parts.push('Every year matches BellBoard’s own count. ');
    }
    parts.push(
      { text: CR.fmt.pct(all.unknown_share), source: 'activity_yearly', field: 'unknown_share', where: { year: 'all', setting: 'all' } },
      ' of performances can’t be called peal or quarter, and ',
      { text: CR.fmt.pct(method.rate), source: 'linkages', field: 'rate', where: { key: 'method' } },
      ' link to a library method.',
    );
    CR.sentence(p, parts);
  }

  function drawTiles(root) {
    const ex = CR.state('years_exact');
    const exRow = CR.rows('years_exact')[0];
    const n = root.querySelector('#exact-n');
    const of = root.querySelector('#exact-of');
    if (ex === 'ok' && exRow) {
      CR.put(n, CR.fmt.n(exRow.exact));
      CR.put(of, CR.fmt.n(exRow.years));
    }
    CR.settle([n], ex);

    const cov = CR.state('field_coverage');
    const decidable = CR.rows('field_coverage').find((r) => r.year === 'all' && r.field_id === 'decidable');
    const dTile = root.querySelector('#tile-decidable');
    if (cov === 'ok' && decidable) {
      CR.put(dTile.querySelector('.cr-tile-value'), CR.fmt.pct(decidable.share));
      CR.put(dTile.querySelector('.cr-total'), CR.fmt.n(decidable.performances));
    }
    CR.settle([dTile.querySelector('.cr-tile-value')], cov);

    const lk = CR.state('linkages');
    const links = CR.rows('linkages');
    for (const [id, key] of [['#tile-method', 'method'], ['#tile-tower', 'tower'], ['#tile-composer', 'composer']]) {
      const tile = root.querySelector(id);
      const r = links.find((x) => x.key === key);
      if (lk === 'ok' && r) {
        CR.put(tile.querySelector('.cr-tile-value'), CR.fmt.pct(r.rate));
        CR.put(tile.querySelector('.cr-total'), CR.fmt.n(r.linked));
        const t2 = tile.querySelector('.cr-total2');
        if (t2) CR.put(t2, CR.fmt.n(r.of));
      }
      CR.settle([tile.querySelector('.cr-tile-value')], lk);
    }
  }

  function drawCoverage(root) {
    const box = root.querySelector('#chart-coverage');
    if (!CR.prep(box, CR.state('field_coverage'))) return;
    const rows = CR.rows('field_coverage');
    const fields = Array.from(d3.group(rows, (r) => r.field_id), ([id, rs]) => ({ id, name: rs[0].field, order: rs[0].order }))
      .sort((a, b) => a.order - b.order);
    const years = Array.from(new Set(rows.map((r) => r.year))).sort((a, b) => (a === 'all') - (b === 'all') || d3.ascending(a, b));
    const lookup = new Map(rows.map((r) => [r.field_id + '|' + r.year, r]));
    const ramp = d3.interpolateRgb(CR.computed('var(--color-panel)'), CR.computed(dash.colors[0]));
    box.replaceChildren();
    const tip = CR.tip(box);
    const labelW = Math.min(192, Math.max(112, box.clientWidth * 0.26));
    const cellW = (box.clientWidth - labelW) / years.length;
    const showText = cellW >= 36;
    const fullYears = cellW >= 34;
    const grid = document.createElement('div');
    grid.className = 'cr-heat';
    grid.style.gridTemplateColumns = `${labelW}px repeat(${years.length}, minmax(0, 1fr))`;
    grid.append(document.createElement('div'));
    for (const y of years) {
      const h = document.createElement('div');
      h.className = 'cr-heat-col';
      h.textContent = y === 'all' ? 'All' : fullYears ? y : '’' + y.slice(2);
      grid.append(h);
    }
    for (const f of fields) {
      const lab = document.createElement('div');
      lab.className = 'cr-heat-row';
      lab.textContent = f.name;
      grid.append(lab);
      for (const y of years) {
        const r = lookup.get(f.id + '|' + y);
        const share = r && r.share != null ? r.share : 0;
        const c = document.createElement('div');
        c.className = 'cr-heat-cell' + (y === 'all' ? ' cr-heat-all' : '');
        c.style.background = ramp(share);
        c.style.color = share > 0.55 ? 'var(--color-bg)' : 'var(--color-fg)';
        if (showText) c.textContent = CR.fmt.pct0(share);
        c.addEventListener('pointermove', (ev) => {
          const b = box.getBoundingClientRect();
          tip.show(`${f.name} · ${y === 'all' ? '2012–24' : y}`, [
            { name: 'Share', value: CR.fmt.pct(r ? r.share : null) },
            { name: 'Performances with it', value: CR.fmt.n(r ? r.populated : null) },
            { name: 'Performances', value: CR.fmt.n(r ? r.performances : null) },
          ], ev.clientX - b.left, ev.clientY - b.top);
        });
        c.addEventListener('pointerleave', () => tip.hide());
        grid.append(c);
      }
    }
    box.append(grid);
  }

  function drawLengthMix(root) {
    const box = root.querySelector('#chart-lengthmix');
    CR.legend(root.querySelector('#lengthmix-legend'), LENGTH.map((l) => ({ name: l.name, color: lengthColor(l.key) })));
    if (!CR.prep(box, CR.state('activity_yearly'))) return;
    const rows = CR.rows('activity_yearly').filter((r) => r.setting === 'all' && r.year !== 'all').sort((a, b) => d3.ascending(a.year, b.year));
    const by = new Map(rows.map((r) => [r.year, r]));
    const years = rows.map((r) => r.year);
    CR.stack(box, {
      label: 'Performances by length class and year',
      cats: years,
      keys: LENGTH.map((l) => l.key),
      color: lengthColor,
      normalize: true,
      height: 220,
      pad: 0.3,
      values: (y) => {
        const r = by.get(y);
        return Object.fromEntries(LENGTH.map((l) => [l.key, r[l.key]]));
      },
      xLabels: (svg, x, yPos) => CR.xYears(svg, x, years, yPos),
      tip: (d, total) => ({
        head: d.cat,
        lines: LENGTH.map((l) => ({
          name: l.name,
          value: `${CR.fmt.n(d[l.key])} · ${CR.fmt.pct(total ? d[l.key] / total : null)}`,
          color: lengthColor(l.key),
        })),
      }),
    });
  }

  function drawUnlinked(root) {
    const box = root.querySelector('#chart-unlinked');
    if (!CR.prep(box, CR.state('unresolved_methods'))) return;
    const rows = CR.rows('unresolved_methods').slice().sort((a, b) => b.performances - a.performances);
    CR.hbars(box, {
      color: dash.colors[0],
      items: rows.map((r) => ({
        label: r.name,
        sub: r.kind,
        value: r.performances,
        tip: [
          { name: 'Performances', value: CR.fmt.n(r.performances) },
          { name: 'Share of the unlinked', value: CR.fmt.pct(r.share_of_unlinked) },
          { name: 'Share of all performances', value: CR.fmt.pct(r.share_of_all) },
        ],
      })),
    });
  }

  CR.pages.health = { draw };
})();
