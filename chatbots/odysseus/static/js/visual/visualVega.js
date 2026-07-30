// visualVega.js — Vega-Lite chart grammar for the visual stage (decision doc:
// dss/VISUAL_BACKEND_DECISION.md). Runs strictly in CSP-interpreter mode (no
// unsafe-eval); specs are built HERE from typed envelope data — producer-supplied
// specs are never accepted. Falls back to the hand-rolled renderer upstream if
// the vendored libs are unavailable.

import { palette, evidenceColor, evidenceLabel } from './visualTheme.js';
import { normaliseSeries, normaliseStrip } from './visualChart.js';

export function vegaAvailable() {
  return typeof window !== 'undefined' && window.vega && window.vegaLite && window.vegaInterpreter;
}

function themeConfig() {
  const p = palette();
  return {
    background: p.surface,
    font: 'system-ui, -apple-system, "Segoe UI", sans-serif',
    axis: {
      labelColor: p.inkMuted, titleColor: p.inkSecondary,
      gridColor: p.grid, domainColor: p.baseline, tickColor: p.baseline,
      labelFontSize: 11, titleFontSize: 11, gridDash: [],
    },
    legend: { labelColor: p.inkSecondary, titleColor: p.inkSecondary, labelFontSize: 12 },
    view: { stroke: null },
    line: { strokeWidth: 2, strokeCap: 'round', strokeJoin: 'round' },
    point: { size: 64, stroke: p.surface, strokeWidth: 2 },
  };
}

// Build a time-series spec from series layers. rows: [{t(ms), value, unit, lower?, upper?, series?}]
export function buildTimeSeriesSpec(visual, layerData, width, height) {
  const seriesLayers = [];
  let strip = null;
  for (const layer of visual.layers || []) {
    const rows = layerData.get(layer.layer_id);
    if (!rows) continue;
    if (/coverage|strip/.test(layer.layer_id) || (rows[0] && 'present' in rows[0])) {
      strip = { layer, cells: normaliseStrip(rows) };
    } else {
      const pts = normaliseSeries(rows).map((d) => ({
        t: d.t, value: d.value, unit: d.unit,
        lower: Number.isFinite(d.raw?.lower) ? d.raw.lower : null,
        upper: Number.isFinite(d.raw?.upper) ? d.raw.upper : null,
        series: layer.legend?.label || evidenceLabel(layer.evidence_class),
        cls: layer.evidence_class || 'observed',
        source_id: d.source_id || null,
      }));
      if (pts.length) seriesLayers.push({ layer, pts });
    }
  }
  if (!seriesLayers.length) return null;
  const all = seriesLayers.flatMap((s) => s.pts);
  const unit = all.find((d) => d.unit)?.unit || '';
  const domain = [...new Set(seriesLayers.map((s) => s.pts[0].series))];
  const range = seriesLayers.map((s) => evidenceColor(s.pts[0].cls));
  const hasBand = all.some((d) => d.lower !== null && d.upper !== null);
  const p = palette();

  const layers = [];
  if (hasBand) {
    layers.push({
      mark: { type: 'errorband', opacity: 0.18 },
      encoding: {
        y: { field: 'lower', type: 'quantitative' },
        y2: { field: 'upper' },
        color: { field: 'series', type: 'nominal', scale: { domain, range }, legend: null },
      },
    });
  }
  layers.push({
    params: [{
      name: 'timeBrush',
      select: { type: 'interval', encodings: ['x'] },
    }],
    mark: { type: 'line' },
    encoding: {
      color: {
        field: 'series', type: 'nominal', scale: { domain, range },
        legend: domain.length > 1 ? { orient: 'top', title: null } : null,
      },
    },
  });
  layers.push({
    // invisible wide-hit points for tooltips (hit target > mark per dataviz rules)
    mark: { type: 'point', opacity: 0, size: 220 },
    encoding: {
      tooltip: [
        { field: 't', type: 'temporal', title: 'date', format: '%b %Y' },
        { field: 'value', type: 'quantitative', title: unit || 'value', format: ',.2f' },
        { field: 'series', type: 'nominal', title: 'series' },
      ],
    },
  });

  const innerW = Math.max(320, width - 110);
  const main = {
    width: innerW,
    height: strip ? Math.max(180, height - 70) : Math.max(200, height - 30),
    data: { name: 'series' },
    layer: layers,
    encoding: {
      x: { field: 't', type: 'temporal', axis: { title: null, format: '%Y', tickCount: 'year' } },
      y: {
        field: 'value', type: 'quantitative',
        axis: { title: unit || null }, scale: { zero: false },
      },
    },
  };

  // Annotations: point anchors → labelled dot; range anchors → shaded band.
  const anns = (visual.annotations || []).filter((a) => a.anchor);
  for (const ann of anns) {
    const a = ann.anchor;
    const toMs = (v) => (typeof v === 'number' ? v : Date.parse(v));
    if (a.kind === 'point' && a.t !== undefined) {
      const t = toMs(a.t);
      const datum = { t, value: Number.isFinite(a.value) ? a.value : null, label: ann.text || '' };
      // Labels near the right edge of the time domain flip to the left of the
      // dot, so they never run off the plot.
      const ts = all.map((d) => toMs(d.t)).filter(Number.isFinite);
      const tMin = Math.min(...ts), tMax = Math.max(...ts);
      const nearRight = ts.length > 1 && (t - tMin) / (tMax - tMin) > 0.72;
      main.layer.push({
        data: { values: [datum] },
        mark: { type: 'point', filled: true, size: 70, color: p.inkPrimary },
        encoding: {
          x: { field: 't', type: 'temporal' },
          y: datum.value !== null ? { field: 'value', type: 'quantitative' } : undefined,
        },
      });
      main.layer.push({
        data: { values: [datum] },
        mark: {
          type: 'text', align: nearRight ? 'right' : 'left', dx: nearRight ? -8 : 8, dy: -10,
          fontWeight: ann.emphasis === 'primary' ? 650 : 400,
          fontSize: ann.emphasis === 'primary' ? 13 : 11.5,
          color: p.inkPrimary,
        },
        encoding: {
          x: { field: 't', type: 'temporal' },
          y: datum.value !== null ? { field: 'value', type: 'quantitative' } : undefined,
          text: { field: 'label' },
        },
      });
    } else if (a.kind === 'range' && a.start !== undefined && a.end !== undefined) {
      main.layer.unshift({
        data: { values: [{ s: toMs(a.start), e: toMs(a.end) }] },
        mark: { type: 'rect', opacity: 0.08, color: p.inkPrimary },
        encoding: { x: { field: 's', type: 'temporal' }, x2: { field: 'e' } },
      });
    }
  }

  const spec = { config: themeConfig(), datasets: { series: all }, vconcat: [main], resolve: { scale: { color: 'independent' } } };
  if (strip && strip.cells.length) {
    spec.datasets.strip = strip.cells.map((c) => ({ t: c.t, present: c.present ? 'covered' : 'missing' }));
    spec.vconcat.push({
      width: innerW,
      height: 16,
      data: { name: 'strip' },
      mark: { type: 'tick', thickness: 5, height: 12 },
      encoding: {
        x: { field: 't', type: 'temporal', axis: null },
        color: {
          field: 'present', type: 'nominal', legend: null,
          scale: {
            domain: ['covered', 'missing'],
            range: [evidenceColor(strip.layer.evidence_class || 'derived'), p.inkMuted],
          },
        },
      },
    });
  }
  return spec;
}

// Faceted small multiples when a grouping field with 2–8 values exists.
export function buildFacetedSeriesSpec(visual, layerData, width) {
  for (const layer of visual.layers || []) {
    const rows = layerData.get(layer.layer_id);
    if (!Array.isArray(rows) || !rows.length) continue;
    const groupKey = ['series', 'group', 'entity', 'facet'].find(
      (k) => rows[0][k] !== undefined
    );
    if (!groupKey) continue;
    const groups = [...new Set(rows.map((r) => r[groupKey]))];
    if (groups.length < 2 || groups.length > 8) continue;
    const pts = normaliseSeries(rows).map((d) => ({
      t: d.t, value: d.value, g: d.raw[groupKey], unit: d.unit,
    })).filter((d) => d.value !== null);
    if (!pts.length) continue;
    const color = evidenceColor(layer.evidence_class || 'observed');
    return {
      config: themeConfig(),
      data: { values: pts },
      facet: { field: 'g', type: 'nominal', columns: Math.min(4, groups.length), title: null },
      spec: {
        width: Math.max(160, Math.floor((width - 80) / Math.min(4, groups.length)) - 24),
        height: 120,
        mark: { type: 'line', color },
        encoding: {
          x: { field: 't', type: 'temporal', axis: { title: null, format: '%Y', tickCount: 'year' } },
          y: { field: 'value', type: 'quantitative', axis: { title: null }, scale: { zero: false } },
          tooltip: [
            { field: 'g', type: 'nominal', title: 'group' },
            { field: 't', type: 'temporal', title: 'date', format: '%b %Y' },
            { field: 'value', type: 'quantitative', format: ',.2f' },
          ],
        },
      },
    };
  }
  return null;
}

// Render a spec in strict CSP mode. Returns the vega View (caller owns cleanup).
export async function renderSpec(container, spec, hooks) {
  const vg = window.vega;
  const vl = window.vegaLite;
  const compiled = vl.compile(spec).spec;
  const runtime = vg.parse(compiled, null, { ast: true });
  const view = new vg.View(runtime, {
    renderer: 'svg',
    container,
    expr: window.vegaInterpreter.expressionInterpreter
      || window.vegaInterpreter, // package exports the interpreter directly in some builds
    hover: true,
  });
  await view.runAsync();
  if (hooks && hooks.onBrush) {
    try {
      view.addSignalListener('timeBrush', (_name, value) => hooks.onBrush(value || {}));
    } catch { /* spec without the brush param */ }
  }
  if (hooks && hooks.onClickDatum) {
    view.addEventListener('click', (_ev, item) => {
      if (item && item.datum) hooks.onClickDatum(item.datum);
    });
  }
  return view;
}
