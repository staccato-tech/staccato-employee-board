/* Staccato Employee Board — static site
 * Data lives in data/employees.json and data/bulletins.json.
 * URL options:  ?tv=1 (kiosk mode, hides controls)   ?interval=20 (seconds per page)
 */
(() => {
  'use strict';

  const params = new URLSearchParams(location.search);
  const TV = params.get('tv') === '1';
  const INTERVAL = Math.max(5, Number(params.get('interval')) || 20) * 1000;
  const VALUE_INTERVAL = 8000;
  const TODAY = new Date();

  const SERVICE = {
    'Army':               { label: 'Army Veteran',         icon: 'i-shield' },
    'Navy':               { label: 'Navy Veteran',         icon: 'i-anchor' },
    'Air Force':          { label: 'Air Force Veteran',    icon: 'i-plane' },
    'Marines':            { label: 'Marine Veteran', icon: 'i-shield' },
    'Coast Guard':        { label: 'Coast Guard Veteran',  icon: 'i-anchor' },
    'Space Force':        { label: 'Space Force Veteran',  icon: 'i-star' },
    'Military':           { label: 'Military Veteran',     icon: 'i-medal' },
    'Law Enforcement':    { label: 'Law Enforcement',      icon: 'i-shield' },
    'Emergency Services': { label: 'Emergency Services',   icon: 'i-medal' },
  };

  const $ = (s, r = document) => r.querySelector(s);
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const icon = id => `<svg><use href="#${id}"/></svg>`;

  if (TV) document.body.classList.add('tv');

  /* ---------- Dates & tenure ---------- */
  const parseDate = s => { if (!s) return null; const [y, m, d] = s.split('-').map(Number); return new Date(y, m - 1, d); };
  function tenure(hire) {
    const h = parseDate(hire); if (!h) return null;
    let months = (TODAY.getFullYear() - h.getFullYear()) * 12 + (TODAY.getMonth() - h.getMonth());
    if (TODAY.getDate() < h.getDate()) months--;
    months = Math.max(0, months);
    return { years: Math.floor(months / 12), months: months % 12, total: months };
  }
  function tenureLabel(t) {
    if (!t) return '';
    if (t.years === 0) return t.months <= 1 ? 'New' : `${t.months} mo`;
    return `${t.years} yr${t.years > 1 ? 's' : ''}`;
  }
  const band = t => !t ? '' : t.years < 1 ? 'new' : t.years >= 10 ? '10' : t.years >= 5 ? '5' : '1';
  const initials = n => n.split(/\s+/).filter(Boolean).map(w => w[0]).slice(0, 2).join('').toUpperCase();

  /* ---------- Card ---------- */
  function cardHTML(e, i) {
    const t = tenure(e.hireDate);
    const svc = e.service && (SERVICE[e.service] || { label: e.service, icon: 'i-medal' });
    const media = e.photo
      ? `<img class="card-photo" src="${esc(e.photo)}" alt="" loading="lazy" onerror="this.replaceWith(Object.assign(document.createElement('div'),{className:'card-mono',innerHTML:'<span>${esc(initials(e.name))}</span>'}))">`
      : `<div class="card-mono"><svg><use href="#i-star"/></svg><span>${esc(initials(e.name))}</span></div>`;
    return `
      <article class="card${e.featured ? ' is-featured' : ''}" style="--i:${i}">
        ${media}
        <div class="badges">
          ${t ? `<span class="badge badge-tenure" data-band="${band(t)}">${esc(tenureLabel(t))}</span>` : ''}
          ${svc ? `<span class="badge badge-service">${icon(svc.icon)}${esc(svc.label)}</span>` : ''}
          ${e.birthday ? `<span class="badge badge-bday">${icon('i-cake')}Happy Birthday</span>` : ''}
        </div>
        <div class="card-body">
          <h3 class="card-name">${esc(e.name)}</h3>
          ${e.title ? `<p class="card-title">${esc(e.title)}</p>` : ''}
          ${e.department ? `<span class="card-dept">${esc(e.department)}</span>` : ''}
        </div>
      </article>`;
  }

  /* ---------- Clock ---------- */
  function tickClock() {
    const d = new Date();
    $('#clock-time').textContent = d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
    $('#clock-date').textContent = d.toLocaleDateString([], { weekday: 'long', month: 'long', day: 'numeric' });
  }
  tickClock(); setInterval(tickClock, 10000);

  /* ---------- Board (rotating mosaic) ---------- */
  let employees = [], queue = [], page = 0, pages = 1, perPage = 10, timer = null, paused = false, progressAnim = null;

  const byNewest = list => list.slice().sort((a, b) => (b.hireDate || '').localeCompare(a.hireDate || ''));
  function shuffle(a) { a = a.slice(); for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; }

  function layout() {
    const mosaic = $('#mosaic');
    const w = mosaic.clientWidth || window.innerWidth;
    const cols = Math.min(7, Math.max(2, Math.round(w / 250)));
    const cardW = (w - (cols - 1) * 14) / cols;
    const idealH = cardW * 1.22;
    const top = mosaic.getBoundingClientRect().top + window.scrollY;
    const avail = window.innerHeight - top - parseInt(getComputedStyle(document.documentElement).getPropertyValue('--ticker-h')) - 44;
    const rows = Math.max(2, Math.round((avail + 14) / (idealH + 14)));
    const fitH = (avail - (rows - 1) * 14) / rows;
    const cardH = Math.round(window.innerWidth > 720 && fitH > idealH * 0.75 ? fitH : idealH);
    mosaic.style.setProperty('--cols', cols);
    mosaic.style.gridAutoRows = cardH + 'px';
    const next = cols * rows;
    if (next !== perPage) { perPage = next; pages = Math.max(1, Math.ceil(queue.length / perPage)); page = Math.min(page, pages - 1); return true; }
    return false;
  }

  function renderPage(animateOut = true) {
    const mosaic = $('#mosaic');
    const draw = () => {
      const slice = queue.slice(page * perPage, page * perPage + perPage);
      mosaic.innerHTML = slice.map(cardHTML).join('');
      $('#page-indicator').textContent = `${page + 1} / ${pages}`;
      restartProgress();
    };
    const old = mosaic.querySelectorAll('.card');
    if (animateOut && old.length && !matchMedia('(prefers-reduced-motion: reduce)').matches) {
      old.forEach(c => c.classList.add('leaving'));
      setTimeout(draw, 450 + Math.min(old.length, 20) * 30);
    } else draw();
  }

  function restartProgress() {
    const bar = $('#progress-bar');
    if (progressAnim) progressAnim.cancel();
    progressAnim = bar.animate([{ width: '0%' }, { width: '100%' }], { duration: INTERVAL, easing: 'linear', fill: 'forwards' });
    if (paused) progressAnim.pause();
  }

  function go(delta) {
    page = (page + delta + pages) % pages;
    renderPage();
    schedule();
  }
  function schedule() { clearInterval(timer); if (!paused) timer = setInterval(() => go(1), INTERVAL); }

  function setPaused(p) {
    paused = p;
    $('#btn-pause').innerHTML = icon(p ? 'i-play' : 'i-pause');
    $('#btn-pause').setAttribute('aria-label', p ? 'Resume rotation' : 'Pause rotation');
    if (progressAnim) p ? progressAnim.pause() : progressAnim.play();
    schedule();
  }

  $('#btn-next').onclick = () => go(1);
  $('#btn-prev').onclick = () => go(-1);
  $('#btn-pause').onclick = () => setPaused(!paused);
  $('#btn-full').onclick = () => document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen?.();
  let resizeT; window.addEventListener('resize', () => { clearTimeout(resizeT); resizeT = setTimeout(() => { if (currentMode() === 'board' && layout()) renderPage(false); }, 200); });

  /* ---------- Rail ---------- */
  function renderMilestones() {
    const month = TODAY.getMonth();
    $('#anniv-month').textContent = TODAY.toLocaleDateString([], { month: 'long' });
    const anniv = employees
      .map(e => ({ e, d: parseDate(e.hireDate) }))
      .filter(x => x.d && x.d.getMonth() === month && x.d.getFullYear() < TODAY.getFullYear())
      .map(x => ({ ...x, yrs: TODAY.getFullYear() - x.d.getFullYear() }))
      .sort((a, b) => b.yrs - a.yrs || a.d.getDate() - b.d.getDate())
      .slice(0, 6);
    $('#anniv-list').innerHTML = anniv.length ? anniv.map(({ e, d, yrs }) => miniRow(e,
      `${d.toLocaleDateString([], { month: 'short', day: 'numeric' })} · ${e.department || e.title}`,
      `${yrs} YR${yrs > 1 ? 'S' : ''}`)).join('') : '<li class="mini-empty">No work anniversaries this month.</li>';

    const cutoff = new Date(TODAY); cutoff.setDate(cutoff.getDate() - 120);
    const fresh = employees.filter(e => { const d = parseDate(e.hireDate); return d && d >= cutoff && d <= TODAY; })
      .sort((a, b) => b.hireDate.localeCompare(a.hireDate)).slice(0, 5);
    $('#new-list').innerHTML = fresh.length ? fresh.map(e => miniRow(e, e.title || e.department,
      parseDate(e.hireDate).toLocaleDateString([], { month: 'short', day: 'numeric' }))).join('') : '<li class="mini-empty">No new hires recently.</li>';
  }
  function miniRow(e, meta, tag) {
    const av = e.photo ? `<img class="mini-av" src="${esc(e.photo)}" alt="" loading="lazy" onerror="this.replaceWith(Object.assign(document.createElement('span'),{className:'mini-av',textContent:'${esc(initials(e.name))}'}))">` : `<span class="mini-av">${esc(initials(e.name))}</span>`;
    return `<li>${av}<div><div class="mini-name">${esc(e.name)}</div><div class="mini-meta">${esc(meta)}</div></div><span class="mini-tag">${esc(tag)}</span></li>`;
  }

  function cleanWP(html) {
    const tpl = document.createElement('template');
    tpl.innerHTML = html.replace(/<!--[\s\S]*?-->/g, '');
    tpl.content.querySelectorAll('script, style, iframe').forEach(n => n.remove());
    tpl.content.querySelectorAll('[style]').forEach(n => n.removeAttribute('style'));
    tpl.content.querySelectorAll('p').forEach(p => { if (!p.textContent.trim() && !p.querySelector('img')) p.remove(); });
    return tpl.innerHTML;
  }

  function renderBulletins(bulletins) {
    const active = bulletins.filter(b => !b.expires || parseDate(b.expires) >= new Date(TODAY.getFullYear(), TODAY.getMonth(), TODAY.getDate()));

    // Core values: any bulletin whose body is a list of <h4>Heading</h4><p>text</p> pairs titled "Core Values"
    const valuesB = active.find(b => /core values/i.test(b.title));
    const values = [];
    if (valuesB) {
      const tpl = document.createElement('template'); tpl.innerHTML = valuesB.html;
      tpl.content.querySelectorAll('h4').forEach(h => values.push({ h: h.textContent.trim(), p: h.nextElementSibling?.textContent.trim() || '' }));
    }
    renderValues(values);

    // Alerts go to the ticker; everything else becomes a rail panel
    const alerts = active.filter(b => b.type === 'alert' && b !== valuesB);
    const panels = active.filter(b => b.type !== 'alert' && b !== valuesB)
      .sort((a, b) => (b.type === 'big') - (a.type === 'big'));
    $('#rail-bulletins').innerHTML = panels.map(b => `
      <section class="panel bulletin type-${esc(b.type)}">
        <h2 class="panel-title">${esc(b.title)}</h2>
        <div class="bulletin-body">${cleanWP(b.html)}</div>
      </section>`).join('');
    $('#rail-bulletins').style.display = panels.length ? 'contents' : 'none';

    const items = alerts.length
      ? alerts.map(b => `<span><b>${esc(b.title)}</b>${esc(stripTags(b.html))}</span>`)
      : values.map(v => `<span><b>${esc(v.h)}</b>${esc(v.p)}</span>`);
    items.push(`<span><b>${employees.length} strong</b>Thank you for everything you do.</span>`);
    const run = $('#ticker-run');
    run.innerHTML = items.join('') + items.join('');  // doubled for a seamless loop
    requestAnimationFrame(() => run.style.setProperty('--dur', Math.max(30, run.scrollWidth / 2 / 60) + 's'));
  }
  const stripTags = h => { const d = document.createElement('div'); d.innerHTML = h.replace(/<!--[\s\S]*?-->/g, ''); return d.textContent.replace(/\s+/g, ' ').trim(); };

  function renderValues(values) {
    const stage = $('#value-stage'), dots = $('#value-dots');
    if (!values.length) { stage.closest('.panel').hidden = true; return; }
    stage.innerHTML = values.map(v => `<div class="value"><h3>${esc(v.h)}</h3><p>${esc(v.p)}</p></div>`).join('');
    dots.innerHTML = values.map(() => '<i></i>').join('');
    let k = 0;
    const show = () => {
      stage.querySelectorAll('.value').forEach((n, i) => n.classList.toggle('on', i === k));
      dots.querySelectorAll('i').forEach((n, i) => n.classList.toggle('on', i === k));
      k = (k + 1) % values.length;
    };
    show(); setInterval(show, VALUE_INTERVAL);
  }

  /* ---------- Directory ---------- */
  function initDirectory() {
    const depts = [...new Set(employees.map(e => e.department).filter(Boolean))].sort();
    $('#dir-dept').innerHTML = `<option value="">All departments</option>` + depts.map(d => `<option>${esc(d)}</option>`).join('');
    ['#dir-search', '#dir-dept', '#dir-sort'].forEach(s => $(s).addEventListener('input', renderDirectory));
  }
  function renderDirectory() {
    const q = $('#dir-search').value.trim().toLowerCase();
    const dept = $('#dir-dept').value;
    const sort = $('#dir-sort').value;
    let list = employees.filter(e => (!dept || e.department === dept) &&
      (!q || e.name.toLowerCase().includes(q) || e.title.toLowerCase().includes(q) || e.department.toLowerCase().includes(q)));
    const last = n => n.split(/\s+/).slice(-1)[0];
    list = list.slice().sort(sort === 'tenure' ? (a, b) => (a.hireDate || '9').localeCompare(b.hireDate || '9')
      : sort === 'newest' ? (a, b) => (b.hireDate || '').localeCompare(a.hireDate || '')
      : (a, b) => a.name.localeCompare(b.name));
    $('#dir-count').textContent = `${list.length} of ${employees.length} teammates`;
    $('#dir-grid').innerHTML = list.map(cardHTML).join('');
  }

  /* ---------- Routing ---------- */
  const currentMode = () => (location.hash === '#directory' && !TV) ? 'directory' : 'board';
  function route() {
    const mode = currentMode();
    $('#view-board').hidden = mode !== 'board';
    $('#view-directory').hidden = mode !== 'directory';
    document.querySelectorAll('.modes a').forEach(a => a.classList.toggle('active', a.dataset.mode === mode));
    if (mode === 'board') { layout(); renderPage(false); schedule(); }
    else { clearInterval(timer); renderDirectory(); }
  }
  window.addEventListener('hashchange', route);

  /* ---------- Boot ---------- */
  Promise.all([
    fetch('data/employees.json').then(r => r.json()),
    fetch('data/bulletins.json').then(r => r.json()).catch(() => []),
  ]).then(([emps, bulletins]) => {
    employees = emps;
    queue = byNewest(employees);  // board order: newest hire first, longest tenure last
    $('#headcount').textContent = employees.length;
    renderMilestones();
    renderBulletins(bulletins);
    initDirectory();
    route();
  }).catch(err => {
    $('#mosaic').innerHTML = `<p class="mini-empty">Couldn't load employee data (${esc(err.message)}). If you opened index.html directly from disk, serve the folder instead — e.g. <code>python3 -m http.server</code>.</p>`;
  });
})();
