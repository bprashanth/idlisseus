// visualLeaflet.js — full interactive map renderer for the side panel.
// Same idli-result/1 layer model as the SVG figure map, drawn with vendored
// Leaflet over proxied basemap tiles (terrain by default — vegetation reads
// well; imagery/streets selectable). Evidence-class styling, tooltips and
// drill-through are preserved; nothing here knows sector vocabulary.

import {
  palette, evidenceColor, evidenceLabel, quantileRamp,
  RAMP_BLUE, RAMP_ORANGE, formatNumber,
} from './visualTheme.js';
import { magnitudeOf } from './visualMap.js';

// The basemaps this consumer can serve, all through the same-origin tile
// proxy. A producer/author declares one of these ids (IDL-REQ-0004).
const BASES = {
  imagery: { label: 'Imagery', attrib: '© Esri — Source: Esri, Maxar, Earthstar Geographics', maxZoom: 15 },
  osm: { label: 'Streets', attrib: '© OpenStreetMap contributors', maxZoom: 15 },
  terrain: { label: 'Terrain', attrib: '© OpenStreetMap contributors · © OpenTopoMap (CC-BY-SA)', maxZoom: 15 },
};

function tooltipNode(rows) {
  const box = document.createElement('div');
  box.className = 'viz-ltooltip';
  for (const r of rows) {
    const line = document.createElement('div');
    const val = document.createElement('strong');
    val.textContent = r.value;
    const lab = document.createElement('span');
    lab.textContent = ` ${r.label}`;
    line.appendChild(val);
    line.appendChild(lab);
    box.appendChild(line);
  }
  return box;
}

function featureRows(layer, props, note) {
  const { key, value } = magnitudeOf(props || {});
  const rows = [];
  // TR-VIS-0009: the treatment is verbal as well as visual — a dashed ring
  // means nothing to a screen reader, and little in a hurry.
  if (note) rows.push({ label: note, value: '' });
  if (key !== null) rows.push({ label: key.replace(/_/g, ' '), value: formatNumber(value) });
  for (const k of ['label', 'event_date', 'source_id', 'source_row', 'unit']) {
    if (props && props[k] !== undefined && props[k] !== null && k !== key) {
      rows.push({ label: k.replace(/_/g, ' '), value: String(props[k]) });
    }
  }
  rows.push({ label: evidenceLabel(layer.evidence_class), value: '' });
  return rows;
}

export function renderLeafletMap(container, visual, layerData, hooks) {
  const L = window.L;
  const p = palette();
  const root = document.createElement('div');
  root.className = 'viz-leaflet-root';
  container.appendChild(root);

  const map = L.map(root, { zoomSnap: 0.5, attributionControl: true });
  map.attributionControl.setPrefix(false);

  const baseLayers = {};
  for (const [id, cfg] of Object.entries(BASES)) {
    baseLayers[cfg.label] = L.tileLayer(`/api/visual/tiles/${id}/{z}/{x}/{y}.png`, {
      attribution: cfg.attrib, maxNativeZoom: cfg.maxZoom, maxZoom: 17,
    });
  }
  // IDL-REQ-0004: when the author who published this analysis declared a
  // basemap, their choice is part of the work and wins over the reader's
  // global preference — for this figure only, and without overwriting it. An
  // id this consumer does not know degrades to the default rather than
  // failing the render, and every tile still goes through the same-origin
  // proxy (the browser never calls a third-party host).
  const declared = hooks.basemap ? String(hooks.basemap).toLowerCase() : null;
  const savedBase = localStorage.getItem('viz-basemap-leaflet') || 'imagery';
  let initial = BASES[savedBase] ? BASES[savedBase].label : 'Imagery';
  let authored = false;
  if (declared && declared !== 'none') {
    if (BASES[declared]) { initial = BASES[declared].label; authored = true; }
  }
  if (declared !== 'none') baseLayers[initial].addTo(map);
  map.on('baselayerchange', (ev) => {
    const id = Object.entries(BASES).find(([, c]) => c.label === ev.name)?.[0];
    // Changing the base on an authored figure is a look, not a new preference.
    if (id && !authored) localStorage.setItem('viz-basemap-leaflet', id);
  });

  const bounds = L.latLngBounds([]);       // everything drawn
  const focusBounds = L.latLngBounds([]);  // non-context features
  const emphasisBounds = L.latLngBounds([]); // the layer the answer is about
  const overlays = {};
  // producer layer_id -> leaflet object (TR-VIS-0008 toggle bar)
  const layerObjects = {};
  // every drawn feature, for focusing one by a producer-declared id
  const featureIndex = [];

  // A feature is "context" when the producer says so (donor/comparison/context
  // roles). Those inform, but they must not dictate the viewport.
  const isContext = (f) => {
    const p = (f && f.properties) || {};
    const role = String(p.scope_role || p.role || '').toLowerCase();
    return role.includes('context') || role.includes('donor') || role.includes('comparison');
  };
  const extendFocus = (fc, layer) => {
    if (!fc || !fc.features) return;
    const emphasis = (layer.style_hint || {}).emphasis === 'primary';
    for (const f of fc.features) {
      if (emphasis) {
        const g0 = f.geometry;
        if (g0) {
          if (g0.type === 'Point') emphasisBounds.extend([g0.coordinates[1], g0.coordinates[0]]);
          else {
            const r0 = g0.type === 'Polygon' ? g0.coordinates[0]
              : g0.type === 'MultiPolygon' ? g0.coordinates[0][0] : null;
            for (const c of r0 || []) emphasisBounds.extend([c[1], c[0]]);
          }
        }
      }
      if (!emphasis && isContext(f)) continue;
      const g = f.geometry;
      if (!g) continue;
      if (g.type === 'Point') focusBounds.extend([g.coordinates[1], g.coordinates[0]]);
      else {
        const ring = g.type === 'Polygon' ? g.coordinates[0]
          : g.type === 'MultiPolygon' ? g.coordinates[0][0] : null;
        for (const c of ring || []) focusBounds.extend([c[1], c[0]]);
      }
    }
  };
  const ramps = { used: 0 };

  const ordered = [...(visual.layers || [])].sort((a, b) => {
    const rank = { raster_image: -1, polygon: 0, raster: 1, cell: 1, line: 2, point: 3 };
    return (rank[a.geometry_type] ?? 1) - (rank[b.geometry_type] ?? 1);
  });

  for (const layer of ordered) {
    const cls = layer.evidence_class || 'observed';
    const color = evidenceColor(cls);
    const label = layer.legend?.label || evidenceLabel(cls);
    // TR-VIS-0008 producer style roles: `validation` marks observations
    // withheld to test with (same evidence class as the ones used to fit, so
    // colour cannot separate them), `selected_field` names the property that
    // flags a location chosen inside the declared budget.
    const styleHint = layer.style_hint || {};
    const validationRole = styleHint.palette_role === 'validation';
    const selectedField = hooks.suppressSelection ? null : (styleHint.selected_field || null);
    // TR-VIS-0009: evidence requests, not recommendations — dashed, and never
    // suppressed by a failed test, because they are what would settle it.
    const priorityField = styleHint.validation_priority_field || null;

    if (layer.geometry_type === 'raster_image' && Array.isArray(layer.bounds)) {
      const url = hooks.rawUrl && hooks.rawUrl(layer.data_ref);
      if (!url) continue;
      const [w, s, e, n] = layer.bounds;
      const img = L.imageOverlay(url, [[s, w], [n, e]], {
        opacity: (layer.style_hint && layer.style_hint.opacity) || 0.75,
      }).addTo(map);
      overlays[label] = img;
      layerObjects[layer.layer_id] = img;
      bounds.extend([[s, w], [n, e]]);
      continue;
    }

    const fc = layerData.get(layer.layer_id);
    if (!fc || !fc.features || !fc.features.length) continue;

    if (['cell', 'raster', 'polygon'].includes(layer.geometry_type)) {
      const isBoundary = cls === 'reported' && layer.geometry_type === 'polygon';
      const values = fc.features.map((f) => magnitudeOf(f.properties || {}).value);
      const ramp = cls === 'modelled' ? RAMP_ORANGE : (ramps.used === 0 ? RAMP_BLUE : RAMP_ORANGE);
      if (!isBoundary && cls !== 'modelled' && cls !== 'missing') ramps.used += 1;
      const q = quantileRamp(values, ramp, 5);
      const gj = L.geoJSON(fc, {
        style: (f) => {
          if (isBoundary) {
            return { color, weight: 2, fillColor: color, fillOpacity: 0.03, dashArray: '' };
          }
          if (cls === 'missing') {
            return { color: p.inkMuted, weight: 1, dashArray: '4 3', fillColor: p.inkMuted, fillOpacity: 0.12 };
          }
          const v = magnitudeOf(f.properties || {}).value;
          // A place chosen inside the declared budget wears a heavy ink
          // collar — a mark, not a hue, so the budget survives greyscale and
          // reads over any ramp step. Only drawn behind a passed test.
          if (selectedField && (f.properties || {})[selectedField]) {
            return {
              color: p.inkPrimary, weight: 3.5, opacity: 1,
              fillColor: q.colorFor(v) || p.inkMuted,
              fillOpacity: cls === 'modelled' ? 0.62 : 0.72,
            };
          }
          if (priorityField && (f.properties || {})[priorityField]) {
            return {
              color: p.inkPrimary, weight: 2.4, opacity: 1, dashArray: '5 4',
              fillColor: q.colorFor(v) || p.inkMuted,
              fillOpacity: cls === 'modelled' ? 0.5 : 0.62,
            };
          }
          return {
            color: '#ffffff', weight: 1.2,
            fillColor: q.colorFor(v) || p.inkMuted,
            fillOpacity: cls === 'modelled' ? 0.45 : 0.62,
          };
        },
        onEachFeature: (f, lyr) => {
          const note = (selectedField && (f.properties || {})[selectedField])
            ? 'chosen within the declared budget'
            : ((priorityField && (f.properties || {})[priorityField])
              ? 'check or collect evidence here' : '');
          lyr.bindTooltip(tooltipNode(featureRows(layer, f.properties, note)),
            { sticky: true, opacity: 0.96 });
          lyr.on('click', () => {
            if (!hooks.onDrill) return;
            const c = lyr.getBounds ? lyr.getBounds().getCenter() : null;
            hooks.onDrill(f, layer, c ? { lat: c.lat, lon: c.lng } : null);
          });
          const c = lyr.getBounds ? lyr.getBounds().getCenter() : null;
          featureIndex.push({ props: f.properties || {}, marker: lyr,
            latlng: c ? [c.lat, c.lng] : null });
        },
      }).addTo(map);
      overlays[label] = gj;
      layerObjects[layer.layer_id] = gj;
      if (gj.getBounds().isValid()) bounds.extend(gj.getBounds());
      if (!isBoundary) extendFocus(fc, layer);
    } else if (layer.geometry_type === 'point') {
      const counts = fc.features.map((f) => magnitudeOf(f.properties || {}).value || 1);
      const maxCount = Math.max(...counts, 1);
      const group = L.featureGroup();
      for (const f of fc.features) {
        const [lon, lat] = f.geometry.coordinates;
        const { value } = magnitudeOf(f.properties || {});
        const r = 4 + 8 * Math.sqrt((value || 1) / maxCount);
        let marker;
        if (validationRole) {
          // Withheld test observations: a crossed ring. Shape is the mandatory
          // secondary encoding — these share an evidence class (and therefore a
          // hue) with the observations used to fit the model.
          const d = Math.ceil(r * 2 + 6);
          const c = d / 2;
          const rr = r;
          marker = L.marker([lat, lon], {
            icon: L.divIcon({
              className: 'viz-withheld-mark',
              iconSize: [d, d],
              iconAnchor: [c, c],
              html: `<svg width="${d}" height="${d}" viewBox="0 0 ${d} ${d}" aria-hidden="true">`
                + `<circle cx="${c}" cy="${c}" r="${rr}" fill="#ffffff" fill-opacity="0.5" `
                + `stroke="${color}" stroke-width="2.4"/>`
                + `<line x1="${c - rr * 0.72}" y1="${c + rr * 0.72}" x2="${c + rr * 0.72}" `
                + `y2="${c - rr * 0.72}" stroke="${color}" stroke-width="2.4" stroke-linecap="round"/>`
                + '</svg>',
            }),
          });
        } else if (priorityField && (f.properties || {})[priorityField]
                   && !(selectedField && (f.properties || {})[selectedField])) {
          // Dashed ring: come and look here, we do not yet know.
          marker = L.circleMarker([lat, lon], {
            radius: r + 1.5, color: p.inkPrimary, weight: 2, dashArray: '3 3',
            fillColor: color, fillOpacity: 0.75,
          });
        } else if (selectedField && (f.properties || {})[selectedField]) {
          // Chosen inside the declared budget: a heavy ink collar around the
          // mark — shape weight, not a different hue.
          marker = L.circleMarker([lat, lon], {
            radius: r, color: p.inkPrimary, weight: 3.5,
            fillColor: color, fillOpacity: cls === 'modelled' ? 0.75 : 0.95,
          });
        } else {
          marker = L.circleMarker([lat, lon], {
            radius: r, color: '#ffffff', weight: 2,
            fillColor: color, fillOpacity: cls === 'modelled' ? 0.55 : 0.9,
          });
        }
        const priority = !!(priorityField && (f.properties || {})[priorityField]);
        const selected = !!(selectedField && (f.properties || {})[selectedField]);
        const note = selected ? 'chosen within the declared budget'
          : (priority ? 'check or collect evidence here' : '');
        marker.bindTooltip(tooltipNode(featureRows(layer, f.properties, note)),
          { sticky: true, opacity: 0.96 });
        if (note) {
          const elm = marker.getElement && marker.getElement();
          if (elm) elm.setAttribute('aria-label', note);
        }
        marker.on('click', () => hooks.onDrill && hooks.onDrill(f, layer, { lat, lon }));
        group.addLayer(marker);
        // TR-VIS-0010: a published answer names places by producer id; keep an
        // index so the article can focus one without recomputing anything.
        featureIndex.push({ props: f.properties || {}, marker, latlng: [lat, lon] });
      }
      group.addTo(map);
      overlays[label] = group;
      layerObjects[layer.layer_id] = group;
      if (group.getBounds().isValid()) bounds.extend(group.getBounds());
      extendFocus(fc, layer);
    } else if (layer.geometry_type === 'line') {
      const gj = L.geoJSON(fc, {
        style: { color, weight: 3, opacity: 0.9 },
        onEachFeature: (f, lyr) => {
          lyr.bindTooltip(tooltipNode(featureRows(layer, f.properties)), { sticky: true });
          lyr.on('click', () => hooks.onDrill && hooks.onDrill(f, layer, null));
        },
      }).addTo(map);
      overlays[label] = gj;
      layerObjects[layer.layer_id] = gj;
      if (gj.getBounds().isValid()) bounds.extend(gj.getBounds());
    }
  }

  L.control.layers(
    Object.fromEntries(Object.entries(BASES).map(([id, c]) => [c.label, baseLayers[c.label]])),
    overlays,
    { collapsed: true, position: 'topright' }
  ).addTo(map);

  // TR-VIS-0008: expose the overlays by producer layer id so an out-of-map
  // toggle bar can show/hide the same objects this control drives. Toggling
  // adds or removes drawn marks only — no producer value is touched.
  root._vizLeafletLayers = layerObjects;
  root._vizLeafletMap = map;
  root._vizFeatures = featureIndex;

  // ---- ground truth: peek at the bare imagery.
  // Hold the button (or toggle it) to fade every data layer away, so the field
  // question "is that square really forest?" is answered without leaving the map.
  const peekWrap = document.createElement('div');
  peekWrap.className = 'viz-peek';
  const peekBtn = document.createElement('button');
  peekBtn.className = 'viz-peek-btn';
  peekBtn.type = 'button';
  peekBtn.textContent = 'Hold to see imagery';
  peekBtn.title = 'Hold to hide the records; click to keep them hidden';
  peekWrap.appendChild(peekBtn);
  const peekTag = document.createElement('span');
  peekTag.className = 'viz-peek-tag';
  peekTag.textContent = 'imagery only';
  peekTag.hidden = true;
  peekWrap.appendChild(peekTag);
  root.appendChild(peekWrap);

  const dataPanes = () => [
    root.querySelector('.leaflet-overlay-pane'),
    root.querySelector('.leaflet-marker-pane'),
    root.querySelector('.leaflet-shadow-pane'),
  ].filter(Boolean);
  let peeking = false;
  const setPeek = (on) => {
    peeking = on;
    for (const pane of dataPanes()) {
      pane.style.transition = 'opacity 0.18s';
      pane.style.opacity = on ? '0' : '';
    }
    peekTag.hidden = !on;
    peekBtn.classList.toggle('on', on);
  };
  peekBtn.addEventListener('pointerdown', (ev) => { ev.preventDefault(); setPeek(true); });
  peekBtn.addEventListener('pointerup', () => setPeek(false));
  peekBtn.addEventListener('pointerleave', () => { if (peeking) setPeek(false); });
  peekBtn.addEventListener('keydown', (ev) => {
    if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); setPeek(!peeking); }
  });

  const fit = () => {
    map.invalidateSize();
    const target = emphasisBounds.isValid() ? emphasisBounds
      : (focusBounds.isValid() ? focusBounds : bounds);
    if (target.isValid()) map.fitBounds(target.pad(0.12), { maxZoom: 14 });
    else map.setView([0, 0], 2);
  };
  fit();
  // The panel mounts, animates in, and tiles arrive asynchronously; refit until
  // the container has settled at its real size.
  requestAnimationFrame(fit);
  setTimeout(fit, 380);
  setTimeout(fit, 1200);
  if (typeof ResizeObserver === 'function') {
    let settled = 0;
    const ro = new ResizeObserver(() => {
      fit();
      if (++settled > 6) ro.disconnect();
    });
    ro.observe(root);
    setTimeout(() => ro.disconnect(), 4000);
  }
  return root;
}
