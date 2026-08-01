// visualShell.js — the EcoData-style application shell.
// Replaces the stock left sidebar with a compact nav rail, and shows a landing
// page listing the sites (site packs) available to this user. A site's context
// rail only appears once a site is open. Everything here is generic: site names,
// sector words and statistics come from the endpoints themselves.

import { openInPanel, refreshContext, noteSessionSwitch } from './visualChat.js';
import { openExplorer } from './visualExplorer.js';
import { openAtlas, hideAtlas } from './visualAtlas.js';
import { openThemes, hideThemes } from './visualThemes.js';

const SHELL_CLASS = 'eco-shell';
let landingEl = null;
let navEl = null;
let sitesCache = null;

function getSessions() {
  return import('../sessions.js');
}

// ---- discovery: which registered endpoints are visual site packs -----------
export async function discoverSites(force) {
  if (sitesCache && !force) return sitesCache;
  let items = [];
  try {
    const res = await fetch('/api/models');
    const data = await res.json();
    items = data.items || [];
  } catch {
    return (sitesCache = []);
  }
  const sites = [];
  await Promise.all(items.map(async (item) => {
    const model = (item.models || []).find((m) => String(m).toLowerCase().startsWith('idli-insight'));
    if (!model) return;
    let caps = null;
    try {
      const r = await fetch(`/api/visual/resolve?endpoint_url=${encodeURIComponent(item.url)}`);
      if (!r.ok) return;
      const { endpoint_id } = await r.json();
      const c = await fetch(`/api/visual/${encodeURIComponent(endpoint_id)}/capabilities`);
      if (!c.ok) return;
      caps = await c.json();
      caps.endpoint_id = endpoint_id;
    } catch {
      return;
    }
    sites.push({
      endpointId: caps.endpoint_id,
      endpointName: item.endpoint_name || '',
      url: item.url,
      model,
      siteId: caps.site_id || '',
      label: caps.label || item.endpoint_name || caps.site_id || 'Site',
      synthetic: !!caps.synthetic,
      capabilities: (caps.capabilities || []).length,
    });
  }));
  sites.sort((a, b) => a.label.localeCompare(b.label));
  return (sitesCache = sites);
}

// A short human sector line for a site card, derived from the pack, never hardcoded.
async function siteBlurb(site) {
  try {
    const r = await fetch(`/api/visual/${encodeURIComponent(site.endpointId)}/headline-stats`);
    if (r.ok) {
      const d = await r.json();
      return (d.stats || []).slice(0, 3).map((s) => `${fmt(s.value)} ${s.label.toLowerCase()}`);
    }
  } catch { /* endpoint may not offer it yet */ }
  try {
    const q = await fetch(`/api/visual/${encodeURIComponent(site.endpointId)}/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ capability_id: 'site-orientation', arguments: {}, question: '' }),
    });
    if (!q.ok) return [];
    const env = await q.json();
    const d = ((env.visuals || [])[0]?.summary?.denominators) || {};
    return Object.entries(d).slice(0, 3).map(([k, v]) => `${fmt(v)} ${humanise(k)}`);
  } catch {
    return [];
  }
}

function fmt(v) {
  return typeof v === 'number' ? v.toLocaleString('en-IN') : String(v ?? '');
}

// Machine-ish plane words the packs still emit; shown to people as plain words.
const HUMAN = {
  records: 'records', entities: 'kinds of things recorded', cells: 'map squares',
  sources: 'data sets', source_versions: 'data sets', measurements: 'measurements',
  effort_rows: 'survey visits', events: 'records',
};
function humanise(key) {
  if (HUMAN[key]) return HUMAN[key];
  return String(key).replace(/_/g, ' ');
}

// ---- nav rail --------------------------------------------------------------
function icon(paths) {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', '0 0 24 24');
  svg.setAttribute('fill', 'none');
  svg.setAttribute('stroke', 'currentColor');
  svg.setAttribute('stroke-width', '1.8');
  svg.setAttribute('stroke-linecap', 'round');
  svg.setAttribute('stroke-linejoin', 'round');
  svg.classList.add('eco-nav-icon');
  for (const d of paths) {
    const p = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    p.setAttribute('d', d);
    svg.appendChild(p);
  }
  return svg;
}

const ICONS = {
  chat: ['M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z'],
  map: ['M9 3 3 6v15l6-3 6 3 6-3V3l-6 3-6-3z', 'M9 3v15', 'M15 6v15'],
  data: ['M3 5c0-1.1 4-2 9-2s9 .9 9 2-4 2-9 2-9-.9-9-2z', 'M3 5v14c0 1.1 4 2 9 2s9-.9 9-2V5', 'M3 12c0 1.1 4 2 9 2s9-.9 9-2'],
  history: ['M12 8v4l3 3', 'M3.05 11a9 9 0 1 1 .5 4', 'M3 5v6h6'],
  research: ['M3 3v18h18', 'M7 15l4-5 3 3 5-7'],
  theme: ['M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z'],
  plus: ['M12 5v14', 'M5 12h14'],
};

// The brand mark: a raven, deliberately cryptic. The PNG carries only the ink
// as alpha and the CSS mask paints it in the theme's ink, so one asset works
// on every theme. The landing shows the same bird resolved out of data points
// — the form only appears once there is enough of it.
const IDLI_MARK_HTML = '<span class="eco-brand-ink" aria-hidden="true"></span>';

function setActiveNav(name) {
  for (const b of document.querySelectorAll('#eco-nav .eco-nav-item')) {
    b.classList.toggle('is-active', b.dataset.nav === name);
  }
}

// ---- theme: light (default) / dark, one localStorage key -------------------
function applyEcoTheme(mode) {
  const dark = mode === 'dark';
  document.body.classList.toggle('eco-dark', dark);
  // Charts key their palette off the root: .light class + --bg luminance.
  document.documentElement.classList.toggle('light', !dark);
  document.documentElement.style.setProperty('--bg', dark ? '#212329' : '#f7f5f0');
  try { localStorage.setItem('idli-theme', mode); } catch { /* private mode */ }
}
function storedEcoTheme() {
  try { return localStorage.getItem('idli-theme') === 'dark' ? 'dark' : 'light'; } catch { return 'light'; }
}
function toggleEcoTheme() {
  applyEcoTheme(storedEcoTheme() === 'dark' ? 'light' : 'dark');
}

function ensureNav() {
  if (navEl) return navEl;
  navEl = document.createElement('nav');
  navEl.id = 'eco-nav';
  navEl.setAttribute('aria-label', 'Main');

  const brand = document.createElement('button');
  brand.type = 'button';
  brand.className = 'eco-brand';
  brand.title = 'Sites';
  const mark = document.createElement('span');
  mark.className = 'eco-brand-mark';
  mark.innerHTML = IDLI_MARK_HTML;
  brand.appendChild(mark);
  const name = document.createElement('span');
  name.className = 'eco-brand-name';
  name.textContent = 'Idli Insights';
  brand.appendChild(name);
  brand.addEventListener('click', () => { hideAtlas(); showLanding(true); setActiveNav('research'); });
  navEl.appendChild(brand);

  const siteCard = document.createElement('button');
  siteCard.className = 'eco-nav-site';
  siteCard.id = 'eco-site-card';
  siteCard.hidden = true;
  siteCard.addEventListener('click', () => showLanding(true));
  navEl.appendChild(siteCard);

  const list = document.createElement('div');
  list.className = 'eco-nav-list';
  const items = [
    ['chat', 'Chat', () => { hideLanding(); hideAtlas(); hideThemes(); }],
    ['map', 'Themes', () => { hideAtlas(); openThemesCentre(); }],
    ['data', 'Data', () => { hideThemes(); openDataExplorer(); }],
    ['history', 'History', () => toggleHistory()],
    ['research', 'Sites', () => { hideAtlas(); hideThemes(); showLanding(true); }],
  ];
  for (const [ic, label, fn] of items) {
    const b = document.createElement('button');
    b.className = 'eco-nav-item';
    b.dataset.nav = ic;
    b.appendChild(icon(ICONS[ic]));
    const t = document.createElement('span');
    t.textContent = label;
    b.appendChild(t);
    b.addEventListener('click', () => { setActiveNav(ic); fn(); });
    list.appendChild(b);
  }
  // Theme is a mode flip, not a destination — no active state.
  const themeBtn = document.createElement('button');
  themeBtn.className = 'eco-nav-item';
  themeBtn.dataset.nav = 'theme';
  themeBtn.appendChild(icon(ICONS.theme));
  const tl = document.createElement('span');
  tl.textContent = 'Theme';
  themeBtn.appendChild(tl);
  themeBtn.addEventListener('click', toggleEcoTheme);
  list.appendChild(themeBtn);
  navEl.appendChild(list);

  const spacer = document.createElement('div');
  spacer.className = 'eco-nav-spacer';
  navEl.appendChild(spacer);

  const newBtn = document.createElement('button');
  newBtn.className = 'eco-new-btn';
  newBtn.appendChild(icon(ICONS.plus));
  const nb = document.createElement('span');
  nb.textContent = 'New analysis';
  newBtn.appendChild(nb);
  newBtn.addEventListener('click', () => showLanding(true));
  navEl.appendChild(newBtn);

  // One row: who is signed in, and the way out — a power button beside the name.
  const user = document.createElement('div');
  user.className = 'eco-user';
  user.id = 'eco-user';
  navEl.appendChild(user);
  const av = document.createElement('span');
  av.className = 'eco-user-avatar';
  user.appendChild(av);
  const uname = document.createElement('span');
  uname.className = 'eco-user-name';
  user.appendChild(uname);
  fetch('/api/auth/status').then((r) => r.json()).then((d) => {
    if (!d || !d.username) return;
    av.textContent = String(d.username).slice(0, 1).toUpperCase();
    uname.textContent = d.username;
    uname.title = `Signed in as ${d.username}`;
  }).catch(() => { /* the rail works without a name */ });

  const signOut = document.createElement('button');
  signOut.className = 'eco-signout';
  signOut.title = 'Sign out';
  signOut.setAttribute('aria-label', 'Sign out');
  signOut.appendChild(icon(['M12 2v10', 'M18.4 6.6a9 9 0 1 1-12.8 0']));
  user.appendChild(signOut);
  signOut.addEventListener('click', async () => {
    try { await fetch('/api/auth/logout', { method: 'POST' }); } catch { /* still leave */ }
    // Same wipe as the stock settings logout: the next account on this browser
    // must not inherit session state. Keep only the remembered username.
    try {
      const keep = new Set(['odysseus-last-user']);
      const drop = [];
      for (let i = 0; i < localStorage.length; i++) {
        const k = localStorage.key(i);
        if (k && !keep.has(k)) drop.push(k);
      }
      drop.forEach((k) => localStorage.removeItem(k));
      sessionStorage.clear();
    } catch { /* private mode */ }
    window.location.href = '/login';
  });

  document.body.appendChild(navEl);
  document.body.classList.add(SHELL_CLASS);
  applyEcoTheme(storedEcoTheme());
  return navEl;
}

// IDL-REQ-0004: Themes opens the recurring questions this pack answers, and
// what has been published against them — not the last figure a conversation
// happened to mention. "Open in chat" carries a theme's question back into
// the composer so it can meet everything else the site knows; it is never
// sent for the reader.
async function openThemesCentre() {
  const active = await syncActiveSite();
  if (!active) { showLanding(true); return; }
  hideLanding();
  openThemes(active.endpointId, {
    onOpenInChat: (question) => {
      const input = document.getElementById('message');
      if (!input || !question) return;
      input.value = question;
      input.dispatchEvent(new Event('input', { bubbles: true }));
      setActiveNav('chat');
      input.focus();
    },
  });
}

async function openDataExplorer() {
  const active = await syncActiveSite();
  if (!active) { showLanding(true); return; }
  // Data is a destination now: the full-page Atlas, with the inventory drawer
  // one click away from inside it.
  openAtlas(active.endpointId, () => openExplorer(active.endpointId));
}

// ---- past conversations: our own quiet drawer, not the stock sidebar -------
let historyEl = null;

function relativeTime(iso) {
  const t = Date.parse(iso || '');
  if (!Number.isFinite(t)) return '';
  const mins = Math.round((Date.now() - t) / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins} min ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs} h ago`;
  const days = Math.round(hrs / 24);
  if (days < 30) return `${days} d ago`;
  return new Date(t).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
}

async function humanSessionName(name) {
  const raw = String(name || '').trim();
  if (!/^idli-insight/i.test(raw)) return raw || 'Untitled conversation';
  const sites = await discoverSites();
  const hit = sites.find((s) => raw.toLowerCase().startsWith(String(s.model).toLowerCase()));
  return hit ? hit.label : raw.replace(/^idli-insight-?/i, '').replace(/[-_]/g, ' ');
}

function ensureHistory() {
  if (historyEl) return historyEl;
  historyEl = document.createElement('aside');
  historyEl.id = 'eco-history';
  historyEl.setAttribute('role', 'dialog');
  historyEl.setAttribute('aria-label', 'Past conversations');
  const head = document.createElement('div');
  head.className = 'viz-side-head';
  const title = document.createElement('span');
  title.className = 'viz-side-title';
  title.textContent = 'Past conversations';
  head.appendChild(title);
  const x = document.createElement('button');
  x.className = 'viz-panel-close';
  x.textContent = '×';
  x.setAttribute('aria-label', 'Close history');
  x.addEventListener('click', closeHistory);
  head.appendChild(x);
  historyEl.appendChild(head);
  const filter = document.createElement('input');
  filter.className = 'eco-explorer-search eco-history-filter';
  filter.type = 'search';
  filter.placeholder = 'Filter conversations…';
  filter.addEventListener('input', () => renderHistoryList(filter.value));
  historyEl.appendChild(filter);
  const list = document.createElement('div');
  list.className = 'eco-history-list';
  list.id = 'eco-history-list';
  historyEl.appendChild(list);
  document.body.appendChild(historyEl);
  document.addEventListener('keydown', (ev) => {
    if (ev.key === 'Escape') closeHistory();
  });
  return historyEl;
}

function closeHistory() {
  document.body.classList.remove('eco-history-open');
  // The drawer is transient; hand the active state back to the visible view.
  setActiveNav(document.body.classList.contains('eco-landing-open') ? 'research' : 'chat');
}

async function renderHistoryList(filterText) {
  const list = document.getElementById('eco-history-list');
  if (!list) return;
  const sessions = await getSessions();
  const all = (sessions.getSessions() || [])
    .slice()
    .sort((a, b) => String(b.last_message_at || b.updated_at || b.created_at || '')
      .localeCompare(String(a.last_message_at || a.updated_at || a.created_at || '')));
  const needle = String(filterText || '').toLowerCase();
  list.replaceChildren();
  let shown = 0;
  for (const s of all) {
    const label = await humanSessionName(s.name);
    if (needle && !label.toLowerCase().includes(needle)) continue;
    shown += 1;
    const item = document.createElement('button');
    item.className = 'eco-history-item';
    const n = document.createElement('span');
    n.className = 'eco-history-name';
    n.textContent = label;
    item.appendChild(n);
    const m = document.createElement('span');
    m.className = 'eco-history-meta';
    m.textContent = relativeTime(s.last_message_at || s.updated_at || s.created_at);
    item.appendChild(m);
    item.addEventListener('click', async () => {
      closeHistory();
      hideLanding();
      setActiveNav('chat');
      (await getSessions()).selectSession(s.id);
      // The restored history carries visual markers; the endpoint may differ.
      noteSessionSwitch();
      setTimeout(syncActiveSite, 1200);
    });
    list.appendChild(item);
  }
  if (!shown) {
    const none = document.createElement('div');
    none.className = 'eco-landing-loading';
    none.textContent = needle ? 'No conversations match.' : 'No conversations yet.';
    list.appendChild(none);
  }
}

function toggleHistory() {
  ensureHistory();
  const open = document.body.classList.toggle('eco-history-open');
  if (open) {
    const filter = historyEl.querySelector('.eco-history-filter');
    if (filter) filter.value = '';
    renderHistoryList('');
  }
}

export function setActiveSite(site) {
  ensureNav();
  // The composer asks about the place, not the product. app.js's resize
  // handler reads the same global, so the copy survives width changes.
  window._idliComposerPlaceholder = site ? 'ready when you are…' : '';
  const input = document.getElementById('message');
  if (input && site && input.getAttribute('placeholder')) {
    input.setAttribute('placeholder', window._idliComposerPlaceholder);
  }
  const card = document.getElementById('eco-site-card');
  if (!card) return;
  if (!site) { card.hidden = true; return; }
  card.hidden = false;
  card.replaceChildren();
  const l = document.createElement('span');
  l.className = 'eco-site-label';
  l.textContent = site.label || site.endpointName || '';
  card.appendChild(l);
  const s = document.createElement('span');
  s.className = 'eco-site-sub';
  s.textContent = site.synthetic ? 'Synthetic test pack' : 'Live site pack';
  card.appendChild(s);
}

// ---- landing page ----------------------------------------------------------
export async function showLanding(force) {
  ensureNav();
  hideAtlas();
  hideThemes();
  if (!landingEl) {
    landingEl = document.createElement('div');
    landingEl.id = 'eco-landing';
    document.body.appendChild(landingEl);
  }
  if (landingEl.dataset.built === '1' && !force) {
    document.body.classList.add('eco-landing-open');
    return;
  }
  document.body.classList.add('eco-landing-open');
  landingEl.replaceChildren();

  const inner = document.createElement('div');
  inner.className = 'eco-landing-inner';
  landingEl.appendChild(inner);

  // The front door: the mark, the name, and every pack as a light whose
  // reach is how much it holds.
  const brandRow = document.createElement('div');
  brandRow.className = 'eco-landing-brand';
  const mark = document.createElement('span');
  mark.className = 'eco-landing-mark';
  mark.setAttribute('aria-hidden', 'true');
  brandRow.appendChild(mark);
  const name = document.createElement('span');
  name.className = 'eco-landing-name';
  name.textContent = 'Idli Insights';
  brandRow.appendChild(name);
  inner.appendChild(brandRow);

  const field = document.createElement('div');
  field.className = 'eco-sky';
  inner.appendChild(field);
  field.appendChild(Object.assign(document.createElement('div'), {
    className: 'eco-landing-loading', textContent: 'Looking for available sites…',
  }));

  const sites = await discoverSites(force);
  field.replaceChildren();
  if (!sites.length) {
    field.appendChild(Object.assign(document.createElement('div'), {
      className: 'eco-landing-loading',
      textContent: 'No site packs are available on this account yet.',
    }));
    landingEl.dataset.built = '1';
    return;
  }
  renderSky(field, sites);
  landingEl.dataset.built = '1';
}


// ---- the sky: one light per pack -------------------------------------------
// Reach is weight: a pack holding more records throws more light. Position is
// composition, not geography — the packs' own endpoints publish no coordinates
// (asked for in IDL-REQ-0004), so the layout says so out loud rather than
// implying a place.
const SKY_SPOTS = [
  // x, y in fractions of the field; a loose scatter that reads as sky.
  [0.26, 0.34], [0.66, 0.52], [0.44, 0.74], [0.80, 0.26],
  [0.16, 0.68], [0.58, 0.18], [0.86, 0.70], [0.34, 0.52],
];

function renderSky(field, sites) {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('class', 'eco-sky-svg');
  // `meet`, never `slice`: a slice crops whichever light sits nearest an edge,
  // and a pack you cannot see is a pack you cannot open.
  svg.setAttribute('viewBox', '0 0 1000 620');
  svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');
  const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
  svg.appendChild(defs);
  field.appendChild(svg);

  const ns = (tag, attrs) => {
    const n = document.createElementNS('http://www.w3.org/2000/svg', tag);
    for (const k in attrs || {}) n.setAttribute(k, attrs[k]);
    return n;
  };

  // A deterministic dust of faint points, so the field reads as a night sky
  // rather than a flat panel. Decorative: carries no data, and says nothing.
  const dust = ns('g', { class: 'eco-sky-dust' });
  let seed = 20260801;
  const rand = () => {
    seed = (seed * 1103515245 + 12345) & 0x7fffffff;
    return seed / 0x7fffffff;
  };
  for (let i = 0; i < 190; i++) {
    dust.appendChild(ns('circle', {
      cx: (rand() * 1000).toFixed(1), cy: (rand() * 620).toFixed(1),
      r: (0.5 + rand() * 1.2).toFixed(2), opacity: (0.10 + rand() * 0.28).toFixed(2),
    }));
  }
  svg.appendChild(dust);

  // Weight per pack drives the radius; until every blurb lands we draw a
  // provisional radius and grow it in place.
  const maxR = 168, minR = 62;
  const entries = sites.map((site, i) => {
    const [fx, fy] = SKY_SPOTS[i % SKY_SPOTS.length];
    const cx = fx * 1000, cy = fy * 620;
    const grad = ns('radialGradient', { id: `eco-glow-${i}`, cx: '50%', cy: '50%', r: '50%' });
    grad.appendChild(ns('stop', { offset: '0%', 'stop-color': 'var(--glow-core)', 'stop-opacity': '0.85' }));
    grad.appendChild(ns('stop', { offset: '32%', 'stop-color': 'var(--glow-mid)', 'stop-opacity': '0.34' }));
    grad.appendChild(ns('stop', { offset: '100%', 'stop-color': 'var(--glow-mid)', 'stop-opacity': '0' }));
    defs.appendChild(grad);

    const g = ns('g', { class: 'eco-spot', tabindex: '0', role: 'button' });
    g.setAttribute('aria-label', `Open ${site.label}`);
    const halo = ns('circle', { cx, cy, r: minR, fill: `url(#eco-glow-${i})`, class: 'eco-spot-halo' });
    const ring = ns('circle', { cx, cy, r: minR * 0.66, class: 'eco-spot-ring' });
    const core = ns('circle', { cx, cy, r: 7, class: 'eco-spot-core' });
    g.appendChild(halo);
    g.appendChild(ring);
    // A few motes inside the reach, echoing the records the pack holds.
    const motes = ns('g', { class: 'eco-spot-motes' });
    g.appendChild(motes);
    g.appendChild(core);

    const label = ns('text', { x: cx, y: cy + minR * 0.66 + 26, class: 'eco-spot-label' });
    // SVG text does not wrap; a long pack name would run off the field. Clip
    // it in the label and keep the whole name in the accessible name + title.
    label.textContent = site.label.length > 26 ? `${site.label.slice(0, 25)}…` : site.label;
    const full = ns('title');
    full.textContent = site.label;
    label.appendChild(full);
    // Two lines: the measure that sets this light's size, then what the pack
    // is about. Showing only the second invites "why is that one bigger?".
    const sub = ns('text', { x: cx, y: cy + minR * 0.66 + 46, class: 'eco-spot-sub' });
    const sub2 = ns('text', { x: cx, y: cy + minR * 0.66 + 64, class: 'eco-spot-sub2' });
    g.appendChild(label);
    g.appendChild(sub);
    g.appendChild(sub2);
    if (site.synthetic) {
      const tag = ns('text', { x: cx, y: cy - minR * 0.66 - 12, class: 'eco-spot-tag' });
      tag.textContent = 'TEST DATA';
      g.appendChild(tag);
    }

    g.addEventListener('click', () => openSite(site));
    g.addEventListener('keydown', (ev) => {
      if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); openSite(site); }
    });
    svg.appendChild(g);
    return { site, cx, cy, halo, ring, core, motes, label, sub, sub2, i };
  });

  // Grow each light to its weight once the pack's own numbers arrive.
  Promise.all(entries.map((e) => siteBlurb(e.site).then((lines) => {
    e.sub2.textContent = lines.length ? lines[0] : '';
    return siteWeight(e.site);
  }).catch(() => 0))).then((weights) => {
    const max = Math.max(...weights.filter((w) => Number.isFinite(w) && w > 0), 1);
    entries.forEach((e, idx) => {
      const w = weights[idx] > 0 ? weights[idx] : max * 0.25;
      const r = minR + (maxR - minR) * Math.sqrt(w / max);
      e.halo.setAttribute('r', r.toFixed(1));
      e.ring.setAttribute('r', (r * 0.66).toFixed(1));
      e.core.setAttribute('r', (6 + 5 * Math.sqrt(w / max)).toFixed(1));
      e.label.setAttribute('y', (e.cy + r * 0.66 + 26).toFixed(1));
      e.sub.setAttribute('y', (e.cy + r * 0.66 + 46).toFixed(1));
      e.sub2.setAttribute('y', (e.cy + r * 0.66 + 64).toFixed(1));
      e.sub.textContent = weights[idx] > 0 ? `${fmt(weights[idx])} records` : '';
      const tag = e.label.parentNode.querySelector('.eco-spot-tag');
      if (tag) tag.setAttribute('y', (e.cy - r * 0.66 - 12).toFixed(1));
      // Each mote is a person credited with the data behind this story. They
      // are scattered and sized irregularly so they read as part of the same
      // dust as the sky, not as a chart — and each carries its surname, so the
      // light is visibly made of people rather than of anonymous points.
      e.motes.replaceChildren();
      siteContributors(e.site).then((people) => {
        e.motes.replaceChildren();
        // Stable per site: the same person keeps the same speck on every load.
        let seed = 9301 + [...e.site.endpointId].reduce((a, c) => a + c.charCodeAt(0), 0);
        const rand = () => {
          seed = (seed * 1103515245 + 12345) & 0x7fffffff;
          return seed / 0x7fffffff;
        };
        const placed = [];
        const specks = people.map((person) => {
          // Uniform over the disc (sqrt keeps them from crowding the centre),
          // then jittered — no ring, no spiral, no grid.
          const a = rand() * Math.PI * 2;
          const rad = r * 0.62 * Math.sqrt(rand());
          return {
            person,
            x: e.cx + Math.cos(a) * rad,
            y: e.cy + Math.sin(a) * rad,
            // The same spread of sizes and brightness as the sky's dust.
            r: 0.7 + rand() * 1.9,
            o: 0.42 + rand() * 0.5,
          };
        });
        // Brighter specks get first claim on a label; the rest keep theirs on
        // hover. Anything that would collide stays unlabelled — a smear of
        // overlapping names would tell you less than none.
        for (const sp of [...specks].sort((a, b) => b.r - a.r)) {
          const full = sp.person.affiliation
            ? `${sp.person.name} · ${sp.person.affiliation}` : sp.person.name;
          const dot = ns('circle', {
            cx: sp.x.toFixed(1), cy: sp.y.toFixed(1), r: sp.r.toFixed(2),
            opacity: sp.o.toFixed(2),
            class: 'eco-spot-mote is-person', tabindex: '0',
          });
          const t = ns('title');
          t.textContent = full;
          dot.appendChild(t);
          const show = (ev) => showTip(field, full, ev);
          dot.addEventListener('mouseenter', show);
          dot.addEventListener('focus', show);
          dot.addEventListener('mouseleave', () => hideTip(field));
          dot.addEventListener('blur', () => hideTip(field));
          e.motes.appendChild(dot);

          const short = surname(sp.person.name);
          const tx = sp.x + sp.r + 3.5;
          const box = { x: tx, y: sp.y - 4, w: short.length * 3.5 + 2, h: 8 };
          const clash = placed.some((q) => !(box.x > q.x + q.w || box.x + box.w < q.x
            || box.y > q.y + q.h || box.y + box.h < q.y));
          // The core outshines anything written across it, and a half-eaten
          // name is worse than none: keep labels clear of the light itself.
          const coreR = 6 + 5 * Math.sqrt(w / max);
          const nearCore = Math.hypot(sp.x - e.cx, sp.y - e.cy) < coreR + 16;
          if (clash || nearCore || box.x + box.w > e.cx + r * 0.98) continue;
          placed.push(box);
          const name = ns('text', {
            x: tx.toFixed(1), y: (sp.y + 2.2).toFixed(1),
            class: 'eco-mote-name', opacity: (0.30 + sp.o * 0.35).toFixed(2),
          });
          name.textContent = short;
          e.motes.appendChild(name);
        }
        if (people.length) e.sub2.textContent = `${people.length} people contributed`;
      });
    });
  });

  // Bringing your own pack — a dark node with no light in it yet.
  const addWrap = document.createElement('div');
  addWrap.className = 'eco-sky-add';
  addWrap.textContent = 'Add a site — coming soon';
  field.appendChild(addWrap);

  const note = document.createElement('p');
  note.className = 'eco-sky-note';
  note.textContent = 'Welcome to Understory: Each light is a story; its reach is '
    + 'how much data sits beneath that story.';
  field.appendChild(note);
}

// The readable short form of a name: the family name alone. Truncating a full
// name mid-word ("T. R. Shanka…") reads worse than the surname it ends in, and
// the whole name is one hover away.
function surname(name) {
  const parts = String(name || '').trim().split(/\s+/).filter(Boolean);
  const last = parts[parts.length - 1] || '';
  const clean = last.replace(/[^\p{L}\p{M}'-]/gu, '');
  const word = clean.length > 1 ? clean : parts.slice(-2).join(' ');
  return word.length > 13 ? `${word.slice(0, 12)}…` : word;
}

// A hover label for a single contributor dot — crisper than a native tooltip
// and it appears at once.
function showTip(field, text, ev) {
  let tip = field.querySelector('.eco-sky-tip');
  if (!tip) {
    tip = document.createElement('div');
    tip.className = 'eco-sky-tip';
    field.appendChild(tip);
  }
  tip.textContent = text;
  const box = field.getBoundingClientRect();
  tip.style.left = `${ev.clientX - box.left}px`;
  tip.style.top = `${ev.clientY - box.top}px`;
  tip.classList.add('is-on');
}
function hideTip(field) {
  const tip = field.querySelector('.eco-sky-tip');
  if (tip) tip.classList.remove('is-on');
}

// One site-orientation call per pack, shared by everything that needs it:
// the weight that sizes a light, the sources behind a story, and the declared
// area that anchors the map underlay. Fetching it three times would be three
// times the wait for the same envelope.
const _orientation = new Map();
function orientation(site) {
  if (_orientation.has(site.endpointId)) return _orientation.get(site.endpointId);
  const pr = fetch(`/api/visual/${encodeURIComponent(site.endpointId)}/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ capability_id: 'site-orientation', arguments: {}, question: '' }),
  }).then((r) => (r.ok ? r.json() : null)).catch(() => null);
  _orientation.set(site.endpointId, pr);
  return pr;
}

// The people credited with the data behind a story. The producer publishes
// each source's DOI but not its authors (IDL-REQ-0004 asks for them), so the
// names come from the public registries that minted those DOIs, through a
// cached same-origin route. A source whose authors cannot be resolved simply
// contributes nobody — an invented name would be worse than a missing one.
async function siteContributors(site) {
  const env = await orientation(site);
  const sources = ((env || {}).audit || {}).source_versions || [];
  const dois = [...new Set(sources.map((s) => (s && s.doi) || '').filter(Boolean))];
  const lists = await Promise.all(dois.map(async (doi) => {
    try {
      const r = await fetch(`/api/visual/doi-authors?doi=${encodeURIComponent(doi)}`);
      if (!r.ok) return [];
      return (await r.json()).people || [];
    } catch {
      return [];
    }
  }));
  // One dot per person, however many sources they contributed to.
  const seen = new Map();
  for (const person of lists.flat()) {
    const key = (person.name || '').toLowerCase();
    if (!key || seen.has(key)) continue;
    seen.set(key, person);
  }
  return [...seen.values()];
}

// How much a pack holds, for the size of its light. This must be ONE measure
// across packs or the comparison is a lie: a pack counting persondays would
// outshine a pack counting bird detections for no reason anyone means. The
// admitted record count is the measure every pack shares; headline stats are
// only a last resort, and then the sizes are merely indicative.
async function siteWeight(site) {
  try {
    const env = await orientation(site);
    const d = ((env || {}).visuals || [])[0]?.summary?.denominators || {};
    for (const k of ['records', 'events', 'observations']) {
      if (typeof d[k] === 'number' && d[k] > 0) return d[k];
    }
  } catch { /* fall through */ }
  try {
    const r = await fetch(`/api/visual/${encodeURIComponent(site.endpointId)}/headline-stats`);
    if (r.ok) {
      const d = await r.json();
      const nums = (d.stats || []).map((s) => s.value).filter((v) => typeof v === 'number');
      if (nums.length) return Math.max(...nums);
    }
  } catch { /* a pack with no numbers gets the floor radius */ }
  return 0;
}

export function hideLanding() {
  document.body.classList.remove('eco-landing-open');
}

async function openSite(site) {
  const sessions = await getSessions();
  sessions.createDirectChat(site.url, site.model, site.endpointId);
  setActiveSite(site);
  hideLanding();
  setActiveNav('chat');
  refreshContext();               // the rail must follow the site, not the last one
  renderSiteWelcome(site);
  setTimeout(() => document.getElementById('message')?.focus(), 400);
}

// The composer placeholder is the whole invitation ("ready when you are…") —
// a header repeating it was noise. This only clears any older welcome node.
async function renderSiteWelcome() {
  const old = document.getElementById('eco-welcome');
  if (old) old.remove();
}

// The stock app titles direct-chat sessions with the machine model id
// (idli-insight-<site>); readers should see the site's own name.
async function prettifyMeta() {
  const meta = document.getElementById('current-meta');
  if (!meta) return;
  const raw = (meta.textContent || '').trim();
  if (!/^idli-insight/i.test(raw)) return;
  const sites = await discoverSites();
  const hit = sites.find((s) => raw.toLowerCase().startsWith(String(s.model).toLowerCase()));
  const label = hit ? hit.label : raw.replace(/^idli-insight-?/i, '').replace(/[-_]/g, ' ');
  if (label) meta.textContent = label;
}
new MutationObserver(() => prettifyMeta()).observe(
  document.getElementById('current-meta') || document.body,
  { childList: true, characterData: true, subtree: true },
);

// The composer carries one affordance: attach something. Shell access and web
// search are hidden by CSS (this product will not offer a shell at all), and
// the tools menu collapses into the attach button it mostly held. The stock
// handlers stay untouched — the attach click is delegated to the menu item
// that already opens the file picker.
const CLIP = 'M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66'
  + 'l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48';
function slimComposer() {
  const plus = document.getElementById('overflow-plus-btn');
  if (!plus || plus.dataset.ecoAttach === '1') return;
  plus.dataset.ecoAttach = '1';
  plus.title = 'Attach a file';
  plus.setAttribute('aria-label', 'Attach a file');
  plus.replaceChildren(icon([CLIP]));
  // Capture phase + stopPropagation: the stock listener on this id opens the
  // tools menu, and there is no menu any more.
  plus.addEventListener('click', (ev) => {
    ev.preventDefault();
    ev.stopPropagation();
    document.getElementById('overflow-attach-btn')?.click();
  }, true);

  // One line means one row: attach and send move into the text row itself, so
  // they sit inside the box beside what you type rather than floating past its
  // right edge. Handlers are bound to the elements, not their parents, so
  // moving them changes nothing about how they behave.
  const top = document.querySelector('.chat-input-bar > .chat-input-top');
  const send = document.querySelector('.chat-input-bar .send-btn');
  if (top) {
    top.appendChild(plus);
    if (send) top.appendChild(send);
  }
}

// ---- boot ------------------------------------------------------------------
async function syncActiveSite() {
  const sessions = await getSessions();
  const url = sessions.getCurrentEndpointUrl && sessions.getCurrentEndpointUrl();
  const sites = await discoverSites();
  const norm = (u) => String(u || '').replace(/\/(chat\/completions|completions)$/, '').replace(/\/$/, '');
  const active = sites.find((s) => norm(s.url) === norm(url));
  setActiveSite(active || null);
  return active;
}

async function boot() {
  ensureNav();
  await syncActiveSite();
  // A refresh mid-chat returns to that chat; every other arrival lands on
  // site selection. The hash alone can't tell the two apart — the stock
  // session layer restores the last conversation and writes its #<session-id>
  // even on a fresh visit — so the hash only counts on an actual reload.
  const deepLink = /^#[0-9a-f][0-9a-f-]{7,}$/i.test(window.location.hash || '');
  let navType = 'navigate';
  try { navType = (performance.getEntriesByType('navigation')[0] || {}).type || 'navigate'; } catch { /* old browsers land on sites */ }
  if (deepLink && navType === 'reload') {
    hideLanding();
    setActiveNav('chat');
  } else {
    showLanding(true);
    setActiveNav('research');
    // The stock restore may already have stamped a session hash before we
    // got here; the landing URL must read clean. (sessions.js also skips the
    // stamp while the landing is open.)
    if (window.location.hash) {
      history.replaceState(null, '', window.location.pathname + window.location.search);
    }
  }
  // The chat meta strip is one plain "Settings" button — the CSS hides the
  // title/count/caret; the stock click handler on this id opens the menu.
  const dl = document.getElementById('export-dl-btn');
  if (dl) { dl.textContent = 'Settings'; dl.title = 'Chat settings'; }
  slimComposer();
  // The view is decided: from here on the session layer may stamp the URL
  // hash again (outside the landing) — see the guard in sessions.js.
  window._ecoShellBooted = true;
  // The shell owns the page now — drop the boot overlay (app.js leaves it up
  // for us; the index.html 20s fallback covers a boot that never gets here).
  const loader = document.getElementById('app-loader');
  if (loader) { loader.style.opacity = '0'; setTimeout(() => loader.remove(), 300); }
  prettifyMeta();
}

setTimeout(boot, 1500);
setInterval(syncActiveSite, 5000);
document.addEventListener('click', (ev) => {
  if (ev.target.closest && ev.target.closest('.list-item[data-session-id]')) {
    hideLanding();
    setTimeout(syncActiveSite, 1200);
  }
}, true);
