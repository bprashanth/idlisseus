// visualExplorer.js — "what does this site actually hold?"
// A browsable inventory of the active site: its datasets, the quantities each
// one carries, and the questions it can answer — all read from the site's own
// declarations, so nothing here is sector-specific. Clicking anything either
// runs it or writes the question into the composer, so exploring the data and
// asking about it are the same motion.

let panel = null;
let cache = null; // {endpointId, sources, capabilities}

const HIDE_CAPS = new Set([
  'cell-estimate-targets', 'cell-estimate-suggest', 'cell-estimate-run',
  'upload-profile', 'upload-cross-join',
]);

function humaniseToken(s) {
  return String(s || '')
    .replace(/^syn-/, '')
    .replace(/[_-]+/g, ' ')
    .replace(/\b([a-z])/g, (m, c) => c.toUpperCase())
    .replace(/\bAoi\b/g, 'area');
}

// Quantity labels still carry raw column/protocol tokens; make them readable
// without inventing meaning (underscores out, sentence case, no ids).
function humaniseLabel(s) {
  return String(s || '')
    .replace(/_/g, ' ')
    .replace(/\bin the (map )?square\b/gi, 'per square')
    .replace(/\btotal ([A-Za-z]+)\b/, (m, w) => `total ${w.toLowerCase()}`)
    .replace(/\s+/g, ' ')
    .replace(/^./, (c) => c.toUpperCase())
    .trim();
}

function fmt(v) {
  return typeof v === 'number' ? v.toLocaleString('en-IN') : String(v ?? '');
}

async function loadInventory(endpointId) {
  if (cache && cache.endpointId === endpointId) return cache;
  const base = `/api/visual/${encodeURIComponent(endpointId)}`;
  const out = { endpointId, sources: new Map(), capabilities: [] };
  try {
    const c = await fetch(`${base}/capabilities`);
    if (c.ok) {
      const d = await c.json();
      out.label = d.label || '';
      out.capabilities = (d.capabilities || []).filter(
        (x) => !HIDE_CAPS.has(x.capability_id) && (x.availability || 'ready') === 'ready'
      );
    }
  } catch { /* keep going: the inventory is still useful without it */ }
  // The estimate target catalogue doubles as a data inventory: every quantity
  // the index can serve, with its record counts and owning datasets.
  try {
    const r = await fetch(`${base}/targets`);
    if (r.ok) {
      const env = await r.json();
      const targets = env.targets || env.catalogue || [];
      for (const t of targets) {
        for (const s of (t.sources || [{ source_id: 'unknown' }])) {
          const key = s.title || s.source_id;
          if (!out.sources.has(key)) out.sources.set(key, { title: key, quantities: [], records: 0 });
          const entry = out.sources.get(key);
          const cov = t.coverage || {};
          entry.quantities.push({
            id: t.target_id,
            label: humaniseLabel(t.label || t.target_id),
            unit: t.unit || '',
            records: cov.records || 0,
            years: cov.years || null,
          });
          entry.records = Math.max(entry.records, cov.records || 0);
        }
      }
    }
  } catch { /* older packs may not offer the catalogue */ }
  cache = out;
  return out;
}

function askInChat(text) {
  const input = document.getElementById('message');
  if (!input) return;
  input.value = text;
  input.dispatchEvent(new Event('input', { bubbles: true }));
  input.focus();
  close();
}

function ensurePanel() {
  if (panel) return panel;
  panel = document.createElement('aside');
  panel.id = 'eco-explorer';
  panel.setAttribute('role', 'dialog');
  panel.setAttribute('aria-label', 'What this site holds');
  const head = document.createElement('div');
  head.className = 'viz-side-head';
  const title = document.createElement('span');
  title.className = 'viz-side-title';
  title.textContent = 'What this site holds';
  head.appendChild(title);
  const x = document.createElement('button');
  x.className = 'viz-panel-close';
  x.textContent = '×';
  x.setAttribute('aria-label', 'Close');
  x.addEventListener('click', close);
  head.appendChild(x);
  panel.appendChild(head);
  const body = document.createElement('div');
  body.className = 'eco-explorer-body';
  panel.appendChild(body);
  document.body.appendChild(panel);
  return panel;
}

export function close() {
  document.body.classList.remove('eco-explorer-open');
}

export async function openExplorer(endpointId) {
  ensurePanel();
  document.body.classList.add('eco-explorer-open');
  const body = panel.querySelector('.eco-explorer-body');
  body.replaceChildren();
  const loading = document.createElement('div');
  loading.className = 'viz-empty-note';
  loading.textContent = 'Reading the site inventory…';
  body.appendChild(loading);

  const inv = await loadInventory(endpointId);
  body.replaceChildren();

  const search = document.createElement('input');
  search.className = 'eco-explorer-search';
  search.type = 'search';
  search.placeholder = 'Filter datasets and questions…';
  body.appendChild(search);

  // ---- questions this site can answer
  if (inv.capabilities.length) {
    const h = document.createElement('div');
    h.className = 'viz-rail-heading';
    h.textContent = 'Questions this site can answer';
    body.appendChild(h);
    const wrap = document.createElement('div');
    wrap.className = 'eco-explorer-caps';
    for (const c of inv.capabilities) {
      const b = document.createElement('button');
      b.className = 'eco-explorer-cap';
      b.dataset.text = `${c.label || ''} ${c.capability_id}`.toLowerCase();
      const l = document.createElement('span');
      l.className = 'eco-explorer-cap-label';
      l.textContent = c.label || humaniseToken(c.capability_id);
      b.appendChild(l);
      b.addEventListener('click', () => askInChat(`${c.label || humaniseToken(c.capability_id)} — show me this for this site.`));
      wrap.appendChild(b);
    }
    body.appendChild(wrap);
  }

  // ---- datasets and what they carry
  const h2 = document.createElement('div');
  h2.className = 'viz-rail-heading';
  h2.textContent = `Datasets (${inv.sources.size})`;
  body.appendChild(h2);
  const list = document.createElement('div');
  list.className = 'eco-explorer-sources';
  body.appendChild(list);

  const sorted = [...inv.sources.values()].sort((a, b) => b.records - a.records);
  for (const src of sorted) {
    const det = document.createElement('details');
    det.className = 'eco-explorer-source';
    det.dataset.text = (src.title + ' ' + src.quantities.map((q) => q.label).join(' ')).toLowerCase();
    const sum = document.createElement('summary');
    const name = document.createElement('span');
    name.className = 'eco-explorer-source-name';
    name.textContent = humaniseToken(src.title);
    sum.appendChild(name);
    const count = document.createElement('span');
    count.className = 'eco-explorer-source-count';
    count.textContent = `${fmt(src.records)} records`;
    sum.appendChild(count);
    det.appendChild(sum);

    const qwrap = document.createElement('div');
    qwrap.className = 'eco-explorer-quantities';
    const seen = new Set();
    for (const q of src.quantities) {
      if (seen.has(q.label)) continue;
      seen.add(q.label);
      const row = document.createElement('button');
      row.className = 'eco-explorer-quantity';
      const ql = document.createElement('span');
      ql.textContent = q.label;
      row.appendChild(ql);
      const meta = document.createElement('span');
      meta.className = 'eco-explorer-quantity-meta';
      meta.textContent = [q.unit ? humaniseLabel(q.unit) : '', q.years ? `${q.years}` : ''].filter(Boolean).join(' · ');
      row.appendChild(meta);
      row.addEventListener('click', () => askInChat(
        `Show me ${q.label.toLowerCase()} from the ${humaniseToken(src.title).toLowerCase()} data, `
        + 'and tell me where the records are and how much I can trust them.'
      ));
      qwrap.appendChild(row);
    }
    det.appendChild(qwrap);
    list.appendChild(det);
  }

  if (!sorted.length) {
    const none = document.createElement('div');
    none.className = 'viz-empty-note';
    none.textContent = 'This site has not published a dataset inventory yet.';
    list.appendChild(none);
  }

  search.addEventListener('input', () => {
    const q = search.value.trim().toLowerCase();
    for (const el of body.querySelectorAll('[data-text]')) {
      el.style.display = !q || el.dataset.text.includes(q) ? '' : 'none';
    }
  });
}
