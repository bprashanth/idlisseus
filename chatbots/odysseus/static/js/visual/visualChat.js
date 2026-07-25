// visualChat.js — glue between the chat app and the visual stage.
// Listens for idli-result markers surfaced by chat.js/chatRenderer.js, enters
// visual mode, fetches envelopes through the odysseus proxy, and renders chapters.
// Also provides ambient site orientation when a conversation starts on a
// visual-capable endpoint, and a toggle back to the classic chat view.

import { VisualStage } from './visualStage.js';
import { VisualClient } from './visualData.js';

let stage = null;
let client = null;
let clientEndpointUrl = null;
let toggleBtn = null;
let lastQuestion = '';
const seenResults = new Set();
const seenRevisions = new Map(); // result_id -> revision

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

function ensureStage() {
  if (stage) return stage;
  const container = document.getElementById('chat-container');
  if (!container) return null;
  stage = new VisualStage(container, {
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
    onAction: (action) => {
      // Actions become ordinary audited chat turns: fill the composer and send.
      const input = document.getElementById('message');
      if (!input) return;
      const text = action.kind === 'follow_up' || action.kind === 'run_capability'
        ? action.label
        : `${action.label}`;
      input.value = text;
      input.dispatchEvent(new Event('input', { bubbles: true }));
      const form = input.closest('form') || document.getElementById('chat-form');
      if (form) form.requestSubmit ? form.requestSubmit() : form.submit();
    },
  });
  ensureToggle();
  ensureFloatingComposer();
  ensureHistoryButton();
  return stage;
}

// ---- floating, draggable, corner-snapping composer -------------------------
const CORNERS = ['br', 'bl', 'tr', 'tl'];

function ensureFloatingComposer() {
  const bar = document.querySelector('.chat-input-bar');
  if (!bar || bar.dataset.vizFloating) return;
  bar.dataset.vizFloating = '1';
  bar.classList.add('viz-float-composer');
  const saved = localStorage.getItem('viz-chatbox-corner');
  bar.dataset.corner = CORNERS.includes(saved) ? saved : 'br';

  const handle = document.createElement('div');
  handle.className = 'viz-float-handle';
  handle.title = 'Drag to move — snaps to a corner';
  handle.setAttribute('aria-label', 'Move chat box');
  handle.innerHTML = '<span></span><span></span><span></span>';
  bar.prepend(handle);

  let drag = null;
  handle.addEventListener('pointerdown', (ev) => {
    const r = bar.getBoundingClientRect();
    drag = { dx: ev.clientX - r.left, dy: ev.clientY - r.top };
    bar.classList.add('viz-float-dragging');
    handle.setPointerCapture(ev.pointerId);
    ev.preventDefault();
  });
  handle.addEventListener('pointermove', (ev) => {
    if (!drag) return;
    bar.style.left = `${ev.clientX - drag.dx}px`;
    bar.style.top = `${ev.clientY - drag.dy}px`;
    bar.style.right = 'auto';
    bar.style.bottom = 'auto';
  });
  const drop = (ev) => {
    if (!drag) return;
    drag = null;
    bar.classList.remove('viz-float-dragging');
    const r = bar.getBoundingClientRect();
    const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
    const corner = `${cy < window.innerHeight / 2 ? 't' : 'b'}${cx < window.innerWidth / 2 ? 'l' : 'r'}`;
    bar.style.left = bar.style.top = bar.style.right = bar.style.bottom = '';
    bar.dataset.corner = corner;
    localStorage.setItem('viz-chatbox-corner', corner);
  };
  handle.addEventListener('pointerup', drop);
  handle.addEventListener('pointercancel', drop);
}

// ---- landing history overlay ----------------------------------------------
let historyPanel = null;

async function buildHistoryPanel() {
  if (historyPanel) { historyPanel.remove(); historyPanel = null; }
  const sessions = await getSessions();
  const list = (sessions.getSessions && sessions.getSessions()) || [];
  historyPanel = document.createElement('div');
  historyPanel.className = 'viz-history-panel';
  const head = document.createElement('div');
  head.className = 'viz-history-head';
  const title = document.createElement('span');
  title.textContent = 'Recent chats';
  head.appendChild(title);
  const close = document.createElement('button');
  close.className = 'viz-panel-close';
  close.textContent = '×';
  close.setAttribute('aria-label', 'Close history');
  close.addEventListener('click', () => historyPanel.classList.remove('on'));
  head.appendChild(close);
  historyPanel.appendChild(head);
  const body = document.createElement('div');
  body.className = 'viz-history-body';
  for (const s of list.slice(0, 24)) {
    const card = document.createElement('button');
    card.className = 'viz-history-card';
    const name = document.createElement('span');
    name.className = 'viz-history-name';
    name.textContent = s.name || s.id;
    card.appendChild(name);
    const meta = document.createElement('span');
    meta.className = 'viz-history-meta';
    meta.textContent = s.model || '';
    card.appendChild(meta);
    card.addEventListener('click', () => {
      // Delegate to the app's own session handler (hidden sidebar item).
      const item = document.querySelector(`.list-item[data-session-id="${s.id}"]`);
      if (item) item.click();
      historyPanel.classList.remove('on');
    });
    body.appendChild(card);
  }
  historyPanel.appendChild(body);
  document.body.appendChild(historyPanel);
  return historyPanel;
}

function ensureHistoryButton() {
  if (document.getElementById('viz-history-btn')) return;
  const btn = document.createElement('button');
  btn.id = 'viz-history-btn';
  btn.className = 'viz-mode-toggle viz-history-btn';
  btn.type = 'button';
  btn.textContent = 'Chats';
  btn.addEventListener('click', async () => {
    const panel = await buildHistoryPanel();
    panel.classList.add('on');
  });
  document.body.appendChild(btn);
}

function ensureToggle() {
  if (toggleBtn) return;
  toggleBtn = document.createElement('button');
  toggleBtn.id = 'visual-mode-toggle';
  toggleBtn.className = 'viz-mode-toggle';
  toggleBtn.type = 'button';
  toggleBtn.textContent = 'Chat view';
  toggleBtn.setAttribute('aria-pressed', 'true');
  document.body.classList.add('visual-had-stage');
  toggleBtn.addEventListener('click', () => {
    const on = document.body.classList.toggle('visual-mode');
    toggleBtn.textContent = on ? 'Chat view' : 'Visual view';
    toggleBtn.setAttribute('aria-pressed', String(on));
    if (stage) stage.root.style.display = on ? '' : 'none';
  });
  document.body.appendChild(toggleBtn);
}

async function handleResultMarker(payload) {
  const resultId = payload && payload.result_id;
  if (!resultId) return;
  const revision = payload.revision || 1;
  if (seenResults.has(resultId) && (seenRevisions.get(resultId) || 1) >= revision) return;
  const c = await resolveClient();
  if (!c) return;
  let envelope;
  try {
    envelope = await c.result(resultId);
  } catch (err) {
    console.warn('visual result fetch failed', resultId, err);
    return;
  }
  seenResults.add(resultId);
  seenRevisions.set(resultId, envelope.revision || revision);
  const st = ensureStage();
  if (!st) return;
  let chapter = st.chapterFor(envelope);
  if (!chapter) {
    const q = (envelope.question?.original || lastQuestion || '').split(/===\s*File:/)[0].trim();
    chapter = st.addChapter(q);
  }
  await chapter.setEnvelope(envelope);
}

// Ambient orientation: when a chat runs on a visual-capable endpoint, open the
// stage with the site-orientation capability before any question is asked.
let ambientTriedFor = null;
async function maybeAmbientOrientation() {
  const c = await resolveClient();
  if (!c || ambientTriedFor === clientEndpointUrl) return;
  ambientTriedFor = clientEndpointUrl;
  try {
    const caps = await c.capabilities();
    const list = caps.capabilities || caps || [];
    const hasOrientation = (Array.isArray(list) ? list : []).some(
      (x) => (x.capability_id || x.id) === 'site-orientation' && (x.availability || 'ready') === 'ready'
    );
    if (!hasOrientation) return;
    const envelope = await c.query('site-orientation', {}, '');
    if (!envelope || !envelope.result_id) return;
    seenResults.add(envelope.result_id);
    seenRevisions.set(envelope.result_id, envelope.revision || 1);
    const st = ensureStage();
    if (!st) return;
    const chapter = st.addChapter(envelope.site?.label || 'Orientation');
    await chapter.setEnvelope(envelope);
  } catch {
    // Endpoint has no visual plane — classic chat continues untouched.
  }
}

window.addEventListener('idli-visual-result', (ev) => {
  handleResultMarker(ev.detail);
});

// Track the question text for chapter headers.
document.addEventListener('submit', (ev) => {
  const form = ev.target;
  if (!(form instanceof HTMLFormElement)) return;
  const input = form.querySelector('#message') || document.getElementById('message');
  if (input && input.value.trim()) {
    // Chapter headers show the question, never inlined file payloads.
    lastQuestion = input.value.split(/===\s*File:/)[0].trim();
  }
  // A new turn on a possibly-new endpoint: refresh the ambient check lazily.
  setTimeout(maybeAmbientOrientation, 400);
}, true);

// First load: give the session list a moment to hydrate, then try orientation.
setTimeout(maybeAmbientOrientation, 2500);

// Watch for endpoint changes (new chat on another model, session switch):
// maybeAmbientOrientation self-dedups per endpoint, so a light poll is enough.
setInterval(async () => {
  const sessions = await getSessions();
  const url = sessions.getCurrentEndpointUrl && sessions.getCurrentEndpointUrl();
  if (url && url !== ambientTriedFor) maybeAmbientOrientation();
}, 4000);
