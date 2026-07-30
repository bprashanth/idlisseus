// visualAtlas.js — the pack as a living constellation.
//
// The Data page opens on the whole graph: every producer-declared node in the
// bounded ambient sample, sized by records, clustered by its real connections
// under a gentle force simulation. Complexity is shown, not hidden — the job
// of the layout is to make the noise legible. Hover makes a name readable and
// lights its filaments; click opens the glass detail card (relations,
// provenance, capability actions — nothing auto-sent); search anchors a node
// at the centre and expands its bounded neighbourhood; expansions MERGE by
// stable id, three hops from the nearest anchor before re-anchoring.
//
// Every edge keeps its producer relation, label, count and evidence basis —
// recorded draws solid, derived (shared source/place) dashed and lighter,
// never colour alone. Node kinds are ring-and-tone styled and named in the
// card and legend. Budgets and omissions are visible.
//
// Modular: data comes only from IDL-REQ-0003 (/v1/graph ambient sample,
// /v1/graph?q= all-kind search, /v1/graph/node/{id} bounded expansion). The
// consumer never infers identity, membership or relationships; the contract
// fixtures render as a labelled sample until the producer ships. The physics
// is presentation only — positions carry no meaning beyond adjacency.

import { tooltip } from './visualRenderers.js';
import { cleanText, formatNumber } from './visualTheme.js';

const FIXTURE_BASE = '/static/contracts/fixtures/graph';
const SVGNS = 'http://www.w3.org/2000/svg';

const NODE_BUDGET = 420;   // ambient sample + expansions, total on canvas
const EDGE_BUDGET = 900;
const MAX_HOP = 3;
const WORLD_W = 1600, WORLD_H = 1000;
const ALWAYS_LABELLED = 14; // heaviest nodes keep their names on

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

// ---- data access (live first; labelled fixture sample as fallback) ---------
async function loadStart(endpointId) {
  if (endpointId) {
    try {
      return { data: await fetchJson(`/api/visual/${encodeURIComponent(endpointId)}/graph`), sample: false };
    } catch { /* endpoint pending */ }
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
  // Sample: canned alias index plus everything already on the canvas.
  const seen = new Map();
  try {
    const idx = await fetchJson(`${FIXTURE_BASE}/search.json`);
    for (const n of idx.nodes || []) seen.set(n.id, n);
  } catch { /* canvas-only */ }
  for (const entry of state.nodes.values()) {
    if (!seen.has(entry.node.id)) seen.set(entry.node.id, entry.node);
  }
  return [...seen.values()].filter((n) =>
    [n.label, ...(n.aliases || [])].some((a) => String(a).toLowerCase().includes(needle)));
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
  document.addEventListener('keydown', (ev) => {
    if (ev.key === 'Escape' && state && state.isolated
        && document.body.classList.contains('eco-atlas-open')) {
      exitIsolation();
    }
  });
  return atlasEl;
}

export function hideAtlas() {
  document.body.classList.remove('eco-atlas-open');
  if (state) state.simRunning = false;
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
    nodes: new Map(),
    edges: new Map(),
    anchors: new Set(),
    relationStyles: new Map(),
    omittedByBudget: 0,
    selected: null,
    hovered: null,
    kindsOff: new Set(),
    view: { x: 0, y: 0, k: 1 },
    alpha: 0,
    simRunning: false,
    maxRecords: 1,
    nodeEls: new Map(),
    edgeEls: new Map(),
    adjacency: new Map(),
  };
  seedAmbient();
  renderShell();
  startSim(1);
}

function kindOff(node) {
  return state.kindsOff.has(node.kind);
}

// Constellation-level visibility from the legend filters: a node shows only
// when its kind is on; an edge only when both its ends show.
function applyKindFilter() {
  if (state.isolated) exitIsolation();
  for (const [id, entry] of state.nodes) {
    const g = state.nodeEls.get(id);
    if (g) g.classList.toggle('is-koff', kindOff(entry.node));
  }
  for (const [key, lineEl] of state.edgeEls) {
    const e = state.edges.get(key);
    const a = state.nodes.get(e.from), b = state.nodes.get(e.to);
    lineEl.classList.toggle('is-koff', !a || !b || kindOff(a.node) || kindOff(b.node));
  }
  renderLegend();
  updateSizes();
  renderStatus();
  scheduleDeclutter();
}

function kindLabel(kind, plural) {
  const k = (state.start.node_kinds || []).find((x) => x.kind === kind);
  const label = (k && k.label) || kind;
  return plural ? label : label.replace(/s$/, '');
}

// ---- graph state -----------------------------------------------------------
function radiusFor(records) {
  return 3 + 19 * Math.sqrt(Math.max(1, records) / state.maxRecords);
}

// TR-VIS-0007 (amended): sizing follows the legend chips automatically.
// Full graph -> producer record counts. Any kind switched off -> each visible
// node is re-sized by its DISTINCT VISIBLE neighbours in the retained
// subgraph, so hiding a kind literally subtracts its connections from what
// remains. Bounded to the edges on this canvas, never a complete total.
function sizingByConnections() {
  return state.kindsOff.size > 0;
}

let _resizeT = null;
function updateSizes() {
  if (sizingByConnections()) {
    const degree = new Map();
    for (const e of state.edges.values()) {
      const a = state.nodes.get(e.from), b = state.nodes.get(e.to);
      if (!a || !b || kindOff(a.node) || kindOff(b.node)) continue;
      if (!degree.has(e.from)) degree.set(e.from, new Set());
      if (!degree.has(e.to)) degree.set(e.to, new Set());
      degree.get(e.from).add(e.to);
      degree.get(e.to).add(e.from);
    }
    const maxDeg = Math.max(...[...degree.values()].map((s) => s.size), 1);
    for (const [id, entry] of state.nodes) {
      if (kindOff(entry.node)) continue; // hidden — radius irrelevant
      const d = (degree.get(id) || { size: 0 }).size;
      // nonzero floor keeps visible-but-unconnected nodes present
      entry.r = 3 + 19 * Math.sqrt(d / maxDeg);
    }
  } else {
    for (const entry of state.nodes.values()) {
      entry.r = radiusFor(entry.node.records || 1);
    }
  }
  // the radius transition exists only for this moment — never during load/settle
  if (state.world) {
    state.world.classList.add('is-resizing');
    clearTimeout(_resizeT);
    _resizeT = setTimeout(() => state.world && state.world.classList.remove('is-resizing'), 400);
  }
  refreshAllNodeClasses();
  startSim(0.25); // let spacing adapt to the new radii
}
function edgeKey(a, b, relation) {
  return [a, b].sort().join('→') + '·' + relation;
}

function seedAmbient() {
  const nodes = state.start.nodes || [];
  state.maxRecords = Math.max(...nodes.map((n) => n.records || 1), 1);
  // deterministic golden-angle spiral start; the sim does the rest
  nodes.forEach((n, i) => {
    const angle = i * 2.399963;
    const rad = 40 + 9 * Math.sqrt(i);
    state.nodes.set(n.id, {
      node: n,
      x: WORLD_W / 2 + Math.cos(angle) * rad,
      y: WORLD_H / 2 + Math.sin(angle) * rad * 0.72,
      vx: 0, vy: 0, fx: null, fy: null,
      r: 0, hop: MAX_HOP, expanded: false,
    });
  });
  for (const entry of state.nodes.values()) entry.r = radiusFor(entry.node.records || 1);
  for (const e of state.start.edges || []) {
    if (!state.nodes.has(e.from) || !state.nodes.has(e.to)) continue;
    const key = edgeKey(e.from, e.to, e.relation || 'related');
    if (state.edges.has(key)) continue;
    const edge = {
      from: e.from, to: e.to,
      relation: e.relation || 'related',
      label: e.label || e.relation || 'related',
      basis: e.basis === 'derived' ? 'derived' : 'recorded',
      records: e.records || 0,
    };
    state.edges.set(key, edge);
    state.relationStyles.set(edge.relation, { label: edge.label, basis: edge.basis });
  }
  rebuildAdjacency();
}

function rebuildAdjacency() {
  state.adjacency = new Map();
  for (const [key, e] of state.edges) {
    if (!state.adjacency.has(e.from)) state.adjacency.set(e.from, []);
    if (!state.adjacency.has(e.to)) state.adjacency.set(e.to, []);
    state.adjacency.get(e.from).push(key);
    state.adjacency.get(e.to).push(key);
  }
}

function recomputeHops() {
  for (const entry of state.nodes.values()) entry.hop = MAX_HOP;
  const queue = [];
  for (const id of state.anchors) {
    const entry = state.nodes.get(id);
    if (entry) { entry.hop = 0; queue.push(id); }
  }
  while (queue.length) {
    const id = queue.shift();
    const d = state.nodes.get(id).hop;
    for (const key of state.adjacency.get(id) || []) {
      const e = state.edges.get(key);
      const next = e.from === id ? e.to : e.from;
      const entry = state.nodes.get(next);
      if (entry && entry.hop > d + 1) { entry.hop = Math.min(d + 1, MAX_HOP); queue.push(next); }
    }
  }
}

function mergeNode(node, near) {
  const existing = state.nodes.get(node.id);
  if (existing) {
    existing.node = { ...existing.node, ...node };
    existing.r = radiusFor(existing.node.records || 1);
    return existing;
  }
  if (state.nodes.size >= NODE_BUDGET) { state.omittedByBudget += 1; return null; }
  const jitter = () => (Math.sin(state.nodes.size * 12.9898) * 43758.5453 % 1) * 120 - 60;
  const entry = {
    node,
    x: (near ? near.x : WORLD_W / 2) + jitter(),
    y: (near ? near.y : WORLD_H / 2) + jitter() * 0.7,
    vx: 0, vy: 0, fx: null, fy: null,
    r: radiusFor(node.records || 1),
    hop: MAX_HOP, expanded: false,
  };
  state.nodes.set(node.id, entry);
  addNodeEl(node.id, entry);
  return entry;
}

async function anchorNode(node) {
  const entry = state.nodes.get(node.id) || mergeNode(node, null);
  if (!entry) return;
  if (state.kindsOff.has(node.kind)) {
    state.kindsOff.delete(node.kind); // you searched for it; turn its kind back on
    applyKindFilter();
  }
  state.anchors.add(node.id); // a memory of where you searched, kept as a tint
  await isolateNode(node.id);
}

// Ease the view to a target rect over ~420ms.
function animateView(toX, toY, toK, after) {
  state.userMovedView = true;
  const fromX = state.view.x, fromY = state.view.y, fromK = state.view.k;
  const t0 = performance.now();
  const step = (t) => {
    const u = Math.min(1, (t - t0) / 420);
    const e = 1 - Math.pow(1 - u, 3);
    state.view.k = fromK + (toK - fromK) * e;
    state.view.x = fromX + (toX - fromX) * e;
    state.view.y = fromY + (toY - fromY) * e;
    applyView();
    if (u < 1) requestAnimationFrame(step);
    else { declutterLabels(); if (after) after(); }
  };
  requestAnimationFrame(step);
}

function viewFor(entries, pad) {
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const p of entries) {
    minX = Math.min(minX, p.x - p.r); maxX = Math.max(maxX, p.x + p.r);
    minY = Math.min(minY, p.y - p.r); maxY = Math.max(maxY, p.y + p.r);
  }
  if (!Number.isFinite(minX)) return null;
  const w = maxX - minX + pad * 2, h = maxY - minY + pad * 2;
  const k = Math.min(3.4, Math.max(0.55, Math.min(WORLD_W / w, WORLD_H / h)));
  return {
    k,
    x: (minX + maxX) / 2 - (WORLD_W / k) / 2,
    y: (minY + maxY) / 2 - (WORLD_H / k) / 2,
  };
}

// ---- isolation: one node and its one-hop links take the stage --------------
// Clicking a node hides the rest of the constellation, lays its neighbours in
// a ring around it, and opens its card. Clicking any neighbour re-isolates on
// that neighbour; dismissing the card restores the full constellation exactly
// as it was.
async function isolateNode(id) {
  const entry = state.nodes.get(id);
  if (!entry) return;
  state.simRunning = false; state.alpha = 0;
  // entering from the constellation: remember every position for the way back
  if (!state.isolated) {
    state.savedPositions = new Map(
      [...state.nodes.entries()].map(([nid, p]) => [nid, { x: p.x, y: p.y }]));
    state.savedView = { ...state.view };
  }
  state.isolated = id;
  state.selected = id;
  // live packs complete the one-hop picture before showing it
  if (!state.sample && !entry.expanded) await expandNode(id, { silent: true });
  if (!entry.detail) entry.detail = await loadNode(id);

  // the one-hop set, via edges incident to the centre
  const spokes = [];
  const seen = new Set([id]);
  for (const key of state.adjacency.get(id) || []) {
    const e = state.edges.get(key);
    const other = e.from === id ? e.to : e.from;
    if (seen.has(other)) continue;
    const nb = state.nodes.get(other);
    if (!nb || kindOff(nb.node)) continue; // the legend filter shapes the ring
    seen.add(other);
    spokes.push({ id: other, entry: nb, edge: e });
  }
  // group spokes by relation so families of links sit together on the ring
  spokes.sort((a, b) => a.edge.relation.localeCompare(b.edge.relation)
    || (b.edge.records || 0) - (a.edge.records || 0));

  // visibility: centre + spokes only; only edges incident to the centre
  for (const [nid, g] of state.nodeEls) {
    g.classList.toggle('is-hidden', !seen.has(nid));
    g.classList.toggle('is-isolated-centre', nid === id);
  }
  for (const [key, lineEl] of state.edgeEls) {
    const e = state.edges.get(key);
    const visible = (e.from === id || e.to === id)
      && seen.has(e.from) && seen.has(e.to);
    lineEl.classList.toggle('is-hidden', !visible);
    lineEl.classList.remove('is-lit', 'is-dim');
  }

  // concentric rings around the centre, each filled to its comfortable
  // capacity so the ego view stays compact enough to read
  const targets = new Map();
  targets.set(id, { x: entry.x, y: entry.y });
  let ringR = 240, placed = 0, ringStart = 0;
  let capacity = Math.floor((2 * Math.PI * ringR) / 100);
  spokes.forEach((s, i) => {
    if (placed >= capacity) {
      ringR += 135; ringStart = i; placed = 0;
      capacity = Math.floor((2 * Math.PI * ringR) / 100);
    }
    const inRing = Math.min(capacity, spokes.length - ringStart);
    const angle = ((i - ringStart) / Math.max(1, inRing)) * Math.PI * 2
      - Math.PI / 2 + (ringR / 500); // slight per-ring twist
    targets.set(s.id, {
      x: entry.x + Math.cos(angle) * ringR,
      y: entry.y + Math.sin(angle) * ringR * 0.82,
    });
    placed += 1;
  });
  animatePositions(targets, 340);
  const rect = viewFor([...seen].map((nid) => {
    const t = targets.get(nid) || state.nodes.get(nid);
    return { x: t.x, y: t.y, r: state.nodes.get(nid).r };
  }), 90);
  if (rect) animateView(rect.x, rect.y, rect.k);

  // in the ego view every visible thing is labelled
  refreshAllNodeClasses();
  for (const nid of seen) {
    const g = state.nodeEls.get(nid);
    if (g) g.classList.add('is-labelled');
  }
  renderStatus();
  renderDetail(id, entry.detail || null,
    spokes.length === 0 && state.kindsOff.size
      ? 'Nothing here connects directly to the kinds currently shown — '
        + 'turn more kinds on in the legend to see how this links through them.'
      : null);
}

function exitIsolation() {
  if (!state.isolated) return;
  state.isolated = null;
  state.selected = null;
  for (const g of state.nodeEls.values()) g.classList.remove('is-hidden', 'is-isolated-centre');
  for (const lineEl of state.edgeEls.values()) lineEl.classList.remove('is-hidden');
  if (state.savedPositions) {
    animatePositions(state.savedPositions, 340);
  }
  if (state.savedView) {
    animateView(state.savedView.x, state.savedView.y, state.savedView.k);
  }
  const panel = atlasEl.querySelector('.eco-atlas-detail');
  if (panel) panel.hidden = true;
  refreshAllNodeClasses();
  refreshHover();
  renderStatus();
}

// Lerp node positions to targets; the sim stays paused while animating.
function animatePositions(targets, ms) {
  const starts = new Map();
  for (const [nid, to] of targets) {
    const p = state.nodes.get(nid);
    if (p) starts.set(nid, { x: p.x, y: p.y, tx: to.x, ty: to.y });
  }
  const t0 = performance.now();
  const step = (t) => {
    const u = Math.min(1, (t - t0) / ms);
    const e = 1 - Math.pow(1 - u, 3);
    for (const [nid, s] of starts) {
      const p = state.nodes.get(nid);
      if (!p) continue;
      p.x = s.x + (s.tx - s.x) * e;
      p.y = s.y + (s.ty - s.y) * e;
    }
    paint();
    if (u < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

async function expandNode(nodeId, opts) {
  const entry = state.nodes.get(nodeId);
  if (!entry) return;
  const detail = await loadNode(nodeId);
  entry.expanded = true;
  if (detail) {
    entry.node = { ...entry.node, ...detail.node };
    for (const rel of detail.relations || []) {
      state.relationStyles.set(rel.relation, {
        label: rel.label || rel.relation,
        basis: rel.basis === 'derived' ? 'derived' : 'recorded',
      });
      for (const nb of rel.neighbors || []) {
        if (state.edges.size >= EDGE_BUDGET) { state.omittedByBudget += 1; continue; }
        const added = mergeNode(nb.node, entry);
        if (!added) continue;
        const key = edgeKey(nodeId, nb.node.id, rel.relation);
        if (!state.edges.has(key)) {
          const edge = {
            from: nodeId, to: nb.node.id,
            relation: rel.relation, label: rel.label || rel.relation,
            basis: rel.basis === 'derived' ? 'derived' : 'recorded',
            records: nb.records || 0,
          };
          state.edges.set(key, edge);
          addEdgeEl(key, edge);
        }
      }
      if (rel.omitted) entry[`omitted:${rel.relation}`] = rel.omitted;
    }
    entry.detail = detail;
  }
  rebuildAdjacency();
  recomputeHops();
  renderLegend();
  if (sizingByConnections()) updateSizes();
  if (!(opts && opts.silent)) {
    refreshAllNodeClasses();
    renderStatus();
    renderDetail(nodeId, entry.detail || null);
    startSim(0.6);
  }
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
    'Everything this pack holds, sized by its records and clustered by its real '
    + 'connections. Switch off kinds in the legend below and what remains is '
    + 're-sized by its connections to what you kept. Hover to read a name; click '
    + 'for its card; search to bring the thing you care about to the centre. '
    + 'Solid filaments are recorded relationships; dashed are derived. Drag to '
    + 'pan, scroll to zoom.'));
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
  const stage = el('div', 'eco-atlas-stage eco-atlas-cosmos');
  body.appendChild(stage);
  const detail = el('aside', 'eco-atlas-detail');
  detail.hidden = true;
  body.appendChild(detail);

  buildCanvas(stage);
  const legend = el('div', 'eco-atlas-legend');
  legend.id = 'eco-atlas-legend';
  inner.appendChild(legend);
  const status = el('div', 'eco-atlas-status');
  inner.appendChild(status);
  renderLegend();
  renderStatus();
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
    b.appendChild(el('span', 'eco-atlas-search-hit-meta',
      `${kindLabel(n.kind)} · ${formatNumber(n.records || 0)} records`));
    b.addEventListener('click', async () => {
      box.remove();
      await anchorNode(n);
    });
    box.appendChild(b);
  }
}

// ---- canvas: SVG + force simulation ----------------------------------------
function buildCanvas(stage) {
  const svg = svgEl('svg', {
    class: 'eco-atlas-svg eco-atlas-svg-cosmos',
    viewBox: `0 0 ${WORLD_W} ${WORLD_H}`,
    preserveAspectRatio: 'xMidYMid slice',
    role: 'img', 'aria-label': 'Relationship constellation',
  });
  window.addEventListener('resize', () => { state.stageRect = null; });
  stage.appendChild(svg);
  const world = svgEl('g', { class: 'eco-atlas-world' });
  svg.appendChild(world);
  const edgeLayer = svgEl('g', { class: 'eco-atlas-edgelayer' });
  world.appendChild(edgeLayer);
  const nodeLayer = svgEl('g', {});
  world.appendChild(nodeLayer);
  state.svg = svg; state.world = world;
  state.edgeLayer = edgeLayer; state.nodeLayer = nodeLayer;

  for (const [key, edge] of state.edges) addEdgeEl(key, edge);
  for (const [id, entry] of state.nodes) addNodeEl(id, entry);
  refreshAllNodeClasses();

  // pan (background drag) + zoom (wheel)
  let panning = null;
  svg.addEventListener('pointerdown', (ev) => {
    if (ev.target.closest('.eco-atlas-dot')) return;
    panning = { x: ev.clientX, y: ev.clientY, vx: state.view.x, vy: state.view.y };
    try { svg.setPointerCapture(ev.pointerId); } catch { /* synthetic events */ }
  });
  svg.addEventListener('pointermove', (ev) => {
    if (!panning) return;
    const scale = worldPerPixel();
    state.userMovedView = true;
    scheduleDeclutter();
    state.view.x = panning.vx - (ev.clientX - panning.x) * scale;
    state.view.y = panning.vy - (ev.clientY - panning.y) * scale;
    applyView();
  });
  svg.addEventListener('pointerup', () => { panning = null; });
  svg.addEventListener('wheel', (ev) => {
    ev.preventDefault();
    state.userMovedView = true;
    scheduleDeclutter();
    const factor = ev.deltaY < 0 ? 0.9 : 1.12;
    const next = Math.min(3.4, Math.max(0.55, state.view.k * factor));
    // anchor the zoom on the cursor so the point under it stays put
    const rect = stageRect();
    const px = (ev.clientX - rect.x) / Math.max(1, rect.width);
    const py = (ev.clientY - rect.y) / Math.max(1, rect.height);
    const wx = state.view.x + px * (WORLD_W / state.view.k);
    const wy = state.view.y + py * (WORLD_H / state.view.k);
    state.view.k = next;
    state.view.x = wx - px * (WORLD_W / next);
    state.view.y = wy - py * (WORLD_H / next);
    applyView();
  }, { passive: false });
  applyView();
}

// Frame the settled constellation, leaving air around it.
function fitView() {
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const p of state.nodes.values()) {
    minX = Math.min(minX, p.x - p.r); maxX = Math.max(maxX, p.x + p.r);
    minY = Math.min(minY, p.y - p.r); maxY = Math.max(maxY, p.y + p.r);
  }
  if (!Number.isFinite(minX)) return;
  const pad = 70;
  const w = maxX - minX + pad * 2, h = maxY - minY + pad * 2;
  const k = Math.min(3.4, Math.max(0.55, Math.min(WORLD_W / w, WORLD_H / h)));
  state.view.k = k;
  state.view.x = (minX + maxX) / 2 - (WORLD_W / k) / 2;
  state.view.y = (minY + maxY) / 2 - (WORLD_H / k) / 2;
  applyView();
}

// Labels must never pile up or clip (TR-VIS-0006). Priority: anchors, then
// the selected node, then landmarks by records. A lower-priority label that
// would sit on a kept one is hidden, never stacked; anchor/selected labels
// are always kept. Each label is measured (chars × font size) and clamped
// inside the stage: flipped below the node near the top edge, re-anchored
// near the sides.
function labelBox(entry) {
  const fontSize = Math.max(11, Math.min(17, entry.r * 1.1));
  const w = Math.max(40, cleanText(entry.node.label).length * fontSize * 0.6);
  return { w, h: fontSize * 1.5, fontSize };
}

function positionLabel(entry, g) {
  const label = g.querySelector('.eco-atlas-dot-label');
  if (!label) return;
  const { w, fontSize } = labelBox(entry);
  const viewLeft = state.view.x, viewTop = state.view.y;
  const viewRight = viewLeft + WORLD_W / state.view.k;
  const pad = 14 / state.view.k;
  // above by default; below when the node settles near the top of the view
  const above = entry.y - entry.r - fontSize * 1.6 > viewTop + pad;
  label.setAttribute('y', above ? -(entry.r + 6) : entry.r + fontSize + 4);
  // keep the text run inside the stage horizontally
  if (entry.x - w / 2 < viewLeft + pad) {
    label.setAttribute('text-anchor', 'start');
    label.setAttribute('x', -entry.r);
  } else if (entry.x + w / 2 > viewRight - pad) {
    label.setAttribute('text-anchor', 'end');
    label.setAttribute('x', entry.r);
  } else {
    label.setAttribute('text-anchor', 'middle');
    label.setAttribute('x', 0);
  }
}

function declutterLabels() {
  const candidates = [];
  for (const [id, entry] of state.nodes) {
    if (kindOff(entry.node)) continue;
    const isAnchor = state.anchors.has(id);
    const isSelected = state.selected === id;
    const isLandmark = state.labelRankCache && state.labelRankCache.has(id);
    if (!isAnchor && !isSelected && !isLandmark) continue;
    candidates.push({
      id, entry,
      priority: isAnchor ? 3 : isSelected ? 2 : 1,
      weight: entry.node.records || 0,
    });
  }
  candidates.sort((a, b) => b.priority - a.priority || b.weight - a.weight);
  const kept = [];
  for (const c of candidates) {
    const g = state.nodeEls.get(c.id);
    if (!g) continue;
    const box = labelBox(c.entry);
    const collide = kept.some((k) =>
      Math.abs(k.entry.x - c.entry.x) < (k.box.w + box.w) / 2 + 8
      && Math.abs(k.entry.y - c.entry.y) < (k.box.h + box.h) / 2 + 26);
    // anchors and the selected node always keep their name (their priority
    // ordering means anything colliding with them is what gets hidden)
    const show = c.priority >= 2 || !collide;
    g.classList.toggle('is-labelled', show);
    if (show) { kept.push({ entry: c.entry, box }); positionLabel(c.entry, g); }
  }
}

function stageRect() {
  if (!state.stageRect) state.stageRect = state.svg.getBoundingClientRect();
  return state.stageRect;
}
function worldPerPixel() {
  return (WORLD_W / state.view.k) / Math.max(1, stageRect().width);
}
function viewCentre() {
  return {
    x: state.view.x + (WORLD_W / state.view.k) / 2,
    y: state.view.y + (WORLD_H / state.view.k) / 2,
  };
}
// One transform on the world group — the browser composites the pan/zoom
// instead of re-rasterising every dot and filament per event.
function applyView() {
  if (state._viewRaf) return;
  state._viewRaf = requestAnimationFrame(() => {
    state._viewRaf = null;
    const { x, y, k } = state.view;
    state.world.setAttribute('transform', `scale(${k}) translate(${-x} ${-y})`);
  });
}

function addEdgeEl(key, edge) {
  if (!state.edgeLayer || state.edgeEls.has(key)) return;
  const line = svgEl('line', {
    class: `eco-atlas-fil basis-${edge.basis}`,
    'stroke-width': Math.max(0.7, 2.6 * Math.sqrt((edge.records || 1) / state.maxRecords) * 4),
  });
  line.addEventListener('mousemove', (ev) => {
    const a = state.nodes.get(edge.from), b = state.nodes.get(edge.to);
    tooltip().show(ev, [
      { value: `${cleanText(a.node.label)} — ${cleanText(b.node.label)}`, label: '', header: true },
      { value: cleanText(edge.label), label: edge.basis === 'derived' ? '(derived)' : '(recorded)' },
      { value: formatNumber(edge.records), label: 'records', strong: true },
    ]);
  });
  line.addEventListener('mouseleave', () => tooltip().hide());
  state.edgeLayer.appendChild(line);
  state.edgeEls.set(key, line);
}

function addNodeEl(id, entry) {
  if (!state.nodeLayer || state.nodeEls.has(id)) return;
  const g = svgEl('g', {
    class: 'eco-atlas-dot', tabindex: 0, role: 'button', 'data-node': id,
  });
  const halo = svgEl('circle', { class: 'eco-atlas-dot-halo', r: entry.r + 7 });
  g.appendChild(halo);
  const circle = svgEl('circle', { class: 'eco-atlas-dot-core', r: entry.r });
  g.appendChild(circle);
  const label = svgEl('text', {
    class: 'eco-atlas-dot-label',
    y: -(entry.r + 6),
    'text-anchor': 'middle',
    'font-size': Math.max(11, Math.min(17, entry.r * 1.1)),
  });
  label.textContent = cleanText(entry.node.label);
  g.appendChild(label);
  const title = svgEl('title', {});
  title.textContent = `${cleanText(entry.node.label)} — ${kindLabel(entry.node.kind)}, ${formatNumber(entry.node.records || 0)} records`;
  g.appendChild(title);

  g.addEventListener('mouseenter', () => { state.hovered = id; refreshHover(); });
  g.addEventListener('mouseleave', () => { state.hovered = null; refreshHover(); });
  g.addEventListener('keydown', (ev) => {
    if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); selectNode(id); }
  });
  // drag a node; a plain click (no movement) selects it
  let drag = null;
  g.addEventListener('pointerdown', (ev) => {
    ev.stopPropagation();
    drag = { moved: false, px: ev.clientX, py: ev.clientY };
    try { g.setPointerCapture(ev.pointerId); } catch { /* synthetic events */ }
  });
  g.addEventListener('pointermove', (ev) => {
    if (!drag) return;
    const dx = ev.clientX - drag.px, dy = ev.clientY - drag.py;
    if (!drag.moved && Math.hypot(dx, dy) < 4) return;
    drag.moved = true;
    const scale = worldPerPixel();
    entry.fx = (entry.fx ?? entry.x) + dx * scale;
    entry.fy = (entry.fy ?? entry.y) + dy * scale;
    drag.px = ev.clientX; drag.py = ev.clientY;
    startSim(0.35);
  });
  g.addEventListener('pointerup', () => {
    if (drag && !drag.moved) selectNode(id);
    else if (!state.anchors.has(id)) { entry.fx = null; entry.fy = null; }
    drag = null;
  });

  state.nodeLayer.appendChild(g);
  state.nodeEls.set(id, g);
}

function nodeClasses(id, entry) {
  const cls = ['eco-atlas-dot', `kind-${entry.node.kind}`];
  if (kindOff(entry.node)) cls.push('is-koff');
  if (state.anchors.has(id)) cls.push('is-anchor');
  if (state.selected === id) cls.push('is-selected');
  if (state.isolated === id) cls.push('is-isolated-centre');
  if (state.isolated) {
    const visible = id === state.isolated || (state.adjacency.get(state.isolated) || [])
      .some((k) => { const e = state.edges.get(k); return e.from === id || e.to === id; });
    if (!visible) cls.push('is-hidden');
  }
  const rank = state.labelRankCache;
  if ((rank && rank.has(id)) || state.anchors.has(id) || state.selected === id) cls.push('is-labelled');
  return cls.join(' ');
}

let _declutterT = null;
function scheduleDeclutter() {
  clearTimeout(_declutterT);
  _declutterT = setTimeout(declutterLabels, 140);
}

function refreshAllNodeClasses() {
  // the biggest nodes keep their names on — the landmarks of the constellation.
  // Rank by current radius so labels follow whichever sizing is active.
  const byWeight = [...state.nodes.entries()]
    .filter(([, entry]) => !kindOff(entry.node))
    .sort((a, b) => b[1].r - a[1].r)
    .slice(0, ALWAYS_LABELLED);
  state.labelRankCache = new Set(byWeight.map(([id]) => id));
  for (const [id, entry] of state.nodes) {
    const g = state.nodeEls.get(id);
    if (!g) continue;
    g.setAttribute('class', nodeClasses(id, entry));
    const r = state.isolated === id ? Math.max(entry.r, 16) : entry.r;
    const core = g.querySelector('.eco-atlas-dot-core');
    if (core) core.setAttribute('r', r);
    const halo = g.querySelector('.eco-atlas-dot-halo');
    if (halo) halo.setAttribute('r', r + 7);
    const label = g.querySelector('.eco-atlas-dot-label');
    if (label) label.setAttribute('font-size', Math.max(11, Math.min(17, r * 1.1)));
  }
  scheduleDeclutter();
}

// The field-dimming lives on the world group (one class); only the hovered
// node's own neighbourhood gets element classes. O(degree), not O(graph).
function refreshHover() {
  const id = state.hovered;
  for (const el of state._litEls || []) el.classList.remove('is-lit', 'is-hovered', 'is-neighbor');
  state._litEls = [];
  state.world.classList.toggle('is-hovering', !!id && !state.isolated);
  if (!id) return;
  const g = state.nodeEls.get(id);
  if (g) { g.classList.add('is-hovered'); state._litEls.push(g); }
  for (const key of state.adjacency.get(id) || []) {
    const lineEl = state.edgeEls.get(key);
    if (lineEl) { lineEl.classList.add('is-lit'); state._litEls.push(lineEl); }
    const e = state.edges.get(key);
    const other = e.from === id ? e.to : e.from;
    const og = state.nodeEls.get(other);
    if (og) { og.classList.add('is-neighbor'); state._litEls.push(og); }
  }
}

// ---- the simulation --------------------------------------------------------
function startSim(alpha) {
  state.alpha = Math.max(state.alpha, alpha);
  if (state.simRunning) return;
  state.simRunning = true;
  const reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduced) {
    for (let i = 0; i < 260; i++) simTick();
    state.alpha = 0; state.simRunning = false;
    paint();
    if (!state.userMovedView) fitView();
    declutterLabels();
    return;
  }
  const loop = () => {
    if (!state || !state.simRunning) return;
    simTick();
    paint();
    state.alpha *= 0.985;
    if (!state.userMovedView && (state._fitCounter = (state._fitCounter || 0) + 1) % 24 === 0) {
      fitView();
    }
    if ((state._fitCounter || 0) % 18 === 0) declutterLabels();
    if (state.alpha < 0.015 || !document.body.classList.contains('eco-atlas-open')) {
      state.simRunning = false;
      if (!state.userMovedView) fitView();
      declutterLabels();
      return;
    }
    requestAnimationFrame(loop);
  };
  requestAnimationFrame(loop);
}

function simTick() {
  const entries = [...state.nodes.values()];
  const a = state.alpha;
  const cap = (v, m) => (v > m ? m : v < -m ? -m : v);
  // pairwise repulsion, radius-weighted so heavy nodes claim space
  for (let i = 0; i < entries.length; i++) {
    const p = entries[i];
    for (let j = i + 1; j < entries.length; j++) {
      const q = entries[j];
      let dx = q.x - p.x, dy = q.y - p.y;
      let d2 = dx * dx + dy * dy;
      if (d2 < 1) { dx = (i % 2 ? 1 : -1); dy = 1; d2 = 2; }
      const d = Math.sqrt(d2);
      const minD = p.r + q.r + 8;
      let f = cap((95 * (p.r + q.r) * a) / d2, 6);
      if (d < minD) f += (minD - d) * 0.06;
      const fx = (dx / d) * f, fy = (dy / d) * f;
      p.vx -= fx; p.vy -= fy;
      q.vx += fx; q.vy += fy;
    }
  }
  // gentle springs along the real connections (capped: stability first)
  for (const e of state.edges.values()) {
    const p = state.nodes.get(e.from), q = state.nodes.get(e.to);
    if (!p || !q) continue;
    const dx = q.x - p.x, dy = q.y - p.y;
    const d = Math.max(1, Math.hypot(dx, dy));
    const rest = 85 + p.r + q.r + (e.basis === 'derived' ? 90 : 0);
    const k = (e.basis === 'derived' ? 0.0035 : 0.009) * a;
    const f = cap(k * (d - rest), 2.4);
    const fx = (dx / d) * f, fy = (dy / d) * f;
    p.vx += fx; p.vy += fy;
    q.vx -= fx; q.vy -= fy;
  }
  // containment gravity + heavy damping + speed clamp + world bounds
  for (const p of entries) {
    p.vx += (WORLD_W / 2 - p.x) * 0.0045 * a;
    p.vy += (WORLD_H / 2 - p.y) * 0.0065 * a;
    p.vx = cap(p.vx * 0.72, 9);
    p.vy = cap(p.vy * 0.72, 9);
    if (p.fx !== null) { p.x = p.fx; p.vx = 0; } else p.x += p.vx;
    if (p.fy !== null) { p.y = p.fy; p.vy = 0; } else p.y += p.vy;
    if (p.x < 40) p.x = 40; else if (p.x > WORLD_W - 40) p.x = WORLD_W - 40;
    if (p.y < 36) p.y = 36; else if (p.y > WORLD_H - 36) p.y = WORLD_H - 36;
  }
}

function paint() {
  for (const [id, g] of state.nodeEls) {
    const p = state.nodes.get(id);
    if (p) g.setAttribute('transform', `translate(${p.x.toFixed(1)}, ${p.y.toFixed(1)})`);
  }
  for (const [key, line] of state.edgeEls) {
    const e = state.edges.get(key);
    const p = state.nodes.get(e.from), q = state.nodes.get(e.to);
    if (!p || !q) continue;
    line.setAttribute('x1', p.x.toFixed(1)); line.setAttribute('y1', p.y.toFixed(1));
    line.setAttribute('x2', q.x.toFixed(1)); line.setAttribute('y2', q.y.toFixed(1));
  }
}

// ---- legend & status -------------------------------------------------------
// The legend is the filter: click a kind to hide or show it, double-click to
// see only that kind. The canvas and the isolation ring both obey it.
function renderLegend() {
  const legend = atlasEl.querySelector('#eco-atlas-legend');
  if (!legend) return;
  legend.replaceChildren();
  const kinds = (state.start.node_kinds || []);
  for (const k of kinds) {
    const item = el('button', 'eco-atlas-legend-item');
    item.type = 'button';
    item.title = 'Click to hide/show · double-click to show only these';
    if (state.kindsOff.has(k.kind)) item.classList.add('is-off');
    const dot = el('span', `eco-atlas-legend-dot kind-${k.kind}`);
    item.appendChild(dot);
    item.appendChild(el('span', 'eco-atlas-legend-label',
      `${k.label}${Number.isFinite(k.count) ? ` · ${formatNumber(k.count)}` : ''}`));
    let clickT = null;
    item.addEventListener('click', () => {
      clearTimeout(clickT);
      clickT = setTimeout(() => {
        if (state.kindsOff.has(k.kind)) state.kindsOff.delete(k.kind);
        else state.kindsOff.add(k.kind);
        applyKindFilter();
      }, 180);
    });
    item.addEventListener('dblclick', () => {
      clearTimeout(clickT);
      state.kindsOff = new Set(kinds.map((x) => x.kind).filter((x) => x !== k.kind));
      applyKindFilter();
    });
    legend.appendChild(item);
  }
  if (state.kindsOff.size) {
    const reset = el('button', 'eco-atlas-legend-reset', 'Show everything');
    reset.type = 'button';
    reset.addEventListener('click', () => {
      state.kindsOff.clear();
      applyKindFilter();
    });
    legend.appendChild(reset);
  }
  for (const [, style] of state.relationStyles) {
    if (style.basis !== 'derived') continue;
    const item = el('span', 'eco-atlas-legend-item is-static');
    const key = el('span', 'eco-atlas-legend-key basis-derived');
    item.appendChild(key);
    item.appendChild(el('span', 'eco-atlas-legend-label', `${cleanText(style.label)} (derived)`));
    legend.appendChild(item);
    break; // one derived example line is enough
  }
}

function renderStatus() {
  const status = atlasEl.querySelector('.eco-atlas-status');
  if (!status) return;
  if (state.isolated) {
    const entry = state.nodes.get(state.isolated);
    const n = (state.adjacency.get(state.isolated) || []).length;
    status.textContent = `Showing ${cleanText(entry.node.label)} and its ${n} connection${n === 1 ? '' : 's'} — close the card to return to the full map`;
    return;
  }
  const bits = [`${state.nodes.size} things · ${state.edges.size} connections on the canvas`];
  if (sizingByConnections()) {
    bits.push('sizes now rank by connections among what you kept — bounded to this canvas, not complete totals');
  }
  if (state.kindsOff.size) {
    const on = (state.start.node_kinds || [])
      .filter((k) => !state.kindsOff.has(k.kind)).map((k) => k.label.toLowerCase());
    bits.push(`showing only ${on.join(', ')} — click the legend to change`);
  }
  const omitted = ((state.start.more || {}).subject || {}).omitted;
  if (omitted && state.sample) {
    bits.push(`${formatNumber(omitted)} more recorded names omitted from this ambient sample — searchable once the live graph is connected`);
  } else if (omitted) {
    bits.push(`${formatNumber(omitted)} more recorded names live behind search`);
  }
  if (state.omittedByBudget) {
    bits.push(`${formatNumber(state.omittedByBudget)} not added — canvas budget reached`);
  }
  status.textContent = bits.join(' · ');
}

// ---- detail card -----------------------------------------------------------
async function selectNode(id) {
  await isolateNode(id);
}

// A node with no producer detail still has its on-canvas edges — group those.
function localDetail(id) {
  const groups = new Map();
  for (const key of state.adjacency.get(id) || []) {
    const e = state.edges.get(key);
    const other = e.from === id ? e.to : e.from;
    const entry = state.nodes.get(other);
    if (!entry) continue;
    if (!groups.has(e.relation)) {
      groups.set(e.relation, { relation: e.relation, label: e.label, basis: e.basis, neighbors: [] });
    }
    groups.get(e.relation).neighbors.push({ node: entry.node, records: e.records });
  }
  for (const g of groups.values()) g.neighbors.sort((a, b) => (b.records || 0) - (a.records || 0));
  return {
    relations: [...groups.values()],
    provenance: ['From the connections already on the canvas — open the full detail by expanding.'],
    actions: [],
    _local: true,
  };
}

function renderDetail(id, detail, note) {
  const panel = atlasEl.querySelector('.eco-atlas-detail');
  const entry = state.nodes.get(id);
  if (!entry) { panel.hidden = true; return; }
  const src = detail || localDetail(id);
  panel.hidden = false;
  panel.replaceChildren();
  const node = (detail && detail.node) || entry.node;

  const head = el('div', 'eco-atlas-detail-head');
  head.appendChild(el('span', 'eco-atlas-detail-title', cleanText(node.label)));
  const x = el('button', 'viz-panel-close', '×');
  x.addEventListener('click', () => exitIsolation());
  head.appendChild(x);
  panel.appendChild(head);
  panel.appendChild(el('div', 'eco-atlas-detail-kind',
    `${kindLabel(node.kind)} · ${formatNumber(node.records || 0)} records`
    + (Number.isFinite(node.sources) ? ` · ${node.sources} source${node.sources === 1 ? '' : 's'}` : '')));
  if (note) panel.appendChild(el('p', 'eco-atlas-detail-note', note));

  panel.appendChild(el('p', 'eco-atlas-detail-note',
    'Click any connection to move there. Close this card to return to the full map.'));

  for (const rel of src.relations || []) {
    const sec = el('div', 'eco-atlas-detail-rel');
    sec.appendChild(el('div', 'eco-atlas-detail-rel-head',
      cleanText(rel.label || rel.relation) + (rel.basis === 'derived' ? ' — derived' : '')));
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

  const prov = src.provenance || null;
  if (prov && prov.length) {
    const p = el('div', 'eco-atlas-detail-prov');
    p.appendChild(el('div', 'eco-atlas-detail-rel-head', 'Provenance'));
    for (const line of [].concat(prov)) {
      p.appendChild(el('div', 'eco-atlas-detail-prov-line', cleanText(
        typeof line === 'string' ? line : (line.statement || ''))));
    }
    panel.appendChild(p);
  }

  const actions = (src.actions || []).filter((a) => a && a.label).slice(0, 3);
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
