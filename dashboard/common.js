// Shared helpers for the three pages. Everything the pages share hangs off window.CR.
(() => {
  const CR = (window.CR = window.CR || {});
  CR.pages = CR.pages || {};

  // ---------------------------------------------------------------- formats
  const comma = d3.format(',');
  const pct1 = d3.format('.1%');
  const pct0 = d3.format('.0%');
  const siTick = d3.format('~s');
  CR.fmt = {
    n: (v) => (v == null ? '—' : comma(v)),
    pct: (v) => (v == null ? '—' : pct1(v)),
    pct0: (v) => (v == null ? '—' : pct0(v)),
    change: (v) => {
      if (v == null) return '';
      if (v === 0) return '0.0%';
      return (v > 0 ? '+' : '−') + pct1(Math.abs(v));
    },
    tick: (v) => (Math.abs(v) >= 1000 ? siTick(v) : comma(v)),
    day: (s) => d3.utcFormat('%-d %b %Y')(new Date(s + 'T00:00:00Z')),
    dayShort: (s) => d3.utcFormat('%-d %b')(new Date(s + 'T00:00:00Z')),
    month: (s) => d3.utcFormat('%b %Y')(new Date(s + '-01T00:00:00Z')),
  };

  // ---------------------------------------------------------------- marks
  const enc = (s) => String(s).replace(/%/g, '%25').replace(/&/g, '%26').replace(/=/g, '%3D');
  CR.where = (obj) => Object.entries(obj).map(([k, v]) => enc(k) + '=' + enc(v)).join('&');

  CR.mark = (el, source, field, where) => {
    if (!el) return;
    el.setAttribute('data-source', source);
    if (field) el.setAttribute('data-field', field);
    else el.removeAttribute('data-field');
    el.removeAttribute('data-where');
    el.removeAttribute('data-row');
    if (typeof where === 'number') el.setAttribute('data-row', String(where));
    else if (where) el.setAttribute('data-where', CR.where(where));
  };

  // Set an element's text (and, given a source, its mark) and drop its skeleton.
  CR.put = (el, text, source, field, where) => {
    if (!el) return;
    if (source) CR.mark(el, source, field, where);
    el.textContent = text;
    el.classList.remove('dash-skeleton');
  };

  // A sentence of plain text and marked figures.
  CR.sentence = (p, parts, source, where) => {
    p.replaceChildren(...parts.map((x) => {
      if (typeof x === 'string') return document.createTextNode(x);
      const s = document.createElement('span');
      s.className = 'cr-fig';
      CR.mark(s, x.source || source, x.field, x.where !== undefined ? x.where : where);
      s.textContent = x.text;
      return s;
    }));
  };

  // ---------------------------------------------------------------- data
  const BAD = new Set(['error', 'declined', 'missing', 'connect', 'reauth', 'absent']);
  CR.state = (...ids) => {
    const all = ids.map((id) => dash.data(id));
    if (all.some((d) => BAD.has(d.status))) return 'error';
    return all.every((d) => d.status === 'ok') ? 'ok' : 'loading';
  };
  CR.rows = (id) => {
    const d = dash.data(id);
    return d.status === 'ok' && Array.isArray(d.data) ? d.data : [];
  };

  // A chart box: true when there is data to draw; otherwise shows loading or failure.
  CR.prep = (box, state) => {
    if (!box) return false;
    if (state === 'ok') {
      box.classList.remove('dash-skeleton');
      return true;
    }
    if (state === 'error') {
      box.classList.remove('dash-skeleton');
      const f = document.createElement('div');
      f.className = 'cr-failed';
      f.textContent = 'Failed to load';
      box.replaceChildren(f);
      return false;
    }
    if (!box.firstElementChild) box.classList.add('dash-skeleton');
    return false;
  };

  // Text marks waiting on a source: on failure, drop the skeleton and leave the dash.
  CR.settle = (els, state) => {
    if (state !== 'error') return;
    for (const el of els) if (el) el.classList.remove('dash-skeleton');
  };

  // ---------------------------------------------------------------- colour
  // Colour follows the entity: each setting keeps its slot whatever is filtered.
  CR.SETTING_SLOT = { tower: 0, hand: 1, virtual: 2, all: 3 };
  CR.settingColor = (s) => dash.colors[CR.SETTING_SLOT[s] ?? 3];
  CR.computed = (color) => {
    const probe = document.createElement('span');
    probe.style.color = color;
    probe.style.display = 'none';
    document.getElementById('cr').append(probe);
    const c = getComputedStyle(probe).color;
    probe.remove();
    return c;
  };

  CR.legend = (el, items) => {
    if (!el) return;
    el.replaceChildren(...items.map((it) => {
      const s = document.createElement('span');
      s.className = 'cr-li';
      const sw = document.createElement('span');
      sw.className = 'cr-sw';
      sw.style.background = it.color;
      const t = document.createElement('span');
      t.textContent = it.name;
      s.append(sw, t);
      if (it.value != null) {
        const v = document.createElement('span');
        v.className = 'cr-li-val';
        v.textContent = it.value;
        s.append(v);
      }
      return s;
    }));
  };

  // ---------------------------------------------------------------- tooltip
  CR.tip = (box) => {
    let el = box.querySelector(':scope > .cr-tip');
    if (!el) {
      el = document.createElement('div');
      el.className = 'cr-tip';
      el.hidden = true;
      box.append(el);
    }
    return {
      show(head, lines, x, y) {
        el.replaceChildren();
        const h = document.createElement('div');
        h.className = 'cr-tip-head';
        h.textContent = head;
        el.append(h);
        for (const l of lines) {
          const row = document.createElement('div');
          row.className = 'cr-tip-row';
          if (l.color) {
            const sw = document.createElement('span');
            sw.className = 'cr-sw';
            sw.style.background = l.color;
            row.append(sw);
          }
          const name = document.createElement('span');
          name.textContent = l.name;
          const val = document.createElement('span');
          val.className = 'cr-tip-val';
          val.textContent = l.value;
          row.append(name, val);
          el.append(row);
        }
        el.hidden = false;
        const bw = box.clientWidth;
        const tw = el.offsetWidth;
        const th = el.offsetHeight;
        let left = x + 14;
        if (left + tw > bw) left = Math.max(0, x - tw - 14);
        let top = y - th - 10;
        if (top < 0) top = y + 14;
        el.style.left = left + 'px';
        el.style.top = top + 'px';
      },
      hide() {
        el.hidden = true;
      },
    };
  };

  // ---------------------------------------------------------------- svg basics
  CR.svg = (box, w, h) => d3.select(box).append('svg')
    .attr('class', 'cr-svg')
    .attr('width', '100%')
    .attr('viewBox', `0 0 ${w} ${h}`)
    .attr('role', 'img');

  // Width of the widest label as drawn, for margins.
  CR.textWidth = (svg, texts) => {
    const g = svg.append('g').attr('class', 'cr-tick');
    let w = 0;
    for (const t of texts) w = Math.max(w, g.append('text').text(t).node().getComputedTextLength());
    g.remove();
    return w;
  };

  CR.yGrid = (svg, y, ticks, x0, x1, fmt = CR.fmt.tick) => {
    const g = svg.append('g');
    g.selectAll('line').data(ticks).join('line')
      .attr('class', (t) => (t === 0 ? 'cr-axisline' : 'cr-gridline'))
      .attr('x1', x0).attr('x2', x1)
      .attr('y1', (t) => Math.round(y(t)) + 0.5).attr('y2', (t) => Math.round(y(t)) + 0.5);
    g.selectAll('text').data(ticks).join('text')
      .attr('class', 'cr-tick')
      .attr('x', x0 - 6).attr('y', (t) => y(t)).attr('dy', '0.32em').attr('text-anchor', 'end')
      .text(fmt);
    return g;
  };

  // Year labels under a band or point scale, shortened or thinned so they never meet.
  CR.xYears = (svg, x, years, yPos) => {
    const step = x.step();
    const full = CR.textWidth(svg, ['2024']) + 6;
    const short = step < full;
    const shortW = CR.textWidth(svg, ['’24']) + 6;
    const every = Math.max(1, Math.ceil((short ? shortW : full) / step));
    const g = svg.append('g').attr('class', 'cr-tick');
    years.forEach((yy, i) => {
      if (i % every) return;
      g.append('text')
        .attr('x', x(yy) + x.bandwidth() / 2).attr('y', yPos).attr('text-anchor', 'middle')
        .text(short ? '’' + yy.slice(2) : yy);
    });
  };

  const barPath = (x, y, w, h, r) => {
    if (!(h > 0) || !(w > 0)) return '';
    r = Math.max(0, Math.min(r, w / 2, h));
    return `M${x},${y + h}V${y + r}Q${x},${y} ${x + r},${y}H${x + w - r}Q${x + w},${y} ${x + w},${y + r}V${y + h}Z`;
  };

  // ---------------------------------------------------------------- sparkline
  CR.spark = (box, rows, field, selected, color) => {
    box.replaceChildren();
    const W = Math.max(box.clientWidth, 80);
    const H = 30;
    const svg = CR.svg(box, W, H).attr('aria-hidden', 'true');
    const sorted = rows.slice().sort((a, b) => d3.ascending(a.year, b.year));
    const x = d3.scalePoint(sorted.map((r) => r.year), [3, W - 3]);
    const y = d3.scaleLinear([0, d3.max(sorted, (r) => r[field]) || 1], [H - 3, 3]);
    svg.append('path').attr('class', 'cr-spark-line').style('stroke', color)
      .attr('d', d3.line().x((r) => x(r.year)).y((r) => y(r[field] ?? 0))(sorted));
    const s = sorted.find((r) => r.year === selected);
    if (s) svg.append('circle').attr('cx', x(s.year)).attr('cy', y(s[field] ?? 0)).attr('r', 3).style('fill', color);
  };

  // ---------------------------------------------------------------- year bars
  // One measure by year: the selected year in colour, the rest muted, its value labelled.
  CR.yearBars = (box, { rows, field, selected, color, name }) => {
    box.replaceChildren();
    const W = Math.max(box.clientWidth, 220);
    const H = 190;
    const mt = 18;
    const mb = 24;
    const svg = CR.svg(box, W, H).attr('aria-label', name + ' by year');
    const y = d3.scaleLinear([0, d3.max(rows, (d) => d[field]) || 1], [H - mb, mt]).nice();
    const ticks = y.ticks(3);
    const ml = Math.ceil(CR.textWidth(svg, ticks.map(CR.fmt.tick))) + 10;
    const x = d3.scaleBand(rows.map((d) => d.year), [ml, W - 2]).paddingInner(0.3).paddingOuter(0.1);
    const bw = x.bandwidth();
    CR.yGrid(svg, y, ticks, ml, W - 2);
    svg.append('g').selectAll('path').data(rows).join('path')
      .attr('d', (d) => barPath(x(d.year), y(d[field] || 0), bw, y(0) - y(d[field] || 0), Math.min(4, bw / 2)))
      .style('fill', (d) => (d.year === selected ? color : 'var(--cds-chart-muted)'));
    const sel = rows.find((d) => d.year === selected);
    if (sel) {
      const label = CR.fmt.n(sel[field]);
      const lw = CR.textWidth(svg, [label]);
      const cx = Math.min(Math.max(x(sel.year) + bw / 2, ml + lw / 2), W - 2 - lw / 2);
      svg.append('text').attr('class', 'cr-valuelabel').attr('text-anchor', 'middle')
        .attr('x', cx).attr('y', Math.max(y(sel[field] || 0) - 6, 11)).text(label);
    }
    CR.xYears(svg, x, rows.map((d) => d.year), H - 6);
    const tip = CR.tip(box);
    svg.append('g').selectAll('rect').data(rows).join('rect').attr('class', 'cr-overlay')
      .attr('x', (d) => x(d.year) - (x.step() - bw) / 2).attr('y', mt)
      .attr('width', x.step()).attr('height', H - mb - mt)
      .on('pointerenter pointermove', (ev, d) => {
        const [px, py] = d3.pointer(ev, box);
        const lines = [{ name, value: CR.fmt.n(d[field]) }];
        if (d[field + '_change'] != null) lines.push({ name: 'Change on the year before', value: CR.fmt.change(d[field + '_change']) });
        tip.show(d.year, lines, px, py);
      })
      .on('pointerleave', () => tip.hide());
  };

  // ---------------------------------------------------------------- stacked bars
  // Categories along x, series stacked bottom-up in the order given; optionally 100%.
  CR.stack = (box, o) => {
    box.replaceChildren();
    const W = Math.max(box.clientWidth, 260);
    const H = o.height || 240;
    const mt = 10;
    const mb = 26;
    const svg = CR.svg(box, W, H).attr('aria-label', o.label || '');
    const data = o.cats.map((c) => ({ cat: c, ...o.values(c) }));
    const totals = data.map((d) => d3.sum(o.keys, (k) => d[k] || 0));
    const y = o.normalize
      ? d3.scaleLinear([0, 1], [H - mb, mt])
      : d3.scaleLinear([0, d3.max(totals) || 1], [H - mb, mt]).nice();
    const ticks = o.normalize ? [0, 0.5, 1] : y.ticks(4);
    const tickFmt = o.normalize ? CR.fmt.pct0 : CR.fmt.tick;
    const ml = Math.ceil(CR.textWidth(svg, ticks.map(tickFmt))) + 10;
    const x = d3.scaleBand(o.cats, [ml, W - 2]).paddingInner(o.pad ?? 0.2);
    const bw = x.bandwidth();
    const half = (x.step() - bw) / 2;
    if (o.band && o.band.length) {
      const a = x(o.band[0]) - half;
      const b = x(o.band[o.band.length - 1]) + bw + half;
      svg.append('rect').attr('class', 'cr-band').attr('x', a).attr('y', mt).attr('width', b - a).attr('height', H - mb - mt);
    }
    CR.yGrid(svg, y, ticks, ml, W - 2, tickFmt);
    const g = svg.append('g');
    data.forEach((d, i) => {
      const tot = totals[i];
      if (!tot) return;
      let acc = 0;
      o.keys.forEach((k, j) => {
        const v = d[k] || 0;
        if (!v) return;
        const v0 = o.normalize ? acc / tot : acc;
        acc += v;
        const v1 = o.normalize ? acc / tot : acc;
        const top = y(v1);
        const bot = y(v0);
        const gap = j > 0 && bot - top > 2 ? 1 : 0;
        const h = bot - top - gap;
        if (h <= 0) return;
        g.append('rect').attr('x', x(d.cat)).attr('y', top).attr('width', bw).attr('height', h).style('fill', o.color(k));
      });
    });
    if (o.xLabels) o.xLabels(svg, x, H - 8);
    const tip = CR.tip(box);
    const hover = svg.append('rect').attr('class', 'cr-hover')
      .attr('y', mt).attr('height', H - mb - mt).attr('width', x.step()).attr('visibility', 'hidden');
    svg.append('rect').attr('class', 'cr-overlay')
      .attr('x', ml).attr('y', mt).attr('width', Math.max(0, W - 2 - ml)).attr('height', H - mb - mt)
      .on('pointermove', (ev) => {
        const [mx] = d3.pointer(ev);
        const i = Math.max(0, Math.min(data.length - 1, Math.round((mx - ml - bw / 2) / x.step())));
        const d = data[i];
        hover.attr('x', x(d.cat) - half).attr('visibility', 'visible');
        const t = o.tip(d, totals[i]);
        const [px, py] = d3.pointer(ev, box);
        tip.show(t.head, t.lines, px, py);
      })
      .on('pointerleave', () => {
        hover.attr('visibility', 'hidden');
        tip.hide();
      });
  };

  // ---------------------------------------------------------------- lines by year
  CR.lines = (box, { rows, series, selected }) => {
    box.replaceChildren();
    const W = Math.max(box.clientWidth, 220);
    const H = 200;
    const mt = 12;
    const mb = 24;
    const svg = CR.svg(box, W, H).attr('aria-label', series.map((s) => s.name).join(' and ') + ' by year');
    const years = rows.map((r) => r.year);
    const max = d3.max(rows, (r) => d3.max(series, (s) => r[s.field] || 0)) || 1;
    const y = d3.scaleLinear([0, max], [H - mb, mt]).nice();
    const ticks = y.ticks(3);
    const ml = Math.ceil(CR.textWidth(svg, ticks.map(CR.fmt.tick))) + 10;
    const last = rows[rows.length - 1];
    const ends = series.map((s) => `${s.name} ${CR.fmt.n(last ? last[s.field] : null)}`);
    let mr = Math.ceil(CR.textWidth(svg, ends)) + 12;
    const showEnds = W - ml - mr >= 150;
    if (!showEnds) mr = 6;
    const x = d3.scalePoint(years, [ml, W - mr]).padding(0.3);
    CR.yGrid(svg, y, ticks, ml, W - mr);
    CR.xYears(svg, x, years, H - 6);
    if (years.includes(selected)) {
      svg.append('line').attr('class', 'cr-refline')
        .attr('x1', x(selected)).attr('x2', x(selected)).attr('y1', mt).attr('y2', H - mb);
    }
    for (const s of series) {
      svg.append('path').attr('class', 'cr-line').style('stroke', s.color)
        .attr('d', d3.line().x((r) => x(r.year)).y((r) => y(r[s.field] || 0))(rows));
    }
    if (showEnds && last) {
      const pos = series.map((s, i) => ({ i, y: y(last[s.field] || 0) })).sort((a, b) => a.y - b.y);
      for (let k = 1; k < pos.length; k++) if (pos[k].y - pos[k - 1].y < 14) pos[k].y = pos[k - 1].y + 14;
      for (const p of pos) {
        svg.append('text').attr('x', x(last.year) + 8).attr('y', p.y).attr('dy', '0.32em').text(ends[p.i]);
      }
    }
    const tip = CR.tip(box);
    const rule = svg.append('line').attr('class', 'cr-axisline').attr('y1', mt).attr('y2', H - mb).attr('visibility', 'hidden');
    const dots = series.map((s) => svg.append('circle').attr('r', 4).style('fill', s.color).attr('visibility', 'hidden'));
    svg.append('rect').attr('class', 'cr-overlay')
      .attr('x', ml).attr('y', mt).attr('width', Math.max(0, W - mr - ml)).attr('height', H - mb - mt)
      .on('pointermove', (ev) => {
        const [mx] = d3.pointer(ev);
        let best = 0;
        years.forEach((yy, i) => { if (Math.abs(x(yy) - mx) < Math.abs(x(years[best]) - mx)) best = i; });
        const r = rows[best];
        rule.attr('x1', x(r.year)).attr('x2', x(r.year)).attr('visibility', 'visible');
        series.forEach((s, i) => dots[i].attr('cx', x(r.year)).attr('cy', y(r[s.field] || 0)).attr('visibility', 'visible'));
        const [px, py] = d3.pointer(ev, box);
        tip.show(r.year, series.map((s) => ({ name: s.name, value: CR.fmt.n(r[s.field]), color: s.color })), px, py);
      })
      .on('pointerleave', () => {
        rule.attr('visibility', 'hidden');
        dots.forEach((d) => d.attr('visibility', 'hidden'));
        tip.hide();
      });
  };

  // ---------------------------------------------------------------- horizontal bars (HTML)
  CR.hbars = (box, { items, color, empty }) => {
    box.replaceChildren();
    if (!items.length) {
      const p = document.createElement('p');
      p.className = 'cr-empty-note';
      p.textContent = empty || 'Nothing to show for this selection.';
      box.append(p);
      return;
    }
    const tip = CR.tip(box);
    const list = document.createElement('div');
    list.className = 'cr-hbars';
    const max = d3.max(items, (d) => Math.max(d.value || 0, d.prev || 0)) || 1;
    for (const it of items) {
      const row = document.createElement('div');
      row.className = 'cr-hbar';
      const lab = document.createElement('div');
      lab.className = 'cr-hbar-label';
      lab.textContent = it.label;
      if (it.sub) {
        const sub = document.createElement('span');
        sub.className = 'cr-hbar-sub';
        sub.textContent = it.sub;
        lab.append(sub);
      }
      const track = document.createElement('div');
      track.className = 'cr-hbar-track';
      const bar = document.createElement('div');
      bar.className = 'cr-hbar-fill';
      bar.style.width = (100 * (it.value || 0)) / max + '%';
      bar.style.background = color;
      track.append(bar);
      if (it.prev != null) {
        const pb = document.createElement('div');
        pb.className = 'cr-hbar-prev';
        pb.style.width = (100 * it.prev) / max + '%';
        track.append(pb);
      }
      const val = document.createElement('div');
      val.className = 'cr-hbar-value';
      val.textContent = CR.fmt.n(it.value);
      row.append(lab, track, val);
      row.addEventListener('pointermove', (ev) => {
        const r = box.getBoundingClientRect();
        tip.show(it.label, it.tip || [], ev.clientX - r.left, ev.clientY - r.top);
      });
      row.addEventListener('pointerleave', () => tip.hide());
      list.append(row);
    }
    box.append(list);
  };

  // ---------------------------------------------------------------- tables
  // Rows are written as words only; the <table> carries the mark and each <tr> its key.
  const cmp = (a, b) => {
    if (typeof a === 'number' && typeof b === 'number') return a - b;
    return String(a).localeCompare(String(b), 'en', { numeric: true });
  };
  const sortWired = new WeakSet();

  CR.sortable = (table, state, redraw) => {
    if (!table || sortWired.has(table)) return;
    sortWired.add(table);
    table.querySelectorAll('thead th').forEach((th) => {
      const b = th.querySelector('button');
      if (!b) return;
      b.addEventListener('click', () => {
        const f = th.dataset.field;
        if (state.field === f) state.dir = -state.dir;
        else {
          state.field = f;
          state.dir = th.classList.contains('cr-n') ? -1 : 1;
        }
        redraw();
      });
    });
  };

  CR.table = (table, { rows, columns, sort, search, rowKey }) => {
    const tbody = table.tBodies[0];
    const q = (search && search.value ? search.value : '').trim().toLowerCase();
    let list = rows;
    if (q) list = list.filter((r) => columns.some((c) => String(r[c.field] ?? '').toLowerCase().includes(q)));
    if (sort && sort.field) {
      const col = columns.find((c) => c.field === sort.field);
      const val = (r) => (col && col.sortVal ? col.sortVal(r) : r[sort.field]);
      list = list.slice().sort((a, b) => {
        const va = val(a);
        const vb = val(b);
        if (va == null && vb == null) return 0;
        if (va == null) return 1;
        if (vb == null) return -1;
        return sort.dir * cmp(va, vb) || (sort.then ? sort.then(a, b) : 0);
      });
    }
    const frag = document.createDocumentFragment();
    for (const r of list) {
      const tr = document.createElement('tr');
      tr.dataset.key = r[rowKey];
      for (const c of columns) {
        const td = document.createElement('td');
        if (c.bar && r[c.field] != null) {
          const track = document.createElement('span');
          track.className = 'cr-cellbar';
          const fill = document.createElement('i');
          fill.style.width = (100 * r[c.field]) / c.bar + '%';
          fill.style.background = c.color;
          track.append(fill);
          td.append(track);
        }
        const v = r[c.field];
        td.append(document.createTextNode(c.fmt ? c.fmt(v, r) : v == null || v === '' ? '—' : String(v)));
        tr.append(td);
      }
      frag.append(tr);
    }
    tbody.replaceChildren(frag);
    table.querySelectorAll('thead th').forEach((th) => {
      th.setAttribute('aria-sort', sort && th.dataset.field === sort.field ? (sort.dir > 0 ? 'ascending' : 'descending') : 'none');
    });
    tableNote(table, list.length ? '' : q ? 'No rows match.' : 'Nothing to show for this selection.', false);
  };

  // A line under a table (never a row inside it, so every row stays a citation).
  const tableNote = (table, text, failed) => {
    let p = table.nextElementSibling;
    if (!p || !p.classList.contains('cr-table-note')) {
      p = document.createElement('p');
      p.className = 'cr-table-note';
      table.after(p);
    }
    p.hidden = !text;
    p.textContent = text;
    p.classList.toggle('cr-failed', !!failed);
    p.classList.toggle('cr-empty-note', !failed);
  };

  // A table whose source isn't ready: on failure, say so under the header.
  CR.tableState = (table, state) => {
    if (state !== 'error') return;
    table.tBodies[0].replaceChildren();
    tableNote(table, 'Failed to load', true);
  };
})();
