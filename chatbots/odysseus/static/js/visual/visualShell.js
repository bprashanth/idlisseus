// visualShell.js — the EcoData-style application shell.
// Replaces the stock left sidebar with a compact nav rail, and shows a landing
// page listing the sites (site packs) available to this user. A site's context
// rail only appears once a site is open. Everything here is generic: site names,
// sector words and statistics come from the endpoints themselves.

import { openInPanel, refreshContext } from './visualChat.js';
import { openExplorer } from './visualExplorer.js';

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

// The brand mark: an idli on a pine tile — a soft steamed disc with rising steam.
const IDLI_MARK_SVG = '<svg viewBox="0 0 32 32" width="28" height="28" aria-hidden="true">'
  + '<rect width="32" height="32" rx="8" fill="#1d5c45"/>'
  + '<ellipse cx="16" cy="20" rx="9.5" ry="5" fill="#fffdfa"/>'
  + '<path d="M12 13c-1.4-1.2-.2-2.6 0-3.8" stroke="#fffdfa" stroke-width="1.6" fill="none" stroke-linecap="round" opacity="0.75"/>'
  + '<path d="M16.5 12.4c-1.4-1.2-.2-2.6 0-3.8" stroke="#fffdfa" stroke-width="1.6" fill="none" stroke-linecap="round" opacity="0.55"/>'
  + '<path d="M21 13c-1.4-1.2-.2-2.6 0-3.8" stroke="#fffdfa" stroke-width="1.6" fill="none" stroke-linecap="round" opacity="0.75"/>'
  + '</svg>';

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
  document.documentElement.style.setProperty('--bg', dark ? '#16140f' : '#f7f5f0');
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

  const brand = document.createElement('div');
  brand.className = 'eco-brand';
  const mark = document.createElement('span');
  mark.className = 'eco-brand-mark';
  mark.innerHTML = IDLI_MARK_SVG;
  brand.appendChild(mark);
  const name = document.createElement('span');
  name.className = 'eco-brand-name';
  name.textContent = 'Idli Insights';
  brand.appendChild(name);
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
    ['chat', 'Chat', () => { hideLanding(); }],
    ['map', 'Maps', () => openLatestVisual()],
    ['data', 'Data', () => openDataExplorer()],
    ['history', 'History', () => toggleHistory()],
    ['research', 'Sites', () => showLanding(true)],
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

async function openLatestVisual() {
  const els = [...document.querySelectorAll('.viz-inline[data-result-id]')];
  const last = els[els.length - 1];
  if (last) { openInPanel(last.dataset.resultId); return; }
  // Nothing on screen yet: orient on the site's own map.
  const active = await syncActiveSite();
  if (!active) { showLanding(true); return; }
  try {
    const r = await fetch(`/api/visual/${encodeURIComponent(active.endpointId)}/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ capability_id: 'site-orientation', arguments: {}, question: '' }),
    });
    if (r.ok) {
      const env = await r.json();
      if (env.result_id) openInPanel(env.result_id);
    }
  } catch { /* leave the chat as it is */ }
}

async function openDataExplorer() {
  const active = await syncActiveSite();
  if (!active) { showLanding(true); return; }
  openExplorer(active.endpointId);
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

  const head = document.createElement('header');
  head.className = 'eco-landing-head';
  const h1 = document.createElement('h1');
  h1.textContent = 'Choose a site to ask a question.';
  head.appendChild(h1);
  const sub = document.createElement('p');
  sub.textContent = 'Idli Insights lets you explore your data visually, in plain conversation.';
  head.appendChild(sub);
  inner.appendChild(head);

  const grid = document.createElement('div');
  grid.className = 'eco-site-grid';
  inner.appendChild(grid);

  const loading = document.createElement('div');
  loading.className = 'eco-landing-loading';
  loading.textContent = 'Looking for available sites…';
  grid.appendChild(loading);

  const sites = await discoverSites(force);
  grid.replaceChildren();
  if (!sites.length) {
    const none = document.createElement('div');
    none.className = 'eco-landing-loading';
    none.textContent = 'No site packs are available on this account yet.';
    grid.appendChild(none);
  }
  for (const site of sites) {
    const card = document.createElement('div');
    card.className = 'eco-card';
    card.setAttribute('role', 'button');
    card.tabIndex = 0;
    const top = document.createElement('div');
    top.className = 'eco-card-top';
    const title = document.createElement('span');
    title.className = 'eco-card-title';
    title.textContent = site.label;
    top.appendChild(title);
    if (site.synthetic) {
      const tag = document.createElement('span');
      tag.className = 'eco-card-tag';
      tag.textContent = 'Test data';
      top.appendChild(tag);
    }
    card.appendChild(top);

    const stats = document.createElement('div');
    stats.className = 'eco-card-stats';
    stats.textContent = 'Loading…';
    card.appendChild(stats);

    const foot = document.createElement('div');
    foot.className = 'eco-card-foot';
    foot.textContent = 'Open site →';
    card.appendChild(foot);

    card.addEventListener('click', () => openSite(site));
    card.addEventListener('keydown', (ev) => {
      if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); openSite(site); }
    });
    grid.appendChild(card);

    siteBlurb(site).then((lines) => {
      stats.replaceChildren();
      if (!lines.length) { stats.textContent = 'Ready'; return; }
      for (const line of lines) {
        const row = document.createElement('span');
        row.className = 'eco-card-stat';
        row.textContent = line;
        stats.appendChild(row);
      }
    });
  }
  landingEl.dataset.built = '1';
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

// A site briefing replaces the generic product welcome, so an empty chat still
// tells you what this site holds and what you can ask of it.
async function renderSiteWelcome(site) {
  const host = document.getElementById('chat-history') || document.querySelector('.chat-history');
  if (!host) return;
  const old = document.getElementById('eco-welcome');
  if (old) old.remove();
  const wrap = document.createElement('div');
  wrap.id = 'eco-welcome';
  const h = document.createElement('h2');
  h.textContent = site.label;
  wrap.appendChild(h);
  const p = document.createElement('p');
  p.textContent = site.synthetic
    ? 'A synthetic test pack. Numbers here are made up for testing, but every one of them can be traced.'
    : 'Ask about this place in plain words. Every answer comes with a visual you can open and trace to its records.';
  wrap.appendChild(p);
  const stats = document.createElement('div');
  stats.className = 'eco-welcome-stats';
  wrap.appendChild(stats);
  const chips = document.createElement('div');
  chips.className = 'eco-welcome-chips';
  for (const q of [
    'What data do you have for this place?',
    'Where are records concentrated?',
    'What is missing here?',
  ]) {
    const chip = document.createElement('button');
    chip.className = 'eco-welcome-chip';
    chip.textContent = q;
    chip.addEventListener('click', () => {
      const input = document.getElementById('message');
      if (!input) return;
      input.value = q;
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.focus();
    });
    chips.appendChild(chip);
  }
  wrap.appendChild(chips);
  host.appendChild(wrap);
  siteBlurb(site).then((lines) => {
    for (const line of lines) {
      const s2 = document.createElement('span');
      s2.className = 'eco-welcome-stat';
      s2.textContent = line;
      stats.appendChild(s2);
    }
  });
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
  // The product always opens on the site-selection page; a restored
  // conversation stays one Chat click away.
  showLanding(true);
  setActiveNav('research');
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
