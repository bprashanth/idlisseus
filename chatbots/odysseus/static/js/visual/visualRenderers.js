// visualRenderers.js — registry mapping idli-result/1 visual objects to DOM.
// Dispatch is by visual_type + layer geometry only (never by view name or any
// sector vocabulary). Unknown visual types fall back to the summary card.

import { renderMap } from './visualMap.js';
import { renderTimeSeries, renderStatTiles } from './visualChart.js';
import { evidenceColor, evidenceLabel, formatNumber } from './visualTheme.js';

// ---- shared tooltip singleton (textContent only — labels are untrusted data)
class Tooltip {
  constructor() {
    this.node = document.createElement('div');
    this.node.className = 'viz-tooltip';
    this.node.setAttribute('role', 'status');
    document.body.appendChild(this.node);
  }
  show(ev, rows) {
    this.node.replaceChildren();
    for (const r of rows) {
      const row = document.createElement('div');
      row.className = 'viz-tooltip-row' + (r.header ? ' viz-tooltip-header' : '');
      if (r.cls) {
        const key = document.createElement('span');
        key.className = 'viz-legend-linekey';
        key.style.setProperty('--sw', evidenceColor(r.cls));
        row.appendChild(key);
      }
      const val = document.createElement('span');
      val.className = r.strong || r.header ? 'viz-tooltip-value' : 'viz-tooltip-plain';
      val.textContent = r.value;
      const lab = document.createElement('span');
      lab.className = 'viz-tooltip-label';
      lab.textContent = r.label;
      // values lead, labels follow
      row.appendChild(val);
      row.appendChild(lab);
      this.node.appendChild(row);
    }
    this.node.classList.add('on');
    this.move(ev);
  }
  move(ev) {
    if (!this.node.classList.contains('on')) return;
    const pad = 14;
    const w = this.node.offsetWidth, h = this.node.offsetHeight;
    let x = ev.clientX + pad, y = ev.clientY + pad;
    if (x + w > window.innerWidth - 8) x = ev.clientX - w - pad;
    if (y + h > window.innerHeight - 8) y = ev.clientY - h - pad;
    this.node.style.transform = `translate(${x}px, ${y}px)`;
  }
  hide() { this.node.classList.remove('on'); }
}

let _tooltip = null;
export function tooltip() {
  if (!_tooltip) _tooltip = new Tooltip();
  return _tooltip;
}

// ---- data table (drilldowns; also the accessible fallback view)
export function renderTable(container, rows, opts) {
  const wrap = document.createElement('div');
  wrap.className = 'viz-table-wrap';
  if (!rows || !rows.length) {
    const none = document.createElement('div');
    none.className = 'viz-empty-note';
    none.textContent = 'No rows.';
    wrap.appendChild(none);
    container.appendChild(wrap);
    return wrap;
  }
  const cols = Object.keys(rows[0]);
  const table = document.createElement('table');
  table.className = 'viz-table';
  const thead = document.createElement('thead');
  const hr = document.createElement('tr');
  for (const c of cols) {
    const th = document.createElement('th');
    th.textContent = c.replace(/_/g, ' ');
    hr.appendChild(th);
  }
  thead.appendChild(hr);
  table.appendChild(thead);
  const tbody = document.createElement('tbody');
  const limit = (opts && opts.limit) || 200;
  for (const r of rows.slice(0, limit)) {
    const tr = document.createElement('tr');
    for (const c of cols) {
      const td = document.createElement('td');
      const v = r[c];
      td.textContent = typeof v === 'number' ? formatNumber(v) : (v === null || v === undefined ? '—' : String(v));
      if (typeof v === 'number') td.className = 'viz-tabular';
      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  }
  table.appendChild(tbody);
  wrap.appendChild(table);
  if (rows.length > limit) {
    const more = document.createElement('div');
    more.className = 'viz-table-more';
    more.textContent = `Showing ${limit} of ${rows.length} rows`;
    wrap.appendChild(more);
  }
  container.appendChild(wrap);
  return wrap;
}

// ---- hierarchy: indented tree with magnitude bars (legible > sunburst)
export function renderHierarchy(container, visual, layerData) {
  const root = document.createElement('div');
  root.className = 'viz-hierarchy';
  let items = [];
  for (const layer of visual.layers || []) {
    const rows = layerData.get(layer.layer_id);
    if (Array.isArray(rows)) {
      items = rows.map((r) => ({
        name: r.name || r.label || '—',
        levels: r.hierarchy ? Object.values(r.hierarchy) : (r.levels || []),
        value: Number.isFinite(r.events) ? r.events : (Number.isFinite(r.value) ? r.value : null),
        cls: layer.evidence_class || 'derived',
      }));
      break;
    }
  }
  if (!items.length) {
    const none = document.createElement('div');
    none.className = 'viz-empty-note';
    none.textContent = 'No hierarchy data in this result.';
    root.appendChild(none);
    container.appendChild(root);
    return root;
  }
  const maxV = Math.max(...items.map((i) => i.value || 0), 1);
  // Group by top level for section headers.
  const groups = new Map();
  for (const it of items) {
    const top = (it.levels && it.levels[0]) || '';
    if (!groups.has(top)) groups.set(top, []);
    groups.get(top).push(it);
  }
  for (const [top, members] of groups) {
    if (top) {
      const h = document.createElement('div');
      h.className = 'viz-hier-group';
      h.textContent = String(top).replace(/_/g, ' ');
      root.appendChild(h);
    }
    for (const it of members) {
      const row = document.createElement('div');
      row.className = 'viz-hier-row';
      const label = document.createElement('span');
      label.className = 'viz-hier-label';
      label.textContent = it.name;
      const sub = (it.levels || []).slice(1).filter(Boolean).join(' · ');
      row.appendChild(label);
      if (sub) {
        const s = document.createElement('span');
        s.className = 'viz-hier-sub';
        s.textContent = String(sub).replace(/_/g, ' ');
        row.appendChild(s);
      }
      const barWrap = document.createElement('span');
      barWrap.className = 'viz-hier-barwrap';
      const bar = document.createElement('span');
      bar.className = 'viz-hier-bar';
      bar.style.width = `${Math.max(2, ((it.value || 0) / maxV) * 100)}%`;
      bar.style.background = evidenceColor(it.cls);
      barWrap.appendChild(bar);
      row.appendChild(barWrap);
      if (it.value !== null) {
        const v = document.createElement('span');
        v.className = 'viz-hier-value viz-tabular';
        v.textContent = formatNumber(it.value);
        row.appendChild(v);
      }
      root.appendChild(row);
    }
  }
  container.appendChild(root);
  return root;
}

// ---- summary/fallback card for unknown visual types or blocked visuals
export function renderSummaryCard(container, visual) {
  const card = document.createElement('div');
  card.className = 'viz-summary-card';
  const head = document.createElement('div');
  head.className = 'viz-summary-headline';
  head.textContent = (visual.summary && visual.summary.headline) || visual.title || '';
  card.appendChild(head);
  const denoms = (visual.summary && visual.summary.denominators) || {};
  const keys = Object.keys(denoms);
  if (keys.length) {
    renderStatTiles(card, keys.map((k) => ({
      label: k.replace(/_/g, ' '), value: denoms[k],
    })));
  }
  container.appendChild(card);
  return card;
}

// ---- metric: stat tiles straight from summary denominators + series layers
function renderMetric(container, visual, layerData) {
  const tiles = [];
  const denoms = (visual.summary && visual.summary.denominators) || {};
  for (const k of Object.keys(denoms)) {
    tiles.push({ label: k.replace(/_/g, ' '), value: denoms[k] });
  }
  for (const layer of visual.layers || []) {
    const rows = layerData.get(layer.layer_id);
    if (Array.isArray(rows) && rows.length && Number.isFinite(rows[0].value)) {
      const values = rows.map((r) => r.value).filter(Number.isFinite);
      tiles.push({
        label: layer.legend?.label || evidenceLabel(layer.evidence_class),
        value: values[values.length - 1],
        unit: rows[rows.length - 1].unit,
        spark: values.slice(-12),
        cls: layer.evidence_class,
      });
    }
  }
  if (!tiles.length) return renderSummaryCard(container, visual);
  return renderStatTiles(container, tiles);
}

// ---- registry
const RENDERERS = {
  map: (c, v, d, h) => renderMap(c, v, d, h),
  chart: (c, v, d, h) => renderTimeSeries(c, v, d, h),
  timeline: (c, v, d, h) => renderTimeSeries(c, v, d, h),
  metric: (c, v, d) => renderMetric(c, v, d),
  hierarchy: (c, v, d) => renderHierarchy(c, v, d),
  table: (c, v, d) => {
    for (const layer of v.layers || []) {
      const rows = d.get(layer.layer_id);
      if (Array.isArray(rows)) return renderTable(c, rows);
    }
    return renderSummaryCard(c, v);
  },
};

// Render one visual object into container. layerData: Map(layer_id -> parsed payload).
// hooks: {onDrill(feature, layer)} — tooltip added here.
export function renderVisual(container, visual, layerData, hooks) {
  const h = { tooltip: tooltip(), onDrill: hooks && hooks.onDrill };
  const status = visual.status || 'ready';
  const frame = document.createElement('figure');
  frame.className = `viz-figure viz-status-${status}`;
  frame.dataset.visualType = visual.visual_type;

  if (status === 'blocked' || status === 'failed') {
    // A failed/blocked visual never erases the frame: show summary + limitation stub.
    renderSummaryCard(frame, visual);
  } else if (visual.visual_type === 'dashboard') {
    const grid = document.createElement('div');
    grid.className = 'viz-dashboard-grid';
    frame.appendChild(grid);
    // Dashboard: each layer group renders via its geometry — cells/points/polygon
    // go to a map card, series to a chart card. Compose generically.
    const geoLayers = (visual.layers || []).filter((l) => ['polygon', 'cell', 'point', 'raster'].includes(l.geometry_type));
    const seriesLayers = (visual.layers || []).filter((l) => ['series', 'strip'].includes(l.geometry_type));
    const restLayers = (visual.layers || []).filter((l) => !geoLayers.includes(l) && !seriesLayers.includes(l));
    if (geoLayers.length) {
      const card = document.createElement('div');
      card.className = 'viz-dash-card';
      grid.appendChild(card);
      renderMap(card, { ...visual, layers: geoLayers }, layerData, h);
    }
    if (seriesLayers.length) {
      const card = document.createElement('div');
      card.className = 'viz-dash-card';
      grid.appendChild(card);
      renderTimeSeries(card, { ...visual, layers: seriesLayers }, layerData, h);
    }
    for (const l of restLayers) {
      const rows = layerData.get(l.layer_id);
      if (!Array.isArray(rows)) continue;
      // Rows that reference prior results (headline/title/status) become result
      // cards, not raw tables — a dashboard is a composition of findings.
      if (rows.length && (rows[0].headline || (rows[0].title && rows[0].status))) {
        for (const r of rows) {
          const card = document.createElement('div');
          card.className = 'viz-dash-card viz-result-card';
          const kind = document.createElement('span');
          kind.className = 'viz-result-kind';
          kind.textContent = r.visual_type || '';
          card.appendChild(kind);
          const title = document.createElement('div');
          title.className = 'viz-result-title';
          title.textContent = r.title || '';
          card.appendChild(title);
          const head = document.createElement('div');
          head.className = 'viz-result-headline';
          head.textContent = r.headline || '';
          card.appendChild(head);
          const status = document.createElement('span');
          status.className = `viz-status-pill viz-pill-${r.status || 'complete'}`;
          status.textContent = r.status || '';
          card.appendChild(status);
          grid.appendChild(card);
        }
      } else {
        const card = document.createElement('div');
        card.className = 'viz-dash-card';
        grid.appendChild(card);
        renderTable(card, rows, { limit: 8 });
      }
    }
    if (!grid.childElementCount) renderSummaryCard(frame, visual);
  } else {
    const impl = RENDERERS[visual.visual_type];
    if (impl) impl(frame, visual, layerData, h);
    else renderSummaryCard(frame, visual); // unknown grammar → graceful fallback
  }

  if (status === 'partial') {
    const note = document.createElement('div');
    note.className = 'viz-partial-note';
    note.textContent = 'Partial result — some declared layers are unavailable.';
    frame.appendChild(note);
  }
  container.appendChild(frame);
  return frame;
}
