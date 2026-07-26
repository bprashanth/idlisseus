// visualMap.js — tile-less SVG "figure map" renderer.
// Draws idli-result/1 map visuals (GeoJSON layers: polygons, cells, points) with a
// print-quality look: neutral surface, hairline graticule, scale bar, evidence-class
// styling, hover tooltips, click-to-drilldown. No external tiles, no libraries.

import {
  palette, evidenceColor, evidenceLabel, quantileRamp, hatchPattern, stipplePattern,
  RAMP_BLUE, RAMP_ORANGE, formatNumber, isDarkMode,
} from './visualTheme.js';

const SVG = 'http://www.w3.org/2000/svg';

function el(name, attrs) {
  const node = document.createElementNS(SVG, name);
  for (const k in attrs || {}) node.setAttribute(k, attrs[k]);
  return node;
}

function geomCoords(geometry) {
  // Yields [lon, lat] pairs for bounds computation.
  const out = [];
  const walk = (c) => {
    if (typeof c[0] === 'number') { out.push(c); return; }
    for (const inner of c) walk(inner);
  };
  if (geometry && geometry.coordinates) walk(geometry.coordinates);
  return out;
}

function haversineKm(lat, lon1, lon2) {
  const rad = Math.PI / 180;
  return 6371 * Math.abs(lon2 - lon1) * rad * Math.cos(lat * rad);
}

// Numeric magnitude property of a cell/point feature, generically:
// prefer common count-ish keys, else the first finite numeric property.
const MAGNITUDE_KEYS = ['records', 'count', 'value', 'effort', 'estimate', 'entities', 'persondays'];
export function magnitudeOf(props) {
  for (const k of MAGNITUDE_KEYS) {
    if (Number.isFinite(props[k])) return { key: k, value: props[k] };
  }
  for (const k in props) {
    if (Number.isFinite(props[k])) return { key: k, value: props[k] };
  }
  return { key: null, value: null };
}

export function renderMap(container, visual, layerData, hooks) {
  // layerData: Map(layer_id -> parsed GeoJSON FeatureCollection)
  // hooks: { onDrill(feature, layer), tooltip }
  const p = palette();
  const root = document.createElement('div');
  root.className = 'viz-map-root';
  container.appendChild(root);

  const width = Math.max(320, root.clientWidth || container.clientWidth || 800);
  const height = Math.max(280, root.clientHeight || container.clientHeight || 520);

  // ---- bounds over all layers
  let minLon = Infinity, maxLon = -Infinity, minLat = Infinity, maxLat = -Infinity;
  // Two passes: features the reader asked about first (declared target roles),
  // falling back to everything when a result is entirely context.
  const isContextFeature = (f) => {
    const p = (f && f.properties) || {};
    const role = String(p.scope_role || p.role || '').toLowerCase();
    return role.includes('context') || role.includes('donor') || role.includes('comparison');
  };
  const emphasisIds = new Set(
    (visual.layers || [])
      .filter((l) => (l.style_hint || {}).emphasis === 'primary')
      .map((l) => l.layer_id)
  );
  // Pass 1: the layer the answer is about. Pass 2: everything non-context.
  // Pass 3: everything, for results that are entirely context.
  for (const pass of [0, 1, 2]) {
    for (const [layerId, fc] of layerData) {
      if (pass === 0 && emphasisIds.size && !emphasisIds.has(layerId)) continue;
      if (pass === 0 && !emphasisIds.size) continue;
      for (const f of (fc && fc.features) || []) {
        if (pass === 1 && isContextFeature(f)) continue;
        for (const [lon, lat] of geomCoords(f.geometry)) {
          if (lon < minLon) minLon = lon;
          if (lon > maxLon) maxLon = lon;
          if (lat < minLat) minLat = lat;
          if (lat > maxLat) maxLat = lat;
        }
      }
    }
    if (Number.isFinite(minLon)) break;
  }
  if (!Number.isFinite(minLon)) { minLon = 0; maxLon = 1; minLat = 0; maxLat = 1; }
  // Enforce a minimum extent so a single place still gets a legible neighbourhood.
  const MIN_SPAN = 0.02;
  if (maxLon - minLon < MIN_SPAN) {
    const c = (minLon + maxLon) / 2;
    minLon = c - MIN_SPAN / 2; maxLon = c + MIN_SPAN / 2;
  }
  if (maxLat - minLat < MIN_SPAN) {
    const c = (minLat + maxLat) / 2;
    minLat = c - MIN_SPAN / 2; maxLat = c + MIN_SPAN / 2;
  }
  const padLon = (maxLon - minLon) * 0.08;
  const padLat = (maxLat - minLat) * 0.08;
  minLon -= padLon; maxLon += padLon; minLat -= padLat; maxLat += padLat;

  // ---- Web-Mercator projection (conformal; basemap tiles align exactly)
  const midLat = (minLat + maxLat) / 2;
  const mercDeg = (lat) => {
    const r = Math.max(-85, Math.min(85, lat)) * Math.PI / 180;
    return Math.log(Math.tan(Math.PI / 4 + r / 2)) * 180 / Math.PI;
  };
  const spanX = maxLon - minLon;
  const spanY = mercDeg(maxLat) - mercDeg(minLat);
  const scale = Math.min(width / spanX, height / spanY);
  const ox = (width - spanX * scale) / 2;
  const oy = (height - spanY * scale) / 2;
  const px = (lon) => ox + (lon - minLon) * scale;
  const py = (lat) => oy + (mercDeg(maxLat) - mercDeg(lat)) * scale;
  const kmPerPx = haversineKm(midLat, minLon, maxLon) / (spanX * scale);

  const svg = el('svg', {
    class: 'viz-map', viewBox: `0 0 ${width} ${height}`,
    role: 'img', 'aria-label': visual.title || 'map',
  });
  root.appendChild(svg);
  const defs = el('defs');
  svg.appendChild(defs);
  svg.appendChild(el('rect', { x: 0, y: 0, width, height, fill: p.surface, rx: 12 }));
  const world = el('g', { class: 'viz-map-world' });
  svg.appendChild(world);
  const legendEntries = [];
  const ramps = { used: 0 };

  // ---- optional basemap (slippy tiles through the same-origin caching proxy).
  // Off by default: the figure map is the identity; terrain is a user choice.
  const basemapGroup = el('g', { class: 'viz-basemap' });
  world.appendChild(basemapGroup);
  const drawBasemap = (source) => {
    basemapGroup.replaceChildren();
    root.querySelector('.viz-map-attrib')?.remove();
    if (!source || source === 'none') return;
    const n = (z) => Math.pow(2, z);
    let z = 15;
    while (z > 2 && (360 / n(z)) * scale < 220) z -= 1;
    const tX = (lon, zz) => Math.floor(((lon + 180) / 360) * n(zz));
    const tY = (lat, zz) => {
      const r = lat * Math.PI / 180;
      return Math.floor(((1 - Math.log(Math.tan(r) + 1 / Math.cos(r)) / Math.PI) / 2) * n(zz));
    };
    const lonOfX = (x, zz) => (x / n(zz)) * 360 - 180;
    const latOfY = (y, zz) => Math.atan(Math.sinh(Math.PI * (1 - (2 * y) / n(zz)))) * 180 / Math.PI;
    const x0 = tX(minLon, z), x1 = tX(maxLon, z);
    const y0 = tY(maxLat, z), y1 = tY(minLat, z);
    for (let x = x0; x <= x1; x++) {
      for (let y = y0; y <= y1; y++) {
        const w = px(lonOfX(x + 1, z)) - px(lonOfX(x, z));
        const h = py(latOfY(y + 1, z)) - py(latOfY(y, z));
        const img = el('image', {
          x: px(lonOfX(x, z)).toFixed(1), y: py(latOfY(y, z)).toFixed(1),
          width: w.toFixed(1), height: h.toFixed(1),
          preserveAspectRatio: 'none',
        });
        img.setAttribute('href', `/api/visual/tiles/${source}/${z}/${x}/${y}.png`);
        basemapGroup.appendChild(img);
      }
    }
    const attrib = document.createElement('div');
    attrib.className = 'viz-map-attrib';
    attrib.textContent = source === 'terrain'
      ? '© OpenStreetMap contributors · © OpenTopoMap (CC-BY-SA)'
      : '© OpenStreetMap contributors';
    root.appendChild(attrib);
  };
  const savedBase = localStorage.getItem('viz-basemap') || 'none';
  drawBasemap(savedBase);
  const basePick = document.createElement('select');
  basePick.className = 'viz-basemap-pick';
  basePick.setAttribute('aria-label', 'Basemap');
  for (const [v, label] of [['none', 'No basemap'], ['terrain', 'Terrain'], ['osm', 'Streets']]) {
    const o = document.createElement('option');
    o.value = v; o.textContent = label;
    basePick.appendChild(o);
  }
  basePick.value = ['none', 'terrain', 'osm'].includes(savedBase) ? savedBase : 'none';
  basePick.addEventListener('change', () => {
    localStorage.setItem('viz-basemap', basePick.value);
    drawBasemap(basePick.value);
  });
  root.appendChild(basePick);

  // ---- computed layers as georeferenced image overlays (e.g. built-up, terrain
  // products from an earth-layer skill): geometry_type "raster_image" with
  // layer.bounds = [w, s, e, n]; the data_ref handle serves the image bytes.
  for (const layer of visual.layers || []) {
    if (layer.geometry_type !== 'raster_image' || !Array.isArray(layer.bounds)) continue;
    const [wB, sB, eB, nB] = layer.bounds;
    const url = hooks.rawUrl && hooks.rawUrl(layer.data_ref);
    if (!url) continue;
    const img = el('image', {
      x: px(wB).toFixed(1), y: py(nB).toFixed(1),
      width: (px(eB) - px(wB)).toFixed(1), height: (py(sB) - py(nB)).toFixed(1),
      preserveAspectRatio: 'none',
      opacity: (layer.style_hint && layer.style_hint.opacity) || 0.75,
    });
    img.setAttribute('href', url);
    world.appendChild(img);
    legendEntries.push({ swatch: 'ramp', ramp: ['#666', '#ccc'], min: null, max: null,
      label: layer.legend?.label || 'computed layer' });
  }

  // ---- graticule (hairline, recessive)
  const grat = el('g');
  world.appendChild(grat);
  const stepCandidates = [0.01, 0.02, 0.05, 0.1, 0.25, 0.5, 1];
  const gstep = stepCandidates.find((s) => (maxLon - minLon) / s <= 8) || 1;
  const gratLabels = width >= 520;
  for (let lon = Math.ceil(minLon / gstep) * gstep; lon < maxLon; lon += gstep) {
    grat.appendChild(el('line', {
      x1: px(lon), y1: 0, x2: px(lon), y2: height, stroke: p.grid, 'stroke-width': 1,
    }));
    if (gratLabels) {
      const t = el('text', { x: px(lon) + 3, y: height - 6, class: 'viz-map-grat-label' });
      t.textContent = `${lon.toFixed(2)}°`;
      grat.appendChild(t);
    }
  }
  for (let lat = Math.ceil(minLat / gstep) * gstep; lat < maxLat; lat += gstep) {
    grat.appendChild(el('line', {
      x1: 0, y1: py(lat), x2: width, y2: py(lat), stroke: p.grid, 'stroke-width': 1,
    }));
    if (gratLabels) {
      const t = el('text', { x: 6, y: py(lat) - 3, class: 'viz-map-grat-label' });
      t.textContent = `${lat.toFixed(2)}°`;
      grat.appendChild(t);
    }
  }

  // ---- draw layers in class order: polygons first, cells, then points on top
  const ordered = [...(visual.layers || [])].sort((a, b) => {
    const rank = { polygon: 0, raster: 1, cell: 1, line: 2, point: 3 };
    return (rank[a.geometry_type] ?? 1) - (rank[b.geometry_type] ?? 1);
  });

  let modelledRasters = 0;
  let filledCellLayers = 0;
  for (const layer of ordered) {
    const fc = layerData.get(layer.layer_id);
    if (!fc || !fc.features || !fc.features.length) continue;
    const cls = layer.evidence_class || 'observed';
    const color = evidenceColor(cls);
    const g = el('g', { class: `viz-layer viz-layer-${cls}`, 'data-layer': layer.layer_id });
    world.appendChild(g);

    if (layer.geometry_type === 'polygon' && cls === 'reported') {
      // Declared boundary: outlined, never filled solid.
      for (const f of fc.features) {
        const d = pathFor(f.geometry, px, py);
        g.appendChild(el('path', {
          d, fill: color, 'fill-opacity': 0.04,
          stroke: color, 'stroke-width': 1.5, 'stroke-dasharray': '', 'stroke-linejoin': 'round',
        }));
      }
      legendEntries.push({ swatch: 'outline', color, label: layer.legend?.label || evidenceLabel(cls) });
    } else if (cls === 'modelled' && layer.geometry_type === 'raster' && modelledRasters++ > 0) {
      // Second modelled surface (e.g. uncertainty beside estimate): outline-only
      // dashed cells so it never occludes the estimate or observed marks.
      for (const f of fc.features) {
        const d = pathFor(f.geometry, px, py);
        const cell = el('path', {
          d, fill: 'none', stroke: color, 'stroke-width': 1.2,
          'stroke-dasharray': '4 3', opacity: 0.7, tabindex: '0', role: 'button',
        });
        const props = f.properties || {};
        const { key, value } = magnitudeOf(props);
        attachHover(cell, hooks, () => tooltipRows(layer, props, key, value));
        attachDrill(cell, hooks, f, layer);
        g.appendChild(cell);
      }
      legendEntries.push({ swatch: 'outline', color, label: layer.legend?.label || evidenceLabel(cls) });
    } else if (cls === 'missing' && ['cell', 'polygon', 'raster'].includes(layer.geometry_type)) {
      // Absence is drawn, never implied — and never colored like data.
      const missing = hatchPattern(SVG, p.inkMuted);
      defs.appendChild(missing.pattern);
      for (const f of fc.features) {
        const d = pathFor(f.geometry, px, py);
        const cell = el('path', {
          d, fill: `url(#${missing.id})`,
          stroke: p.baseline, 'stroke-width': 1, 'stroke-linejoin': 'round',
          tabindex: '0', role: 'button',
        });
        const props = f.properties || {};
        attachHover(cell, hooks, () => tooltipRows(layer, props, null, null));
        attachDrill(cell, hooks, f, layer);
        g.appendChild(cell);
      }
      legendEntries.push({ swatch: 'hatch', color: p.inkMuted, label: layer.legend?.label || evidenceLabel(cls) });
    } else if (cls !== 'modelled' && ['cell', 'raster'].includes(layer.geometry_type) && filledCellLayers > 0) {
      // A second concurrent cell layer (e.g. effort beside coverage) draws as
      // weighted outlines, never a second fill — two fills mud together.
      const values = fc.features.map((f) => magnitudeOf(f.properties || {}).value);
      const vmax = Math.max(...values.filter(Number.isFinite), 1);
      const oc = palette().modelled; // orange family: the second-context hue
      for (const f of fc.features) {
        const props = f.properties || {};
        const { key, value } = magnitudeOf(props);
        const w = 1.5 + 2.5 * Math.sqrt((value || 0) / vmax);
        const d = pathFor(f.geometry, px, py);
        const cell = el('path', {
          d, fill: 'none', stroke: oc, 'stroke-width': w.toFixed(1),
          'stroke-linejoin': 'round', tabindex: '0', role: 'button',
        });
        attachHover(cell, hooks, () => tooltipRows(layer, props, key, value));
        attachDrill(cell, hooks, f, layer);
        g.appendChild(cell);
      }
      legendEntries.push({ swatch: 'outline', color: oc, label: layer.legend?.label || evidenceLabel(cls) });
    } else if (['cell', 'polygon', 'raster'].includes(layer.geometry_type)) {
      // Choropleth cells. Primary magnitude ramp = blue; second concurrent ramp = orange;
      // modelled surfaces always use the modelled treatment (orange + translucency).
      const values = fc.features.map((f) => magnitudeOf(f.properties || {}).value);
      const ramp = cls === 'modelled' ? RAMP_ORANGE : (ramps.used === 0 ? RAMP_BLUE : RAMP_ORANGE);
      if (cls !== 'modelled') { ramps.used += 1; filledCellLayers += 1; }
      const q = quantileRamp(values, ramp, 5);
      // Model-agreement texture (IPCC convention): stipple = robust signal,
      // hatch = low agreement or weak signal. Declared in the envelope, never inferred.
      let agreementOverlay = null;
      const agr = layer.uncertainty && layer.uncertainty.agreement;
      if (cls === 'modelled' && agr) {
        if (agr.fraction >= 0.9 && (agr.signal_to_noise || 0) > 2) {
          const s = stipplePattern(SVG, p.inkPrimary);
          defs.appendChild(s.pattern);
          agreementOverlay = { id: s.id, label: 'robust agreement' };
        } else if (agr.fraction < 0.8 || (agr.signal_to_noise || 99) < 1) {
          const hh = hatchPattern(SVG, p.inkPrimary);
          defs.appendChild(hh.pattern);
          agreementOverlay = { id: hh.id, label: 'low model agreement' };
        }
      }
      const missing = hatchPattern(SVG, p.inkMuted);
      defs.appendChild(missing.pattern);
      for (const f of fc.features) {
        const props = f.properties || {};
        const { key, value } = magnitudeOf(props);
        const fill = q.colorFor(value);
        const d = pathFor(f.geometry, px, py);
        const cell = el('path', {
          d,
          fill: fill || `url(#${missing.id})`,
          'fill-opacity': cls === 'modelled' ? 0.55 : 0.85,
          stroke: p.surface, 'stroke-width': 2, 'stroke-linejoin': 'round',
          tabindex: '0', role: 'button',
        });
        attachHover(cell, hooks, () => tooltipRows(layer, props, key, value));
        attachDrill(cell, hooks, f, layer);
        g.appendChild(cell);
        if (agreementOverlay) {
          g.appendChild(el('path', {
            d, fill: `url(#${agreementOverlay.id})`, 'pointer-events': 'none',
          }));
        }
      }
      legendEntries.push({
        swatch: 'ramp', ramp: q.colors || [], min: q.min, max: q.max,
        label: layer.legend?.label || evidenceLabel(cls),
        hatched: cls === 'modelled',
      });
      if (agreementOverlay) {
        legendEntries.push({ swatch: 'hatch', color: p.inkPrimary, label: agreementOverlay.label });
      }
      if (layer.absence_semantics === 'unknown') {
        legendEntries.push({ swatch: 'outline', color: p.inkMuted, label: 'absence not interpretable (no effort data)' });
      }
    } else if (layer.geometry_type === 'line') {
      // Transects/routes: stroked lines with a surface casing so they stay
      // legible over cell fills; width scales with the magnitude property.
      const values = fc.features.map((f) => magnitudeOf(f.properties || {}).value || 1);
      const vmax = Math.max(...values, 1);
      for (const f of fc.features) {
        const props = f.properties || {};
        const { key, value } = magnitudeOf(props);
        const coordsSets = f.geometry.type === 'MultiLineString'
          ? f.geometry.coordinates : [f.geometry.coordinates];
        const w = 1.5 + 2.5 * Math.sqrt((value || 1) / vmax);
        for (const coords of coordsSets) {
          const d = coords.map(([lon, lat], i) => `${i ? 'L' : 'M'} ${px(lon).toFixed(1)} ${py(lat).toFixed(1)}`).join(' ');
          g.appendChild(el('path', {
            d, fill: 'none', stroke: p.surface,
            'stroke-width': (w + 2.5).toFixed(1), 'stroke-linecap': 'round', 'stroke-linejoin': 'round',
          }));
          const line = el('path', {
            d, fill: 'none', stroke: color, 'stroke-width': w.toFixed(1),
            'stroke-linecap': 'round', 'stroke-linejoin': 'round',
            tabindex: '0', role: 'button',
          });
          attachHover(line, hooks, () => tooltipRows(layer, props, key, value));
          attachDrill(line, hooks, f, layer);
          g.appendChild(line);
        }
      }
      legendEntries.push({ swatch: 'line', color, label: layer.legend?.label || evidenceLabel(cls) });
    } else if (layer.geometry_type === 'point') {
      // Aggregate coincident points (same coordinate) into one mark so repeat
      // records at a single place read as weight, not as a hidden stack.
      const groups = new Map();
      for (const f of fc.features) {
        const [lon, lat] = f.geometry.coordinates;
        const k = `${lon.toFixed(5)},${lat.toFixed(5)}`;
        if (!groups.has(k)) groups.set(k, []);
        groups.get(k).push(f);
      }
      const merged = [...groups.values()].map((fs) => {
        if (fs.length === 1) return fs[0];
        const total = fs.reduce((s, f) => s + (magnitudeOf(f.properties || {}).value || 1), 0);
        const dates = fs.map((f) => (f.properties || {}).event_date).filter(Boolean).sort();
        const first = fs[0];
        return {
          ...first,
          properties: {
            ...first.properties,
            count: total,
            records: fs.length,
            event_date: dates.length ? `${dates[0]} – ${dates[dates.length - 1]}` : undefined,
          },
          _members: fs,
        };
      });
      const counts = merged.map((f) => magnitudeOf(f.properties || {}).value || 1);
      const maxCount = Math.max(...counts, 1);
      for (const f of merged) {
        const props = f.properties || {};
        const [lon, lat] = f.geometry.coordinates;
        const { key, value } = magnitudeOf(props);
        const dense = merged.length > 15;
        const r = (dense ? 3.5 : 5) + (dense ? 6 : 9) * Math.sqrt((value || 1) / maxCount);
        const x = px(lon), y = py(lat);
        let mark;
        if (cls === 'designed') {
          // Proposed points: diamonds — shape is the mandatory secondary encoding.
          mark = el('path', {
            d: `M ${x} ${y - r} L ${x + r} ${y} L ${x} ${y + r} L ${x - r} ${y} Z`,
            fill: color, stroke: p.surface, 'stroke-width': 2,
          });
        } else {
          mark = el('circle', {
            cx: x, cy: y, r,
            fill: color, 'fill-opacity': cls === 'modelled' ? 0.55 : 0.9,
            stroke: p.surface, 'stroke-width': 2,
          });
        }
        // Uncertainty halo when declared.
        const unc = props.coordinate_uncertainty_m;
        if (Number.isFinite(unc) && unc > 0) {
          const uncPx = (unc / 1000) / kmPerPx;
          if (uncPx > r + 2 && uncPx < Math.min(width, height) / 4) {
            g.appendChild(el('circle', {
              cx: x, cy: y, r: uncPx, fill: 'none',
              stroke: color, 'stroke-width': 1, 'stroke-dasharray': '3 3', opacity: 0.5,
            }));
          }
        }
        // Oversized transparent hit target (≥24px) so hover is reliable.
        const hit = el('circle', {
          cx: x, cy: y, r: Math.max(r + 6, 14), fill: 'transparent',
          tabindex: '0', role: 'button', class: 'viz-hit',
        });
        attachHover(hit, hooks, () => tooltipRows(layer, props, key, value), mark);
        attachDrill(hit, hooks, f, layer);
        g.appendChild(mark);
        g.appendChild(hit);
      }
      legendEntries.push({
        swatch: cls === 'designed' ? 'diamond' : 'dot', color,
        label: layer.legend?.label || evidenceLabel(cls),
      });
    }
  }

  // ---- annotations: leader-line labels anchored to coordinates (NYT device)
  for (const ann of visual.annotations || []) {
    const a = ann.anchor || {};
    if (a.kind !== 'point' || !Number.isFinite(a.lon) || !Number.isFinite(a.lat)) continue;
    const ax = px(a.lon), ay = py(a.lat);
    const up = ay > height / 2;
    const tx = Math.min(width - 150, ax + 26);
    const ty = up ? ay - 28 : ay + 32;
    const ag = el('g', { class: 'viz-map-annotation' });
    ag.appendChild(el('line', {
      x1: ax, y1: ay, x2: tx - 4, y2: ty - 4,
      stroke: p.inkSecondary, 'stroke-width': 1,
    }));
    ag.appendChild(el('circle', { cx: ax, cy: ay, r: 3, fill: p.inkSecondary }));
    const label = el('text', {
      x: tx, y: ty,
      class: `viz-ann-label${ann.emphasis === 'primary' ? ' viz-ann-primary' : ''}`,
    });
    label.textContent = ann.text || '';
    ag.appendChild(label);
    world.appendChild(ag);
  }

  // ---- scale bar
  const targetPx = width / 5;
  const niceKm = [0.25, 0.5, 1, 2, 5, 10, 20, 50, 100].find((k) => k / kmPerPx >= targetPx * 0.6) || 100;
  const barPx = niceKm / kmPerPx;
  const sb = el('g', { class: 'viz-map-scalebar' });
  const sbx = width - barPx - 20, sby = height - 18;
  sb.appendChild(el('line', { x1: sbx, y1: sby, x2: sbx + barPx, y2: sby, stroke: p.inkSecondary, 'stroke-width': 2 }));
  sb.appendChild(el('line', { x1: sbx, y1: sby - 4, x2: sbx, y2: sby + 4, stroke: p.inkSecondary, 'stroke-width': 2 }));
  sb.appendChild(el('line', { x1: sbx + barPx, y1: sby - 4, x2: sbx + barPx, y2: sby + 4, stroke: p.inkSecondary, 'stroke-width': 2 }));
  const sbt = el('text', { x: sbx + barPx / 2, y: sby - 7, 'text-anchor': 'middle', class: 'viz-map-scale-label' });
  sbt.textContent = niceKm < 1 ? `${niceKm * 1000} m` : `${niceKm} km`;
  sb.appendChild(sbt);
  svg.appendChild(sb);

  // ---- zoom & pan on the world group
  installZoom(svg, world, width, height);

  // ---- legend (HTML, not SVG, for wrapping)
  const legend = document.createElement('div');
  legend.className = 'viz-map-legend';
  for (const e of legendEntries) {
    const item = document.createElement('span');
    item.className = 'viz-legend-item';
    if (e.swatch === 'ramp') {
      const bar = document.createElement('span');
      bar.className = 'viz-legend-ramp' + (e.hatched ? ' viz-legend-ramp-modelled' : '');
      bar.style.background = `linear-gradient(90deg, ${e.ramp.join(',')})`;
      item.appendChild(bar);
      const lab = document.createElement('span');
      lab.textContent = `${e.label} (${formatNumber(e.min)}–${formatNumber(e.max)})`;
      item.appendChild(lab);
    } else {
      const sw = document.createElement('span');
      sw.className = `viz-legend-swatch viz-legend-${e.swatch}`;
      sw.style.setProperty('--sw', e.color);
      item.appendChild(sw);
      const lab = document.createElement('span');
      lab.textContent = e.label;
      item.appendChild(lab);
    }
    legend.appendChild(item);
  }
  root.appendChild(legend);
  return root;
}

function pathFor(geometry, px, py) {
  const ring = (coords) => coords.map(([lon, lat], i) => `${i ? 'L' : 'M'} ${px(lon).toFixed(1)} ${py(lat).toFixed(1)}`).join(' ') + ' Z';
  if (geometry.type === 'Polygon') return geometry.coordinates.map(ring).join(' ');
  if (geometry.type === 'MultiPolygon') return geometry.coordinates.map((poly) => poly.map(ring).join(' ')).join(' ');
  return '';
}

function tooltipRows(layer, props, magnitudeKey, magnitudeValue) {
  const rows = [];
  if (magnitudeKey !== null) {
    rows.push({ label: magnitudeKey.replace(/_/g, ' '), value: formatNumber(magnitudeValue), strong: true });
  }
  for (const k of ['label', 'event_date', 'source_id', 'source_row', 'records', 'unit', 'scope_role', 'role', 'uncertainty']) {
    if (props[k] !== undefined && props[k] !== null && k !== magnitudeKey) {
      rows.push({ label: k.replace(/_/g, ' '), value: String(props[k]) });
    }
  }
  rows.push({ label: 'evidence', value: evidenceLabel(layer.evidence_class), cls: layer.evidence_class });
  return rows;
}

function attachHover(node, hooks, rowsFn, liftTarget) {
  const enter = (ev) => {
    if (liftTarget) liftTarget.setAttribute('filter', 'brightness(1.12)');
    else node.setAttribute('filter', 'brightness(1.12)');
    hooks.tooltip.show(ev, rowsFn());
  };
  const move = (ev) => hooks.tooltip.move(ev);
  const leave = () => {
    if (liftTarget) liftTarget.removeAttribute('filter');
    else node.removeAttribute('filter');
    hooks.tooltip.hide();
  };
  node.addEventListener('pointerenter', enter);
  node.addEventListener('pointermove', move);
  node.addEventListener('pointerleave', leave);
  node.addEventListener('focus', (ev) => hooks.tooltip.show(ev, rowsFn()));
  node.addEventListener('blur', leave);
}

function centroidOf(geometry) {
  // Mean of the outer ring / the point itself — enough to name a mark by location.
  if (!geometry) return null;
  if (geometry.type === 'Point') {
    return { lon: geometry.coordinates[0], lat: geometry.coordinates[1] };
  }
  const ring = geometry.type === 'Polygon' ? geometry.coordinates[0]
    : geometry.type === 'MultiPolygon' ? geometry.coordinates[0][0] : null;
  if (!ring || !ring.length) return null;
  let lon = 0, lat = 0;
  for (const [x, y] of ring) { lon += x; lat += y; }
  return { lon: lon / ring.length, lat: lat / ring.length };
}

function attachDrill(node, hooks, feature, layer) {
  if (!hooks.onDrill) return;
  node.classList.add('viz-drillable');
  const fire = () => hooks.onDrill(feature, layer, centroidOf(feature.geometry));
  node.addEventListener('click', fire);
  node.addEventListener('keydown', (ev) => {
    if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); fire(); }
  });
}

function installZoom(svg, world, width, height) {
  let scale = 1, tx = 0, ty = 0;
  const apply = () => world.setAttribute('transform', `translate(${tx} ${ty}) scale(${scale})`);
  svg.addEventListener('wheel', (ev) => {
    ev.preventDefault();
    const factor = ev.deltaY < 0 ? 1.15 : 1 / 1.15;
    const ns = Math.min(12, Math.max(1, scale * factor));
    const rect = svg.getBoundingClientRect();
    const mx = ((ev.clientX - rect.left) / rect.width) * width;
    const my = ((ev.clientY - rect.top) / rect.height) * height;
    tx = mx - ((mx - tx) * ns) / scale;
    ty = my - ((my - ty) * ns) / scale;
    scale = ns;
    if (scale === 1) { tx = 0; ty = 0; }
    apply();
  }, { passive: false });
  let dragging = null;
  svg.addEventListener('pointerdown', (ev) => {
    if (scale === 1) return;
    dragging = { x: ev.clientX, y: ev.clientY, tx, ty };
    svg.setPointerCapture(ev.pointerId);
  });
  svg.addEventListener('pointermove', (ev) => {
    if (!dragging) return;
    const rect = svg.getBoundingClientRect();
    tx = dragging.tx + ((ev.clientX - dragging.x) / rect.width) * width;
    ty = dragging.ty + ((ev.clientY - dragging.y) / rect.height) * height;
    apply();
  });
  svg.addEventListener('pointerup', () => { dragging = null; });
  svg.addEventListener('dblclick', () => { scale = 1; tx = 0; ty = 0; apply(); });
}
