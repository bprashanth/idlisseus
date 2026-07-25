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

const BASES = {
  terrain: { label: 'Terrain', attrib: '© OpenStreetMap contributors · © OpenTopoMap (CC-BY-SA)', maxZoom: 15 },
  imagery: { label: 'Imagery', attrib: '© Esri — Source: Esri, Maxar, Earthstar Geographics', maxZoom: 15 },
  osm: { label: 'Streets', attrib: '© OpenStreetMap contributors', maxZoom: 15 },
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

function featureRows(layer, props) {
  const { key, value } = magnitudeOf(props || {});
  const rows = [];
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

  const savedBase = localStorage.getItem('viz-basemap-leaflet') || 'terrain';
  const baseLayers = {};
  for (const [id, cfg] of Object.entries(BASES)) {
    baseLayers[cfg.label] = L.tileLayer(`/api/visual/tiles/${id}/{z}/{x}/{y}.png`, {
      attribution: cfg.attrib, maxNativeZoom: cfg.maxZoom, maxZoom: 17,
    });
  }
  const initial = BASES[savedBase] ? BASES[savedBase].label : 'Terrain';
  baseLayers[initial].addTo(map);
  map.on('baselayerchange', (ev) => {
    const id = Object.entries(BASES).find(([, c]) => c.label === ev.name)?.[0];
    if (id) localStorage.setItem('viz-basemap-leaflet', id);
  });

  const bounds = L.latLngBounds([]);
  const overlays = {};
  const ramps = { used: 0 };

  const ordered = [...(visual.layers || [])].sort((a, b) => {
    const rank = { raster_image: -1, polygon: 0, raster: 1, cell: 1, line: 2, point: 3 };
    return (rank[a.geometry_type] ?? 1) - (rank[b.geometry_type] ?? 1);
  });

  for (const layer of ordered) {
    const cls = layer.evidence_class || 'observed';
    const color = evidenceColor(cls);
    const label = layer.legend?.label || evidenceLabel(cls);

    if (layer.geometry_type === 'raster_image' && Array.isArray(layer.bounds)) {
      const url = hooks.rawUrl && hooks.rawUrl(layer.data_ref);
      if (!url) continue;
      const [w, s, e, n] = layer.bounds;
      const img = L.imageOverlay(url, [[s, w], [n, e]], {
        opacity: (layer.style_hint && layer.style_hint.opacity) || 0.75,
      }).addTo(map);
      overlays[label] = img;
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
          return {
            color: '#ffffff', weight: 1.2,
            fillColor: q.colorFor(v) || p.inkMuted,
            fillOpacity: cls === 'modelled' ? 0.45 : 0.62,
          };
        },
        onEachFeature: (f, lyr) => {
          lyr.bindTooltip(tooltipNode(featureRows(layer, f.properties)), { sticky: true, opacity: 0.96 });
          lyr.on('click', () => {
            if (!hooks.onDrill) return;
            const c = lyr.getBounds ? lyr.getBounds().getCenter() : null;
            hooks.onDrill(f, layer, c ? { lat: c.lat, lon: c.lng } : null);
          });
        },
      }).addTo(map);
      overlays[label] = gj;
      if (gj.getBounds().isValid()) bounds.extend(gj.getBounds());
    } else if (layer.geometry_type === 'point') {
      const counts = fc.features.map((f) => magnitudeOf(f.properties || {}).value || 1);
      const maxCount = Math.max(...counts, 1);
      const group = L.featureGroup();
      for (const f of fc.features) {
        const [lon, lat] = f.geometry.coordinates;
        const { value } = magnitudeOf(f.properties || {});
        const r = 4 + 8 * Math.sqrt((value || 1) / maxCount);
        const marker = L.circleMarker([lat, lon], {
          radius: r, color: '#ffffff', weight: 2,
          fillColor: color, fillOpacity: cls === 'modelled' ? 0.55 : 0.9,
        });
        marker.bindTooltip(tooltipNode(featureRows(layer, f.properties)), { sticky: true, opacity: 0.96 });
        marker.on('click', () => hooks.onDrill && hooks.onDrill(f, layer, { lat, lon }));
        group.addLayer(marker);
      }
      group.addTo(map);
      overlays[label] = group;
      if (group.getBounds().isValid()) bounds.extend(group.getBounds());
    } else if (layer.geometry_type === 'line') {
      const gj = L.geoJSON(fc, {
        style: { color, weight: 3, opacity: 0.9 },
        onEachFeature: (f, lyr) => {
          lyr.bindTooltip(tooltipNode(featureRows(layer, f.properties)), { sticky: true });
          lyr.on('click', () => hooks.onDrill && hooks.onDrill(f, layer, null));
        },
      }).addTo(map);
      overlays[label] = gj;
      if (gj.getBounds().isValid()) bounds.extend(gj.getBounds());
    }
  }

  L.control.layers(
    Object.fromEntries(Object.entries(BASES).map(([id, c]) => [c.label, baseLayers[c.label]])),
    overlays,
    { collapsed: true, position: 'topright' }
  ).addTo(map);

  const fit = () => {
    map.invalidateSize();
    if (bounds.isValid()) map.fitBounds(bounds.pad(0.06));
    else map.setView([0, 0], 2);
  };
  fit();
  // The panel mounts and transitions in; refit once layout has real dimensions.
  requestAnimationFrame(fit);
  setTimeout(fit, 380);
  return root;
}
