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
  renderValidationPanel, renderLayerToggles, selectionAllowed, focusNamedLocation,
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

// Catalogue readiness, not validation: `ready` and `partial` both run.
// `awaiting-validation-data` and `blocked` are readiness views only.
const RUNNABLE = new Set(['ready', 'partial']);

const READINESS = {
  ready: 'Answered',
  partial: 'Evidence, not yet an answer',
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
 *   opts.onOpenInChat({question, resultId, text}) — carry a theme into the
 *   reader's own conversation. From the index only the question travels
 *   (nothing has been run yet); from a reading view the published answer
 *   travels with it — the map plus the facts behind it — so the next question
 *   can be about the work itself. The reader's question is never auto-sent.
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

  // TR-VIS-0009: `partial` runs too. Catalogue readiness is not the same as a
  // passing test: a partial recipe returns measured evidence and the places
  // worth checking, and says so — it is not an admitted decision model.
  if (RUNNABLE.has(recipe.status)) {
    const open = el('button', 'eco-theme-open',
      recipe.status === 'ready' ? 'Open the answer →' : 'Open the evidence →');
    open.addEventListener('click', () => openSolution(recipe, inner, catalogue));
    row.appendChild(open);
    if (recipe.status === 'partial') {
      row.appendChild(el('p', 'eco-theme-partialnote',
        'Runs on measured evidence and marks where another observation would '
        + 'settle the question. It does not recommend action.'));
    }
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
      // Nothing has been run from the index, so only the question travels.
      onOpenInChat({ question: questions[0] || recipe.title || '' });
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
  const pub = publishedAnswer(recipe);
  const head = el('header', 'eco-solution-head');
  head.appendChild(el('h1', 'eco-solution-q',
    (pub && pub.title) || questions[0] || recipe.title || ''));
  // The producer publishes no author yet (IDL-REQ-0004) — so no byline is
  // shown. What it does publish is the recipe identity and its version.
  const by = el('p', 'eco-solution-by');
  const pubMeta = (pub && pub.publication) || {};
  by.textContent = [
    pubMeta.credit || 'Published in this site pack',
    pubMeta.published_at ? `published ${pubMeta.published_at}` : '',
    recipe.version ? `recipe ${recipe.recipe_id} v${recipe.version}` : '',
  ].filter(Boolean).join(' · ');
  head.appendChild(by);
  inner.appendChild(head);

  const stage = el('div', 'eco-solution-stage');
  inner.appendChild(stage);
  stage.appendChild(el('div', 'eco-landing-loading', 'Running the published analysis…'));

  // Arguments the recipe advertises, at their declared defaults. The reader
  // changes them from the panel's own rerun action, not from here.
  // A published answer declares the arguments it was written about; run those
  // so the article and the map on screen describe the same thing.
  const declaredDefaults = ((publishedAnswer(recipe) || {}).default_arguments) || {};
  const args = { recipe_id: recipe.recipe_id, ...declaredDefaults };
  for (const [name, spec] of Object.entries((recipe.invocation || {}).arguments || {})) {
    if (args[name] !== undefined) continue;
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
  let frame = null;
  const visuals = env.visuals || [];
  const primary = visuals.find((v) => v.view === 'validated-decision-map')
    || visuals.find((v) => v.priority === 'primary') || visuals[0] || null;

  // Lead with the published short answer where there is one; the run's own
  // headline stands in otherwise. Either way it comes before the map.
  const pa = publishedAnswer(recipe);
  const answer = env.answer || {};
  if (pa && pa.standfirst) stage.appendChild(el('p', 'eco-note-standfirst', pa.standfirst));
  else if (answer.headline) stage.appendChild(el('h2', 'eco-solution-headline', answer.headline));

  // The map, in the author's own presentation where they declare one.
  if (primary) {
    const figure = el('div', 'eco-solution-figure');
    stage.appendChild(figure);
    const suppressSelection = !selectionAllowed(env);
    frame = renderMapInto(figure, primary, env, suppressSelection);
  }

  // TR-VIS-0010: when the pack publishes a field note, that is the answer.
  // The consumer renders it; it does not paraphrase it, reorder its claims or
  // let it outrank validation. Packs without one keep the old assembly.
  if (pa) renderFieldNote(stage, pa, recipe, env, frame);
  else renderAssembledWriteup(stage, recipe);

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
      // The answer itself travels — the map and the facts behind it — so the
      // next question can be about the work, not just about the topic.
      onOpenInChat({
        question: (recipe.questions || [])[0] || recipe.title || '',
        resultId: env.result_id,
        text: briefing(recipe, env),
        // The assistant answers by running capabilities, not by re-reading the
        // transcript, so a bare "this" leaves it asking which visual is meant.
        // The composer opens with the analysis named — visible, editable, and
        // deletable — and the reader writes their question after it.
        anchor: `About the ${recipe.recipe_id} analysis above (${env.result_id}): `,
      });
    });
    foot.appendChild(ask);
    foot.appendChild(el('span', 'eco-solution-foothint',
      'Drops this map and the facts behind it into your chat, so you can ask '
      + 'how it was made, what it used, or how it meets your own question.'));
  }
  stage.appendChild(foot);
}

// Everything a reader might reasonably ask of a published analysis, written
// out so it travels with the map into the conversation: which recipe ran, the
// method behind the estimate, how it was tested and against what thresholds,
// which data sets it drew on (with DOIs), whose basemap is under it, and what
// it does not tell you. Every line is producer text or a producer number —
// nothing here is the consumer's opinion of the work.
function briefing(recipe, env) {
  const pa = publishedAnswer(recipe);
  if (pa) return publishedBriefing(pa, recipe, env);
  const q = (recipe.questions || [])[0] || recipe.title || '';
  const answer = env.answer || {};
  const val = answer.validation || {};
  const out = [];
  out.push(`**Published analysis — ${q}**`);
  out.push('');
  out.push('Copied from this site’s Themes. The site pack published it; it was '
    + 'not worked out in this conversation.');
  out.push('');
  if (answer.headline) out.push(answer.headline);
  if (answer.detail) out.push('', answer.detail);
  out.push('');
  const bits = [];
  bits.push(`- Recipe: \`${recipe.recipe_id}\`${recipe.version ? ` v${recipe.version}` : ''} `
    + `(capability \`${recipe.capability_id || 'validated-decision-map'}\`), result \`${env.result_id}\``);
  if (recipe.decision) bits.push(`- Decision it supports: ${recipe.decision}`);
  const product = recipe.product || {};
  if (product.modelled) bits.push(`- How the estimate is made: ${product.modelled}`);
  if (product.observed) bits.push(`- What is measured directly: ${product.observed}`);
  if (val.method || (recipe.validation || {}).method) {
    bits.push(`- How it was tested: ${val.method || recipe.validation.method}`);
  }
  if (val.kind) {
    const checks = Object.entries(val.checks || {}).map(([k, c]) =>
      `${k.replace(/_/g, ' ')} ${c.value} ${c.operator || '>='} ${c.threshold} — ${c.passed ? 'met' : 'NOT met'}`);
    bits.push(`- Test: ${val.kind}, status ${val.status || 'unknown'}`
      + (val.split_rule ? ` (${val.split_rule})` : '')
      + (checks.length ? `; checks: ${checks.join('; ')}` : ''));
  }
  const sources = ((env.audit || {}).source_versions || []).map((sv) =>
    (typeof sv === 'string' ? sv : `${sv.title || sv.source_id}${sv.doi ? ` (doi:${sv.doi})` : ''}`));
  if (sources.length) bits.push(`- Data sets used: ${sources.join('; ')}`);
  // The basemap question deserves a straight answer either way.
  const declared = ((env.visuals || []).find((v) => v.presentation) || {}).presentation;
  bits.push(declared && declared.basemap
    ? `- Basemap: \`${declared.basemap}\`, declared by the publisher; tiles are proxied by this app.`
    : '- Basemap: none declared by the publisher — shown on this app’s default '
      + 'basemap (Esri imagery or OpenStreetMap, proxied same-origin).');
  const lims = (env.limitations || []).map((l) => l && l.message).filter(Boolean);
  if (lims.length) bits.push(`- Limits stated by the publisher: ${lims.join(' ')}`);
  out.push(bits.join('\n'));
  out.push('');
  // Readers say "this"; without something to bind it to, the assistant has to
  // stop and ask which visual is meant. Naming the referent in the transcript
  // costs one line and is as visible to the reader as it is to the model.
  out.push(`Ask about it below — in this conversation, “this analysis”, “this map” `
    + `and “this” mean the ${recipe.recipe_id} analysis above.`);
  return out.join('\n');
}

// TR-VIS-0010: when a field note exists, that is what travels into the
// conversation — the short answer, the evidence, the named estimator, the
// plain-language test, the recommendation, the named places and why stronger
// advice would be premature. Never the mechanically assembled write-up.
function publishedBriefing(pa, recipe, env) {
  const out = [];
  const pub = pa.publication || {};
  out.push(`**${pa.title || recipe.recipe_id}**`);
  out.push('');
  out.push('Published field note, copied from this site’s Themes. The site pack '
    + 'published it; it was not worked out in this conversation.');
  out.push('');
  if (pa.standfirst) out.push(pa.standfirst);
  const rec = pa.recommendation || {};
  if (rec.summary || (rec.steps || []).length) {
    out.push('', '**What to do now**');
    if (rec.summary) out.push(rec.summary);
    (rec.steps || []).forEach((step, i) => out.push(`${i + 1}. ${step}`));
  }
  if (pa.what_was_measured) out.push('', `**What was measured** — ${pa.what_was_measured}`);
  const est = pa.estimate || {};
  if (est.name || est.plain_language) {
    out.push('', `**What was estimated** — ${[est.name, est.plain_language].filter(Boolean).join(': ')}`);
  }
  const test = pa.test || {};
  if (test.outcome || test.plain_language) {
    out.push('', `**How it was tested** — outcome: ${test.outcome || 'unknown'}`
      + (test.plain_language ? `. ${test.plain_language}` : ''));
  }
  if (pa.why_this_advice) out.push('', `**Why not stronger advice** — ${pa.why_this_advice}`);
  const spots = pa.named_locations || [];
  if (spots.length) {
    out.push('', `**Named places** (${spots.length}): `
      + spots.map((sp) => `${sp.location_id}${sp.role ? ` [${sp.role}]` : ''}`).join(', '));
  }
  const val = (env.answer || {}).validation || {};
  out.push('', `- Recipe \`${recipe.recipe_id}\`${recipe.version ? ` v${recipe.version}` : ''}, `
    + `result \`${env.result_id}\`, validation ${val.status || 'unknown'}`);
  out.push(`- Arguments this note describes: ${JSON.stringify(pa.default_arguments || {})}`);
  if (pub.credit) out.push(`- Credit: ${pub.credit}${pub.published_at ? `, published ${pub.published_at}` : ''}`);
  const sources = ((env.audit || {}).source_versions || []).map((sv) =>
    (typeof sv === 'string' ? sv : `${sv.title || sv.source_id}${sv.doi ? ` (doi:${sv.doi})` : ''}`));
  if (sources.length) out.push(`- Data sets used: ${sources.join('; ')}`);
  out.push('');
  out.push(`Ask about it below — in this conversation, “this analysis”, “this map” `
    + `and “this” mean the ${recipe.recipe_id} analysis above.`);
  return out.join('\n');
}

// ---- TR-VIS-0010: the published field note --------------------------------

// A published answer is bound to the arguments it was written about. If a
// reader reruns with different ones, the article no longer describes what is
// on screen, so it is withheld rather than re-captioned.
export function publishedAnswer(recipe, usedArgs) {
  const pa = recipe && recipe.published_answer;
  if (!pa || ((pa.publication || {}).status !== 'published')) return null;
  if (usedArgs) {
    const declared = pa.default_arguments || {};
    const same = Object.entries(declared)
      .every(([k, v]) => String(usedArgs[k] ?? '') === String(v ?? ''));
    if (!same) return null;
  }
  return pa;
}

// Everything below is producer prose, inserted as TEXT — never as markup and
// never executed. Order is the producer's: the short answer, then what to do,
// then the evidence, the estimator, the test, and why stronger advice would be
// premature.
function renderFieldNote(stage, pa, recipe, env, frame) {
  const article = el('article', 'eco-note');

  // What to do now — the reason a reader opened this at all.
  const rec = pa.recommendation || {};
  if (rec.summary || (rec.steps || []).length) {
    const box = el('section', 'eco-note-do');
    box.appendChild(el('h3', 'eco-note-doh', 'What to do now'));
    if (rec.summary) box.appendChild(el('p', 'eco-note-dosum', rec.summary));
    if ((rec.steps || []).length) {
      const ol = el('ol', 'eco-note-steps');
      for (const step of rec.steps) ol.appendChild(el('li', null, step));
      box.appendChild(ol);
    }
    article.appendChild(box);
  }

  // The named places, as a field checklist. Clicking one finds it on the map.
  const spots = pa.named_locations || [];
  if (spots.length) {
    const box = el('section', 'eco-note-spots');
    box.appendChild(el('h3', 'eco-solution-h', 'Where'));
    const list = el('ul', 'eco-note-list');
    for (const spot of spots) {
      const li = el('li', 'eco-note-spot');
      li.dataset.role = spot.role || '';
      const btn = el('button', 'eco-note-spot-btn');
      btn.appendChild(el('span', 'eco-note-spot-label', spot.label || spot.location_id || ''));
      // Role is wording and treatment only — never a subject-specific meaning.
      if (spot.role) btn.appendChild(el('span', `eco-note-role eco-note-role-${spot.role}`,
        ROLE_WORDS[spot.role] || String(spot.role).replace(/[-_]/g, ' ')));
      btn.addEventListener('click', () => {
        // Finds the feature and flashes it. Nothing recomputes, no value moves;
        // a location the map does not carry simply stays readable text.
        const found = frame && frame.el && focusNamedLocation(frame.el, spot.location_id);
        btn.classList.toggle('is-missing', !found);
      });
      li.appendChild(btn);
      if (spot.instruction) li.appendChild(el('p', 'eco-note-spot-do', spot.instruction));
      list.appendChild(li);
    }
    box.appendChild(list);
    article.appendChild(box);
  }

  // The evidence, the estimator and the test, in reading order.
  if (pa.what_was_measured) {
    article.appendChild(el('h3', 'eco-solution-h', 'What was measured'));
    article.appendChild(el('p', 'eco-note-p', pa.what_was_measured));
  }
  const est = pa.estimate || {};
  if (est.name || est.plain_language) {
    article.appendChild(el('h3', 'eco-solution-h', 'What was estimated'));
    if (est.name) article.appendChild(el('p', 'eco-note-method', est.name));
    if (est.plain_language) article.appendChild(el('p', 'eco-note-p', est.plain_language));
  }
  const test = pa.test || {};
  if (test.outcome || test.plain_language) {
    article.appendChild(el('h3', 'eco-solution-h', 'How the estimate was tested'));
    if (test.outcome) {
      // The outcome is a word, not a colour.
      const line = el('p', 'eco-note-outcome');
      line.appendChild(el('span', `eco-note-outcome-word eco-note-outcome-${test.outcome}`,
        outcomeWords(test.outcome)));
      article.appendChild(line);
    }
    if (test.plain_language) article.appendChild(el('p', 'eco-note-p', test.plain_language));
  }
  if (pa.why_this_advice) {
    article.appendChild(el('h3', 'eco-solution-h', 'Why we are not giving stronger advice'));
    article.appendChild(el('p', 'eco-note-p', pa.why_this_advice));
  }

  // Credit, and only real contributors.
  const pub = pa.publication || {};
  const credit = [pub.credit, pub.published_at ? `published ${pub.published_at}` : '']
    .filter(Boolean).join(' · ');
  const people = (pub.contributors || []).filter(Boolean);
  if (credit || people.length) {
    const foot = el('p', 'eco-note-credit',
      [credit, people.length ? people.join(', ') : ''].filter(Boolean).join(' — '));
    article.appendChild(foot);
  }
  stage.appendChild(article);
}

const ROLE_WORDS = {
  act: 'act here',
  'check-first': 'check first',
  'measure-first': 'measure first',
  'do-not-act': 'do not act here',
};
const OUTCOME_WORDS = {
  passed: 'The test passed',
  failed: 'The test did not pass',
  'not-yet-testable': 'Not yet testable',
  pending: 'Not tested yet',
  'not-applicable': 'No test applies',
};
// An outcome word this consumer has not met still reads as words, not as a
// machine token: hyphens out, first letter up.
function outcomeWords(outcome) {
  const key = String(outcome || '');
  if (OUTCOME_WORDS[key]) return OUTCOME_WORDS[key];
  const words = key.replace(/[-_]/g, ' ').trim();
  return words ? words.charAt(0).toUpperCase() + words.slice(1) : '';
}

// The pre-TR-VIS-0010 fallback: a pack with no field note still reads, from
// its own declared sentences, labelled as such.
function renderAssembledWriteup(stage, recipe) {
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
}

// The author's declared presentation, honoured where it exists. A basemap the
// consumer does not recognise degrades to the default — it never fails the
// render, and tiles always go through the same-origin proxy.
function renderMapInto(host, visual, env, suppressSelection) {
  // The frame is returned as a live handle: the field-note checklist focuses
  // features inside it once the layers have landed.
  const handle = { el: null };
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
    // TR-VIS-0009: name the marks under the map. The Leaflet panel has no
    // printed legend, and a dashed ring that nobody explains is decoration.
    const marks = [];
    for (const layer of visual.layers || []) {
      const hint = layer.style_hint || {};
      const fc = layerData.get(layer.layer_id);
      const count = (field) => ((fc && fc.features) || [])
        .filter((f) => (f.properties || {})[field]).length;
      if (hint.selected_field && !suppressSelection) {
        const n = count(hint.selected_field);
        if (n) marks.push(['solid', `${n} chosen within the declared budget`]);
      }
      if (hint.validation_priority_field) {
        const n = count(hint.validation_priority_field);
        if (n) marks.push(['dashed', `${n} marked: check or collect evidence here — not a recommendation`]);
      }
    }
    if (marks.length) {
      const key = el('div', 'eco-solution-key');
      for (const [kind, text] of marks) {
        const item = el('span', 'eco-solution-keyitem');
        item.appendChild(el('span', `eco-solution-keymark is-${kind}`));
        item.appendChild(el('span', null, text));
        key.appendChild(item);
      }
      frame.appendChild(key);
    }
    handle.el = frame;
  });
  return handle;
}
