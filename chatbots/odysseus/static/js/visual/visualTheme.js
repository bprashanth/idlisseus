// visualTheme.js — evidence-class design system for the visual stage.
// The palette is validated (dataviz six-checks) — do not eyeball-edit hex values.
// Free-mixing hue classes are capped at three (observed/derived/modelled);
// designed and proxy ALWAYS carry shape/dash secondary encoding.

export const EVIDENCE_CLASSES = [
  'observed', 'reported', 'derived', 'proxy', 'modelled', 'designed', 'model_memory', 'missing',
];

// Validated all-pairs in both modes: observed/derived/modelled (blue/aqua/orange).
const LIGHT = {
  observed: '#2a78d6',
  derived: '#1baf7a',
  modelled: '#eb6834',
  designed: '#e87ba4',   // diamond markers only — never area fill without shape
  proxy: '#eda100',      // dashed outline only
  reported: '#52514e',   // outline/neutral, not a series hue
  model_memory: '#898781',
  missing: '#898781',
  surface: '#fcfcfb',
  page: '#f9f9f7',
  inkPrimary: '#0b0b0b',
  inkSecondary: '#52514e',
  inkMuted: '#898781',
  grid: '#e1e0d9',
  baseline: '#c3c2b7',
  ring: 'rgba(11,11,11,0.10)',
};

const DARK = {
  observed: '#3987e5',
  derived: '#199e70',
  modelled: '#d95926',
  designed: '#d55181',
  proxy: '#c98500',
  reported: '#c3c2b7',
  model_memory: '#898781',
  missing: '#898781',
  surface: '#1a1a19',
  page: '#0d0d0d',
  inkPrimary: '#ffffff',
  inkSecondary: '#c3c2b7',
  inkMuted: '#898781',
  grid: '#2c2c2a',
  baseline: '#383835',
  ring: 'rgba(255,255,255,0.10)',
};

// Sequential ramps (from the validated reference palette). Primary magnitude = blue;
// a second concurrent magnitude context (e.g. effort beside coverage) = orange.
export const RAMP_BLUE = ['#cde2fb', '#9ec5f4', '#6da7ec', '#3987e5', '#256abf', '#184f95', '#0d366b'];
export const RAMP_ORANGE = ['#fde3d3', '#f8c4a4', '#f2a578', '#eb6834', '#d95926', '#b0431a', '#8a3212'];

export function isDarkMode() {
  // Trust the app's light class when present; otherwise infer from the actual
  // theme background so light themes never get dark chart surfaces.
  if (document.documentElement.classList.contains('light')) return false;
  const bg = getComputedStyle(document.documentElement).getPropertyValue('--bg').trim();
  const m = /^#([0-9a-f]{6})$/i.exec(bg);
  if (m) {
    const n = parseInt(m[1], 16);
    const lum = 0.2126 * ((n >> 16) & 255) + 0.7152 * ((n >> 8) & 255) + 0.0722 * (n & 255);
    return lum < 128;
  }
  return true;
}

export function palette() {
  return isDarkMode() ? DARK : LIGHT;
}

export function evidenceColor(cls) {
  const p = palette();
  return p[cls] || p.inkMuted;
}

// Human labels for evidence classes — generic, never sector vocabulary.
export const EVIDENCE_LABELS = {
  observed: 'Observed',
  reported: 'Reported',
  derived: 'Derived',
  proxy: 'Proxy',
  modelled: 'Modelled',
  designed: 'Proposed',
  model_memory: 'Model lead',
  missing: 'No data',
};

export function evidenceLabel(cls) {
  return EVIDENCE_LABELS[cls] || cls;
}

// Quantile thresholds for a choropleth: returns {steps, colorFor(value)}.
export function quantileRamp(values, ramp, bins) {
  const sorted = values.filter((v) => Number.isFinite(v)).sort((a, b) => a - b);
  const n = Math.min(bins || 5, ramp.length);
  if (!sorted.length) return { steps: [], colorFor: () => ramp[0] };
  const steps = [];
  for (let i = 1; i < n; i++) {
    steps.push(sorted[Math.min(sorted.length - 1, Math.floor((sorted.length * i) / n))]);
  }
  // Use the mid-to-dark portion of the ramp so the lightest bin still reads on the surface.
  const offset = ramp.length - n;
  const colors = ramp.slice(offset < 0 ? 0 : Math.floor(offset / 2)).slice(0, n);
  const colorFor = (v) => {
    if (!Number.isFinite(v)) return null;
    let i = 0;
    while (i < steps.length && v > steps[i]) i++;
    return colors[Math.min(i, colors.length - 1)];
  };
  return { steps, colors, colorFor, min: sorted[0], max: sorted[sorted.length - 1] };
}

// Pick white or ink for text sitting inside a colored fill, by luminance.
export function inkOn(hex) {
  const c = hex.replace('#', '');
  const r = parseInt(c.slice(0, 2), 16) / 255;
  const g = parseInt(c.slice(2, 4), 16) / 255;
  const b = parseInt(c.slice(4, 6), 16) / 255;
  const lum = 0.2126 * r + 0.7152 * g + 0.0722 * b;
  return lum > 0.55 ? '#0b0b0b' : '#ffffff';
}

let _hatchCounter = 0;
// Returns a <pattern> element (45° hatch) for "missing"/texture use; caller appends to <defs>.
export function hatchPattern(svgNS, color) {
  const id = `viz-hatch-${++_hatchCounter}`;
  const pattern = document.createElementNS(svgNS, 'pattern');
  pattern.setAttribute('id', id);
  pattern.setAttribute('width', '6');
  pattern.setAttribute('height', '6');
  pattern.setAttribute('patternUnits', 'userSpaceOnUse');
  pattern.setAttribute('patternTransform', 'rotate(45)');
  const line = document.createElementNS(svgNS, 'line');
  line.setAttribute('x1', '0');
  line.setAttribute('y1', '0');
  line.setAttribute('x2', '0');
  line.setAttribute('y2', '6');
  line.setAttribute('stroke', color);
  line.setAttribute('stroke-width', '1.2');
  line.setAttribute('opacity', '0.55');
  pattern.appendChild(line);
  return { id, pattern };
}

// Stipple pattern (model-agreement "robust" texture, IPCC convention).
export function stipplePattern(svgNS, color) {
  const id = `viz-stipple-${++_hatchCounter}`;
  const pattern = document.createElementNS(svgNS, 'pattern');
  pattern.setAttribute('id', id);
  pattern.setAttribute('width', '7');
  pattern.setAttribute('height', '7');
  pattern.setAttribute('patternUnits', 'userSpaceOnUse');
  const dot = document.createElementNS(svgNS, 'circle');
  dot.setAttribute('cx', '3.5');
  dot.setAttribute('cy', '3.5');
  dot.setAttribute('r', '1');
  dot.setAttribute('fill', color);
  dot.setAttribute('opacity', '0.6');
  pattern.appendChild(dot);
  return { id, pattern };
}

export function formatNumber(v) {
  if (v === null || v === undefined || Number.isNaN(v)) return '—';
  const abs = Math.abs(v);
  if (abs >= 1e6) return (v / 1e6).toFixed(1).replace(/\.0$/, '') + 'M';
  if (abs >= 1e4) return (v / 1e3).toFixed(1).replace(/\.0$/, '') + 'K';
  if (Number.isInteger(v)) return v.toLocaleString('en-US');
  return v.toLocaleString('en-US', { maximumFractionDigits: 2 });
}
