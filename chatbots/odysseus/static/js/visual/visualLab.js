// visualLab.js — fixture-driven development page for the visual stage.
// Renders every idli-result/1 contract fixture through the exact same stage code
// the live app uses. Zero backends: fixtures + payloads are static files.

import { VisualStage } from './visualStage.js';
import { fixtureFetcher } from './visualData.js';

const FIXTURE_BASE = './contracts/fixtures';
const FIXTURES = [
  '01-site-orientation', '02-observed-points', '03-coverage-effort',
  '04-empty-target-surrounding', '05-modelled-passing-gates', '06-failed-gate',
  '07-data-request', '08-time-series', '09-partial-source-outage', '10-dashboard',
  '11-model-selected-subject',
  // TR-VIS-0008 — captured from the live Valparai producer, payloads included,
  // so the validated-decision-map treatment renders with no backend running.
  '12-decision-map-hindcast-passed', '13-decision-map-hindcast-failed',
  '14-decision-map-spatial-holdout',
];

const host = document.getElementById('lab-host');
const select = document.getElementById('fixture-select');
const status = document.getElementById('lab-status');
const fetchData = fixtureFetcher(FIXTURE_BASE);

let stage = null;

function resetStage() {
  if (stage) stage.destroy();
  host.replaceChildren();
  stage = new VisualStage(host, {
    fetchData,
    onAction: (action) => {
      status.textContent = `action: ${action.action_id} (${action.kind})`;
    },
  });
}

async function loadFixture(name) {
  const res = await fetch(`${FIXTURE_BASE}/${name}.json`);
  if (!res.ok) throw new Error(`fixture ${name}: ${res.status}`);
  return res.json();
}

async function showOne(name) {
  resetStage();
  status.textContent = 'loading…';
  try {
    const envelope = await loadFixture(name);
    const ch = stage.addChapter(envelope.question?.original || name);
    await ch.setEnvelope(envelope);
    status.textContent = `${name} · status=${envelope.status} · visuals=${(envelope.visuals || []).length}`;
    window.__labReady = true;
  } catch (err) {
    status.textContent = `error: ${err.message}`;
    window.__labError = String(err);
  }
}

async function showAll() {
  resetStage();
  status.textContent = 'loading all…';
  window.__labReady = false;
  for (const name of FIXTURES) {
    try {
      const envelope = await loadFixture(name);
      const ch = stage.addChapter(envelope.question?.original || name);
      await ch.setEnvelope(envelope);
    } catch (err) {
      console.warn('fixture failed', name, err);
    }
  }
  stage.scroller.scrollTop = 0;
  status.textContent = `all ${FIXTURES.length} fixtures`;
  window.__labReady = true;
}

for (const name of FIXTURES) {
  const opt = document.createElement('option');
  opt.value = name;
  opt.textContent = name;
  select.appendChild(opt);
}
select.addEventListener('change', () => showOne(select.value));
document.getElementById('prev-btn').addEventListener('click', () => {
  select.selectedIndex = (select.selectedIndex - 1 + FIXTURES.length) % FIXTURES.length;
  showOne(select.value);
});
document.getElementById('next-btn').addEventListener('click', () => {
  select.selectedIndex = (select.selectedIndex + 1) % FIXTURES.length;
  showOne(select.value);
});
document.getElementById('theme-btn').addEventListener('click', () => {
  document.documentElement.classList.toggle('light');
  showOne(select.value); // re-render with the other palette
});
document.getElementById('all-btn').addEventListener('click', showAll);

// URL params for headless screenshots: ?fixture=NAME&theme=light|dark&all=1
const params = new URLSearchParams(location.search);
// Light is the product default; ?theme=dark still exercises the dark palette.
if (params.get('theme') === 'dark') document.documentElement.classList.remove('light');
else document.documentElement.classList.add('light');
if (params.get('all')) {
  showAll();
} else {
  const initial = params.get('fixture') || FIXTURES[0];
  select.value = FIXTURES.includes(initial) ? initial : FIXTURES[0];
  showOne(select.value);
}
