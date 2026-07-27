// visualAtlas.js — the pack as a graph: where the data comes from, and how
// measurements and recorded names connect. Full-page view under the Data nav.
//
// Two levels, both deliberately small:
//   Overview — a left-to-right flow: sources → kinds of measurement → the
//   most-recorded entities, ribbon width ∝ records. ~25 elements, no motion.
//   Focus — one node at the centre with its neighbors grouped by relation,
//   every edge counted, one hop per click, breadcrumbs back.
//
// The graph is an index, not an analysis engine: node click-throughs seed the
// mapped question into the composer, so insight still flows through audited
// turns. Data comes from the producer's bounded /v1/graph (IDL-REQ-0003); the
// contract fixtures render as a labelled sample until that endpoint ships.

import { tooltip } from './visualRenderers.js';
import { cleanText, formatNumber } from './visualTheme.js';

const FIXTURE_BASE = '/static/contracts/fixtures/graph';
const FIXTURE_NODES = {
  'ent:a': 'node-ent-a.json',
  'ent:c': 'node-ent-c.json',
  'src:frugivore-watch': 'node-src-frugivore-watch.json',
};
const SVGNS = 'http://www.w3.org/2000/svg';

let atlasEl = null;
let state = null; // { endpointId, sample, overview, trail: [{id,label}] }

function el(tag, cls, text) {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text !== undefined) node.textContent = text;
  return node;
}

function svgEl(tag, attrs) {
  const node = document.createElementNS(SVGNS, tag);
  for (const [k, v] of Object.entries(attrs || {})) node.setAttribute(k, v);
  return node;
}

async function fetchJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${res.status}`);
  return res.json();
}

async function loadOverview(endpointId) {
  if (endpointId) {
    try {
      return { data: await fetchJson(`/api/visual/${encodeURIComponent(endpointId)}/graph`), sample: false };
    } catch { /* endpoint not shipped yet — fall through to the fixture */ }
  }
  return { data: await fetchJson(`${FIXTURE_BASE}/overview.json`), sample: true };
}

async function loadNode(nodeId) {
  if (!state.sample && state.endpointId) {
    try {
      return await fetchJson(
        `/api/visual/${encodeURIComponent(state.endpointId)}/graph/node/${encodeURIComponent(nodeId)}`);
    } catch { return null; }
  }
  const file = FIXTURE_NODES[nodeId];
  if (!file) return null;
  try { return await fetchJson(`${FIXTURE_BASE}/${file}`); } catch { return null; }
}

// ---- shell -----------------------------------------------------------------
function ensureAtlas() {
  if (atlasEl) return atlasEl;
  atlasEl = el('div');
  atlasEl.id = 'eco-atlas';
  document.body.appendChild(atlasEl);
  return atlasEl;
}

export function hideAtlas() {
  document.body.classList.remove('eco-atlas-open');
}

export async function openAtlas(endpointId, openExplorerFn) {
  ensureAtlas();
  document.body.classList.remove('eco-landing-open');
  document.body.classList.add('eco-atlas-open');
  atlasEl.replaceChildren();
  const inner = el('div', 'eco-atlas-inner');
  atlasEl.appendChild(inner);
  const loading = el('div', 'eco-landing-loading', 'Reading the shape of this pack…');
  inner.appendChild(loading);
  let overview;
  try {
    overview = await loadOverview(endpointId);
  } catch {
    loading.textContent = 'The pack graph is not available right now.';
    return;
  }
  state = { endpointId, sample: overview.sample, overview: overview.data, trail: [], openExplorerFn };
  renderOverview();
}

function header(titleText, subText) {
  const head = el('header', 'eco-atlas-head');
  const titleRow = el('div', 'eco-atlas-title-row');
  const h1 = el('h1', 'eco-atlas-title', titleText);
  titleRow.appendChild(h1);
  if (state.sample) {
    const ribbon = el('span', 'viz-synthetic-ribbon', 'Sample data — live graph pending (IDL-REQ-0003)');
    titleRow.appendChild(ribbon);
  } else if (state.overview.site && state.overview.site.synthetic) {
    titleRow.appendChild(el('span', 'viz-synthetic-ribbon', 'Synthetic test data'));
  }
  head.appendChild(titleRow);
  head.appendChild(el('p', 'eco-atlas-sub', subText));
  return head;
}

function controls() {
  const row = el('div', 'eco-atlas-controls');
  const search = document.createElement('input');
  search.type = 'search';
  search.className = 'eco-explorer-search eco-atlas-search';
  search.placeholder = 'Find a recorded name…';
  search.addEventListener('input', () => filterEntities(search.value));
  row.appendChild(search);
  if (state.openExplorerFn) {
    const inv = el('button', 'eco-atlas-inventory-btn', 'Browse the inventory →');
    inv.type = 'button';
    inv.addEventListener('click', () => state.openExplorerFn());
    row.appendChild(inv);
  }
  return row;
}

// ---- overview: sources → measurements → entities ---------------------------
const KIND_COLUMNS = ['source', 'measurement', 'entity'];
const COL_X = { source: 0.14, measurement: 0.5, entity: 0.86 };
const PILL_W = 208;
const PILL_H = 44;
const ROW_GAP = 14;

function kindLabel(kind) {
  const k = (state.overview.node_kinds || []).find((x) => x.kind === kind);
  return (k && k.label) || kind;
}

function renderOverview() {
  state.trail = [];
  const inner = atlasEl.querySelector('.eco-atlas-inner');
  inner.replaceChildren();
  const site = state.overview.site || {};
  inner.appendChild(header(
    site.label ? `How ${site.label}'s data fits together` : 'How this pack fits together',
    'Data sets on the left, what they measure in the middle, and the most-recorded '
    + 'names on the right. Ribbons are record counts — follow one to see where a '
    + 'number would come from, or click anything to look closer.'));
  inner.appendChild(controls());

  const stage = el('div', 'eco-atlas-stage');
  inner.appendChild(stage);

  const nodes = (state.overview.nodes || []).filter((n) => KIND_COLUMNS.includes(n.kind));
  const byKind = new Map(KIND_COLUMNS.map((k) => [k, []]));
  for (const n of nodes) byKind.get(n.kind).push(n);
  for (const list of byKind.values()) list.sort((a, b) => (b.records || 0) - (a.records || 0));

  const rows = Math.max(...KIND_COLUMNS.map((k) => byKind.get(k).length), 1);
  const height = Math.max(360, rows * (PILL_H + ROW_GAP) + 90);
  const svg = svgEl('svg', {
    class: 'eco-atlas-svg', viewBox: `0 0 1200 ${height}`,
    preserveAspectRatio: 'xMidYMin meet', role: 'img',
    'aria-label': 'Pack graph: sources, measurements and recorded names',
  });
  stage.appendChild(svg);

  // column headings with kind totals
  for (const kind of KIND_COLUMNS) {
    const total = ((state.overview.node_kinds || []).find((x) => x.kind === kind) || {}).count;
    const t = svgEl('text', {
      x: 1200 * COL_X[kind], y: 24, 'text-anchor': 'middle', class: 'eco-atlas-colhead',
    });
    t.textContent = kindLabel(kind) + (Number.isFinite(total) ? ` · ${formatNumber(total)}` : '');
    svg.appendChild(t);
  }

  // node positions
  const pos = new Map();
  for (const kind of KIND_COLUMNS) {
    const list = byKind.get(kind);
    const colH = list.length * PILL_H + (list.length - 1) * ROW_GAP;
    let y = Math.max(48, (height - colH) / 2);
    for (const n of list) {
      pos.set(n.id, { x: 1200 * COL_X[kind] - PILL_W / 2, y, node: n });
      y += PILL_H + ROW_GAP;
    }
  }

  // edges beneath nodes
  const maxRecords = Math.max(...(state.overview.edges || []).map((e) => e.records || 1), 1);
  const edgeLayer = svgEl('g', { class: 'eco-atlas-edges' });
  svg.appendChild(edgeLayer);
  for (const edge of state.overview.edges || []) {
    const a = pos.get(edge.from), b = pos.get(edge.to);
    if (!a || !b) continue;
    const x1 = a.x + PILL_W, y1 = a.y + PILL_H / 2;
    const x2 = b.x, y2 = b.y + PILL_H / 2;
    const mx = (x1 + x2) / 2;
    const path = svgEl('path', {
      d: `M ${x1} ${y1} C ${mx} ${y1}, ${mx} ${y2}, ${x2} ${y2}`,
      class: 'eco-atlas-ribbon',
      'stroke-width': Math.max(1.5, 13 * Math.sqrt((edge.records || 1) / maxRecords)),
      'data-from': edge.from, 'data-to': edge.to,
      fill: 'none',
    });
    path.addEventListener('mousemove', (ev) => {
      tooltip().show(ev, [
        { value: `${pos.get(edge.from).node.label} → ${pos.get(edge.to).node.label}`, label: '', header: true },
        { value: formatNumber(edge.records), label: 'records', strong: true },
      ]);
    });
    path.addEventListener('mouseleave', () => tooltip().hide());
    edgeLayer.appendChild(path);
  }

  // node pills
  for (const { x, y, node } of pos.values()) {
    svg.appendChild(nodePill(node, x, y, () => focusNode(node.id, node.label)));
  }

  // the honest fold: entities the cap omitted
  const omitted = ((state.overview.more || {}).entity || {}).omitted;
  if (omitted) {
    const list = byKind.get('entity');
    const last = list.length
      ? pos.get(list[list.length - 1].id) : { y: 48 - PILL_H - ROW_GAP };
    const g = svgEl('g', { class: 'eco-atlas-more', transform: `translate(${1200 * COL_X.entity - PILL_W / 2}, ${last.y + PILL_H + ROW_GAP})` });
    const r = svgEl('rect', { width: PILL_W, height: 34, rx: 9, class: 'eco-atlas-more-box' });
    g.appendChild(r);
    const t = svgEl('text', { x: PILL_W / 2, y: 22, 'text-anchor': 'middle', class: 'eco-atlas-more-text' });
    t.textContent = `…and ${formatNumber(omitted)} more — search above`;
    g.appendChild(t);
    g.addEventListener('click', () => {
      const s = atlasEl.querySelector('.eco-atlas-search');
      if (s) s.focus();
    });
    svg.appendChild(g);
  }
}

function nodePill(node, x, y, onOpen) {
  const g = svgEl('g', { class: `eco-atlas-node eco-atlas-node-${node.kind}`, transform: `translate(${x}, ${y})`, tabindex: 0, role: 'button', 'data-node': node.id });
  g.appendChild(svgEl('rect', { width: PILL_W, height: PILL_H, rx: 10, class: 'eco-atlas-pill' }));
  const label = svgEl('text', { x: 12, y: 19, class: 'eco-atlas-node-label' });
  const text = cleanText(node.label);
  label.textContent = text.length > 26 ? text.slice(0, 25).trimEnd() + '…' : text;
  g.appendChild(label);
  const meta = svgEl('text', { x: 12, y: 35, class: 'eco-atlas-node-meta' });
  meta.textContent = `${formatNumber(node.records || 0)} records`
    + (Number.isFinite(node.sources) ? ` · ${node.sources} source${node.sources === 1 ? '' : 's'}` : '');
  g.appendChild(meta);
  const open = () => onOpen && onOpen();
  g.addEventListener('click', open);
  g.addEventListener('keydown', (ev) => {
    if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); open(); }
  });
  g.addEventListener('mouseenter', () => setEdgeHighlight(node.id, true));
  g.addEventListener('mouseleave', () => setEdgeHighlight(node.id, false));
  if (text.length > 26) {
    const t = svgEl('title', {});
    t.textContent = text;
    g.appendChild(t);
  }
  return g;
}

function setEdgeHighlight(nodeId, on) {
  for (const p of atlasEl.querySelectorAll('.eco-atlas-ribbon')) {
    const hit = p.dataset.from === nodeId || p.dataset.to === nodeId;
    p.classList.toggle('is-lit', on && hit);
    p.classList.toggle('is-dim', on && !hit);
  }
}

function filterEntities(text) {
  const needle = String(text || '').trim().toLowerCase();
  for (const g of atlasEl.querySelectorAll('.eco-atlas-node-entity')) {
    const node = (state.overview.nodes || []).find((n) => n.id === g.dataset.node);
    const hit = !needle || (node && node.label.toLowerCase().includes(needle));
    g.classList.toggle('is-faded', !hit);
  }
  // live endpoint: bounded server-side search folds unseen entities in
  if (needle.length >= 2 && !state.sample && state.endpointId) {
    clearTimeout(filterEntities._t);
    filterEntities._t = setTimeout(async () => {
      try {
        const found = await fetchJson(
          `/api/visual/${encodeURIComponent(state.endpointId)}/graph?q=${encodeURIComponent(needle)}`);
        renderSearchResults(found.nodes || []);
      } catch { /* search is optional */ }
    }, 250);
  } else {
    renderSearchResults([]);
  }
}

function renderSearchResults(nodes) {
  let box = atlasEl.querySelector('.eco-atlas-search-results');
  if (!nodes.length) { if (box) box.remove(); return; }
  if (!box) {
    box = el('div', 'eco-atlas-search-results');
    atlasEl.querySelector('.eco-atlas-controls').appendChild(box);
  }
  box.replaceChildren();
  for (const n of nodes.slice(0, 12)) {
    const b = el('button', 'eco-atlas-search-hit');
    b.type = 'button';
    b.appendChild(el('span', 'eco-atlas-search-hit-name', cleanText(n.label)));
    b.appendChild(el('span', 'eco-atlas-search-hit-meta', `${formatNumber(n.records || 0)} records`));
    b.addEventListener('click', () => focusNode(n.id, n.label));
    box.appendChild(b);
  }
}

// ---- focus: one node, its neighborhood -------------------------------------
async function focusNode(nodeId, label) {
  const inner = atlasEl.querySelector('.eco-atlas-inner');
  const detail = await loadNode(nodeId);
  if (!detail) {
    if (state.sample) {
      askAbout(label);
      return;
    }
    return;
  }
  state.trail.push({ id: nodeId, label: detail.node.label });
  renderFocus(detail);
  inner.scrollTop = 0;
}

function renderFocus(detail) {
  const inner = atlasEl.querySelector('.eco-atlas-inner');
  inner.replaceChildren();
  const node = detail.node || {};
  inner.appendChild(header(cleanText(node.label),
    `${kindLabel(node.kind)} · ${formatNumber(node.records || 0)} records. `
    + 'Each connection is counted; follow one to keep exploring, one hop at a time.'));

  // breadcrumbs
  const crumbs = el('nav', 'eco-atlas-crumbs');
  const home = el('button', 'eco-atlas-crumb', 'Overview');
  home.type = 'button';
  home.addEventListener('click', renderOverview);
  crumbs.appendChild(home);
  state.trail.forEach((step, i) => {
    crumbs.appendChild(el('span', 'eco-atlas-crumb-sep', '›'));
    const b = el('button', 'eco-atlas-crumb', cleanText(step.label));
    b.type = 'button';
    if (i === state.trail.length - 1) b.classList.add('is-here');
    else b.addEventListener('click', async () => {
      state.trail = state.trail.slice(0, i);
      await focusNode(step.id, step.label);
    });
    crumbs.appendChild(b);
  });
  inner.appendChild(crumbs);

  const stage = el('div', 'eco-atlas-stage');
  inner.appendChild(stage);

  const relations = detail.relations || [];
  const nAll = relations.reduce((s, r) => s + r.neighbors.length + (r.omitted ? 1 : 0), 0);
  const height = Math.max(420, 150 + Math.ceil(nAll / 2) * (PILL_H + ROW_GAP) + 60);
  const svg = svgEl('svg', {
    class: 'eco-atlas-svg', viewBox: `0 0 1200 ${height}`,
    preserveAspectRatio: 'xMidYMin meet', role: 'img',
    'aria-label': `Connections of ${node.label}`,
  });
  stage.appendChild(svg);

  const cx = 600, cy = height / 2;
  const edgeLayer = svgEl('g', {});
  svg.appendChild(edgeLayer);

  // neighbors fan out left/right, grouped by relation; edges carry the counts
  const sides = [-1, 1];
  const maxEdge = Math.max(...relations.flatMap((r) => r.neighbors.map((n) => n.records || 1)), 1);
  let sideRows = { '-1': [], 1: [] };
  relations.forEach((rel, ri) => {
    const side = sides[ri % 2];
    sideRows[side].push({ rel, header: true });
    for (const nb of rel.neighbors) sideRows[side].push({ rel, nb });
    if (rel.omitted) sideRows[side].push({ rel, omitted: rel.omitted });
  });
  for (const side of sides) {
    const rows = sideRows[side];
    const colH = rows.length * (PILL_H + ROW_GAP);
    let y = Math.max(56, cy - colH / 2);
    const x = side < 0 ? 90 : 1200 - 90 - PILL_W;
    for (const row of rows) {
      if (row.header) {
        const t = svgEl('text', { x: x + PILL_W / 2, y: y + 16, 'text-anchor': 'middle', class: 'eco-atlas-colhead' });
        t.textContent = cleanText(row.rel.label || row.rel.relation);
        svg.appendChild(t);
        y += 34;
        continue;
      }
      if (row.omitted) {
        const t = svgEl('text', { x: x + PILL_W / 2, y: y + 14, 'text-anchor': 'middle', class: 'eco-atlas-more-text' });
        t.textContent = `…and ${formatNumber(row.omitted)} more`;
        svg.appendChild(t);
        y += 30;
        continue;
      }
      const nb = row.nb;
      const nx = x, ny = y;
      const ex1 = cx + (side < 0 ? -110 : 110), ey1 = cy;
      const ex2 = side < 0 ? nx + PILL_W : nx, ey2 = ny + PILL_H / 2;
      const mx = (ex1 + ex2) / 2;
      const path = svgEl('path', {
        d: `M ${ex1} ${ey1} C ${mx} ${ey1}, ${mx} ${ey2}, ${ex2} ${ey2}`,
        class: 'eco-atlas-ribbon',
        'stroke-width': Math.max(1.5, 11 * Math.sqrt((nb.records || 1) / maxEdge)),
        fill: 'none',
      });
      path.addEventListener('mousemove', (ev) => tooltip().show(ev, [
        { value: cleanText(nb.node.label), label: '', header: true },
        { value: formatNumber(nb.records || 0), label: 'records together', strong: true },
      ]));
      path.addEventListener('mouseleave', () => tooltip().hide());
      edgeLayer.appendChild(path);
      // count sits on the ribbon, near the neighbor
      const ct = svgEl('text', {
        x: side < 0 ? nx + PILL_W + 26 : nx - 26, y: ey2 + 4,
        'text-anchor': side < 0 ? 'start' : 'end', class: 'eco-atlas-edge-count',
      });
      ct.textContent = formatNumber(nb.records || 0);
      svg.appendChild(ct);
      svg.appendChild(nodePill({ ...nb.node, records: nb.node.records ?? nb.records }, nx, ny,
        () => focusNode(nb.node.id, nb.node.label)));
      y += PILL_H + ROW_GAP;
    }
  }

  // the centre card, drawn last so it sits above ribbons
  const centre = svgEl('g', { class: 'eco-atlas-centre', transform: `translate(${cx - 110}, ${cy - 44})` });
  centre.appendChild(svgEl('rect', { width: 220, height: 88, rx: 14, class: 'eco-atlas-centre-box' }));
  const cl = svgEl('text', { x: 110, y: 34, 'text-anchor': 'middle', class: 'eco-atlas-centre-label' });
  const ctext = cleanText(node.label);
  cl.textContent = ctext.length > 24 ? ctext.slice(0, 23).trimEnd() + '…' : ctext;
  centre.appendChild(cl);
  const cm = svgEl('text', { x: 110, y: 58, 'text-anchor': 'middle', class: 'eco-atlas-centre-meta' });
  cm.textContent = `${formatNumber(node.records || 0)} records`;
  centre.appendChild(cm);
  svg.appendChild(centre);

  // actions: the graph hands off to the audited conversation
  const acts = el('div', 'eco-atlas-actions');
  for (const a of (detail.actions || []).filter((a) => a && a.label).slice(0, 3)) {
    const chip = el('button', 'viz-action-chip', cleanText(a.label));
    chip.type = 'button';
    chip.addEventListener('click', () => askAbout(null, a.label));
    acts.appendChild(chip);
  }
  if (!acts.childElementCount) {
    const chip = el('button', 'viz-action-chip', `Ask about ${cleanText(node.label)}`);
    chip.type = 'button';
    chip.addEventListener('click', () => askAbout(node.label));
    acts.appendChild(chip);
  }
  inner.appendChild(acts);
}

function askAbout(label, exactText) {
  const input = document.getElementById('message');
  if (!input) return;
  input.value = exactText || `What data do you have for ${cleanText(label)}?`;
  input.dispatchEvent(new Event('input', { bubbles: true }));
  hideAtlas();
  input.focus();
}
