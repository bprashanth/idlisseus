// visualMapsCentre.js — TR-VIS-0008: the Maps centre.
//
// A catalogue of the decision maps this pack currently publishes — not a
// history of maps that happened to appear in a conversation. Every card comes
// from the producer's GET /v1/decision-maps; nothing here is inferred from a
// recipe id, a subject or a place.
//
// A ready card can run its declared capability with its declared arguments.
// A waiting card names the exact inputs the producer still lacks and offers no
// run affordance, so the centre can never imply a map already exists.

import { VisualClient } from './visualData.js';

let centreEl = null;
let onOpenResult = null;

// The producer's decision themes, in the order DECISION_MAPS.md lists them.
// A theme the consumer has not seen still renders — under its own name.
const THEME_ORDER = ['protect', 'restore', 'reconnect', 'anticipate', 'listen', 'learn'];
const THEME_WORDS = {
  protect: 'Protect',
  restore: 'Restore',
  reconnect: 'Reconnect',
  anticipate: 'Anticipate',
  listen: 'Listen',
  learn: 'Learn',
};

// Readiness in the reader's words. Only `ready` earns a run affordance.
const STATUS_WORDS = {
  ready: 'Ready to run',
  partial: 'Partly ready',
  'awaiting-validation-data': 'Waiting for evidence',
  blocked: 'Blocked',
};

const VALIDATION_WORDS = {
  'temporal-hindcast': 'tested on later withheld records',
  'spatial-holdout': 'tested on whole withheld places',
  'field-ground-truth': 'tested against field measurements',
  'observation-only': 'measured evidence only',
  pending: 'no test possible yet',
};

function el(tag, cls, text) {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text !== undefined) n.textContent = text;
  return n;
}

export function hideMapsCentre() {
  document.body.classList.remove('eco-maps-open');
}

function ensureCentre() {
  if (centreEl) return centreEl;
  centreEl = el('div');
  centreEl.id = 'eco-maps';
  document.body.appendChild(centreEl);
  return centreEl;
}

/**
 * Open the Maps centre for a site.
 *   endpointId  — the registered visual endpoint.
 *   opts.onResult(resultId) — called when a run produces a result, so the
 *     caller can show it exactly as a chat result is shown.
 */
export async function openMapsCentre(endpointId, opts) {
  ensureCentre();
  onOpenResult = (opts && opts.onResult) || null;
  document.body.classList.remove('eco-landing-open', 'eco-atlas-open');
  document.body.classList.add('eco-maps-open');
  centreEl.replaceChildren();

  const inner = el('div', 'eco-maps-inner');
  centreEl.appendChild(inner);
  inner.appendChild(el('div', 'eco-landing-loading', 'Reading this pack’s decision maps…'));

  const client = new VisualClient(endpointId);
  let catalogue;
  try {
    catalogue = await client.decisionMaps();
  } catch {
    // A pack that predates the catalogue contract is not an error state.
    inner.replaceChildren();
    inner.appendChild(header(null));
    inner.appendChild(el('div', 'eco-landing-loading',
      'This site pack does not publish decision maps yet.'));
    return;
  }

  const recipes = (catalogue && catalogue.recipes) || [];
  inner.replaceChildren();
  inner.appendChild(header(catalogue));
  if (!recipes.length) {
    inner.appendChild(el('div', 'eco-landing-loading',
      'This site pack publishes no decision maps yet.'));
    return;
  }

  // Group by the producer's generic theme field, producer order first.
  const themes = [...new Set(recipes.map((r) => r.theme || 'other'))]
    .sort((a, b) => {
      const ia = THEME_ORDER.indexOf(a), ib = THEME_ORDER.indexOf(b);
      return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib);
    });
  for (const theme of themes) {
    const group = el('section', 'eco-maps-group');
    const h = el('h2', 'eco-maps-theme', THEME_WORDS[theme] || String(theme).replace(/[-_]/g, ' '));
    group.appendChild(h);
    const grid = el('div', 'eco-maps-grid');
    group.appendChild(grid);
    for (const recipe of recipes.filter((r) => (r.theme || 'other') === theme)) {
      grid.appendChild(card(recipe, client, endpointId));
    }
    inner.appendChild(group);
  }
}

function header(catalogue) {
  const head = el('header', 'eco-maps-head');
  const h1 = el('h1', null, 'Maps');
  head.appendChild(h1);
  const sub = el('p', null,
    'Decision maps this pack publishes. Each one supports a bounded choice and '
    + 'says how it was tested — including the ones still waiting for evidence.');
  head.appendChild(sub);
  const site = catalogue && catalogue.site;
  if (site && site.label) {
    head.appendChild(el('p', 'eco-maps-site', site.label));
  }
  return head;
}

function card(recipe, client, endpointId) {
  const c = el('article', 'eco-maps-card');
  c.dataset.status = recipe.status || 'unknown';
  c.dataset.recipe = recipe.recipe_id || '';

  const top = el('div', 'eco-maps-card-top');
  top.appendChild(el('h3', 'eco-maps-card-title', recipe.title || recipe.recipe_id || 'Untitled'));
  const pill = el('span', `eco-maps-pill eco-maps-pill-${recipe.status || 'unknown'}`,
    STATUS_WORDS[recipe.status] || String(recipe.status || '').replace(/[-_]/g, ' '));
  top.appendChild(pill);
  c.appendChild(top);

  // The decision this map exists to support — the producer's own sentence.
  if (recipe.decision) c.appendChild(el('p', 'eco-maps-decision', recipe.decision));

  // Freshness: the recipe version and how it is tested. Version is what the
  // producer actually revises; inventing a timestamp would be a lie.
  const meta = el('div', 'eco-maps-meta');
  const val = recipe.validation || {};
  meta.appendChild(el('span', null, VALIDATION_WORDS[val.kind] || String(val.kind || '').replace(/[-_]/g, ' ')));
  if (recipe.version) meta.appendChild(el('span', null, `recipe v${recipe.version}`));
  c.appendChild(meta);

  if (recipe.status === 'ready') {
    c.appendChild(runRow(recipe, client, c));
  } else {
    // A waiting card must show exactly what is missing, and must not imply a
    // map exists. No run affordance is rendered at all.
    const missing = (recipe.required_inputs || []).filter((i) => i && i.status !== 'available');
    const box = el('div', 'eco-maps-missing');
    box.appendChild(el('div', 'eco-maps-missing-cap',
      missing.length ? 'Still needed before this can be tested' : 'Not runnable yet'));
    const ul = el('ul');
    for (const m of missing) {
      const li = el('li');
      li.appendChild(el('span', 'eco-maps-missing-role', m.role || ''));
      li.appendChild(document.createTextNode(` — ${m.description || ''}`));
      if (m.status === 'needs-review') li.appendChild(el('span', 'eco-maps-missing-flag', ' (needs review)'));
      ul.appendChild(li);
    }
    if (missing.length) box.appendChild(ul);
    c.appendChild(box);
    if (val.claim_if_failed || val.method) {
      c.appendChild(el('p', 'eco-maps-note', val.method || ''));
    }
  }
  return c;
}

// The run row exposes only the arguments the producer advertises, with its own
// declared bounds. Nothing else can be sent.
function runRow(recipe, client, cardEl) {
  const row = el('div', 'eco-maps-run');
  const args = (recipe.invocation && recipe.invocation.arguments) || {};
  const controls = new Map();

  for (const [name, spec] of Object.entries(args)) {
    const field = el('label', 'eco-maps-arg');
    field.appendChild(el('span', 'eco-maps-arg-name', name.replace(/_/g, ' ')));
    let input;
    if (Array.isArray(spec)) {
      input = document.createElement('select');
      for (const opt of spec) {
        const o = document.createElement('option');
        o.value = String(opt);
        o.textContent = String(opt).replace(/_/g, ' ');
        input.appendChild(o);
      }
    } else if (spec && typeof spec === 'object' && ('minimum' in spec || 'maximum' in spec)) {
      input = document.createElement('input');
      input.type = 'number';
      if (spec.minimum !== undefined) input.min = spec.minimum;
      if (spec.maximum !== undefined) input.max = spec.maximum;
      input.value = spec.default !== undefined ? spec.default : (spec.minimum ?? 1);
    } else {
      input = document.createElement('input');
      input.type = 'text';
    }
    input.className = 'eco-maps-arg-input';
    field.appendChild(input);
    controls.set(name, { input, spec });
    row.appendChild(field);
  }

  const run = el('button', 'eco-maps-run-btn', 'Open this map');
  row.appendChild(run);
  const note = el('div', 'eco-maps-run-note');
  row.appendChild(note);

  run.addEventListener('click', async () => {
    run.disabled = true;
    const original = run.textContent;
    run.textContent = 'Running the declared test…';
    note.textContent = '';
    const payload = { recipe_id: recipe.recipe_id };
    for (const [name, { input, spec }] of controls) {
      let v = input.value;
      if (spec && typeof spec === 'object' && !Array.isArray(spec) && input.type === 'number') {
        v = Number(v);
        if (!Number.isFinite(v)) continue;
        if (spec.minimum !== undefined) v = Math.max(spec.minimum, v);
        if (spec.maximum !== undefined) v = Math.min(spec.maximum, v);
      }
      if (v !== '' && v !== undefined) payload[name] = v;
    }
    try {
      const env = await client.query('validated-decision-map', payload, recipe.title || '');
      if (env && env.result_id && onOpenResult) {
        hideMapsCentre();
        onOpenResult(env.result_id);
      } else {
        note.textContent = 'The producer returned no result for those arguments.';
      }
    } catch (err) {
      // The producer is the authority on failure; never fabricate a map.
      note.textContent = 'That run did not complete. The catalogue is unchanged.';
      console.warn('decision map run failed', err);
    } finally {
      run.disabled = false;
      run.textContent = original;
    }
  });
  return row;
}
