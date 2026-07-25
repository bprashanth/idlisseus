// visualChat.js — inline visuals in the stock Idlisseus chat.
// chatRenderer/chat.js insert `.viz-inline[data-result-id]` slots wherever an
// assistant message carried an idli-result marker (live, final and history).
// This module hydrates each slot into a compact visual card inside the bubble,
// and opens the full interactive view (Leaflet maps, drill-down, explain,
// estimate, actions) in a side panel when the card is clicked.
// The old full-screen takeover is retired; the classic chat layout is the UI.

import { VisualStage } from './visualStage.js';
import { VisualClient } from './visualData.js';
import { renderVisual } from './visualRenderers.js';

let client = null;
let clientEndpointUrl = null;

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
  title.textContent = 'Visual detail';
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
  await chapter.setEnvelope(envelope);
}

// ---- inline hydration ------------------------------------------------------
const hydrating = new Set();

async function hydrateSlot(slot) {
  const resultId = slot.dataset.resultId;
  if (!resultId || hydrating.has(resultId + ':' + (slot.dataset.revision || ''))) return;
  hydrating.add(resultId + ':' + (slot.dataset.revision || ''));
  const c = await resolveClient();
  if (!c) { hydrating.delete(resultId); return; }
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
setTimeout(() => scanForSlots(document), 3000);
document.addEventListener('click', (ev) => {
  if (ev.target.closest && ev.target.closest('.list-item[data-session-id]')) {
    client = null; clientEndpointUrl = null; // endpoint may change with the session
    setTimeout(() => scanForSlots(document), 2500);
  }
}, true);
