// visualDecisionMap.js — TR-VIS-0008: validated decision maps.
//
// A decision map is not "a map that happens to exist": it supports a bounded
// choice, and the producer declares how it was tested. This module owns the
// consumer treatment of that contract:
//
//   * "How this map was tested" is rendered beside the map itself — never
//     behind an audit log or a details accordion;
//   * observations used to fit, observations withheld to test, modelled
//     values and selected budget locations stay distinguishable without
//     colour (each carries its own mark and its own legend line);
//   * a failed test keeps its evidence and loses its recommendation — no
//     place is styled as selected when the test did not pass;
//   * layer toggles hide marks only. They never recompute anything, never
//     change a producer value, and never hide the validation state.
//
// Everything here reads producer fields (layer ids, evidence classes, legend
// labels, style hints, declared thresholds). No scientific semantics are
// inferred from field names, and nothing dispatches on a particular subject,
// place, intervention or recipe id.

const DECISION_VIEW = 'validated-decision-map';
const VALIDATION_VIEW = 'validation-summary';

export function isDecisionMapVisual(visual) {
  return !!visual && visual.view === DECISION_VIEW;
}

export function decisionMapVisuals(envelope) {
  const visuals = (envelope && envelope.visuals) || [];
  return {
    map: visuals.find((v) => v.view === DECISION_VIEW) || null,
    validation: visuals.find((v) => v.view === VALIDATION_VIEW) || null,
  };
}

// The producer's own verdict. Absent (an ordinary map) → null, and every
// treatment below is skipped.
export function validationOf(envelope) {
  return ((envelope || {}).answer || {}).validation || null;
}

export function validationPassed(envelope) {
  const v = validationOf(envelope);
  return !!v && v.status === 'passed';
}

// A recommendation exists only behind a passed test. Anything else — failed,
// pending, runtime, unknown — must not be drawn as chosen.
export function selectionAllowed(envelope) {
  const v = validationOf(envelope);
  return !!v && v.status === 'passed';
}

// ---- plain language ---------------------------------------------------------

const KIND_WORDS = {
  'temporal-hindcast': 'Tested on later records held back from fitting',
  'spatial-holdout': 'Tested on whole places held back from fitting',
  'field-ground-truth': 'Tested against independently positioned field measurements',
  'observation-only': 'Measured evidence only — no predictive claim',
  pending: 'Not yet testable with this pack',
};

const STATUS_WORDS = {
  passed: 'Test passed',
  failed: 'Test failed',
  pending: 'Test pending',
  runtime: 'Tested at run time',
  'not-applicable': 'No test applies',
};

// Threshold operators as words, so a reader never has to parse ">=".
const OPERATOR_WORDS = { '>=': 'at least', '<=': 'at most', '>': 'above', '<': 'below', '==': 'exactly' };

export function validationKindLabel(kind) {
  return KIND_WORDS[kind] || String(kind || '').replace(/[-_]/g, ' ');
}

export function validationStatusLabel(status) {
  return STATUS_WORDS[status] || String(status || '').replace(/[-_]/g, ' ');
}

// Producer metric keys are machine words; show them as reading words. Unknown
// keys degrade to their own text rather than being dropped or guessed at.
const METRIC_WORDS = {
  auc: 'ranking skill (AUC)',
  top_20_percent_capture: 'share of withheld records in the top-ranked fifth',
  top_20_percent_cells: 'cells in the top-ranked fifth',
  training_events: 'records used to fit',
  validation_events: 'records withheld to test',
  plots: 'plots used',
  landscapes: 'landscapes used',
  mae_improvement_over_baseline: 'error improvement over the baseline',
  minimum_training_events: 'records used to fit',
  minimum_validation_events: 'records withheld to test',
  minimum_auc: 'ranking skill (AUC)',
  minimum_top_20_percent_capture: 'share of withheld records in the top-ranked fifth',
  minimum_plots: 'plots used',
  minimum_landscapes: 'landscapes used',
  minimum_mae_improvement_over_baseline: 'error improvement over the baseline',
};

function metricLabel(key) {
  return METRIC_WORDS[key] || String(key).replace(/_/g, ' ');
}

// Producer values arrive as raw numbers. Fractions read as percentages; other
// numbers keep enough precision to be checked against their threshold.
function formatValue(key, value) {
  if (typeof value !== 'number' || !Number.isFinite(value)) return String(value ?? '');
  const k = String(key);
  if (/capture|improvement|fraction|share|rate/.test(k) && value <= 1) {
    return `${(value * 100).toFixed(0)}%`;
  }
  if (Number.isInteger(value)) return value.toLocaleString('en-IN');
  return value.toFixed(3);
}

function dateRange(period) {
  if (!period || typeof period !== 'object') return '';
  const a = period.start || '';
  const b = period.end || '';
  if (a && b) return `${a} to ${b}`;
  return a || b || '';
}

// ---- "How this map was tested" ---------------------------------------------

/**
 * Render the validation panel. `envelope.answer.validation` is the authority;
 * the validation-summary visual supplies the producer's own title, headline
 * and denominators when present.
 *
 * Returns the panel element, or null when the envelope declares no validation
 * (an ordinary map renders exactly as it did before this proposal).
 */
export function renderValidationPanel(container, envelope, opts) {
  const v = validationOf(envelope);
  if (!v) return null;
  const { validation: vis } = decisionMapVisuals(envelope);

  const panel = document.createElement('section');
  panel.className = 'viz-validation';
  panel.dataset.status = v.status || 'unknown';

  const head = document.createElement('div');
  head.className = 'viz-validation-head';
  const title = document.createElement('h4');
  title.className = 'viz-validation-title';
  // The producer titles this visual; the proposal's wording is the fallback.
  title.textContent = (vis && vis.title) || 'How this map was tested';
  head.appendChild(title);
  const pill = document.createElement('span');
  pill.className = `viz-validation-pill viz-validation-${v.status || 'unknown'}`;
  pill.textContent = validationStatusLabel(v.status);
  head.appendChild(pill);
  panel.appendChild(head);

  const kind = document.createElement('p');
  kind.className = 'viz-validation-kind';
  kind.textContent = validationKindLabel(v.kind);
  panel.appendChild(kind);

  // The split rule in the producer's own words, plus the periods or groups it
  // separated — the reader must be able to see what was held back.
  const splitBits = [];
  if (v.split_rule) splitBits.push(String(v.split_rule));
  const fit = dateRange(v.training_period);
  const test = dateRange(v.validation_period);
  if (fit) splitBits.push(`fitted on ${fit}`);
  if (test) splitBits.push(`tested on ${test}`);
  if (v.holdout_rule) splitBits.push(String(v.holdout_rule));
  if (v.holdout_groups) splitBits.push(`${v.holdout_groups} groups withheld`);
  if (splitBits.length) {
    const split = document.createElement('p');
    split.className = 'viz-validation-split';
    split.textContent = splitBits.join(' · ');
    panel.appendChild(split);
  }

  // Checks: value against declared threshold, pass state carried by a word and
  // a mark, never by colour alone.
  const checks = v.checks && typeof v.checks === 'object' ? Object.entries(v.checks) : [];
  if (checks.length) {
    const table = document.createElement('table');
    table.className = 'viz-validation-checks';
    const tb = document.createElement('tbody');
    for (const [key, c] of checks) {
      const tr = document.createElement('tr');
      tr.className = c && c.passed ? 'is-pass' : 'is-fail';
      const name = document.createElement('th');
      name.scope = 'row';
      name.textContent = metricLabel(key);
      tr.appendChild(name);
      const val = document.createElement('td');
      val.className = 'viz-validation-value';
      val.textContent = formatValue(key, c && c.value);
      tr.appendChild(val);
      const need = document.createElement('td');
      need.className = 'viz-validation-need';
      const op = OPERATOR_WORDS[(c && c.operator) || '>='] || (c && c.operator) || '';
      need.textContent = c && c.threshold !== undefined
        ? `needs ${op} ${formatValue(key, c.threshold)}` : '';
      tr.appendChild(need);
      const mark = document.createElement('td');
      mark.className = 'viz-validation-mark';
      // Shape + word: "✓ met" / "✗ not met" survives greyscale and screen readers.
      mark.textContent = c && c.passed ? '✓ met' : '✗ not met';
      tr.appendChild(mark);
      tb.appendChild(tr);
    }
    table.appendChild(tb);
    panel.appendChild(table);
  }

  // Sample sizes the producer counted for this run.
  const denoms = (vis && vis.summary && vis.summary.denominators) || {};
  const sizeBits = Object.entries(denoms).map(([k, n]) => `${formatValue(k, n)} ${metricLabel(k)}`);
  if (!sizeBits.length && v.metrics) {
    for (const k of ['training_events', 'validation_events', 'plots', 'landscapes']) {
      if (typeof v.metrics[k] === 'number') sizeBits.push(`${formatValue(k, v.metrics[k])} ${metricLabel(k)}`);
    }
  }
  if (sizeBits.length) {
    const sizes = document.createElement('p');
    sizes.className = 'viz-validation-sizes';
    sizes.textContent = sizeBits.join(' · ');
    panel.appendChild(sizes);
  }

  // The bounded claim: what may be said now that the test has passed — or, on
  // a failure, what the producer says instead. Never reworded by the consumer.
  const claim = v.claim || (vis && vis.summary && vis.summary.headline) || '';
  if (claim) {
    const c = document.createElement('p');
    c.className = 'viz-validation-claim';
    c.textContent = claim;
    panel.appendChild(c);
  }

  // A failed test is a product, not an error: say plainly that nothing is
  // recommended, in the same visual field as the map.
  if (v.status === 'failed') {
    const warn = document.createElement('p');
    warn.className = 'viz-validation-failnote';
    warn.textContent = 'The test did not pass, so no place is marked for action here. '
      + 'The recorded evidence and the checks that failed are shown above.';
    panel.appendChild(warn);
  }

  // Limitations that the producer attached to the validation itself.
  const lims = ((envelope || {}).limitations || [])
    .filter((l) => l && Array.isArray(l.affects) && l.affects.includes('validation-summary'))
    .map((l) => l.message)
    .filter(Boolean);
  if (lims.length) {
    const ul = document.createElement('ul');
    ul.className = 'viz-validation-limits';
    for (const m of lims.slice(0, 4)) {
      const li = document.createElement('li');
      li.textContent = m;
      ul.appendChild(li);
    }
    panel.appendChild(ul);
  }

  if (opts && opts.compact) panel.classList.add('viz-validation-compact');
  container.appendChild(panel);
  return panel;
}

// ---- layer toggles ----------------------------------------------------------

// Toggle rows read from the producer's own layers: legend label, evidence
// class and style role. Hiding a layer sets a class on the figure; the map
// keeps every value it computed.
export function renderLayerToggles(container, visual, frame, opts) {
  const layers = (visual && visual.layers) || [];
  if (layers.length < 2) return null;
  const suppressed = (opts && opts.suppressedLayers) || new Set();

  const bar = document.createElement('div');
  bar.className = 'viz-layer-toggles';
  const caption = document.createElement('span');
  caption.className = 'viz-layer-toggles-cap';
  caption.textContent = 'Show';
  bar.appendChild(caption);

  for (const layer of layers) {
    const id = layer.layer_id;
    if (!id) continue;
    const label = document.createElement('label');
    label.className = 'viz-layer-toggle';
    const box = document.createElement('input');
    box.type = 'checkbox';
    box.checked = !suppressed.has(id);
    box.addEventListener('change', () => {
      frame.classList.toggle(`viz-hide-${cssSafe(id)}`, !box.checked);
      // SVG figure map: the layer is one <g data-layer="…">.
      const g = frame.querySelector(`[data-layer="${cssEscape(id)}"]`);
      if (g) g.style.display = box.checked ? '' : 'none';
      // Leaflet panel map: add/remove the registered overlay object. Either
      // way this only shows or hides drawn marks — nothing recomputes and no
      // producer value changes.
      const root = frame.querySelector('.viz-leaflet-root') || frame;
      const objs = root._vizLeafletLayers;
      const map = root._vizLeafletMap;
      if (objs && map && objs[id]) {
        if (box.checked) objs[id].addTo(map);
        else map.removeLayer(objs[id]);
      }
    });
    label.appendChild(box);
    const text = document.createElement('span');
    text.textContent = (layer.legend && layer.legend.label) || id.replace(/[-_]/g, ' ');
    label.appendChild(text);
    bar.appendChild(label);
    // A layer the producer emitted but this run must not show (a selection
    // under a failed test) starts off and says why.
    if (suppressed.has(id)) {
      box.checked = false;
      box.disabled = true;
      label.classList.add('is-suppressed');
      label.title = 'Not shown: the declared test did not pass.';
    }
  }
  container.appendChild(bar);
  return bar;
}

function cssSafe(id) {
  return String(id).replace(/[^A-Za-z0-9_-]/g, '-');
}

function cssEscape(id) {
  return (window.CSS && CSS.escape) ? CSS.escape(id) : String(id).replace(/"/g, '\\"');
}
