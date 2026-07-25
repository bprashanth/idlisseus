// visualChart.js — SVG time-series renderer (line + area wash + coverage strip)
// and stat tiles, per the dataviz mark specs: 2px lines, ≥8px end markers with
// surface rings, hairline solid gridlines, crosshair tooltip listing every series.

import { palette, evidenceColor, evidenceLabel, formatNumber, hatchPattern } from './visualTheme.js';

const SVG = 'http://www.w3.org/2000/svg';

function el(name, attrs) {
  const node = document.createElementNS(SVG, name);
  for (const k in attrs || {}) node.setAttribute(k, attrs[k]);
  return node;
}

// Normalise series rows into {t, value, unit, source_id, label}. Accepts
// {year, month?, value} rows or {date|time|t, value} rows — generic on purpose.
export function normaliseSeries(rows) {
  const out = [];
  for (const r of rows || []) {
    let t = null;
    if (Number.isFinite(r.year)) {
      const m = Number.isFinite(r.month) ? r.month : 1;
      t = Date.UTC(r.year, m - 1, 15);
    } else if (r.date || r.time || r.t) {
      const parsed = Date.parse(r.date || r.time || r.t);
      if (Number.isFinite(parsed)) t = parsed;
    }
    if (t === null) continue;
    out.push({ t, value: Number.isFinite(r.value) ? r.value : null, unit: r.unit, source_id: r.source_id, raw: r });
  }
  out.sort((a, b) => a.t - b.t);
  return out;
}

export function normaliseStrip(rows) {
  const out = [];
  for (const r of rows || []) {
    if (!Number.isFinite(r.year)) continue;
    const m = Number.isFinite(r.month) ? r.month : 1;
    out.push({ t: Date.UTC(r.year, m - 1, 15), present: !!r.present });
  }
  out.sort((a, b) => a.t - b.t);
  return out;
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
function fmtT(t, span) {
  const d = new Date(t);
  if (span > 3 * 365 * 86400e3) return String(d.getUTCFullYear());
  return `${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
}

function niceTicks(min, max, n) {
  const span = max - min || 1;
  const step0 = span / n;
  const mag = Math.pow(10, Math.floor(Math.log10(step0)));
  const step = [1, 2, 5, 10].map((m) => m * mag).find((s) => span / s <= n) || mag * 10;
  const ticks = [];
  for (let v = Math.ceil(min / step) * step; v <= max + 1e-9; v += step) ticks.push(v);
  return ticks;
}

export function renderTimeSeries(container, visual, layerData, hooks) {
  const p = palette();
  const root = document.createElement('div');
  root.className = 'viz-chart-root';
  container.appendChild(root);

  // Split layers: series-bearing vs coverage strips.
  const seriesLayers = [];
  let strip = null;
  for (const layer of visual.layers || []) {
    const rows = layerData.get(layer.layer_id);
    if (!rows) continue;
    if (/coverage|strip/.test(layer.layer_id) || (rows[0] && 'present' in rows[0])) {
      strip = { layer, cells: normaliseStrip(rows) };
    } else {
      const pts = normaliseSeries(rows);
      if (pts.length) seriesLayers.push({ layer, pts });
    }
  }
  if (!seriesLayers.length) {
    const none = document.createElement('div');
    none.className = 'viz-empty-note';
    none.textContent = 'No series data in this result.';
    root.appendChild(none);
    return root;
  }

  const width = Math.max(360, root.clientWidth || container.clientWidth || 800);
  const stripH = strip ? 26 : 0;
  const height = Math.max(240, Math.min(430, (root.clientHeight || 360)));
  const m = { top: 18, right: 84, bottom: 34 + stripH, left: 56 };
  const iw = width - m.left - m.right;
  const ih = height - m.top - m.bottom;

  const allT = seriesLayers.flatMap((s) => s.pts.map((d) => d.t));
  const allV = seriesLayers.flatMap((s) => s.pts.map((d) => d.value)).filter((v) => v !== null);
  const t0 = Math.min(...allT), t1 = Math.max(...allT);
  let v0 = Math.min(...allV), v1 = Math.max(...allV);
  if (v0 === v1) { v0 -= 1; v1 += 1; }
  const vPad = (v1 - v0) * 0.12;
  const vlo = Math.max(0, v0 - vPad) < v0 * 0.5 ? 0 : v0 - vPad; // baseline at 0 when close
  const vhi = v1 + vPad;
  const x = (t) => m.left + ((t - t0) / (t1 - t0 || 1)) * iw;
  const y = (v) => m.top + ih - ((v - vlo) / (vhi - vlo)) * ih;

  const svg = el('svg', { class: 'viz-chart', viewBox: `0 0 ${width} ${height}`, role: 'img', 'aria-label': visual.title || 'chart' });
  root.appendChild(svg);
  const defs = el('defs');
  svg.appendChild(defs);
  svg.appendChild(el('rect', { x: 0, y: 0, width, height, fill: p.surface, rx: 12 }));

  // gridlines + y ticks (clean numbers, hairline solid)
  const unit = seriesLayers[0].pts.find((d) => d.unit)?.unit || '';
  for (const tv of niceTicks(vlo, vhi, 4)) {
    svg.appendChild(el('line', { x1: m.left, y1: y(tv), x2: width - m.right, y2: y(tv), stroke: p.grid, 'stroke-width': 1 }));
    const t = el('text', { x: m.left - 8, y: y(tv) + 4, 'text-anchor': 'end', class: 'viz-axis-label viz-tabular' });
    t.textContent = formatNumber(tv);
    svg.appendChild(t);
  }
  if (unit) {
    const u = el('text', { x: m.left - 8, y: m.top - 4, 'text-anchor': 'end', class: 'viz-axis-unit' });
    u.textContent = unit;
    svg.appendChild(u);
  }
  // x ticks
  const span = t1 - t0;
  const years = new Set();
  for (const t of allT) years.add(new Date(t).getUTCFullYear());
  const yearList = [...years].sort();
  const tickEvery = Math.max(1, Math.ceil(yearList.length / 7));
  for (let i = 0; i < yearList.length; i += tickEvery) {
    const yr = yearList[i];
    const tx = x(Date.UTC(yr, 5, 15));
    const t = el('text', { x: tx, y: height - stripH - 12, 'text-anchor': 'middle', class: 'viz-axis-label' });
    t.textContent = String(yr);
    svg.appendChild(t);
  }
  // baseline
  svg.appendChild(el('line', { x1: m.left, y1: m.top + ih, x2: width - m.right, y2: m.top + ih, stroke: p.baseline, 'stroke-width': 1 }));

  // series (gaps break the line; area wash at 10%)
  seriesLayers.forEach((s, idx) => {
    const color = evidenceColor(s.layer.evidence_class || 'observed');
    let d = '', area = '', started = false, lastX = null;
    for (const pt of s.pts) {
      if (pt.value === null) { started = false; continue; }
      const X = x(pt.t).toFixed(1), Y = y(pt.value).toFixed(1);
      d += started ? ` L ${X} ${Y}` : ` M ${X} ${Y}`;
      area += started ? ` L ${X} ${Y}` : `${area ? ' ' : ''}M ${X} ${y(vlo).toFixed(1)} L ${X} ${Y}`;
      started = true;
      lastX = { X, Y, pt };
    }
    if (area) area += ` L ${lastX.X} ${y(vlo).toFixed(1)} Z`;
    if (idx === 0 && area) svg.appendChild(el('path', { d: area, fill: color, opacity: 0.1 }));
    svg.appendChild(el('path', {
      d, fill: 'none', stroke: color, 'stroke-width': 2,
      'stroke-linecap': 'round', 'stroke-linejoin': 'round',
      'stroke-dasharray': s.layer.evidence_class === 'proxy' ? '6 4' : '',
    }));
    // end marker ≥8px with surface ring + direct end label
    if (lastX) {
      svg.appendChild(el('circle', { cx: lastX.X, cy: lastX.Y, r: 4.5, fill: color, stroke: p.surface, 'stroke-width': 2 }));
      const lbl = el('text', { x: Number(lastX.X) + 10, y: Number(lastX.Y) + 4, class: 'viz-end-label' });
      lbl.textContent = formatNumber(lastX.pt.value);
      svg.appendChild(lbl);
    }
  });

  // coverage strip
  if (strip && strip.cells.length) {
    const missing = hatchPattern(SVG, p.inkMuted);
    defs.appendChild(missing.pattern);
    const sy = height - stripH + 2;
    const cellW = Math.max(2, iw / strip.cells.length - 1);
    for (const c of strip.cells) {
      svg.appendChild(el('rect', {
        x: x(c.t) - cellW / 2, y: sy, width: cellW, height: 8, rx: 1.5,
        fill: c.present ? evidenceColor(strip.layer.evidence_class || 'derived') : `url(#${missing.id})`,
        opacity: c.present ? 0.8 : 0.9,
      }));
    }
    const lab = el('text', { x: m.left, y: sy + 20, class: 'viz-axis-label' });
    lab.textContent = strip.layer.legend?.label || 'Coverage';
    svg.appendChild(lab);
  }

  // legend for ≥2 series
  if (seriesLayers.length >= 2) {
    const legend = document.createElement('div');
    legend.className = 'viz-chart-legend';
    for (const s of seriesLayers) {
      const item = document.createElement('span');
      item.className = 'viz-legend-item';
      const key = document.createElement('span');
      key.className = 'viz-legend-linekey';
      key.style.setProperty('--sw', evidenceColor(s.layer.evidence_class || 'observed'));
      item.appendChild(key);
      const lab = document.createElement('span');
      lab.textContent = s.layer.legend?.label || evidenceLabel(s.layer.evidence_class);
      item.appendChild(lab);
      legend.appendChild(item);
    }
    root.appendChild(legend);
  }

  // crosshair tooltip: vertical hairline snaps to nearest t; lists every series
  const cross = el('line', { y1: m.top, y2: m.top + ih, stroke: p.inkMuted, 'stroke-width': 1, opacity: 0 });
  svg.appendChild(cross);
  const hitTs = [...new Set(seriesLayers.flatMap((s) => s.pts.filter((d) => d.value !== null).map((d) => d.t)))].sort((a, b) => a - b);
  svg.addEventListener('pointermove', (ev) => {
    const rect = svg.getBoundingClientRect();
    const mx = ((ev.clientX - rect.left) / rect.width) * width;
    if (mx < m.left || mx > width - m.right) { cross.setAttribute('opacity', 0); hooks.tooltip.hide(); return; }
    let best = hitTs[0], bd = Infinity;
    for (const t of hitTs) {
      const d = Math.abs(x(t) - mx);
      if (d < bd) { bd = d; best = t; }
    }
    cross.setAttribute('x1', x(best));
    cross.setAttribute('x2', x(best));
    cross.setAttribute('opacity', 0.6);
    const rows = [{ label: fmtT(best, span), value: '', header: true }];
    for (const s of seriesLayers) {
      const pt = s.pts.find((d) => d.t === best && d.value !== null);
      if (pt) {
        rows.push({
          label: s.layer.legend?.label || evidenceLabel(s.layer.evidence_class),
          value: `${formatNumber(pt.value)}${pt.unit ? ' ' + pt.unit : ''}`,
          strong: true, cls: s.layer.evidence_class,
        });
      }
    }
    hooks.tooltip.show(ev, rows);
  });
  svg.addEventListener('pointerleave', () => { cross.setAttribute('opacity', 0); hooks.tooltip.hide(); });
  return root;
}

// ---- stat tiles (metric visual_type, and dashboard summary rows)
export function renderStatTiles(container, tiles) {
  // tiles: [{label, value, unit, delta, spark: [numbers], cls}]
  const row = document.createElement('div');
  row.className = 'viz-stat-row';
  for (const t of tiles) {
    const tile = document.createElement('div');
    tile.className = 'viz-stat-tile';
    const lab = document.createElement('div');
    lab.className = 'viz-stat-label';
    lab.textContent = t.label;
    tile.appendChild(lab);
    const val = document.createElement('div');
    val.className = 'viz-stat-value';
    val.textContent = formatNumber(t.value) + (t.unit ? ` ${t.unit}` : '');
    tile.appendChild(val);
    if (t.spark && t.spark.length > 1) tile.appendChild(sparkline(t.spark, t.cls));
    row.appendChild(tile);
  }
  container.appendChild(row);
  return row;
}

function sparkline(values, cls) {
  const w = 96, h = 26;
  const svg = el('svg', { class: 'viz-sparkline', viewBox: `0 0 ${w} ${h}` });
  const lo = Math.min(...values), hi = Math.max(...values);
  const pts = values.map((v, i) => `${(i / (values.length - 1)) * w},${h - 3 - ((v - lo) / (hi - lo || 1)) * (h - 6)}`);
  svg.appendChild(el('polyline', {
    points: pts.join(' '), fill: 'none',
    stroke: evidenceColor(cls || 'observed'), 'stroke-width': 1.5,
    'stroke-linecap': 'round', 'stroke-linejoin': 'round',
  }));
  const [lx, ly] = pts[pts.length - 1].split(',');
  svg.appendChild(el('circle', { cx: lx, cy: ly, r: 2.5, fill: evidenceColor(cls || 'observed') }));
  return svg;
}
