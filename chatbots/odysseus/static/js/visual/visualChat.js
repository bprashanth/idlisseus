// visualChat.js — inline visuals in the stock Idlisseus chat.
// chatRenderer/chat.js insert `.viz-inline[data-result-id]` slots wherever an
// assistant message carried an idli-result marker (live, final and history).
// This module hydrates each slot into a compact visual card inside the bubble,
// and opens the full interactive view (Leaflet maps, drill-down, explain,
// estimate, actions) in a side panel when the card is clicked.
// The old full-screen takeover is retired; the classic chat layout is the UI.

import { VisualStage, markLabel, markValue } from './visualStage.js';
import { VisualClient } from './visualData.js';
import { renderVisual, renderTable, renderSubjectDisclosure, subjectActionLabel } from './visualRenderers.js';
import { cleanText } from './visualTheme.js';
import {
  isDecisionMapVisual, renderValidationPanel, renderLayerToggles,
  selectionAllowed, validationOf,
} from './visualDecisionMap.js';

let client = null;
let clientEndpointUrl = null;

// The ecodata skin (static/ecodata.css) applies only under this body class,
// so the stock themes stay untouched. Cheap to re-check; theme switches are rare.
function syncEcoThemeClass() {
  let name = 'ecodata';
  try {
    const saved = JSON.parse(localStorage.getItem('idlisseus-theme') || 'null');
    if (saved && saved.name) name = saved.name;
  } catch { /* default */ }
  document.body.classList.toggle('theme-ecodata', name === 'ecodata');
}
syncEcoThemeClass();

// Defensive: clear any takeover-era state a stale cached bundle left behind.
document.body.classList.remove('visual-mode', 'visual-had-stage');
for (const id of ['visual-mode-toggle', 'viz-history-btn']) {
  document.getElementById(id)?.remove();
}
document.querySelector('.viz-float-handle')?.remove();
document.querySelector('.chat-input-bar')?.classList.remove('viz-float-composer', 'viz-float-dragging');

function getSessions() {
  return import('../sessions.js');
}

async function resolveClient() {
  const sessions = await getSessions();
  const url = sessions.getCurrentEndpointUrl && sessions.getCurrentEndpointUrl();
  if (!url) return null;
  if (client && clientEndpointUrl === url) return client;
  try {
    const res = await fetch(`/api/visual/resolve?endpoint_url=${encodeURIComponent(url)}`);
    if (!res.ok) return null;
    const { endpoint_id } = await res.json();
    client = new VisualClient(endpoint_id);
    clientEndpointUrl = url;
    return client;
  } catch {
    return null;
  }
}

// ---- side panel: one full interactive chapter per opened result ------------
let panel = null;
let panelStage = null;
const panelChapters = new Map(); // result_id -> chapter

function ensurePanel() {
  if (panel) return panel;
  panel = document.createElement('aside');
  panel.id = 'viz-side-panel';
  panel.setAttribute('role', 'dialog');
  panel.setAttribute('aria-label', 'Visual detail');
  const head = document.createElement('div');
  head.className = 'viz-side-head';
  const title = document.createElement('span');
  title.className = 'viz-side-title';
  title.id = 'viz-side-title';
  title.textContent = 'Figure detail';
  head.appendChild(title);
  const close = document.createElement('button');
  close.className = 'viz-panel-close';
  close.textContent = '×';
  close.setAttribute('aria-label', 'Close visual panel');
  close.addEventListener('click', closePanel);
  head.appendChild(close);
  panel.appendChild(head);
  const host = document.createElement('div');
  host.className = 'viz-side-host';
  panel.appendChild(host);
  document.body.appendChild(panel);
  panelStage = new VisualStage(host, {
    noTakeover: true,
    preferLeaflet: true,
    fetchData: (ref, envelope) => {
      if (!client) throw new Error('no visual client');
      return client.fetchData(ref, envelope);
    },
    explain: (resultId, layerId, mark) => {
      if (!client) throw new Error('no visual client');
      return client.explain(resultId, layerId, mark);
    },
    rawUrl: (ref, envelope) => {
      if (!client || !ref || !envelope) return null;
      if (ref.kind === 'result_data' && ref.handle) {
        return `${client.base}/results/${encodeURIComponent(envelope.result_id)}/data/${encodeURIComponent(ref.handle)}`;
      }
      return null;
    },
    onMarkClick: ({ layer, props, markId, envelope }) => {
      // Interactions in the panel drive the main conversation: clicking a mark
      // inserts that mark's question into the composer (user presses send).
      const input = document.getElementById('message');
      if (!input) return;
      const what = (layer.legend && layer.legend.label) || layer.layer_id;
      // A mark without a number is not a mark whose value is null: asking
      // "the value of null" invited the assistant to answer "a count of the 0
      // records", which is an invented figure. And a bare id read as a place
      // ("at 2541") when it is a row in a source table.
      const val = markValue(props);
      const where = markLabel(props, markId);
      input.value = val !== undefined
        ? `In result ${envelope.result_id}: what is behind the ${what} value of ${val} `
          + `at ${where}? Which source rows produced it?`
        : `In result ${envelope.result_id}: what does the ${what} mark at ${where} record? `
          + 'It carries no count — say what the source rows actually contain, and do not '
          + 'treat a missing count as zero.';
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.focus();
    },
    onAction: (action) => {
      // Actions stay ordinary audited chat turns through the normal composer.
      const input = document.getElementById('message');
      if (!input) return;
      input.value = action.label;
      input.dispatchEvent(new Event('input', { bubbles: true }));
      const form = input.closest('form') || document.getElementById('chat-form');
      if (form) form.requestSubmit ? form.requestSubmit() : form.submit();
      closePanel();
    },
  });
  return panel;
}

function closePanel() {
  document.body.classList.remove('viz-panel-open');
}

export async function openInPanel(resultId) {
  const c = await resolveClient();
  if (!c) return;
  ensurePanel();
  // One right-hand surface at a time: the explorer yields to the figure panel.
  document.body.classList.remove('eco-explorer-open');
  document.body.classList.add('viz-panel-open');
  let chapter = panelChapters.get(resultId);
  if (chapter) {
    chapter.node.scrollIntoView({ block: 'start' });
    window.dispatchEvent(new Event('resize')); // leaflet size recalc
    return;
  }
  let envelope;
  try {
    envelope = await c.result(resultId);
  } catch (err) {
    console.warn('visual result fetch failed', resultId, err);
    return;
  }
  // One chapter at a time keeps the panel focused; prior ones are dropped.
  for (const [, ch] of panelChapters) ch.node.remove();
  panelChapters.clear();
  panelStage.chapters.length = 0;
  panelStage.rail.replaceChildren();
  chapter = panelStage.addChapter(envelope.question?.original || '');
  panelChapters.set(resultId, chapter);
  const title = document.getElementById('viz-side-title');
  if (title) title.textContent = envelope.site?.label || 'Figure detail';
  await chapter.setEnvelope(envelope);
}

// ---- right context rail: what THIS answer consulted ------------------------
// The rail follows the conversation, not the site: each answered question
// replaces the list with the data streams its envelope actually cites
// (audit.source_versions). Site-level stat tiles lived here before and were
// static noise — the numbers never changed between questions.
let contextRail = null;
const recentVisuals = [];
// Guard against a late hydration of an older slot overwriting the newest
// answer's sources: only a slot at or past the last rendered DOM position wins.
const consulted = { idx: -1, sources: [] };

async function ensureContextRail() {
  const c = await resolveClient();
  if (!c) { removeContextRail(); return; }
  // Already built for this endpoint: the lists re-render in place (hydrations
  // call this often; the skeleton and site name don't change between answers).
  if (contextRail && contextRail.dataset.built === '1') {
    renderConsultedList();
    return;
  }
  if (!contextRail) {
    contextRail = document.createElement('aside');
    contextRail.id = 'viz-context-rail';
    contextRail.setAttribute('aria-label', 'Answer sources');
    document.body.appendChild(contextRail);
    document.body.classList.add('viz-context-open');
  }
  try {
    contextRail.dataset.built = '1';
    const r = await fetch(`${c.base}/capabilities`);
    if (!r.ok) throw new Error('no capabilities');
    const caps = await r.json();
    contextRail.replaceChildren();
    const site = document.createElement('div');
    site.className = 'viz-rail-site';
    site.textContent = caps.label || '';
    contextRail.appendChild(site);
    if (caps.synthetic) {
      const ribbon = document.createElement('span');
      ribbon.className = 'viz-synthetic-ribbon';
      ribbon.textContent = 'Synthetic test data';
      contextRail.appendChild(ribbon);
    }
    const sh = document.createElement('div');
    sh.className = 'viz-rail-heading';
    sh.textContent = 'Data streams';
    contextRail.appendChild(sh);
    const streams = document.createElement('div');
    streams.className = 'viz-rail-streams';
    streams.id = 'viz-rail-consulted';
    contextRail.appendChild(streams);
    renderConsultedList();
  } catch {
    removeContextRail(); // endpoint has no visual plane
  }
}

// A source row links out when the producer gives us anywhere to go (a URL or
// a DOI); otherwise the honest fallback is the name alone.
function sourceHref(s) {
  if (!s || typeof s === 'string') return null;
  const direct = s.url || s.uri || s.href || s.landing_url || s.landing_page;
  if (direct && /^https?:\/\//i.test(String(direct))) return String(direct);
  if (s.doi) return `https://doi.org/${String(s.doi).replace(/^doi:/i, '')}`;
  return null;
}

function renderConsultedList() {
  const streams = document.getElementById('viz-rail-consulted');
  if (!streams) return;
  streams.replaceChildren();
  // Before the first answer the section sits quietly empty — no hint copy.
  if (consulted.idx < 0 || !consulted.sources.length) return;
  const seen = new Set();
  for (const s of consulted.sources) {
    const raw = typeof s === 'string' ? s : (s.title || s.source_id || '');
    const key = typeof s === 'string' ? s : `${s.source_id || raw}@${s.version || ''}`;
    if (!raw || seen.has(key)) continue;
    seen.add(key);
    if (seen.size > 10) break;
    const row = document.createElement('div');
    row.className = 'viz-rail-stream';
    const dot = document.createElement('span');
    dot.className = 'viz-rail-stream-dot';
    row.appendChild(dot);
    const href = sourceHref(s);
    const name = document.createElement(href ? 'a' : 'span');
    name.className = 'viz-rail-stream-name';
    name.textContent = String(raw).replace(/^syn-/, '').replace(/[-_]/g, ' ');
    name.title = String(raw) + (typeof s === 'object' && s.version ? ` (v${s.version})` : '');
    if (href) {
      name.href = href;
      name.target = '_blank';
      name.rel = 'noopener noreferrer';
    }
    row.appendChild(name);
    streams.appendChild(row);
  }
}

// A new question is in flight: the rail must stop showing the previous
// answer's streams. The next hydrated envelope refills it; a text-only
// answer (no visual, so no envelope) leaves it honestly empty.
function noteNewQuestion() {
  consulted.sources = [];
  renderConsultedList();
}

function noteConsultedSources(slot, envelope) {
  const all = [...document.querySelectorAll('.viz-inline[data-result-id]')];
  const idx = all.indexOf(slot);
  if (idx < consulted.idx) return; // an older answer finished hydrating late
  consulted.idx = idx;
  consulted.sources = ((envelope && envelope.audit) || {}).source_versions || [];
  renderConsultedList();
}

export function refreshContext() {
  client = null; clientEndpointUrl = null;
  recentVisuals.length = 0;
  consulted.idx = -1; consulted.sources = [];
  removeContextRail();
  setTimeout(() => ensureContextRail(), 600);
}

function removeContextRail() {
  if (contextRail) { contextRail.remove(); contextRail = null; }
  document.body.classList.remove('viz-context-open');
}

function noteRecentVisual(resultId, headline) {
  if (recentVisuals.some((r) => r.resultId === resultId)) return;
  recentVisuals.unshift({ resultId, headline });
  recentVisuals.length = Math.min(recentVisuals.length, 8);
  renderRecentList();
}

function renderRecentList() {
  const list = document.getElementById('viz-rail-recent');
  if (!list) return;
  list.replaceChildren();
  for (const r of recentVisuals) {
    const item = document.createElement('button');
    item.className = 'viz-rail-recent-item';
    item.textContent = r.headline || r.resultId;
    item.addEventListener('click', () => openInPanel(r.resultId));
    list.appendChild(item);
  }
  if (!recentVisuals.length) {
    const none = document.createElement('div');
    none.className = 'viz-rail-empty';
    none.textContent = 'Ask a question to see visuals here.';
    list.appendChild(none);
  }
}

// Card kind labels are words a reader would say, not producer enum values.
const KIND_LABELS = {
  figure_map: 'Map', map: 'Map', leaflet: 'Map',
  time_series: 'Time series', timeseries: 'Time series',
  stat_tiles: 'Key figures', stats: 'Key figures',
  hierarchy: 'Breakdown', matrix: 'Matrix', table: 'Records',
  dashboard: 'Dashboard', chart: 'Chart', summary: 'Summary',
  result: 'Figure',
  // TR-VIS-0008: reading words, like every other kind label.
  validated_decision_map: 'Decision map', validation_summary: 'How this was tested',
};
function humanKind(kind) {
  const key = String(kind || '').toLowerCase().replace(/-/g, '_');
  return KIND_LABELS[key] || key.replace(/_/g, ' ').replace(/^./, (c) => c.toUpperCase());
}

// ---- inline hydration ------------------------------------------------------
const hydrating = new Set();

async function hydrateSlot(slot) {
  const resultId = slot.dataset.resultId;
  const hydrationKey = resultId + ':' + (slot.dataset.revision || '');
  if (!resultId || hydrating.has(hydrationKey)) return;
  hydrating.add(hydrationKey);
  // `c` is used far below (layer/rows fetches) — it must outlive this try.
  let c;
  let envelope;
  try {
    c = await resolveClient();
    if (!c) return;
    // A session switch can race the endpoint change: an attempt against the
    // outgoing endpoint may hang rather than fail. Time-box it so the guard is
    // released and a later sweep retries against the right endpoint.
    envelope = await Promise.race([
      c.result(resultId),
      new Promise((_, rej) => setTimeout(() => rej(new Error('visual result timeout')), 12000)),
    ]);
  } catch {
    slot.classList.add('viz-inline-unavailable');
    slot.textContent = 'Visual unavailable for this endpoint.';
    return;
  } finally {
    // In-flight guard only: the .hydrated class is what stops re-hydration of
    // finished slots, so the key must never outlive the attempt.
    hydrating.delete(hydrationKey);
  }
  slot.classList.add('hydrated');
  slot.replaceChildren();

  const card = document.createElement('figure');
  card.className = 'viz-inline-card';
  const primaryV = (envelope.visuals || []).find((v) => v.priority === 'primary') || (envelope.visuals || [])[0];
  const titlebar = document.createElement('div');
  titlebar.className = 'viz-card-titlebar';
  const tname = document.createElement('span');
  tname.textContent = humanKind((primaryV && (primaryV.view || primaryV.visual_type)) || 'result');
  titlebar.appendChild(tname);
  const topen = document.createElement('span');
  topen.className = 'viz-card-titlebar-open';
  topen.textContent = '⤢';
  titlebar.appendChild(topen);
  card.appendChild(titlebar);
  const headRow = document.createElement('figcaption');
  headRow.className = 'viz-inline-head';
  if (envelope.site && envelope.site.synthetic) {
    const ribbon = document.createElement('span');
    ribbon.className = 'viz-synthetic-ribbon';
    ribbon.textContent = 'Synthetic test data';
    headRow.appendChild(ribbon);
  }
  const head = document.createElement('span');
  head.className = 'viz-inline-headline';
  head.textContent = cleanText((envelope.answer && envelope.answer.headline) || '');
  headRow.appendChild(head);
  card.appendChild(headRow);

  // TR-VIS-0003: a model-read subject is disclosed beside the claim it shaped.
  renderSubjectDisclosure(card, envelope);

  const canvas = document.createElement('div');
  canvas.className = 'viz-inline-canvas';
  card.appendChild(canvas);

  const visuals = envelope.visuals || [];
  const primary = visuals.find((v) => v.priority === 'primary') || visuals[0] || null;
  if (primary) {
    const layerData = new Map();
    await Promise.all((primary.layers || []).map(async (layer) => {
      if (!layer.data_ref) return;
      try {
        const parsed = await c.fetchData(layer.data_ref, envelope);
        if (parsed) layerData.set(layer.layer_id, parsed);
      } catch { /* partial inline render is fine; the panel retries */ }
    }));
    // TR-VIS-0008: on a decision map, a selection may only be drawn behind a
    // passed test. The producer still ships the layer; we refuse to style it.
    const decisionMap = isDecisionMapVisual(primary);
    const suppressSelection = decisionMap && !selectionAllowed(envelope);
    const frame = renderVisual(canvas, primary, layerData, {
      rawUrl: (ref) => {
        if (ref && ref.kind === 'result_data' && ref.handle) {
          return `${c.base}/results/${encodeURIComponent(envelope.result_id)}/data/${encodeURIComponent(ref.handle)}`;
        }
        return null;
      },
      // Inline cards are previews: clicks open the panel rather than drilling.
      onDrill: () => openInPanel(resultId),
      suppressSelection,
    });
    if (decisionMap) {
      // Toggles hide marks only — no recomputation, no producer value changes,
      // and the validation panel below is never hidden by them.
      const toggleHost = document.createElement('div');
      toggleHost.className = 'viz-inline-toggles';
      card.appendChild(toggleHost);
      // Every producer layer stays toggleable — on a failed test the evidence
      // is exactly what must remain readable; it is the *selection styling*
      // that is withheld (suppressSelection above), not the values.
      renderLayerToggles(toggleHost, primary, frame, {});
      // "How this map was tested" sits with the map, in the reading flow —
      // not behind the audit link, not inside an accordion.
      renderValidationPanel(card, envelope, { compact: true });
    }
  }

  // Rows are the evidence: show the first few under the answer rather than
  // behind a click, with the full set one tap away in the panel.
  const drill = (primary && (primary.drilldowns || [])[0])
    || ((envelope.visuals || []).flatMap((v) => v.drilldowns || [])[0]);
  if (drill && drill.data_ref) {
    try {
      const rows = await c.fetchData(drill.data_ref, envelope);
      if (Array.isArray(rows) && rows.length) {
        const box = document.createElement('div');
        box.className = 'viz-inline-rows';
        const cap = document.createElement('div');
        cap.className = 'viz-inline-rows-cap';
        cap.textContent = drill.label || 'Records behind this';
        box.appendChild(cap);
        // Inline preview: a readable handful of columns, not the whole schema —
        // the panel keeps every column and every row.
        const cols = Object.keys(rows[0] || {});
        const preferred = cols.filter((c) => !/^(properties|geometry|cell_id|uncertainty)/i.test(c));
        const shown = preferred.slice(0, 5);
        const slim = rows.slice(0, 4).map((r) => Object.fromEntries(shown.map((c) => [c, r[c]])));
        renderTable(box, slim, { limit: 4 });
        if (cols.length > shown.length) {
          const note = document.createElement('div');
          note.className = 'viz-inline-rows-more';
          note.textContent = `${shown.length} of ${cols.length} columns shown`;
          box.appendChild(note);
        }
        if (rows.length > 4) {
          const more = document.createElement('div');
          more.className = 'viz-inline-rows-more';
          more.textContent = `${rows.length.toLocaleString('en-IN')} rows in total — open to read them all`;
          box.appendChild(more);
        }
        card.appendChild(box);
      }
    } catch { /* rows stay in the panel */ }
  }

  // TR-VIS-0002: statements the producing capability says must accompany this
  // result, in its own words. Rendered as the floor under the model's prose —
  // visibly the source's voice, not the assistant's.
  // Some required statements are addressed to the answering model ("Name the
  // survey each figure came from: …") rather than to the reader. Those are a
  // producer instruction, not a fact to display; show only reader-facing ones.
  const MODEL_DIRECTED = /^(name|say|state|mention|report|include|use|avoid|do not|don't)\b/i;
  const required = (envelope.required_statements || [])
    .filter((r) => r && r.statement && !MODEL_DIRECTED.test(r.statement.trim()));
  if (required.length) {
    const box = document.createElement('div');
    box.className = 'viz-required';
    const cap = document.createElement('div');
    cap.className = 'viz-required-cap';
    cap.textContent = 'What this result requires you to know';
    box.appendChild(cap);
    for (const r of required.slice(0, 4)) {
      const line = document.createElement('div');
      line.className = 'viz-required-line';
      if (r.id) line.dataset.statementId = r.id;
      const mark = document.createElement('span');
      mark.className = 'viz-required-mark';
      mark.textContent = '§';
      line.appendChild(mark);
      const txt = document.createElement('span');
      txt.textContent = r.statement;
      if (r.why) txt.title = r.why;
      line.appendChild(txt);
      box.appendChild(line);
    }
    card.appendChild(box);
  }

  // The honesty lives with the number, not one click away: surface the
  // serious caveats on the card, keep the rest for the panel.
  const requiredText = new Set(required.map((r) => (r.statement || '').slice(0, 60)));
  const serious = (envelope.limitations || [])
    .filter((l) => l && (l.severity === 'error' || l.severity === 'warning') && l.message)
    .filter((l) => !requiredText.has(l.message.slice(0, 60)));
  if (serious.length) {
    const lims = document.createElement('div');
    lims.className = 'viz-inline-limits';
    for (const l of serious.slice(0, 2)) {
      const row = document.createElement('div');
      row.className = `viz-inline-limit viz-sev-${l.severity}`;
      const icon = document.createElement('span');
      icon.textContent = l.severity === 'error' ? '⛔' : '⚠';
      row.appendChild(icon);
      const msg = document.createElement('span');
      msg.textContent = l.message;
      row.appendChild(msg);
      lims.appendChild(row);
    }
    if (serious.length > 2) {
      const more = document.createElement('div');
      more.className = 'viz-inline-limit-more';
      more.textContent = serious.length - 2 === 1
        ? 'One more caveat — open to read it'
        : `${serious.length - 2} more caveats — open to read them`;
      lims.appendChild(more);
    }
    card.appendChild(lims);
  }

  const actions = (envelope.actions || []).filter((a) => a && a.label).slice(0, 4);
  if (actions.length) {
    const row = document.createElement('div');
    row.className = 'viz-inline-actions';
    for (const a of actions) {
      const chip = document.createElement('button');
      chip.className = 'viz-action-chip';
      chip.type = 'button';
      chip.dataset.kind = a.kind || 'follow_up';
      chip.textContent = subjectActionLabel(a) || a.label;
      chip.addEventListener('click', (ev) => {
        ev.stopPropagation();          // a next step, not a request to expand
        const input = document.getElementById('message');
        if (!input) return;
        input.value = a.label;
        input.dispatchEvent(new Event('input', { bubbles: true }));
        const form = input.closest('form') || document.getElementById('chat-form');
        if (form) (form.requestSubmit ? form.requestSubmit() : form.submit());
      });
      row.appendChild(chip);
    }
    card.appendChild(row);
  }

  const foot = document.createElement('div');
  foot.className = 'viz-inline-foot';
  const meta = document.createElement('span');
  const n = visuals.length;
  meta.textContent = `${envelope.site?.label || ''}${n > 1 ? ` · ${n} views` : ''}`;
  foot.appendChild(meta);
  const footRight = document.createElement('span');
  footRight.className = 'viz-inline-foot-right';
  // TR-VIS-0005: reporting is always discoverable, and prominent when the
  // result is blocked, failed or carries an error-severity limitation.
  const troubled = envelope.status === 'failed' || envelope.status === 'blocked'
    || (envelope.limitations || []).some((l) => l && l.severity === 'error');
  const report = document.createElement('button');
  report.type = 'button';
  report.className = 'viz-report-btn' + (troubled ? ' viz-report-prominent' : '');
  report.textContent = 'Report a problem';
  report.addEventListener('click', (ev) => { ev.stopPropagation(); openReportDialog(); });
  footRight.appendChild(report);
  const open = document.createElement('button');
  open.className = 'viz-inline-open';
  open.type = 'button';
  open.textContent = 'Open ↗';
  footRight.appendChild(open);
  foot.appendChild(footRight);
  card.appendChild(foot);

  card.addEventListener('click', (ev) => {
    // Any click on the card (including marks and Open) expands to the panel.
    ev.preventDefault();
    openInPanel(resultId);
  });
  slot.appendChild(card);
  noteRecentVisual(resultId, cleanText((envelope.answer && envelope.answer.headline) || ''));
  noteConsultedSources(slot, envelope);
  ensureContextRail();
}

function scanForSlots(rootNode) {
  const scope = rootNode && rootNode.querySelectorAll ? rootNode : document;
  for (const slot of scope.querySelectorAll('.viz-inline:not(.hydrated):not(.viz-inline-unavailable)')) {
    hydrateSlot(slot);
  }
}

const observer = new MutationObserver((mutations) => {
  for (const m of mutations) {
    for (const node of m.addedNodes) {
      if (node.nodeType !== 1) continue;
      if (node.matches && node.matches('.viz-inline')) hydrateSlot(node);
      else if (node.matches && node.matches('.msg.msg-user')) noteNewQuestion();
      else if (node.querySelectorAll) scanForSlots(node);
    }
  }
});
observer.observe(document.body, { childList: true, subtree: true });

// Live-stream markers arrive before the final bubble exists; retry shortly.
window.addEventListener('idli-visual-result', () => {
  setTimeout(() => scanForSlots(document), 600);
  setTimeout(() => scanForSlots(document), 2500);
});

// History loads render in bulk; sweep once after load and on session switches.
setTimeout(() => { scanForSlots(document); ensureContextRail(); }, 3000);

// A session switch may change the endpoint behind the visuals: drop the cached
// client and re-hydrate whatever the restored history brought with it. Two
// sweeps because history rendering is not instant.
export function noteSessionSwitch() {
  client = null; clientEndpointUrl = null;
  recentVisuals.length = 0;
  consulted.idx = -1; consulted.sources = [];
  removeContextRail(); // rebuilt against the new session's endpoint
  const sweep = () => {
    // Slots that failed against the previous endpoint get another chance.
    for (const el of document.querySelectorAll('.viz-inline.viz-inline-unavailable')) {
      el.classList.remove('viz-inline-unavailable');
      el.textContent = '';
    }
    scanForSlots(document);
    ensureContextRail();
  };
  setTimeout(sweep, 1200);
  setTimeout(sweep, 3500);
}
document.addEventListener('click', (ev) => {
  if (ev.target.closest && ev.target.closest('.list-item[data-session-id]')) {
    noteSessionSwitch();
  }
}, true);

// ---- TR-VIS-0005: reviewable public problem report -------------------------
// The producer owns redaction, immutable drafts and the destination repository;
// this dialog owns the description, the public warning, the full preview and
// the explicit confirmation. Nothing is published without the second click,
// and only the visible user/assistant conversation is ever included.
let reportOverlay = null;

function visibleTranscript() {
  const out = [];
  for (const msg of document.querySelectorAll('#chat-history .msg')) {
    const role = msg.classList.contains('msg-user') ? 'user'
      : msg.classList.contains('msg-ai') ? 'assistant' : null;
    if (!role) continue;
    const body = msg.querySelector('.body');
    const text = body ? body.innerText.trim() : '';
    if (text) out.push({ role, content: text.slice(0, 6000) });
  }
  return out.slice(-60);
}

function reportEl(tag, cls, text) {
  const el = document.createElement(tag);
  if (cls) el.className = cls;
  if (text !== undefined) el.textContent = text;
  return el;
}

export async function openReportDialog() {
  const c = await resolveClient();
  if (!reportOverlay) {
    reportOverlay = reportEl('div', 'viz-report-overlay');
    reportOverlay.addEventListener('click', (ev) => {
      if (ev.target === reportOverlay) closeReportDialog();
    });
    document.body.appendChild(reportOverlay);
  }
  reportOverlay.replaceChildren();
  reportOverlay.classList.add('on');
  const box = reportEl('div', 'viz-report-box');
  box.setAttribute('role', 'dialog');
  box.setAttribute('aria-label', 'Report a problem');
  reportOverlay.appendChild(box);
  const head = reportEl('div', 'viz-report-head');
  head.appendChild(reportEl('span', 'viz-report-title', 'Report a problem'));
  const x = reportEl('button', 'viz-panel-close', '×');
  x.addEventListener('click', closeReportDialog);
  head.appendChild(x);
  box.appendChild(head);

  if (!c) {
    box.appendChild(reportEl('p', 'viz-report-note',
      'Reporting is not available for this conversation — no site service is connected.'));
    return;
  }

  // ---- step 1: describe
  box.appendChild(reportEl('p', 'viz-report-note',
    'This files a public issue in the repository this site is configured to use. '
    + 'Nothing is published until you review the exact issue text and confirm.'));
  const desc = document.createElement('textarea');
  desc.className = 'viz-report-desc';
  desc.placeholder = 'What went wrong, in your own words? (required)';
  desc.rows = 5;
  box.appendChild(desc);
  const inc = reportEl('label', 'viz-report-include');
  const check = document.createElement('input');
  check.type = 'checkbox';
  check.checked = true;
  inc.appendChild(check);
  inc.appendChild(document.createTextNode(' Include this conversation (visible messages only)'));
  box.appendChild(inc);
  const err = reportEl('div', 'viz-report-error');
  box.appendChild(err);
  const row = reportEl('div', 'viz-report-actions');
  const draftBtn = reportEl('button', 'viz-report-primary', 'Preview the public issue');
  const cancelBtn = reportEl('button', 'viz-report-secondary', 'Cancel');
  cancelBtn.addEventListener('click', closeReportDialog);
  row.appendChild(cancelBtn);
  row.appendChild(draftBtn);
  box.appendChild(row);

  draftBtn.addEventListener('click', async () => {
    err.textContent = '';
    const description = desc.value.trim();
    if (!description) { err.textContent = 'A description is required.'; desc.focus(); return; }
    draftBtn.disabled = true;
    draftBtn.textContent = 'Drafting…';
    let draft;
    try {
      const sessions = await getSessions();
      const sessionId = (sessions.getCurrentSessionId && sessions.getCurrentSessionId())
        || window.location.hash.replace('#', '') || 'unknown';
      const res = await fetch(`${c.base}/feedback/draft`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          description,
          include_conversation: check.checked,
          transcript: check.checked ? visibleTranscript() : [],
        }),
      });
      if (!res.ok) throw new Error(`draft failed (${res.status})`);
      draft = await res.json();
    } catch (e) {
      err.textContent = 'Could not draft the report: ' + (e.message || e);
      draftBtn.disabled = false;
      draftBtn.textContent = 'Preview the public issue';
      return;
    }
    renderReportPreview(box, c, draft);
  });
}

function renderReportPreview(box, c, draft) {
  box.replaceChildren();
  const head = reportEl('div', 'viz-report-head');
  head.appendChild(reportEl('span', 'viz-report-title', 'Review before publishing'));
  const x = reportEl('button', 'viz-panel-close', '×');
  x.addEventListener('click', closeReportDialog);
  head.appendChild(x);
  box.appendChild(head);
  box.appendChild(reportEl('p', 'viz-report-warning',
    draft.public_warning || `This will create a public issue in ${draft.repository}.`));
  const metaBits = [`Repository: ${draft.repository}`];
  if (draft.include_conversation) {
    metaBits.push(`${draft.conversation_messages} conversation message${draft.conversation_messages === 1 ? '' : 's'} included`);
  } else {
    metaBits.push('conversation not included');
  }
  box.appendChild(reportEl('div', 'viz-report-meta', metaBits.join(' · ')));
  box.appendChild(reportEl('div', 'viz-report-preview-title', draft.title || ''));
  const body = reportEl('pre', 'viz-report-preview-body', draft.body || '');
  box.appendChild(body);
  const err = reportEl('div', 'viz-report-error');
  box.appendChild(err);
  const row = reportEl('div', 'viz-report-actions');
  const cancel = reportEl('button', 'viz-report-secondary', 'Cancel');
  cancel.addEventListener('click', closeReportDialog);
  const submit = reportEl('button', 'viz-report-primary', 'Publish this issue');
  row.appendChild(cancel);
  row.appendChild(submit);
  box.appendChild(row);
  submit.addEventListener('click', async () => {
    err.textContent = '';
    submit.disabled = true;
    submit.textContent = 'Publishing…';
    let out;
    try {
      const res = await fetch(`${c.base}/feedback/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ report_id: draft.report_id, confirmed: true }),
      });
      if (!res.ok) throw new Error(`submit failed (${res.status})`);
      out = await res.json();
    } catch (e) {
      err.textContent = 'Could not publish: ' + (e.message || e);
      submit.disabled = false;
      submit.textContent = 'Publish this issue';
      return;
    }
    box.replaceChildren();
    const h2 = reportEl('div', 'viz-report-head');
    h2.appendChild(reportEl('span', 'viz-report-title', 'Report sent'));
    const x2 = reportEl('button', 'viz-panel-close', '×');
    x2.addEventListener('click', closeReportDialog);
    h2.appendChild(x2);
    box.appendChild(h2);
    if (out.status === 'ready_for_browser_confirmation' && out.url) {
      box.appendChild(reportEl('p', 'viz-report-note',
        'One more step: the issue opens pre-filled in your browser — press its Submit button there.'));
      window.open(out.url, '_blank', 'noopener');
      const link = reportEl('a', 'viz-report-link', 'Open the pre-filled issue');
      link.href = out.url; link.target = '_blank'; link.rel = 'noopener';
      box.appendChild(link);
    } else if (out.url) {
      box.appendChild(reportEl('p', 'viz-report-note', 'Thank you — the issue is public:'));
      const link = reportEl('a', 'viz-report-link', out.url);
      link.href = out.url; link.target = '_blank'; link.rel = 'noopener';
      box.appendChild(link);
    } else {
      box.appendChild(reportEl('p', 'viz-report-note', 'The report was recorded.'));
    }
    const done = reportEl('div', 'viz-report-actions');
    const ok = reportEl('button', 'viz-report-primary', 'Done');
    ok.addEventListener('click', closeReportDialog);
    done.appendChild(ok);
    box.appendChild(done);
  });
}

function closeReportDialog() {
  if (reportOverlay) reportOverlay.classList.remove('on');
}
