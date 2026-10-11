// Tabs, links and the one onData that redraws whatever is showing.
(() => {
  const CR = window.CR;
  const PAGES = ['activity', 'health', 'project'];
  const made = new Set();
  let current = null;

  // Which page holds a name: a page itself, or any id inside one of the templates.
  function pageOf(name) {
    if (!name) return null;
    if (PAGES.includes(name)) return name;
    for (const p of PAGES) {
      const t = document.getElementById('tpl-' + p);
      if (t && t.content.getElementById(name)) return p;
    }
    return null;
  }

  function drawFooter() {
    const st = CR.state('snapshot');
    const s = CR.rows('snapshot')[0];
    const commit = document.getElementById('foot-commit');
    const date = document.getElementById('foot-date');
    if (st === 'ok' && s) {
      CR.put(commit, s.commit);
      CR.put(date, CR.fmt.day(s.commit_date));
    }
    CR.settle([commit, date], st);
  }

  function drawAll() {
    drawFooter();
    if (!current) return;
    const sec = document.getElementById(current);
    if (sec && !sec.hidden && CR.pages[current]) CR.pages[current].draw(sec);
  }

  // A page's HTML lives in a <template> until first shown, so its data loads only then.
  function show(page) {
    if (!PAGES.includes(page)) page = PAGES[0];
    const sec = document.getElementById(page);
    if (!made.has(page)) {
      sec.append(document.getElementById('tpl-' + page).content.cloneNode(true));
      made.add(page);
    }
    for (const p of PAGES) {
      document.getElementById(p).hidden = p !== page;
      const tab = document.getElementById('tab-' + p);
      tab.setAttribute('aria-selected', String(p === page));
      tab.tabIndex = p === page ? 0 : -1;
    }
    current = page;
    drawAll();
  }

  document.querySelectorAll('.cr-tab').forEach((tab, i, tabs) => {
    tab.addEventListener('click', () => {
      show(tab.dataset.page);
      dash.setLink(tab.dataset.page);
    });
    tab.addEventListener('keydown', (ev) => {
      if (ev.key !== 'ArrowRight' && ev.key !== 'ArrowLeft') return;
      ev.preventDefault();
      const next = tabs[(i + (ev.key === 'ArrowRight' ? 1 : tabs.length - 1)) % tabs.length];
      next.focus();
      next.click();
    });
  });

  dash.onData(drawAll);

  const name = location.hash.slice(1);
  show(pageOf(name) || PAGES[0]);
  if (name && !PAGES.includes(name)) {
    const el = document.getElementById(name);
    if (el) el.scrollIntoView();
  }
})();
