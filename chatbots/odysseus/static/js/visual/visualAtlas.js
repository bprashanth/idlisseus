// visualAtlas.js — the pack as a subject-centred relationship explorer.
//
// The model is how people think, not how the pipeline runs: you search for the
// thing you care about — a recorded name, a place, a group, a data set — make
// it the anchor of the canvas, and walk outward one bounded neighbourhood at a
// time. Expansions MERGE into the existing graph (stable ids, never replaced),
// up to three hops from the nearest anchor; prominence decays with distance.
//
// Every edge keeps its producer-supplied relation, label, count and evidence
// basis: explicitly recorded relationships draw solid, derived ones (shared
// source, shared location) draw dashed and lighter — never colour alone.
// Budgets cap the canvas (per-relation producer caps + total node/edge budgets
// here) and omissions are counted, not hidden.
//
// Clicking a node opens its detail panel — relations, provenance, capability
// actions. Nothing is ever sent to the chat automatically; an action fills the
// composer and leaves the sending to the person.
//
// Data: /v1/graph (starting points + kind totals), /v1/graph?q= (search across
// every node kind and alias), /v1/graph/node/{id} (the bounded expansion
// primitive) — IDL-REQ-0003 (amended). The consumer never infers identity,
// membership or relationships; fixtures render as a labelled sample until the
// producer ships.

import { tooltip } from './visualRenderers.js';
import { cleanText, formatNumber } from './visualTheme.js';

const FIXTURE_BASE = '/static/contracts/fixtures/graph';
const SVGNS = 'http://www.w3.org/2000/svg';

const NODE_BUDGET = 60;
const EDGE_BUDGET = 140;
const MAX_HOP = 3;

// Pill geometry per prominence tier (hop distance from the nearest anchor).
const TIERS = [
  { w: 236, h: 54, label: 15, meta: 11, cls: 'hop0' },
  { w: 204, h: 46, label: 13, meta: 10.5, cls: 'hop1' },
  { w: 178, h: 40, label: 12, meta: 10, cls: 'hop2' },
  { w: 156, h: 34, label: 11, meta: 9.5, cls: 'hop3' },
];

let atlasEl = null;
let state = null;

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

// ---- data access (live first, labelled fixture sample as fallback) ---------
async function loadStart(endpointId) {
  if (endpointId) {
    try {
      return { data: await fetchJson(`/api/visual/${encodeURIComponent(endpointId)}/graph`), sample: false };
    } catch { /* endpoint pending — sample below */ }
  }
  return { data: await fetchJson(`${FIXTURE_BASE}/overview.json`), sample: true };
}

async function searchNodes(text) {
  const needle = String(text || '').trim().toLowerCase();
  if (needle.length < 2) return [];
  if (!state.sample && state.endpointId) {
    try {
      const out = await fetchJson(
        `/api/visual/${encodeURIComponent(state.endpointId)}/graph?q=${encodeURIComponent(needle)}`);
      return out.nodes || [];
    } catch { return []; }
  }
  // Sample: one canned index across every kind and alias.
  try {
    const idx = await fetchJson(`${FIXTURE_BASE}/search.json`);
    return (idx.nodes || []).filter((n) =>
      [n.label, ...(n.aliases || [])].some((a) => String(a).toLowerCase().includes(needle)));
  } catch { return []; }
}

async function loadNode(nodeId) {
  if (!state.sample && state.endpointId) {
    try {
      return await fetchJson(
        `/api/visual/${encodeURIComponent(state.endpointId)}/graph/node/${encodeURIComponent(nodeId)}`);
    } catch { return null; }
  }
  const file = 'node-' + nodeId.replace(/[^A-Za-z0-9]+/g, '-') + '.json';
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
  inner.appendChild(el('div', 'eco-landing-loading', 'Reading the shape of this pack…'));
  let start;
  try {
    start = await loadStart(endpointId);
  } catch {
    inner.replaceChildren(el('div', 'eco-landing-loading', 'The pack graph is not available right now.'));
    return;
  }
  state = {
    endpointId,
    sample: start.sample,
    start: start.data,
    openExplorerFn,
    nodes: new Map(),      // id -> {node, x, y, hop, expanded}
    edges: new Map(),      // key -> {from, to, relation, label, records, basis}
    anchors: new Set(),    // searched/re-focused node ids: hop 0
    relationStyles: new Map(), // relation -> {label, basis}
    omittedByBudget: 0,
    selected: null,
  };
  renderShell();
}

function kindLabel(kind, plural) {
  const k = (state.start.node_kinds || []).find((x) => x.kind === kind);
  const label = (k && k.label) || kind;
  return plural ? label : label.replace(/s$/, '');
}

// ---- static frame ----------------------------------------------------------
function renderShell() {
  const inner = atlasEl.querySelector('.eco-atlas-inner');
  inner.replaceChildren();

  const head = el('header', 'eco-atlas-head');
  const titleRow = el('div', 'eco-atlas-title-row');
  const site = state.start.site || {};
  titleRow.appendChild(el('h1', 'eco-atlas-title',
    site.label ? `Explore ${site.label}'s data` : 'Explore this pack'));
  if (state.sample) {
    titleRow.appendChild(el('span', 'viz-synthetic-ribbon', 'Sample data — live graph pending (IDL-REQ-0003)'));
  } else if (site.synthetic) {
    titleRow.appendChild(el('span', 'viz-synthetic-ribbon', 'Synthetic test data'));
  }
  head.appendChild(titleRow);
  head.appendChild(el('p', 'eco-atlas-sub',
    'Start from anything — a recorded name, a place, a group, a data set — and walk '
    + 'its connections one bounded step at a time. Solid links are explicitly recorded; '
    + 'dashed links are derived (a shared source or place). Every link is counted.'));
  inner.appendChild(head);

  const controls = el('div', 'eco-atlas-controls');
  const search = document.createElement('input');
  search.type = 'search';
  search.className = 'eco-explorer-search eco-atlas-search';
  search.placeholder = 'Search names, places, groups, data sets…';
  let t = null;
  search.addEventListener('input', () => {
    clearTimeout(t);
    t = setTimeout(async () => renderSearchResults(await searchNodes(search.value)), 220);
  });
  controls.appendChild(search);
  if (state.openExplorerFn) {
    const inv = el('button', 'eco-atlas-inventory-btn', 'Browse the inventory →');
    inv.type = 'button';
    inv.addEventListener('click', () => state.openExplorerFn());
    controls.appendChild(inv);
  }
  inner.appendChild(controls);

  const body = el('div', 'eco-atlas-body');
  inner.appendChild(body);
  const stage = el('div', 'eco-atlas-stage');
  body.appendChild(stage);
  const detail = el('aside', 'eco-atlas-detail');
  detail.hidden = true;
  body.appendChild(detail);

  const status = el('div', 'eco-atlas-status');
  inner.appendChild(status);

  renderCanvas();
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
    const left = el('span', 'eco-atlas-search-hit-name', cleanText(n.label));
    b.appendChild(left);
    const right = el('span', 'eco-atlas-search-hit-meta',
      `${kindLabel(n.kind)} · ${formatNumber(n.records || 0)} records`);
    b.appendChild(right);
    b.addEventListener('click', async () => {
      box.remove();
      await anchorNode(n);
    });
    box.appendChild(b);
  }
}

// ---- graph state -----------------------------------------------------------
function edgeKey(a, b, relation) {
  return [a, b].sort().join('→') + '·' + relation;
}

function recomputeHops() {
  // BFS from all anchors; prominence = distance to the nearest anchor.
  for (const entry of state.nodes.values()) entry.hop = Infinity;
  const adj = new Map();
  for (const e of state.edges.values()) {
    if (!adj.has(e.from)) adj.set(e.from, []);
    if (!adj.has(e.to)) adj.set(e.to, []);
    adj.get(e.from).push(e.to);
    adj.get(e.to).push(e.from);
  }
  const queue = [];
  for (const id of state.anchors) {
    const entry = state.nodes.get(id);
    if (entry) { entry.hop = 0; queue.push(id); }
  }
  while (queue.length) {
    const id = queue.shift();
    const d = state.nodes.get(id).hop;
    for (const next of adj.get(id) || []) {
      const entry = state.nodes.get(next);
      if (entry && entry.hop > d + 1) { entry.hop = d + 1; queue.push(next); }
    }
  }
  for (const entry of state.nodes.values()) {
    if (!Number.isFinite(entry.hop)) entry.hop = MAX_HOP;
  }
}

// Incremental collision-avoiding placement: new nodes ring their parent in
// free angular space; existing nodes never move, so the graph accretes.
function placeAround(parent, count) {
  const spots = [];
  const px = parent ? parent.x : 640, py = parent ? parent.y : 420;
  let radius = parent ? 230 : 0;
  let placed = 0;
  let attempt = 0;
  const GOLDEN = 2.399963;
  while (placed < count && attempt < count * 40) {
    const angle = attempt * GOLDEN;
    const x = px + Math.cos(angle) * radius;
    const y = py + Math.sin(angle) * radius * 0.62; // gentle vertical squash
    attempt += 1;
    if (attempt % 18 === 0) radius += 90;
    let clear = true;
    for (const other of state.nodes.values()) {
      if (Math.abs(other.x - x) < 215 && Math.abs(other.y - y) < 64) { clear = false; break; }
    }
    for (const s of spots) {
      if (Math.abs(s.x - x) < 215 && Math.abs(s.y - y) < 64) { clear = false; break; }
    }
    if (!clear) continue;
    spots.push({ x, y });
    placed += 1;
  }
  while (spots.length < count) {
    spots.push({ x: px + (spots.length + 1) * 240, y: py + 240 });
  }
  return spots;
}

function mergeNode(node, near) {
  const existing = state.nodes.get(node.id);
  if (existing) {
    existing.node = { ...existing.node, ...node };
    return existing;
  }
  if (state.nodes.size >= NODE_BUDGET) { state.omittedByBudget += 1; return null; }
  const [spot] = placeAround(near, 1);
  const entry = { node, x: spot.x, y: spot.y, hop: MAX_HOP, expanded: false };
  state.nodes.set(node.id, entry);
  return entry;
}

async function anchorNode(node) {
  // A searched (or re-focused) node becomes an anchor: dominant, hop 0.
  const entry = mergeNode(node, null) || state.nodes.get(node.id);
  if (!entry) return;
  state.anchors.add(node.id);
  entry.hop = 0; // before the expansion guard reads it
  state.selected = node.id;
  await expandNode(node.id);
}

async function expandNode(nodeId) {
  const entry = state.nodes.get(nodeId);
  if (!entry) return;
  if (entry.hop >= MAX_HOP) {
    // Three hops is the horizon; walking further means re-anchoring here.
    renderCanvas();
    renderDetail(nodeId, null, 'Three hops from your search — make it a focus to keep walking.');
    return;
  }
  const detail = await loadNode(nodeId);
  entry.expanded = true;
  if (detail) {
    entry.node = { ...entry.node, ...detail.node };
    for (const rel of detail.relations || []) {
      state.relationStyles.set(rel.relation, {
        label: rel.label || rel.relation,
        basis: rel.basis || 'recorded',
      });
      for (const nb of rel.neighbors || []) {
        if (state.edges.size >= EDGE_BUDGET) { state.omittedByBudget += 1; continue; }
        const added = mergeNode(nb.node, entry);
        if (!added) continue;
        const key = edgeKey(nodeId, nb.node.id, rel.relation);
        if (!state.edges.has(key)) {
          state.edges.set(key, {
            from: nodeId, to: nb.node.id,
            relation: rel.relation,
            label: rel.label || rel.relation,
            basis: rel.basis || 'recorded',
            records: nb.records || 0,
          });
        }
      }
      if (rel.omitted) entry[`omitted:${rel.relation}`] = rel.omitted;
    }
    entry.detail = detail;
  }
  recomputeHops();
  renderCanvas();
  renderDetail(nodeId, entry.detail || null);
}

// ---- canvas ----------------------------------------------------------------
function tierFor(hop) {
  return TIERS[Math.max(0, Math.min(TIERS.length - 1, hop))];
}

function renderCanvas() {
  const stage = atlasEl.querySelector('.eco-atlas-stage');
  stage.replaceChildren();

  if (!state.nodes.size) {
    stage.appendChild(emptyState());
    renderStatus();
    return;
  }

  // fit the viewBox to the accreted graph
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const n of state.nodes.values()) {
    const t = tierFor(n.hop);
    minX = Math.min(minX, n.x - t.w / 2); maxX = Math.max(maxX, n.x + t.w / 2);
    minY = Math.min(minY, n.y - t.h / 2); maxY = Math.max(maxY, n.y + t.h / 2);
  }
  const pad = 60;
  const vb = [minX - pad, minY - pad, Math.max(900, maxX - minX + pad * 2), Math.max(480, maxY - minY + pad * 2)];
  const svg = svgEl('svg', {
    class: 'eco-atlas-svg', viewBox: vb.join(' '),
    preserveAspectRatio: 'xMidYMid meet', role: 'img',
    'aria-label': 'Relationship graph',
  });
  stage.appendChild(svg);

  const edgeLayer = svgEl('g', {});
  svg.appendChild(edgeLayer);
  const maxRecords = Math.max(...[...state.edges.values()].map((e) => e.records || 1), 1);
  for (const e of state.edges.values()) {
    const a = state.nodes.get(e.from), b = state.nodes.get(e.to);
    if (!a || !b) continue;
    const midX = (a.x + b.x) / 2, midY = (a.y + b.y) / 2 - 26;
    const path = svgEl('path', {
      d: `M ${a.x} ${a.y} Q ${midX} ${midY}, ${b.x} ${b.y}`,
      class: `eco-atlas-ribbon basis-${e.basis === 'derived' ? 'derived' : 'recorded'}`,
      'stroke-width': Math.max(1.4, 9 * Math.sqrt((e.records || 1) / maxRecords)),
      'data-from': e.from, 'data-to': e.to,
      fill: 'none',
    });
    path.addEventListener('mousemove', (ev) => tooltip().show(ev, [
      { value: `${cleanText(a.node.label)} — ${cleanText(b.node.label)}`, label: '', header: true },
      { value: cleanText(e.label), label: e.basis === 'derived' ? '(derived)' : '(recorded)' },
      { value: formatNumber(e.records), label: 'records', strong: true },
    ]));
    path.addEventListener('mouseleave', () => tooltip().hide());
    edgeLayer.appendChild(path);
  }

  for (const [id, entry] of state.nodes) {
    svg.appendChild(nodePill(id, entry));
  }

  renderLegend(stage);
  renderStatus();
}

function emptyState() {
  const wrap = el('div', 'eco-atlas-empty');
  wrap.appendChild(el('p', 'eco-atlas-empty-lead',
    'Search above, or start from one of the most-recorded things in this pack:'));
  const chips = el('div', 'eco-atlas-suggestions');
  const starters = (state.start.nodes || [])
    .slice()
    .sort((a, b) => (b.records || 0) - (a.records || 0))
    .slice(0, 9);
  for (const n of starters) {
    const chip = el('button', 'eco-atlas-suggestion');
    chip.type = 'button';
    chip.appendChild(el('span', 'eco-atlas-suggestion-name', cleanText(n.label)));
    chip.appendChild(el('span', 'eco-atlas-suggestion-meta',
      `${kindLabel(n.kind)} · ${formatNumber(n.records || 0)}`));
    chip.addEventListener('click', () => anchorNode(n));
    chips.appendChild(chip);
  }
  wrap.appendChild(chips);
  return wrap;
}

function nodePill(id, entry) {
  const t = tierFor(entry.hop);
  const x = entry.x - t.w / 2, y = entry.y - t.h / 2;
  const classes = ['eco-atlas-node', `eco-atlas-node-${entry.node.kind}`, `eco-atlas-${t.cls}`];
  if (state.anchors.has(id)) classes.push('is-anchor');
  if (state.selected === id) classes.push('is-selected');
  const g = svgEl('g', {
    class: classes.join(' '), transform: `translate(${x}, ${y})`,
    tabindex: 0, role: 'button', 'data-node': id,
  });
  g.appendChild(svgEl('rect', { width: t.w, height: t.h, rx: 11, class: 'eco-atlas-pill' }));
  const label = svgEl('text', { x: 12, y: t.h / 2 - 2, class: 'eco-atlas-node-label', 'font-size': t.label });
  const text = cleanText(entry.node.label);
  const maxChars = Math.floor(t.w / (t.label * 0.56));
  label.textContent = text.length > maxChars ? text.slice(0, maxChars - 1).trimEnd() + '…' : text;
  g.appendChild(label);
  const meta = svgEl('text', { x: 12, y: t.h - 8, class: 'eco-atlas-node-meta', 'font-size': t.meta });
  meta.textContent = `${kindLabel(entry.node.kind)} · ${formatNumber(entry.node.records || 0)}`;
  g.appendChild(meta);
  if (!entry.expanded && entry.hop < MAX_HOP) {
    const hint = svgEl('circle', { cx: t.w - 12, cy: 12, r: 3.5, class: 'eco-atlas-expandable-dot' });
    g.appendChild(hint);
  }
  const open = () => selectNode(id);
  g.addEventListener('click', open);
  g.addEventListener('keydown', (ev) => {
    if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); open(); }
  });
  g.addEventListener('mouseenter', () => setEdgeHighlight(id, true));
  g.addEventListener('mouseleave', () => setEdgeHighlight(id, false));
  if (text.length > maxChars) {
    const title = svgEl('title', {});
    title.textContent = text;
    g.appendChild(title);
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

function renderLegend(stage) {
  if (!state.relationStyles.size) return;
  const legend = el('div', 'eco-atlas-legend');
  for (const [relation, style] of state.relationStyles) {
    const item = el('span', 'eco-atlas-legend-item');
    const key = el('span', `eco-atlas-legend-key basis-${style.basis === 'derived' ? 'derived' : 'recorded'}`);
    item.appendChild(key);
    item.appendChild(el('span', 'eco-atlas-legend-label',
      cleanText(style.label) + (style.basis === 'derived' ? ' (derived)' : '')));
    legend.appendChild(item);
  }
  stage.appendChild(legend);
}

function renderStatus() {
  const status = atlasEl.querySelector('.eco-atlas-status');
  if (!status) return;
  const bits = [];
  if (state.nodes.size) {
    bits.push(`${state.nodes.size} of at most ${NODE_BUDGET} things on the canvas`);
    bits.push(`${state.edges.size} connections`);
  }
  if (state.omittedByBudget) {
    bits.push(`${formatNumber(state.omittedByBudget)} not added — the canvas is at its budget; focus something to go deeper`);
  }
  status.textContent = bits.join(' · ');
}

// ---- detail panel ----------------------------------------------------------
async function selectNode(id) {
  state.selected = id;
  const entry = state.nodes.get(id);
  renderCanvas();
  if (entry && !entry.detail) {
    entry.detail = await loadNode(id);
  }
  renderDetail(id, entry ? entry.detail : null);
}

function renderDetail(id, detail, note) {
  const panel = atlasEl.querySelector('.eco-atlas-detail');
  const entry = state.nodes.get(id);
  if (!entry) { panel.hidden = true; return; }
  panel.hidden = false;
  panel.replaceChildren();
  const node = (detail && detail.node) || entry.node;

  const head = el('div', 'eco-atlas-detail-head');
  head.appendChild(el('span', 'eco-atlas-detail-title', cleanText(node.label)));
  const x = el('button', 'viz-panel-close', '×');
  x.addEventListener('click', () => { panel.hidden = true; state.selected = null; renderCanvas(); });
  head.appendChild(x);
  panel.appendChild(head);
  panel.appendChild(el('div', 'eco-atlas-detail-kind',
    `${kindLabel(node.kind)} · ${formatNumber(node.records || 0)} records`
    + (Number.isFinite(node.sources) ? ` · ${node.sources} source${node.sources === 1 ? '' : 's'}` : '')));
  if (note) panel.appendChild(el('p', 'eco-atlas-detail-note', note));

  // primary moves: walk outward, or re-anchor here
  const moves = el('div', 'eco-atlas-detail-moves');
  if (!entry.expanded && entry.hop < MAX_HOP) {
    const ex = el('button', 'eco-atlas-move-primary', 'Show its connections');
    ex.type = 'button';
    ex.addEventListener('click', () => expandNode(id));
    moves.appendChild(ex);
  }
  if (!state.anchors.has(id)) {
    const re = el('button', 'eco-atlas-move-secondary', 'Make this the focus');
    re.type = 'button';
    re.addEventListener('click', async () => {
      state.anchors.add(id);
      recomputeHops();
      await expandNode(id);
    });
    moves.appendChild(re);
  }
  panel.appendChild(moves);

  // relations: the counted, evidence-labelled list (also the accessible view)
  for (const rel of (detail && detail.relations) || []) {
    const sec = el('div', 'eco-atlas-detail-rel');
    sec.appendChild(el('div', 'eco-atlas-detail-rel-head',
      cleanText(rel.label || rel.relation)
      + (rel.basis === 'derived' ? ' — derived' : '')));
    for (const nb of (rel.neighbors || []).slice(0, 8)) {
      const row = el('button', 'eco-atlas-detail-neighbor');
      row.type = 'button';
      row.appendChild(el('span', 'eco-atlas-detail-neighbor-name', cleanText(nb.node.label)));
      row.appendChild(el('span', 'eco-atlas-detail-neighbor-count', formatNumber(nb.records || 0)));
      row.addEventListener('click', () => selectNode(nb.node.id));
      sec.appendChild(row);
    }
    if (rel.omitted) {
      sec.appendChild(el('div', 'eco-atlas-detail-omitted',
        `…and ${formatNumber(rel.omitted)} more not shown`));
    }
    panel.appendChild(sec);
  }

  // provenance: where this node's numbers stand
  const prov = (detail && detail.provenance) || null;
  if (prov) {
    const p = el('div', 'eco-atlas-detail-prov');
    p.appendChild(el('div', 'eco-atlas-detail-rel-head', 'Provenance'));
    for (const line of [].concat(prov)) {
      p.appendChild(el('div', 'eco-atlas-detail-prov-line', cleanText(
        typeof line === 'string' ? line : (line.statement || ''))));
    }
    panel.appendChild(p);
  }

  // capability actions: fill the composer, never send
  const actions = ((detail && detail.actions) || []).filter((a) => a && a.label).slice(0, 3);
  if (actions.length) {
    const row = el('div', 'eco-atlas-actions');
    for (const a of actions) {
      const chip = el('button', 'viz-action-chip', cleanText(a.label));
      chip.type = 'button';
      chip.addEventListener('click', () => stageQuestion(a.label));
      row.appendChild(chip);
    }
    panel.appendChild(row);
    panel.appendChild(el('div', 'eco-atlas-detail-hint',
      'Actions put the question in the message box — nothing is sent until you send it.'));
  }
}

function stageQuestion(text) {
  const input = document.getElementById('message');
  if (!input) return;
  input.value = text;
  input.dispatchEvent(new Event('input', { bubbles: true }));
  hideAtlas();
  input.focus();
}
