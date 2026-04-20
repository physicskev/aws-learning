const API = '';
const PAGE_SIZE = 20;

const state = {
  q: '',
  start: 0,
  sort: 'relevance',
  datePreset: 'all',          // all | 7d | 30d | 90d | custom
  dateFrom: '',
  dateTo: '',
  minTurns: '',
  minDuration: '',            // minutes; converted to seconds for API
  filters: { source: new Set(), project: new Set(), doc_type: new Set(), is_agent: '' },
};

const $ = sel => document.querySelector(sel);
const fmtInt = n => (n ?? 0).toLocaleString();
const fmtHours = secs => {
  if (secs == null) return '';
  const h = secs / 3600;
  return h >= 1 ? `${h.toFixed(1)} h` : `${Math.round(secs / 60)} min`;
};
const fmtDate = d => (d || '').slice(0, 10);

// ============================================================================
// URL <-> state sync
// ============================================================================

function stateToUrl() {
  const p = new URLSearchParams();
  if (state.q) p.set('q', state.q);
  if (state.sort !== 'relevance') p.set('sort', state.sort);
  if (state.datePreset !== 'all') p.set('date', state.datePreset);
  if (state.datePreset === 'custom') {
    if (state.dateFrom) p.set('from', state.dateFrom);
    if (state.dateTo) p.set('to', state.dateTo);
  }
  if (state.minTurns) p.set('min_turns', state.minTurns);
  if (state.minDuration) p.set('min_dur', state.minDuration);
  for (const s of state.filters.source)   p.append('source', s);
  for (const pr of state.filters.project) p.append('project', pr);
  for (const dt of state.filters.doc_type) p.append('doc_type', dt);
  if (state.filters.is_agent) p.set('is_agent', state.filters.is_agent);
  if (state.start) p.set('start', state.start);
  history.replaceState(null, '', p.toString() ? `?${p}` : location.pathname);
}

function urlToState() {
  const p = new URLSearchParams(location.search);
  state.q = p.get('q') || '';
  state.sort = p.get('sort') || (state.q ? 'relevance' : 'started_desc');
  state.datePreset = p.get('date') || 'all';
  state.dateFrom = p.get('from') || '';
  state.dateTo = p.get('to') || '';
  state.minTurns = p.get('min_turns') || '';
  state.minDuration = p.get('min_dur') || '';
  state.filters.source = new Set(p.getAll('source'));
  state.filters.project = new Set(p.getAll('project'));
  state.filters.doc_type = new Set(p.getAll('doc_type'));
  state.filters.is_agent = p.get('is_agent') || '';
  state.start = parseInt(p.get('start') || '0', 10);
}

// ============================================================================
// Building the API URL for the current state
// ============================================================================

function dateRange() {
  if (state.datePreset === '7d')  return ['NOW-7DAYS', 'NOW'];
  if (state.datePreset === '30d') return ['NOW-30DAYS', 'NOW'];
  if (state.datePreset === '90d') return ['NOW-90DAYS', 'NOW'];
  if (state.datePreset === 'custom') {
    const f = state.dateFrom ? `${state.dateFrom}T00:00:00Z` : '';
    const t = state.dateTo   ? `${state.dateTo}T23:59:59Z` : '';
    return [f, t];
  }
  return ['', ''];
}

function buildUrl() {
  const p = new URLSearchParams();
  p.set('q', state.q || '*:*');
  p.set('start', state.start);
  p.set('rows', PAGE_SIZE);
  p.set('sort', state.sort);
  const [f, t] = dateRange();
  if (f) p.set('date_from', f);
  if (t) p.set('date_to', t);
  if (state.minTurns)    p.set('min_turns', state.minTurns);
  if (state.minDuration) p.set('min_duration_seconds', String(parseInt(state.minDuration, 10) * 60));
  for (const s of state.filters.source)    p.append('source', s);
  for (const pr of state.filters.project)  p.append('project', pr);
  for (const dt of state.filters.doc_type) p.append('doc_type', dt);
  if (state.filters.is_agent) p.set('is_agent', state.filters.is_agent);
  return `${API}/api/search?${p}`;
}

// ============================================================================
// Search — monotonic sequence. Only the latest response ever renders.
// ============================================================================

let searchSeq = 0;
async function search() {
  stateToUrl();
  const mySeq = ++searchSeq;
  const url = buildUrl();
  setDebug(`fetching #${mySeq}: ${url.replace(location.origin, '')}`);
  try {
    const r = await fetch(url, { cache: 'no-store' });
    const j = await r.json();
    if (mySeq !== searchSeq) {
      setDebug(`discarded #${mySeq} (superseded by #${searchSeq})`);
      return;
    }
    setDebug(`rendered #${mySeq}: ${j.numFound} hits · url=${url.replace(location.origin, '')}`);
    render(j);
  } catch (e) {
    console.error('search failed', e);
    setDebug(`error on #${mySeq}: ${e.message}`);
  }
}

function setDebug(msg) {
  const d = $('#debug');
  if (d) d.textContent = msg;
}

// ============================================================================
// Render — one j, all sub-areas updated from it
// ============================================================================

function render(j) {
  renderChips();
  renderStats(j);
  renderHistogram(j.date_facets || []);
  renderFacets(j.facets || {});
  renderResults(j);
  renderSuggestion(j.suggestion);
}

// ---- chips ----
function renderChips() {
  const box = $('#chips');
  box.innerHTML = '';
  const add = (label, onRemove) => {
    const c = document.createElement('span');
    c.className = 'chip';
    c.appendChild(document.createTextNode(label));
    const btn = document.createElement('button');
    btn.title = 'Remove';
    btn.textContent = '×';
    btn.addEventListener('click', () => { onRemove(); state.start = 0; search(); });
    c.appendChild(btn);
    box.appendChild(c);
  };
  if (state.q) add(`q: ${state.q}`, () => { state.q = ''; $('#q').value = ''; });
  if (state.datePreset !== 'all') {
    const lbl = state.datePreset === 'custom'
      ? `date: ${state.dateFrom || '…'} → ${state.dateTo || '…'}`
      : `date: last ${state.datePreset}`;
    add(lbl, () => { state.datePreset = 'all'; state.dateFrom = ''; state.dateTo = ''; applyPresetButtons(); $('#custom-dates').classList.add('hidden'); });
  }
  if (state.minTurns)    add(`${state.minTurns}+ turns`, () => { state.minTurns = ''; $('#min-turns').value = ''; });
  if (state.minDuration) {
    const m = parseInt(state.minDuration, 10);
    const label = m >= 60 ? `${(m / 60).toFixed(m % 60 === 0 ? 0 : 1)}h+ duration` : `${m}m+ duration`;
    add(label, () => { state.minDuration = ''; $('#min-duration').value = ''; });
  }
  for (const s of state.filters.source)    add(`source: ${s}`,  () => state.filters.source.delete(s));
  for (const p of state.filters.project)   add(`project: ${p}`, () => state.filters.project.delete(p));
  for (const d of state.filters.doc_type)  add(`type: ${d}`,    () => state.filters.doc_type.delete(d));
  if (state.filters.is_agent) add(`agent: ${state.filters.is_agent}`, () => { state.filters.is_agent = ''; });
}

// ---- stats ----
function renderStats(j) {
  const card = $('#stats');
  card.innerHTML = '';

  const s = j.stats || {};
  const turns = s.user_turns || {};
  const asst  = s.assistant_turns || {};
  const tot   = s.total_turns || {};
  const dur   = s.duration_seconds || {};
  const dates = s.started || {};
  const us = s.user_seconds || {};
  const as_ = s.assistant_seconds || {};
  const idle = s.idle_seconds || {};
  const act = s.active_seconds || {};

  const cap = s._capped_at_seconds;
  const capHours = cap ? (cap / 3600).toFixed(0) : '';
  const capNote = cap ? `capped at ${capHours}h per session` : '';

  // Helpers
  const box = (label, value, sub, variant, tip) => {
    const b = document.createElement('div');
    b.className = 'stat-box' + (variant ? ' variant-' + variant : '');
    if (tip) b.dataset.tip = tip;
    const lbl = document.createElement('div'); lbl.className = 'stat-label'; lbl.textContent = label;
    const val = document.createElement('div'); val.className = 'stat-value'; val.textContent = String(value);
    b.appendChild(lbl); b.appendChild(val);
    if (sub) { const s2 = document.createElement('div'); s2.className = 'stat-sub'; s2.textContent = sub; b.appendChild(s2); }
    return b;
  };
  const section = (label, cls) => {
    const sec = document.createElement('div');
    sec.className = 'stats-section ' + cls;
    const hd = document.createElement('div');
    hd.className = 'section-label';
    hd.textContent = label;
    sec.appendChild(hd);
    const grid = document.createElement('div');
    grid.className = 'section-grid';
    sec.appendChild(grid);
    sec._grid = grid;
    return sec;
  };

  // --- Documents section (left) ---
  const docs = section('Documents', 'docs');
  docs._grid.appendChild(box('Hits', fmtInt(j.numFound), '', null,
    'Number of documents matching the current query and filters.'));
  if (dates.min && dates.max) {
    docs._grid.appendChild(box('Date span',
      `${fmtDate(dates.min)} → ${fmtDate(dates.max)}`, '', null,
      'Earliest and latest "started" timestamp across matching documents.'));
  }
  card.appendChild(docs);

  // --- Activity section (right) ---
  const act_sec = section('Activity', 'activity');
  let any = false;

  if (tot.sum != null && tot.count > 0) {
    act_sec._grid.appendChild(box('Total turns', fmtInt(tot.sum),
      `${fmtInt(turns.sum ?? 0)}u + ${fmtInt(asst.sum ?? 0)}a · avg ${(tot.mean ?? 0).toFixed(1)}`,
      null,
      'Total messages across matching sessions. 1 message = 1 turn (user OR assistant).'));
    any = true;
  }
  if (dur.sum != null && dur.count > 0) {
    const totalHours = (dur.sum / 3600).toFixed(1);
    const sub = [dur.max ? `longest ${fmtHours(dur.max)}` : '', capNote].filter(Boolean).join(' · ');
    act_sec._grid.appendChild(box('Total time', `${totalHours} h`, sub, null,
      `Sum of wall-clock duration (last message − first message) across matching sessions. Each session is capped at ${capHours}h so a session left open overnight doesn't dominate the sum.`));
    any = true;
  }
  if (act.sum != null && act.count > 0) {
    const pct = (n) => act.sum ? `${Math.round((n / act.sum) * 100)}%` : '';
    act_sec._grid.appendChild(box('Active time', `${(act.sum / 3600).toFixed(1)} h`, 'user + agent', 'active',
      `User time + Agent time. The time you were actually engaged with Claude (gaps of 10 min or more count as idle, not active). Each session capped at ${capHours}h.`));
    act_sec._grid.appendChild(box('User time', `${(us.sum / 3600).toFixed(1)} h`, pct(us.sum) + ' of active', 'user',
      `Time between the model responding and your next message — i.e. you reading, thinking, and typing. Each session capped at ${capHours}h.`));
    act_sec._grid.appendChild(box('Agent time', `${(as_.sum / 3600).toFixed(1)} h`, pct(as_.sum) + ' of active', 'agent',
      `Time between your message and the next event — the model thinking, generating, and running tools. Each session capped at ${capHours}h.`));
    if (idle.sum > 0) {
      act_sec._grid.appendChild(box('Idle time', `${(idle.sum / 3600).toFixed(1)} h`, 'gaps >10 min', 'idle',
        `Sum of gaps longer than 10 minutes within sessions. Presumed away-from-keyboard / session left open. Each session capped at ${capHours}h.`));
    }
    any = true;
  }
  if (any) card.appendChild(act_sec);

  card.classList.remove('hidden');
}

// ---- histogram ----
function renderHistogram(buckets) {
  const box = $('#histogram');
  box.innerHTML = '';
  if (!buckets.length) { box.classList.add('hidden'); return; }
  const total = buckets.reduce((a, b) => a + b.count, 0);
  if (total === 0) { box.classList.add('hidden'); return; }
  const max = Math.max(...buckets.map(b => b.count), 1);

  let first = 0, last = buckets.length - 1;
  while (first < last && buckets[first].count === 0) first++;
  while (last > first && buckets[last].count === 0) last--;
  const visible = buckets.slice(first, last + 1);

  box.classList.remove('hidden');
  const lbl = document.createElement('div');
  lbl.className = 'histogram-label';
  lbl.textContent = 'Activity by month · click a bar to filter';
  box.appendChild(lbl);

  const bars = document.createElement('div');
  bars.className = 'histogram-bars';
  const activeFrom = state.datePreset === 'custom' ? state.dateFrom : '';
  for (const b of visible) {
    const ym = (b.value || '').slice(0, 7);
    const isActive = activeFrom && ym === activeFrom.slice(0, 7);
    const bar = document.createElement('div');
    bar.className = 'hbar' + (b.count === 0 ? ' empty' : '') + (isActive ? ' active' : '');
    bar.setAttribute('data-tip', `${ym}: ${b.count}`);
    bar.style.height = `${Math.max(2, (b.count / max) * 100)}%`;
    if (b.count > 0) {
      bar.dataset.ym = ym;
      bar.addEventListener('click', () => drillIntoMonth(ym));
    }
    bars.appendChild(bar);
  }
  box.appendChild(bars);

  const axis = document.createElement('div');
  axis.className = 'histogram-axis';
  const a1 = document.createElement('span'); a1.textContent = (visible[0]?.value || '').slice(0, 7);
  const a2 = document.createElement('span'); a2.textContent = (visible.at(-1)?.value || '').slice(0, 7);
  axis.appendChild(a1); axis.appendChild(a2);
  box.appendChild(axis);
}

function drillIntoMonth(ym) {
  const year = parseInt(ym.slice(0, 4), 10);
  const mon = parseInt(ym.slice(5, 7), 10);
  const nextMon = mon === 12 ? `${year + 1}-01` : `${year}-${String(mon + 1).padStart(2, '0')}`;
  state.datePreset = 'custom';
  state.dateFrom = `${ym}-01`;
  state.dateTo = `${nextMon}-01`;
  $('#date-from').value = state.dateFrom;
  $('#date-to').value = state.dateTo;
  applyPresetButtons();
  $('#custom-dates').classList.remove('hidden');
  state.start = 0;
  search();
}

// ---- suggestion ----
function renderSuggestion(s) {
  const box = $('#didyoumean');
  box.innerHTML = '';
  if (!s || s === state.q) return;
  const a = document.createElement('a');
  a.textContent = s;
  a.addEventListener('click', () => { state.q = s; $('#q').value = s; state.start = 0; search(); });
  box.append(document.createTextNode('Did you mean: '), a);
}

// ---- facets (static DOM + event delegation) ----
const FACET_DEFS = [
  ['doc_type', 'Doc type'],
  ['source',   'Source'],
  ['is_agent', 'Agent'],
  ['project',  'Project'],
];

function renderFacets(facets) {
  const container = $('#facets');
  container.innerHTML = '';
  let any = false;
  for (const [key, label] of FACET_DEFS) {
    const values = facets[key] || [];
    if (!values.length) continue;
    any = true;

    const group = document.createElement('div');
    group.className = 'facet-group';
    const h = document.createElement('h3');
    h.textContent = label;
    group.appendChild(h);

    for (const { value, count } of values.slice(0, 20)) {
      const valStr = String(value);
      const isRadio = key === 'is_agent';
      const selected = isRadio
        ? state.filters.is_agent === valStr
        : state.filters[key].has(valStr);

      const row = document.createElement('div');
      row.className = 'facet-item' + (selected ? ' active' : '');
      row.dataset.facetKey = key;
      row.dataset.facetValue = valStr;
      row.dataset.facetKind = isRadio ? 'radio' : 'check';

      // Purely visual indicator. Click is handled by delegation on #facets.
      const mark = document.createElement('span');
      mark.className = 'facet-mark' + (selected ? ' on' : '') + (isRadio ? ' radio' : '');
      mark.textContent = selected ? '✓' : '';

      const text = document.createElement('span');
      text.className = 'facet-text';
      text.textContent = valStr;

      const cnt = document.createElement('span');
      cnt.className = 'facet-count';
      cnt.textContent = String(count);

      row.appendChild(mark);
      row.appendChild(text);
      row.appendChild(cnt);
      group.appendChild(row);
    }
    container.appendChild(group);
  }
  if (!any) {
    const hint = document.createElement('div');
    hint.className = 'hint';
    hint.textContent = 'No facets';
    container.appendChild(hint);
  }
}

// Single delegated click handler — attached ONCE at init
function wireFacetClicks() {
  $('#facets').addEventListener('click', (e) => {
    const row = e.target.closest('.facet-item');
    if (!row) return;
    e.preventDefault();
    const key = row.dataset.facetKey;
    const value = row.dataset.facetValue;
    const kind = row.dataset.facetKind;
    if (!key || value == null) return;

    if (kind === 'radio') {
      state.filters.is_agent = state.filters.is_agent === value ? '' : value;
    } else {
      if (state.filters[key].has(value)) state.filters[key].delete(value);
      else state.filters[key].add(value);
    }
    state.start = 0;
    search();
  });
}

// ---- results ----
function renderResults(j) {
  const root = $('#results');
  root.innerHTML = '';
  const total = j.numFound || 0;
  const meta = document.createElement('div');
  meta.className = 'meta';
  meta.textContent = `${total.toLocaleString()} results · ${j.qtime ?? '?'}ms · sort: ${state.sort}`;
  root.appendChild(meta);

  if (!j.docs?.length) {
    const h = document.createElement('div');
    h.className = 'hint';
    h.textContent = 'No matches. Try loosening filters.';
    root.appendChild(h);
    return;
  }

  for (const d of j.docs) root.appendChild(renderHit(d));
  root.appendChild(renderPager(j));
}

function renderHit(d) {
  const card = document.createElement('div');
  card.className = 'hit';

  const title = document.createElement('div');
  title.className = 'hit-title';
  title.textContent = d.title || d.id;
  card.appendChild(title);

  const meta = document.createElement('div');
  meta.className = 'hit-meta';
  const tag = (text, cls) => {
    const s = document.createElement('span');
    s.className = 'tag' + (cls ? ' ' + cls : '');
    s.textContent = text;
    return s;
  };
  meta.appendChild(tag(d.doc_type || '?', d.doc_type));
  if (d.source)  meta.appendChild(tag(d.source));
  if (d.project) meta.appendChild(tag(d.project));
  const bits = [];
  if (d.started) bits.push(d.started.slice(0, 16).replace('T', ' '));
  if (d.duration) bits.push(d.duration);
  if (typeof d.total_turns === 'number') bits.push(`${d.total_turns} turns (${d.user_turns ?? 0}u+${d.assistant_turns ?? 0}a)`);
  if (typeof d.active_seconds === 'number') {
    const us = Math.round((d.user_seconds ?? 0) / 60);
    const as_ = Math.round((d.assistant_seconds ?? 0) / 60);
    bits.push(`${us}m user + ${as_}m agent`);
  }
  if (d.size_kb) bits.push(`${d.size_kb.toFixed(1)}kb`);
  if (bits.length) meta.appendChild(document.createTextNode(bits.join(' · ')));
  card.appendChild(meta);

  if (d._highlights?.length) {
    const snippet = document.createElement('div');
    snippet.className = 'snippet';
    snippet.innerHTML = d._highlights.join(' … ');
    card.appendChild(snippet);
  }

  const actions = document.createElement('div');
  actions.className = 'hit-actions';
  const openBtn = document.createElement('button');
  openBtn.textContent = 'open';
  openBtn.addEventListener('click', () => openDoc(d.id));
  const mltBtn = document.createElement('button');
  mltBtn.textContent = 'more like this';
  mltBtn.addEventListener('click', () => mlt(d.id));
  actions.appendChild(openBtn);
  actions.appendChild(mltBtn);
  card.appendChild(actions);
  return card;
}

function renderPager(j) {
  const p = document.createElement('div');
  p.className = 'pager';
  const total = j.numFound || 0;
  const pages = Math.ceil(total / PAGE_SIZE);
  const cur = Math.floor(state.start / PAGE_SIZE);
  const mkBtn = (label, onclick, disabled, active) => {
    const b = document.createElement('button');
    b.textContent = label;
    if (active) b.className = 'active';
    b.disabled = !!disabled;
    b.addEventListener('click', onclick);
    return b;
  };
  p.appendChild(mkBtn('← prev', () => { if (cur > 0) { state.start -= PAGE_SIZE; search(); } }, cur === 0));
  const first = Math.max(0, cur - 3);
  const last = Math.min(pages, first + 7);
  for (let i = first; i < last; i++) {
    p.appendChild(mkBtn(String(i + 1), () => { state.start = i * PAGE_SIZE; search(); }, false, i === cur));
  }
  p.appendChild(mkBtn('next →', () => { if (cur + 1 < pages) { state.start += PAGE_SIZE; search(); } }, cur + 1 >= pages));
  return p;
}

// ============================================================================
// Doc modal (rendered markdown + raw toggle)
// ============================================================================

const MARKDOWN_TYPES = new Set(['session', 'project_doc', 'summary_row']);

function renderBody(body, mode, docType) {
  if (!body) { const d = document.createElement('div'); d.className = 'hint'; d.textContent = '(no body)'; return d; }
  if (mode === 'rendered' && MARKDOWN_TYPES.has(docType) && window.marked && window.DOMPurify) {
    const div = document.createElement('div');
    div.className = 'md-body';
    div.innerHTML = DOMPurify.sanitize(marked.parse(body));
    return div;
  }
  const pre = document.createElement('pre');
  pre.textContent = body;
  return pre;
}

async function openDoc(id) {
  const r = await fetch(`${API}/api/doc/${encodeURIComponent(id)}`);
  const d = await r.json();
  const content = $('#modal-content');
  content.innerHTML = '';
  const h2 = document.createElement('h2'); h2.textContent = d.title || d.id; content.appendChild(h2);
  if (d.path) {
    const p = document.createElement('div'); p.className = 'path'; p.textContent = d.path; content.appendChild(p);
  }
  const metaBits = [d.doc_type, d.source, d.project, d.started].filter(Boolean).join(' · ');
  const m = document.createElement('div'); m.className = 'path'; m.textContent = metaBits; content.appendChild(m);

  const canRender = MARKDOWN_TYPES.has(d.doc_type);
  let mode = canRender ? 'rendered' : 'raw';
  const bodyHost = document.createElement('div');
  const refresh = () => { bodyHost.innerHTML = ''; bodyHost.appendChild(renderBody(d.body, mode, d.doc_type)); };

  if (canRender) {
    const toggle = document.createElement('div'); toggle.className = 'view-toggle';
    const btnR = document.createElement('button'); btnR.textContent = 'Rendered'; btnR.className = 'active';
    const btnW = document.createElement('button'); btnW.textContent = 'Raw';
    btnR.addEventListener('click', () => { mode = 'rendered'; btnR.classList.add('active'); btnW.classList.remove('active'); refresh(); });
    btnW.addEventListener('click', () => { mode = 'raw';      btnW.classList.add('active'); btnR.classList.remove('active'); refresh(); });
    toggle.appendChild(btnR); toggle.appendChild(btnW);
    content.appendChild(toggle);
  }
  content.appendChild(bodyHost);
  refresh();
  $('#modal').classList.remove('hidden');
}

async function mlt(id) {
  const r = await fetch(`${API}/api/mlt/${encodeURIComponent(id)}`);
  const j = await r.json();
  const content = $('#modal-content');
  content.innerHTML = '';
  const h2 = document.createElement('h2'); h2.textContent = 'More like this'; content.appendChild(h2);
  if (j.match) {
    const p = document.createElement('div'); p.className = 'path';
    p.textContent = `Based on: ${j.match.title || j.match.id}`;
    content.appendChild(p);
  }
  if (!j.similar?.length) {
    const h = document.createElement('div'); h.className = 'hint'; h.textContent = 'No similar docs found.';
    content.appendChild(h);
  }
  for (const d of j.similar || []) {
    const card = document.createElement('div'); card.className = 'hit'; card.style.cursor = 'pointer';
    card.addEventListener('click', () => openDoc(d.id));
    const title = document.createElement('div'); title.className = 'hit-title'; title.textContent = d.title || d.id;
    card.appendChild(title);
    const meta = document.createElement('div'); meta.className = 'hit-meta';
    const tag = (t, cls) => { const s = document.createElement('span'); s.className = 'tag' + (cls ? ' ' + cls : ''); s.textContent = t; return s; };
    meta.appendChild(tag(d.doc_type || '?', d.doc_type));
    if (d.source)  meta.appendChild(tag(d.source));
    if (d.project) meta.appendChild(tag(d.project));
    card.appendChild(meta);
    content.appendChild(card);
  }
  $('#modal').classList.remove('hidden');
}

// ============================================================================
// Health + toolbar wiring
// ============================================================================

async function health() {
  try {
    const r = await fetch(`${API}/api/health`);
    const j = await r.json();
    const s = $('#status');
    if (j.solr === 'up') {
      s.className = 'status up';
      s.textContent = `solr up · ${j.numDocs.toLocaleString()} docs`;
    } else { s.className = 'status down'; s.textContent = 'solr down'; }
  } catch {
    $('#status').className = 'status down'; $('#status').textContent = 'api unreachable';
  }
}

function applyPresetButtons() {
  document.querySelectorAll('#date-presets button').forEach(b => {
    b.classList.toggle('active', b.dataset.preset === state.datePreset);
  });
}

function wireToolbar() {
  document.querySelectorAll('#date-presets button').forEach(b => {
    b.addEventListener('click', () => {
      state.datePreset = b.dataset.preset;
      applyPresetButtons();
      $('#custom-dates').classList.toggle('hidden', state.datePreset !== 'custom');
      if (state.datePreset !== 'custom') { state.dateFrom = ''; state.dateTo = ''; state.start = 0; search(); }
    });
  });
  $('#apply-dates').addEventListener('click', () => {
    state.dateFrom = $('#date-from').value;
    state.dateTo   = $('#date-to').value;
    state.start = 0; search();
  });
  $('#sort').addEventListener('change',         e => { state.sort = e.target.value;      state.start = 0; search(); });
  $('#min-turns').addEventListener('change',    e => { state.minTurns = e.target.value;  state.start = 0; search(); });
  $('#min-duration').addEventListener('change', e => { state.minDuration = e.target.value; state.start = 0; search(); });
}

function hydrateControls() {
  $('#q').value = state.q;
  $('#sort').value = state.sort;
  $('#min-turns').value = state.minTurns;
  $('#min-duration').value = state.minDuration;
  $('#date-from').value = state.dateFrom;
  $('#date-to').value = state.dateTo;
  applyPresetButtons();
  $('#custom-dates').classList.toggle('hidden', state.datePreset !== 'custom');
}

// Search button / enter / reset
$('#go').addEventListener('click', () => {
  state.q = $('#q').value.trim();
  if (state.q && state.sort === 'started_desc') state.sort = 'relevance';
  if (!state.q && state.sort === 'relevance')   state.sort = 'started_desc';
  $('#sort').value = state.sort;
  state.start = 0; search();
});
$('#q').addEventListener('keydown', e => { if (e.key === 'Enter') $('#go').click(); });
$('#clear').addEventListener('click', () => {
  state.q = ''; state.start = 0; state.sort = 'started_desc';
  state.datePreset = 'all'; state.dateFrom = ''; state.dateTo = '';
  state.minTurns = ''; state.minDuration = '';
  state.filters = { source: new Set(), project: new Set(), doc_type: new Set(), is_agent: '' };
  hydrateControls(); search();
});

document.querySelectorAll('[data-close]').forEach(x => x.addEventListener('click', () => $('#modal').classList.add('hidden')));
document.addEventListener('keydown', e => { if (e.key === 'Escape') $('#modal').classList.add('hidden'); });
window.addEventListener('popstate', () => { urlToState(); hydrateControls(); search(); });

// ============================================================================
// Init
// ============================================================================

urlToState();
if (!state.sort) state.sort = state.q ? 'relevance' : 'started_desc';
wireToolbar();
wireFacetClicks();
hydrateControls();
health();
search();
