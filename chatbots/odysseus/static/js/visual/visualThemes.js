// visualThemes.js — the Themes centre (IDL-REQ-0004; supersedes the Maps centre).
//
// People do not arrive wanting maps. They arrive with a question, and the
// questions repeat. A THEME is one of those recurring questions; a SOLUTION is
// something somebody published to answer it — their analysis, their map, their
// styling, their name on it.
//
// Everything here is producer-supplied. The consumer does not mine the
// conversations, does not rank the themes, does not judge the solutions and
// does not paraphrase an author. Where the producer says nothing, this screen
// shows less rather than inventing: no mined count, no byline, no leaderboard
// position, and a write-up drawn from the pack's own declared sentences,
// labelled as such.
//
// Two boundaries hold no matter what a solution declares:
//   * an author's prose is rendered as TEXT — never as markup, never executed;
//   * a failed validation keeps its evidence and loses its recommendation
//     (visualDecisionMap.js owns that; a write-up cannot override it).

import { VisualClient } from './visualData.js';
import {
  renderValidationPanel, renderLayerToggles, selectionAllowed,
} from './visualDecisionMap.js';
import { renderVisual } from './visualRenderers.js';

let centreEl = null;
let onOpenInChat = null;
let client = null;

// The producer's decision themes, in the order DECISION_MAPS.md lists them.
// A theme key the consumer has not seen still renders — under its own name.
const GROUP_ORDER = ['protect', 'restore', 'reconnect', 'anticipate', 'listen', 'learn'];
const GROUP_WORDS = {
  protect: 'Protect', restore: 'Restore', reconnect: 'Reconnect',
  anticipate: 'Anticipate', listen: 'Listen', learn: 'Learn',
};

const READINESS = {
  ready: 'Answered',
  partial: 'Partly answered',
  'awaiting-validation-data': 'Open question',
  blocked: 'Blocked',
};

const TESTED_AS = {
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

export function hideThemes() {
  document.body.classList.remove('eco-themes-open');
}

function ensureCentre() {
  if (centreEl) return centreEl;
  centreEl = el('div');
  centreEl.id = 'eco-themes';
  document.body.appendChild(centreEl);
  document.addEventListener('keydown', (ev) => {
    if (ev.key === 'Escape' && document.body.classList.contains('eco-themes-open')) {
      const back = centreEl.querySelector('.eco-theme-back');
      if (back) back.click();
    }
  });
  return centreEl;
}

/**
 * Open the Themes centre for a site.
 *   opts.onOpenInChat(text) — put a theme's question in the composer so the
 *   reader can carry it into their own conversation with everything else the
 *   site knows. Never auto-sent.
 */
export async function openThemes(endpointId, opts) {
  ensureCentre();
  onOpenInChat = (opts && opts.onOpenInChat) || null;
  document.body.classList.remove('eco-landing-open', 'eco-atlas-open');
  document.body.classList.add('eco-themes-open');
  centreEl.replaceChildren();
  client = new VisualClient(endpointId);

  const inner = el('div', 'eco-themes-inner');
  centreEl.appendChild(inner);
  inner.appendChild(el('div', 'eco-landing-loading', 'Reading the questions this pack answers…'));

  let catalogue;
  try {
    catalogue = await client.decisionMaps();
  } catch {
    inner.replaceChildren();
    inner.appendChild(header(null));
    inner.appendChild(el('div', 'eco-landing-loading',
      'This site pack publishes no themes yet.'));
    return;
  }
  renderIndex(inner, catalogue);
}

// ---- the index: recurring questions ----------------------------------------

function renderIndex(inner, catalogue) {
  const recipes = (catalogue && catalogue.recipes) || [];
  inner.replaceChildren();
  inner.appendChild(header(catalogue));
  if (!recipes.length) {
    inner.appendChild(el('div', 'eco-landing-loading', 'No themes yet for this pack.'));
    return;
  }

  const groups = [...new Set(recipes.map((r) => r.theme || 'other'))].sort((a, b) => {
    const ia = GROUP_ORDER.indexOf(a), ib = GROUP_ORDER.indexOf(b);
    return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib);
  });
  for (const group of groups) {
    const section = el('section', 'eco-themes-group');
    section.appendChild(el('h2', 'eco-themes-grouphead',
      GROUP_WORDS[group] || String(group).replace(/[-_]/g, ' ')));
    for (const recipe of recipes.filter((r) => (r.theme || 'other') === group)) {
      section.appendChild(themeRow(recipe, inner, catalogue));
    }
    inner.appendChild(section);
  }
}

function header(catalogue) {
  const head = el('header', 'eco-themes-head');
  head.appendChild(el('h1', null, 'Themes'));
  head.appendChild(el('p', null,
    'Thematic problems that keep coming up across users of this site. Open one '
    + 'to read the analysis, then take the question into your own chat.'));
  const site = catalogue && catalogue.site;
  if (site && site.label) head.appendChild(el('p', 'eco-themes-site', site.label));
  return head;
}

// One recurring question. The title is the question itself, not a map name.
function themeRow(recipe, inner, catalogue) {
  const questions = recipe.questions || [];
  const row = el('article', 'eco-theme-row');
  row.dataset.status = recipe.status || 'unknown';

  const q = el('h3', 'eco-theme-q', questions[0] || recipe.title || recipe.recipe_id);
  row.appendChild(q);

  // The other phrasings this theme absorbs — evidence that it recurs.
  if (questions.length > 1) {
    const alts = el('div', 'eco-theme-alts');
    for (const alt of questions.slice(1, 4)) alts.appendChild(el('span', 'eco-theme-alt', alt));
    row.appendChild(alts);
  }

  const meta = el('div', 'eco-theme-meta');
  meta.appendChild(el('span', `eco-theme-pill eco-theme-${recipe.status || 'unknown'}`,
    READINESS[recipe.status] || String(recipe.status || '').replace(/[-_]/g, ' ')));
  const val = recipe.validation || {};
  if (val.kind) {
    meta.appendChild(el('span', 'eco-theme-metabit',
      TESTED_AS[val.kind] || String(val.kind).replace(/[-_]/g, ' ')));
  }
  // No mined count exists yet (IDL-REQ-0004): say nothing rather than guess.
  row.appendChild(meta);

  if (recipe.status === 'ready') {
    const open = el('button', 'eco-theme-open', 'Open the answer →');
    open.addEventListener('click', () => openSolution(recipe, inner, catalogue));
    row.appendChild(open);
  } else {
    const missing = (recipe.required_inputs || []).filter((i) => i && i.status !== 'available');
    const box = el('div', 'eco-theme-missing');
    box.appendChild(el('div', 'eco-theme-missing-cap',
      'Nobody can answer this yet — what is missing'));
    const ul = el('ul');
    for (const m of missing) {
      const li = el('li');
      li.appendChild(el('span', 'eco-theme-missing-role', m.role || ''));
      li.appendChild(document.createTextNode(` — ${m.description || ''}`));
      if (m.status === 'needs-review') li.appendChild(el('span', 'eco-theme-flag', ' (needs review)'));
      ul.appendChild(li);
    }
    if (missing.length) box.appendChild(ul);
    row.appendChild(box);
  }

  // An open question is still worth asking in your own words.
  if (onOpenInChat) {
    const ask = el('button', 'eco-theme-ask', 'Ask this in chat');
    ask.addEventListener('click', () => {
      hideThemes();
      onOpenInChat(questions[0] || recipe.title || '');
    });
    row.appendChild(ask);
  }
  return row;
}

// ---- the reading view: one published answer --------------------------------

async function openSolution(recipe, inner, catalogue) {
  inner.replaceChildren();

  const back = el('button', 'eco-theme-back', '← All themes');
  back.addEventListener('click', () => renderIndex(inner, catalogue));
  inner.appendChild(back);

  const questions = recipe.questions || [];
  const head = el('header', 'eco-solution-head');
  head.appendChild(el('h1', 'eco-solution-q', questions[0] || recipe.title || ''));
  // The producer publishes no author yet (IDL-REQ-0004) — so no byline is
  // shown. What it does publish is the recipe identity and its version.
  const by = el('p', 'eco-solution-by');
  by.textContent = recipe.version
    ? `Published in this site pack · recipe ${recipe.recipe_id} v${recipe.version}`
    : 'Published in this site pack';
  head.appendChild(by);
  inner.appendChild(head);

  const stage = el('div', 'eco-solution-stage');
  inner.appendChild(stage);
  stage.appendChild(el('div', 'eco-landing-loading', 'Running the published analysis…'));

  // Arguments the recipe advertises, at their declared defaults. The reader
  // changes them from the panel's own rerun action, not from here.
  const args = { recipe_id: recipe.recipe_id };
  for (const [name, spec] of Object.entries((recipe.invocation || {}).arguments || {})) {
    if (Array.isArray(spec) && spec.length) args[name] = spec[0];
    else if (spec && typeof spec === 'object' && spec.default !== undefined) args[name] = spec.default;
  }

  let env;
  try {
    env = await client.query('validated-decision-map', args, questions[0] || '');
  } catch {
    stage.replaceChildren(el('div', 'eco-landing-loading',
      'That analysis did not complete just now. Nothing here has changed.'));
    return;
  }
  stage.replaceChildren();
  renderSolution(stage, env, recipe);
}

function renderSolution(stage, env, recipe) {
  const visuals = env.visuals || [];
  const primary = visuals.find((v) => v.view === 'validated-decision-map')
    || visuals.find((v) => v.priority === 'primary') || visuals[0] || null;

  // The headline the producer wrote for this run.
  const answer = env.answer || {};
  if (answer.headline) stage.appendChild(el('h2', 'eco-solution-headline', answer.headline));

  // The map, in the author's own presentation where they declare one.
  if (primary) {
    const figure = el('div', 'eco-solution-figure');
    stage.appendChild(figure);
    const suppressSelection = !selectionAllowed(env);
    renderMapInto(figure, primary, env, suppressSelection);
  }

  // The write-up. Until the producer ships an author's prose (IDL-REQ-0004),
  // this is assembled from the pack's OWN declared sentences and labelled as
  // such — it is never presented as somebody's analysis when it is not.
  const writeup = el('section', 'eco-solution-writeup');
  writeup.appendChild(el('h3', 'eco-solution-h', 'What this does'));
  if (recipe.decision) writeup.appendChild(el('p', null, recipe.decision));
  const product = recipe.product || {};
  const dl = el('dl', 'eco-solution-dl');
  for (const [k, label] of [['observed', 'What is measured'], ['modelled', 'What is estimated'],
    ['decision_output', 'What it recommends']]) {
    if (!product[k]) continue;
    dl.appendChild(el('dt', null, label));
    dl.appendChild(el('dd', null, product[k]));
  }
  if (dl.childElementCount) writeup.appendChild(dl);
  const method = (recipe.validation || {}).method;
  if (method) {
    writeup.appendChild(el('h3', 'eco-solution-h', 'How it was checked'));
    writeup.appendChild(el('p', null, method));
  }
  writeup.appendChild(el('p', 'eco-solution-src',
    'These words are the site pack’s own description of the recipe. '
    + 'Author write-ups are not published by this pack yet.'));
  stage.appendChild(writeup);

  // The test, in full — the same treatment a decision map gets in chat. Its
  // limitations are omitted here because this view gives them their own
  // section below; printing them twice reads as noise, not as emphasis.
  renderValidationPanel(stage, env, { omitLimitations: true });

  // Limits the producer attached to the answer itself.
  const lims = (env.limitations || []).map((l) => l && l.message).filter(Boolean);
  if (lims.length) {
    const box = el('section', 'eco-solution-limits');
    box.appendChild(el('h3', 'eco-solution-h', 'What it does not tell you'));
    const ul = el('ul');
    for (const m of lims) ul.appendChild(el('li', null, m));
    box.appendChild(ul);
    stage.appendChild(box);
  }

  // Carry it into a conversation, where it can meet everything else.
  const foot = el('div', 'eco-solution-foot');
  if (onOpenInChat) {
    const ask = el('button', 'eco-theme-open', 'Open in chat');
    ask.addEventListener('click', () => {
      hideThemes();
      onOpenInChat((recipe.questions || [])[0] || recipe.title || '');
    });
    foot.appendChild(ask);
    foot.appendChild(el('span', 'eco-solution-foothint',
      'Puts the question in your composer, so you can cross it with anything '
      + 'else this site holds.'));
  }
  stage.appendChild(foot);
}

// The author's declared presentation, honoured where it exists. A basemap the
// consumer does not recognise degrades to the default — it never fails the
// render, and tiles always go through the same-origin proxy.
function renderMapInto(host, visual, env, suppressSelection) {
  const layerData = new Map();
  const rawUrl = (ref) => (ref && ref.kind === 'result_data' && ref.handle
    ? `${client.base}/results/${encodeURIComponent(env.result_id)}/data/${encodeURIComponent(ref.handle)}`
    : null);
  Promise.all((visual.layers || []).map(async (layer) => {
    if (!layer.data_ref) return;
    try {
      const parsed = await client.fetchData(layer.data_ref, env);
      if (parsed) layerData.set(layer.layer_id, parsed);
    } catch { /* a missing layer renders as a gap, never as a guess */ }
  })).then(() => {
    const frame = renderVisual(host, visual, layerData, {
      rawUrl,
      preferLeaflet: true,
      suppressSelection,
      // IDL-REQ-0004: presentation.basemap when the producer declares one.
      basemap: (visual.presentation || {}).basemap
        || ((env.answer || {}).presentation || {}).basemap || null,
    });
    const toggles = el('div', 'eco-solution-toggles');
    frame.appendChild(toggles);
    renderLayerToggles(toggles, visual, frame, {});
  });
}
