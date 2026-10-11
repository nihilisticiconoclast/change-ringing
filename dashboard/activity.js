// Page 1: ringing activity, 2012-24, filtered by setting and year.
(() => {
  const CR = window.CR;
  const SETTINGS = { all: 'All ringing', tower: 'Tower bells', hand: 'Handbells', virtual: 'Virtual' };
  const ADJ = { all: '', tower: 'tower-bell ', hand: 'handbell ', virtual: 'virtual ' };
  const DEFAULTS = { setting: 'all', year: '2024' };
  const STACK = ['tower', 'hand', 'virtual'];
  const TILES = [
    ['tile-performances', 'performances'],
    ['tile-peals', 'peals'],
    ['tile-quarters', 'quarters'],
    ['tile-ringers', 'ringers'],
    ['tile-firsts', 'first_quarters'],
  ];
  const sortMethods = { field: 'performances', dir: -1 };
  const sortTowers = { field: 'performances', dir: -1 };
  const wired = new WeakSet();

  function wire(root) {
    if (wired.has(root)) return;
    wired.add(root);
    const redraw = () => draw(root);
    root.querySelectorAll('[data-setting]').forEach((b) => {
      const sw = document.createElement('span');
      sw.className = 'cr-sw';
      sw.style.background = CR.settingColor(b.dataset.setting);
      b.prepend(sw);
      b.addEventListener('click', () => dash.setParams({ setting: b.dataset.setting }));
    });
    const sel = root.querySelector('#activity-year');
    sel.addEventListener('change', () => {
      if (sel.value) dash.setParams({ year: sel.value });
    });
    root.querySelector('#activity-reset').addEventListener('click', () => dash.resetParams());
    root.querySelector('#methods-search').addEventListener('input', redraw);
    root.querySelector('#towers-search').addEventListener('input', redraw);
    CR.sortable(root.querySelector('#table-methods'), sortMethods, redraw);
    CR.sortable(root.querySelector('#table-towers'), sortTowers, redraw);
  }

  function draw(root) {
    wire(root);
    const st = CR.state('activity_yearly');
    const yearly = CR.rows('activity_yearly');
    const years = Array.from(new Set(yearly.map((r) => r.year).filter((y) => y !== 'all'))).sort().reverse();
    const p = dash.params();
    const setting = Object.prototype.hasOwnProperty.call(SETTINGS, p.setting) ? p.setting : DEFAULTS.setting;
    let year = p.year != null ? String(p.year) : DEFAULTS.year;
    if (years.length && !years.includes(year)) year = years[0];
    const prev = String(Number(year) - 1);
    const hasPrev = years.includes(prev);

    root.querySelectorAll('[data-setting]').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.setting === setting)));
    const sel = root.querySelector('#activity-year');
    if (years.length && sel.options.length !== years.length) sel.replaceChildren(...years.map((y) => new Option(y, y)));
    if (document.activeElement !== sel && sel.options.length) sel.value = year;
    root.querySelector('#activity-reset').hidden = setting === DEFAULTS.setting && year === DEFAULTS.year;

    const ctx = { root, st, yearly, setting, year, prev, hasPrev };
    drawTiles(ctx);
    drawTakeaway(ctx);
    drawMonthly(ctx);
    drawYearBars(ctx);
    drawFirsts(ctx);
    drawStages(ctx);
    drawCounties(ctx);
    drawMethods(ctx);
    drawTowers(ctx);
  }

  function fillTile(tile, { source, field, where, totalWhere, row, total, rows, selected, color, ok, prevLabel }) {
    const v = tile.querySelector('.cr-tile-value');
    const d = tile.querySelector('.cr-delta');
    const vs = tile.querySelector('.cr-vs');
    const t = tile.querySelector('.cr-total');
    CR.mark(v, source, field, where);
    CR.mark(d, source, field + '_change', where);
    CR.mark(t, source, field, totalWhere);
    if (!ok || !row) return;
    CR.put(v, CR.fmt.n(row[field]));
    const ch = row[field + '_change'];
    d.textContent = CR.fmt.change(ch);
    d.className = 'cr-delta' + (ch > 0 ? ' cr-up' : ch < 0 ? ' cr-down' : '');
    vs.textContent = prevLabel ? 'vs ' + prevLabel : 'first year';
    CR.put(t, CR.fmt.n(total ? total[field] : null));
    CR.spark(tile.querySelector('.cr-spark'), rows, field, selected, color);
  }

  function drawTiles({ root, st, yearly, setting, year, prev, hasPrev }) {
    const row = yearly.find((r) => r.year === year && r.setting === setting);
    const total = yearly.find((r) => r.year === 'all' && r.setting === setting);
    const series = yearly.filter((r) => r.setting === setting && r.year !== 'all');
    for (const [id, field] of TILES) {
      const tile = root.querySelector('#' + id);
      fillTile(tile, {
        source: 'activity_yearly', field, where: { year, setting }, totalWhere: { year: 'all', setting },
        row, total, rows: series, selected: year, color: CR.settingColor(setting), ok: st === 'ok',
        prevLabel: hasPrev ? prev : null,
      });
      CR.settle([tile.querySelector('.cr-tile-value')], st);
    }
    const tst = CR.state('towers_yearly');
    const towers = CR.rows('towers_yearly');
    const tile = root.querySelector('#tile-towers');
    fillTile(tile, {
      source: 'towers_yearly', field: 'towers', where: { year }, totalWhere: { year: 'all' },
      row: towers.find((r) => r.year === year), total: towers.find((r) => r.year === 'all'),
      rows: towers.filter((r) => r.year !== 'all'), selected: year, color: CR.settingColor('tower'),
      ok: tst === 'ok', prevLabel: towers.some((r) => r.year === prev) ? prev : null,
    });
    CR.settle([tile.querySelector('.cr-tile-value')], tst);
  }

  function drawTakeaway({ root, st, yearly, setting, year, prev, hasPrev }) {
    const p = root.querySelector('#activity-takeaway');
    if (st === 'error') {
      p.replaceChildren();
      return;
    }
    const r = yearly.find((x) => x.year === year && x.setting === setting);
    if (st !== 'ok' || !r) return;
    const parts = [`In ${year}, BellBoard records `, { text: CR.fmt.n(r.performances), field: 'performances' }, ` ${ADJ[setting]}performances`];
    if (hasPrev && r.performances_change != null) {
      parts.push(', ', { text: CR.fmt.change(r.performances_change), field: 'performances_change' }, ` on ${prev}`);
    }
    if (r.peal_share != null) {
      parts.push('. Of those with a known length, ', { text: CR.fmt.pct(r.peal_share), field: 'peal_share' }, ' were peals.');
    } else {
      parts.push('.');
    }
    CR.sentence(p, parts, 'activity_yearly', { year, setting });
  }

  function drawMonthly({ root, setting, year }) {
    const box = root.querySelector('#chart-monthly');
    const keys = setting === 'all' ? STACK : [setting];
    CR.legend(root.querySelector('#monthly-legend'),
      keys.length > 1 ? keys.map((k) => ({ name: SETTINGS[k], color: CR.settingColor(k) })) : []);
    if (!CR.prep(box, CR.state('activity_monthly'))) return;
    const rows = CR.rows('activity_monthly');
    const by = d3.group(rows, (r) => r.month);
    const months = Array.from(by.keys()).sort();
    const years = Array.from(new Set(months.map((m) => m.slice(0, 4))));
    CR.stack(box, {
      label: 'Performances by month',
      cats: months,
      keys,
      color: (k) => CR.settingColor(k),
      values: (m) => {
        const o = {};
        for (const k of STACK) {
          const r = by.get(m).find((x) => x.setting === k);
          o[k] = r ? r.performances : 0;
        }
        return o;
      },
      band: months.filter((m) => m.startsWith(year)),
      height: 250,
      pad: 0.18,
      xLabels: (svg, x, yPos) => {
        const yearW = x.step() * 12;
        const full = CR.textWidth(svg, ['2024']) + 8;
        const short = yearW < full;
        const every = Math.max(1, Math.ceil((short ? CR.textWidth(svg, ['’24']) + 8 : full) / yearW));
        const g = svg.append('g').attr('class', 'cr-tick');
        years.forEach((yy, i) => {
          if (i % every) return;
          const ms = months.filter((m) => m.startsWith(yy));
          const cx = (x(ms[0]) + x(ms[ms.length - 1]) + x.bandwidth()) / 2;
          g.append('text').attr('x', cx).attr('y', yPos).attr('text-anchor', 'middle').text(short ? '’' + yy.slice(2) : yy);
        });
      },
      tip: (d, total) => {
        const lines = keys.map((k) => ({ name: SETTINGS[k], value: CR.fmt.n(d[k]), color: keys.length > 1 ? CR.settingColor(k) : null }));
        if (keys.length > 1) lines.push({ name: 'Total', value: CR.fmt.n(total) });
        return { head: CR.fmt.month(d.cat), lines };
      },
    });
  }

  function drawYearBars({ root, st, yearly, setting, year }) {
    const rows = yearly.filter((r) => r.setting === setting && r.year !== 'all').sort((a, b) => d3.ascending(a.year, b.year));
    for (const [id, field, name] of [['chart-peals', 'peals', 'Peals'], ['chart-quarters', 'quarters', 'Quarter peals']]) {
      const box = root.querySelector('#' + id);
      if (!CR.prep(box, st)) continue;
      CR.yearBars(box, { rows, field, selected: year, color: CR.settingColor(setting), name });
    }
  }

  function drawFirsts({ root, st, yearly, setting, year }) {
    const box = root.querySelector('#chart-firsts');
    const series = [
      { field: 'first_quarters', name: 'First quarters', color: dash.colors[5] },
      { field: 'first_peals', name: 'First peals', color: dash.colors[4] },
    ];
    CR.legend(root.querySelector('#firsts-legend'), series);
    if (!CR.prep(box, st)) return;
    const rows = yearly.filter((r) => r.setting === setting && r.year !== 'all').sort((a, b) => d3.ascending(a.year, b.year));
    CR.lines(box, { rows, series, selected: year });
  }

  function drawStages({ root, setting, year, prev, hasPrev }) {
    const box = root.querySelector('#chart-stages');
    root.querySelector('#stages-note').textContent = hasPrev
      ? `Performances by stage in ${year}; the thin bar under each is ${prev}.`
      : `Performances by stage in ${year}.`;
    if (!CR.prep(box, CR.state('stage_mix'))) return;
    const rows = CR.rows('stage_mix').filter((r) => r.year === year && r.setting === setting).sort((a, b) => a.order - b.order);
    CR.hbars(box, {
      color: CR.settingColor(setting),
      items: rows.map((r) => ({
        label: r.stage_group,
        value: r.performances,
        prev: hasPrev ? r.performances_prev : null,
        tip: [
          { name: 'Performances', value: CR.fmt.n(r.performances) },
          { name: 'Peals', value: CR.fmt.n(r.peals) },
          { name: 'Quarters', value: CR.fmt.n(r.quarters) },
          { name: 'Share of the year', value: CR.fmt.pct(r.share) },
          ...(hasPrev ? [{ name: prev, value: CR.fmt.n(r.performances_prev) }] : []),
        ],
      })),
    });
  }

  function drawCounties({ root, setting, year }) {
    const box = root.querySelector('#chart-counties');
    if (!CR.prep(box, CR.state('counties'))) return;
    const rows = CR.rows('counties').filter((r) => r.year === year && r.setting === setting).sort((a, b) => a.rank - b.rank);
    CR.hbars(box, {
      color: CR.settingColor(setting),
      empty: 'No performances with a county recorded for this selection.',
      items: rows.map((r) => ({
        label: r.county,
        value: r.performances,
        tip: [
          { name: 'Performances', value: CR.fmt.n(r.performances) },
          { name: 'Share of the year', value: CR.fmt.pct(r.share) },
          ...(r.performances_change != null ? [{ name: 'Change on the year before', value: CR.fmt.change(r.performances_change) }] : []),
        ],
      })),
    });
  }

  function drawMethods({ root, setting, year }) {
    const table = root.querySelector('#table-methods');
    const st = CR.state('top_methods');
    if (st !== 'ok') {
      CR.tableState(table, st);
      return;
    }
    const rows = CR.rows('top_methods').filter((r) => r.year === year && r.setting === setting);
    CR.table(table, {
      rows,
      rowKey: 'key',
      sort: sortMethods,
      search: root.querySelector('#methods-search'),
      columns: [
        { field: 'rank', fmt: CR.fmt.n },
        { field: 'method' },
        { field: 'stage_group' },
        { field: 'performances', fmt: CR.fmt.n, bar: d3.max(rows, (r) => r.performances) || 1, color: CR.settingColor(setting) },
        { field: 'peals', fmt: CR.fmt.n },
        { field: 'quarters', fmt: CR.fmt.n },
        { field: 'performances_prev', fmt: CR.fmt.n },
        { field: 'performances_change', fmt: CR.fmt.change },
      ],
    });
  }

  function drawTowers({ root, year }) {
    const table = root.querySelector('#table-towers');
    const st = CR.state('top_towers');
    if (st !== 'ok') {
      CR.tableState(table, st);
      return;
    }
    const rows = CR.rows('top_towers').filter((r) => r.year === year);
    CR.table(table, {
      rows,
      rowKey: 'key',
      sort: sortTowers,
      search: root.querySelector('#towers-search'),
      columns: [
        { field: 'rank', fmt: CR.fmt.n },
        { field: 'place' },
        { field: 'dedication' },
        { field: 'county' },
        { field: 'performances', fmt: CR.fmt.n, bar: d3.max(rows, (r) => r.performances) || 1, color: CR.settingColor('tower') },
        { field: 'peals', fmt: CR.fmt.n },
        { field: 'quarters', fmt: CR.fmt.n },
        { field: 'performances_change', fmt: CR.fmt.change },
      ],
    });
  }

  CR.pages.activity = { draw };
})();
