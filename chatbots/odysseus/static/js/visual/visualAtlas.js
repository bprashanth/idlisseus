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

function kindLabel(kind, plural) {
  const k = (state.start.node_kinds || []).find((x) => x.kind === kind);
  const label = (k && k.label) || kind;
  return plural ? label : label.replace(/s$/, '');
}

// ---- graph state -----------------------------------------------------------
function radiusFor(records) {
  return 3 + 19 * Math.sqrt(Math.max(1, records) / state.maxRecords);
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
  let entry = state.nodes.get(node.id) || mergeNode(node, null);
  if (!entry) return;
  state.anchors.add(node.id);
  entry.hop = 0;
  // The camera moves to the searched thing — the graph never rearranges for
  // a search, so anchoring adds emphasis without adding clutter.
  state.spotlight = node.id;
  glideTo(entry);
  recomputeHops();
  refreshAllNodeClasses();
  refreshHover();
  // Live packs load the anchor's full bounded neighbourhood; the sample
  // already shows everything it has.
  if (!state.sample) await expandNode(node.id);
  else await selectNode(node.id);
}

// Ease the view toward a node over ~450ms; the person keeps control after.
function glideTo(entry) {
  state.userMovedView = true;
  const fromX = state.view.x, fromY = state.view.y, fromK = state.view.k;
  const toK = Math.max(fromK, 1.35);
  const toX = entry.x - (WORLD_W / toK) / 2;
  const toY = entry.y - (WORLD_H / toK) / 2;
  const t0 = performance.now();
  const step = (t) => {
    const u = Math.min(1, (t - t0) / 450);
    const e = 1 - Math.pow(1 - u, 3);
    state.view.k = fromK + (toK - fromK) * e;
    state.view.x = fromX + (toX - fromX) * e;
    state.view.y = fromY + (toY - fromY) * e;
    applyView();
    if (u < 1) requestAnimationFrame(step);
    else declutterLabels();
  };
  requestAnimationFrame(step);
}

async function expandNode(nodeId) {
  const entry = state.nodes.get(nodeId);
  if (!entry) return;
  if (state.anchors.size && entry.hop >= MAX_HOP) {
    refreshAllNodeClasses();
    renderDetail(nodeId, entry.detail || null,
      'Three hops from your search — make it a focus to keep walking.');
    return;
  }
  const detail = await loadNode(nodeId);
  entry.expanded = true;
  if (!state.anchors.size) { state.anchors.add(nodeId); entry.hop = 0; }
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
  refreshAllNodeClasses();
  renderLegend();
  renderStatus();
  renderDetail(nodeId, entry.detail || null);
  startSim(0.6);
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
    + 'connections. Hover to read a name; click for its card; search to bring the '
    + 'thing you care about to the centre. Solid filaments are recorded '
    + 'relationships; dashed are derived. Drag to pan, scroll to zoom.'));
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
    preserveAspectRatio: 'xMidYMid meet',
    role: 'img', 'aria-label': 'Relationship constellation',
  });
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
    const factor = ev.deltaY < 0 ? 0.88 : 1.14;
    state.userMovedView = true;
    scheduleDeclutter();
    const next = Math.min(3.4, Math.max(0.55, state.view.k * factor));
    state.view.k = next;
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

function worldPerPixel() {
  const rect = state.svg.getBoundingClientRect();
  return (WORLD_W / state.view.k) / Math.max(1, rect.width);
}
function viewCentre() {
  return {
    x: state.view.x + (WORLD_W / state.view.k) / 2,
    y: state.view.y + (WORLD_H / state.view.k) / 2,
  };
}
function applyView() {
  const w = WORLD_W / state.view.k, h = WORLD_H / state.view.k;
  state.svg.setAttribute('viewBox', `${state.view.x} ${state.view.y} ${w} ${h}`);
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
  if (state.anchors.has(id)) cls.push('is-anchor');
  if (state.selected === id) cls.push('is-selected');
  if (state.anchors.size && entry.hop >= MAX_HOP && !state.anchors.has(id)) cls.push('is-far');
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
  // the heaviest nodes keep their names on — the landmarks of the constellation
  const byWeight = [...state.nodes.entries()]
    .sort((a, b) => (b[1].node.records || 0) - (a[1].node.records || 0))
    .slice(0, ALWAYS_LABELLED);
  state.labelRankCache = new Set(byWeight.map(([id]) => id));
  for (const [id, entry] of state.nodes) {
    const g = state.nodeEls.get(id);
    if (!g) continue;
    g.setAttribute('class', nodeClasses(id, entry));
    const r = entry.r;
    const core = g.querySelector('.eco-atlas-dot-core');
    if (core) core.setAttribute('r', r);
    const halo = g.querySelector('.eco-atlas-dot-halo');
    if (halo) halo.setAttribute('r', r + 7);
    const label = g.querySelector('.eco-atlas-dot-label');
    if (label) label.setAttribute('font-size', Math.max(11, Math.min(17, r * 1.1)));
  }
  scheduleDeclutter();
}

function refreshHover() {
  const id = state.hovered || state.spotlight;
  for (const [key, lineEl] of state.edgeEls) {
    const e = state.edges.get(key);
    const hit = id && (e.from === id || e.to === id);
    lineEl.classList.toggle('is-lit', !!hit);
    lineEl.classList.toggle('is-dim', !!id && !hit);
  }
  for (const [nid, g] of state.nodeEls) {
    g.classList.toggle('is-hovered', nid === id);
    if (id && nid !== id) {
      const touching = (state.adjacency.get(id) || []).some((k) => {
        const e = state.edges.get(k);
        return e.from === nid || e.to === nid;
      });
      g.classList.toggle('is-neighbor', touching);
      g.classList.toggle('is-bg', !touching);
    } else {
      g.classList.remove('is-neighbor', 'is-bg');
    }
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
    state.alpha *= 0.99;
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
function renderLegend() {
  const legend = atlasEl.querySelector('#eco-atlas-legend');
  if (!legend) return;
  legend.replaceChildren();
  const kinds = (state.start.node_kinds || []);
  for (const k of kinds) {
    const item = el('span', 'eco-atlas-legend-item');
    const dot = el('span', `eco-atlas-legend-dot kind-${k.kind}`);
    item.appendChild(dot);
    item.appendChild(el('span', 'eco-atlas-legend-label',
      `${k.label}${Number.isFinite(k.count) ? ` · ${formatNumber(k.count)}` : ''}`));
    legend.appendChild(item);
  }
  for (const [, style] of state.relationStyles) {
    if (style.basis !== 'derived') continue;
    const item = el('span', 'eco-atlas-legend-item');
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
  const bits = [`${state.nodes.size} things · ${state.edges.size} connections on the canvas`];
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
  state.selected = id;
  refreshAllNodeClasses();
  const entry = state.nodes.get(id);
  if (entry && !entry.detail) entry.detail = await loadNode(id);
  renderDetail(id, entry ? entry.detail : null);
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
  x.addEventListener('click', () => {
    panel.hidden = true; state.selected = null; state.spotlight = null;
    refreshAllNodeClasses(); refreshHover();
  });
  head.appendChild(x);
  panel.appendChild(head);
  panel.appendChild(el('div', 'eco-atlas-detail-kind',
    `${kindLabel(node.kind)} · ${formatNumber(node.records || 0)} records`
    + (Number.isFinite(node.sources) ? ` · ${node.sources} source${node.sources === 1 ? '' : 's'}` : '')));
  if (note) panel.appendChild(el('p', 'eco-atlas-detail-note', note));

  const moves = el('div', 'eco-atlas-detail-moves');
  // Sticky version of the hover highlight: dim everything not connected.
  const spot = el('button', 'eco-atlas-move-primary',
    state.spotlight === id ? 'Clear spotlight' : 'Spotlight connections');
  spot.type = 'button';
  spot.addEventListener('click', () => {
    state.spotlight = state.spotlight === id ? null : id;
    refreshHover();
    renderDetail(id, detail, note);
  });
  moves.appendChild(spot);
  // More neighbours exist only on a live pack (the sample shows all it has).
  const moreKnown = ((detail && detail.relations) || [])
    .reduce((s, r) => s + (r.omitted || 0), 0);
  if (!state.sample && (!entry.expanded || moreKnown) && (!state.anchors.size || entry.hop < MAX_HOP)) {
    const ex = el('button', 'eco-atlas-move-secondary',
      moreKnown ? `Load ${formatNumber(moreKnown)} more connections` : 'Load its full neighbourhood');
    ex.type = 'button';
    ex.addEventListener('click', () => expandNode(id));
    moves.appendChild(ex);
  }
  panel.appendChild(moves);

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
