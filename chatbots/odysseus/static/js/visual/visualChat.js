// visualChat.js — inline visuals in the stock Idlisseus chat.
// chatRenderer/chat.js insert `.viz-inline[data-result-id]` slots wherever an
// assistant message carried an idli-result marker (live, final and history).
// This module hydrates each slot into a compact visual card inside the bubble,
// and opens the full interactive view (Leaflet maps, drill-down, explain,
// estimate, actions) in a side panel when the card is clicked.
// The old full-screen takeover is retired; the classic chat layout is the UI.

import { VisualStage } from './visualStage.js';
import { VisualClient } from './visualData.js';
import { renderVisual, renderTable } from './visualRenderers.js';

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
      const val = ['records', 'count', 'value', 'estimate', 'effort']
        .map((k) => props && props[k]).find((v) => v !== undefined);
      const where = markId || 'this location';
      input.value = `In result ${envelope.result_id}: what is behind the ${what}`
        + (val !== undefined ? ` value of ${val}` : '') + ` at ${where}?`
        + ' Which source rows produced it?';
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

// ---- right context rail (EcoData "Current Context" inspiration) ------------
let contextRail = null;
const recentVisuals = [];

async function ensureContextRail() {
  const c = await resolveClient();
  if (!c) { removeContextRail(); return; }
  if (!contextRail) {
    contextRail = document.createElement('aside');
    contextRail.id = 'viz-context-rail';
    contextRail.setAttribute('aria-label', 'Site context');
    document.body.appendChild(contextRail);
    document.body.classList.add('viz-context-open');
  }
  let human = null;
  try {
    const hr = await fetch(`${c.base}/headline-stats`);
    if (hr.ok) human = await hr.json();
  } catch { /* optional: packs may not publish plain-worded stats */ }
  try {
    const env = await c.query('site-orientation', {}, '');
    contextRail.replaceChildren();
    const h = document.createElement('div');
    h.className = 'viz-rail-heading';
    h.textContent = 'Current context';
    contextRail.appendChild(h);
    const site = document.createElement('div');
    site.className = 'viz-rail-site';
    site.textContent = (env.site && env.site.label) || '';
    contextRail.appendChild(site);
    if (env.site && env.site.synthetic) {
      const ribbon = document.createElement('span');
      ribbon.className = 'viz-synthetic-ribbon';
      ribbon.textContent = 'Synthetic test data';
      contextRail.appendChild(ribbon);
    }
    const primary = (env.visuals || [])[0] || {};
    const denoms = (primary.summary && primary.summary.denominators) || {};
    const tiles = document.createElement('div');
    tiles.className = 'viz-rail-tiles';
    let entries;
    let details = null;
    if (human && Array.isArray(human.stats) && human.stats.length) {
      entries = human.stats.slice(0, 4).map((s) => [s.label, s.value]);
      details = new Map(human.stats.slice(0, 4).map((s) => [s.label, s.detail || '']));
    } else {
      entries = Object.entries(denoms).slice(0, 3);
      if (!denoms.sources && !denoms.source_versions) {
        entries.push(['sources', ((env.audit || {}).source_versions || []).length]);
      }
    }
    // No meter bars: the tiles hold unlike quantities, and a shared scale would
    // imply a comparison the numbers don't support.
    for (const [k, v] of entries) {
      const tile = document.createElement('div');
      tile.className = 'viz-rail-tile';
      const val = document.createElement('div');
      val.className = 'viz-rail-tile-value';
      val.textContent = typeof v === 'number' ? v.toLocaleString('en-IN') : String(v);
      tile.appendChild(val);
      const lab = document.createElement('div');
      lab.className = 'viz-rail-tile-label';
      lab.textContent = String(k).replace(/_/g, ' ');
      if (details && details.get(k)) lab.title = details.get(k);
      tile.appendChild(lab);
      tiles.appendChild(tile);
    }
    contextRail.appendChild(tiles);
    // Data streams — which sources this site is actually reading (mockup's
    // "connected sensors", but honest: it lists real source versions).
    const sources = (env.audit || {}).source_versions || [];
    if (sources.length) {
      const sh = document.createElement('div');
      sh.className = 'viz-rail-heading';
      sh.textContent = 'Data streams';
      contextRail.appendChild(sh);
      const streams = document.createElement('div');
      streams.className = 'viz-rail-streams';
      for (const s of sources.slice(0, 6)) {
        const row = document.createElement('div');
        row.className = 'viz-rail-stream';
        const dot = document.createElement('span');
        dot.className = 'viz-rail-stream-dot';
        row.appendChild(dot);
        const name = document.createElement('span');
        name.className = 'viz-rail-stream-name';
        const raw = typeof s === 'string' ? s : (s.title || s.source_id || '');
        name.textContent = String(raw).replace(/^syn-/, '').replace(/[-_]/g, ' ');
        name.title = String(raw);
        row.appendChild(name);
        // Every listed stream is indexed by definition; the dot says so without
        // repeating the same word down the column.
        streams.appendChild(row);
      }
      contextRail.appendChild(streams);
    }

    const rh = document.createElement('div');
    rh.className = 'viz-rail-heading';
    rh.textContent = 'Recent visuals';
    contextRail.appendChild(rh);
    const list = document.createElement('div');
    list.className = 'viz-rail-recent';
    list.id = 'viz-rail-recent';
    contextRail.appendChild(list);
    renderRecentList();
  } catch {
    removeContextRail(); // endpoint has no visual plane
  }
}

export function refreshContext() {
  client = null; clientEndpointUrl = null;
  recentVisuals.length = 0;
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
  const c = await resolveClient();
  if (!c) { hydrating.delete(hydrationKey); return; }
  let envelope;
  try {
    envelope = await c.result(resultId);
  } catch {
    slot.classList.add('viz-inline-unavailable');
    slot.textContent = 'Visual unavailable for this endpoint.';
    return;
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
  head.textContent = (envelope.answer && envelope.answer.headline) || '';
  headRow.appendChild(head);
  card.appendChild(headRow);

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
    renderVisual(canvas, primary, layerData, {
      rawUrl: (ref) => {
        if (ref && ref.kind === 'result_data' && ref.handle) {
          return `${c.base}/results/${encodeURIComponent(envelope.result_id)}/data/${encodeURIComponent(ref.handle)}`;
        }
        return null;
      },
      // Inline cards are previews: clicks open the panel rather than drilling.
      onDrill: () => openInPanel(resultId),
    });
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
      chip.textContent = a.label;
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
  const open = document.createElement('button');
  open.className = 'viz-inline-open';
  open.type = 'button';
  open.textContent = 'Open ↗';
  foot.appendChild(open);
  card.appendChild(foot);

  card.addEventListener('click', (ev) => {
    // Any click on the card (including marks and Open) expands to the panel.
    ev.preventDefault();
    openInPanel(resultId);
  });
  slot.appendChild(card);
  noteRecentVisual(resultId, (envelope.answer && envelope.answer.headline) || '');
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
document.addEventListener('click', (ev) => {
  if (ev.target.closest && ev.target.closest('.list-item[data-session-id]')) {
    client = null; clientEndpointUrl = null; // endpoint may change with the session
    recentVisuals.length = 0;
    setTimeout(() => { scanForSlots(document); ensureContextRail(); }, 2500);
  }
}, true);
