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
  return stage;
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
