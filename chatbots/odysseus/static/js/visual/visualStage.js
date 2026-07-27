// visualStage.js — the visual-first conversation stage.
// A conversation is a scrollable sequence of chapters; one question → one chapter.
// Each chapter renders an idli-result/1 envelope: primary visual full-bleed,
// caption card with headline + evidence chips, supporting visuals as a rail,
// structured limitations, capability-derived action chips, and a slide-in
// evidence panel for drill-downs. Revisions replace in place — no jumps.

import { renderVisual, renderTable, tooltip } from './visualRenderers.js';
import { evidenceColor, evidenceLabel, formatNumber, cleanText } from './visualTheme.js';

export class VisualStage {
  // host: element the stage mounts into. opts.fetchData(ref) -> Promise<parsed payload>
  // opts.onAction(action, envelope) — action chip clicked.
  constructor(host, opts) {
    this.host = host;
    this.opts = opts || {};
    this.root = document.createElement('div');
    this.root.className = 'viz-stage';
    this.rail = document.createElement('nav');
    this.rail.className = 'viz-chapter-rail';
    this.rail.setAttribute('aria-label', 'Chapters');
    this.root.appendChild(this.rail);
    this.scroller = document.createElement('div');
    this.scroller.className = 'viz-stage-scroller';
    this.root.appendChild(this.scroller);
    host.appendChild(this.root);
    this.chapters = [];
    this.takeover = !(opts && opts.noTakeover);
    if (this.takeover) document.body.classList.add('visual-mode');
  }

  destroy() {
    if (this.takeover) document.body.classList.remove('visual-mode');
    this.root.remove();
  }

  addChapter(question) {
    const ch = new Chapter(this, question, this.chapters.length);
    this.chapters.push(ch);
    this.scroller.appendChild(ch.node);
    this._railDot(ch);
    requestAnimationFrame(() => ch.node.scrollIntoView({ behavior: 'smooth', block: 'start' }));
    return ch;
  }

  // Find a chapter by request/result id (revision routing).
  chapterFor(envelope) {
    return this.chapters.find(
      (c) => c.resultId === envelope.result_id || c.requestId === envelope.request_id
    ) || null;
  }

  _railDot(ch) {
    const dot = document.createElement('button');
    dot.className = 'viz-rail-dot';
    dot.title = ch.question || `Chapter ${ch.index + 1}`;
    dot.setAttribute('aria-label', dot.title);
    dot.addEventListener('click', () => ch.node.scrollIntoView({ behavior: 'smooth', block: 'start' }));
    this.rail.appendChild(dot);
    ch.railDot = dot;
    // active-dot tracking
    if (!this._observer) {
      this._observer = new IntersectionObserver((entries) => {
        for (const e of entries) {
          const c = this.chapters.find((x) => x.node === e.target);
          if (c && c.railDot) c.railDot.classList.toggle('on', e.isIntersecting);
        }
      }, { root: this.scroller, threshold: 0.5 });
    }
    this._observer.observe(ch.node);
  }
}

class Chapter {
  constructor(stage, question, index) {
    this.stage = stage;
    this.question = question;
    this.index = index;
    this.resultId = null;
    this.requestId = null;
    this.revision = 0;
    this.node = document.createElement('section');
    this.node.className = 'viz-chapter';
    // question header (small, quiet — the visual is the answer)
    this.qNode = document.createElement('div');
    this.qNode.className = 'viz-chapter-question';
    this.qNode.textContent = question || '';
    this.node.appendChild(this.qNode);
    // activity ticker
    this.activityNode = document.createElement('div');
    this.activityNode.className = 'viz-activity';
    this.node.appendChild(this.activityNode);
    // main canvas
    this.canvas = document.createElement('div');
    this.canvas.className = 'viz-canvas';
    this.node.appendChild(this.canvas);
    // caption card
    this.caption = document.createElement('div');
    this.caption.className = 'viz-caption-card';
    this.node.appendChild(this.caption);
    // supporting rail
    this.supportRail = document.createElement('div');
    this.supportRail.className = 'viz-support-rail';
    this.node.appendChild(this.supportRail);
    // evidence panel host
    this.panel = null;
    this._skeleton();
  }

  _skeleton() {
    this.canvas.replaceChildren();
    const sk = document.createElement('div');
    sk.className = 'viz-skeleton';
    sk.innerHTML = '<div class="viz-skeleton-pulse"></div>';
    this.canvas.appendChild(sk);
  }

  setActivity(activity) {
    // activity: idli-activity/1 event or plain string
    const label = typeof activity === 'string' ? activity : (activity && activity.label) || '';
    const state = typeof activity === 'object' && activity ? activity.state : 'running';
    this.activityNode.replaceChildren();
    if (!label || state === 'complete') {
      this.activityNode.classList.remove('on');
      return;
    }
    this.activityNode.classList.add('on');
    const pulse = document.createElement('span');
    pulse.className = 'viz-activity-pulse';
    this.activityNode.appendChild(pulse);
    const text = document.createElement('span');
    text.textContent = label;
    this.activityNode.appendChild(text);
  }

  appendProse(markdownHtml) {
    // Streamed assistant prose lands in the caption's expandable detail area.
    if (!this.proseNode) {
      this.proseNode = document.createElement('details');
      this.proseNode.className = 'viz-caption-more';
      const sum = document.createElement('summary');
      sum.textContent = 'More';
      this.proseNode.appendChild(sum);
      this.proseBody = document.createElement('div');
      this.proseNode.appendChild(this.proseBody);
      this.caption.appendChild(this.proseNode);
    }
    this.proseBody.innerHTML = markdownHtml; // caller sanitizes via app markdown pipeline
  }

  async setEnvelope(envelope) {
    // Progressive: revisions replace content in place, keyed by result_id.
    if (envelope.revision && envelope.revision <= this.revision
        && this.resultId === envelope.result_id) return;
    this.revision = envelope.revision || 1;
    this.resultId = envelope.result_id;
    this.requestId = envelope.request_id;
    this.envelope = envelope;
    if (envelope.status === 'complete' || envelope.status === 'partial') this.setActivity('');
    await this._render();
  }

  async _render() {
    const env = this.envelope;
    const fetchData = this.stage.opts.fetchData;
    // ---- caption card
    this.caption.replaceChildren();
    if (env.site && env.site.synthetic) {
      const ribbon = document.createElement('div');
      ribbon.className = 'viz-synthetic-ribbon';
      ribbon.textContent = 'Synthetic test data';
      this.caption.appendChild(ribbon);
    }
    const head = document.createElement('h2');
    head.className = 'viz-headline';
    head.textContent = cleanText((env.answer && env.answer.headline) || '');
    this.caption.appendChild(head);
    if (env.answer && env.answer.detail) {
      const detail = document.createElement('p');
      detail.className = 'viz-detail';
      detail.textContent = cleanText(env.answer.detail);
      this.caption.appendChild(detail);
    }
    // evidence chips
    const chips = document.createElement('div');
    chips.className = 'viz-chip-row';
    for (const cls of (env.answer && env.answer.evidence_classes) || []) {
      chips.appendChild(evidenceChip(cls));
    }
    this.caption.appendChild(chips);
    // limitations
    for (const lim of env.limitations || []) {
      this.caption.appendChild(limitationBanner(lim));
    }
    // actions
    const actions = (env.actions || []).filter((a) => a && a.label);
    if (actions.length) {
      const row = document.createElement('div');
      row.className = 'viz-action-row';
      for (const a of actions) {
        const chip = document.createElement('button');
        chip.className = 'viz-action-chip';
        chip.dataset.kind = a.kind || 'follow_up';
        chip.textContent = a.label;
        chip.addEventListener('click', () => {
          if (this.stage.opts.onAction) this.stage.opts.onAction(a, env);
        });
        row.appendChild(chip);
      }
      this.caption.appendChild(row);
    }
    // provenance footer (compact, honest)
    this.caption.appendChild(provenanceFooter(env, () => this._openAudit()));
    if (this.proseNode) this.caption.appendChild(this.proseNode);

    // ---- visuals
    const visuals = env.visuals || [];
    const primary = visuals.find((v) => v.priority === 'primary') || visuals[0] || null;
    let supporting = visuals.filter((v) => v !== primary && v.priority !== 'audit');

    this.canvas.replaceChildren();
    this.node.classList.remove('viz-primary-map', 'viz-primary-chart', 'viz-chapter-split');
    if (!primary) {
      // Text-only answer: the caption *is* the content; show it centered.
      this.node.classList.add('viz-chapter-textonly');
    } else {
      this.node.classList.remove('viz-chapter-textonly');
      // Variety rule: a conversation should not show the same form twice in a
      // row when the envelope offers another grammar. If this chapter's primary
      // repeats the previous chapter's, co-star a different-grammar supporting
      // visual in a split view instead of another lone repeat.
      const prev = this.stage.chapters[this.index - 1];
      const repeated = prev && prev.primaryType === primary.visual_type;
      const alt = repeated
        ? supporting.find((v) => v.visual_type !== primary.visual_type
            && (v.status === 'ready' || v.status === 'partial'))
        : null;
      this.primaryType = primary.visual_type;
      // Full-bleed maps carry the caption as an overlay (desktop); charts stack.
      if (!alt && primary.visual_type === 'map' && (primary.status === 'ready' || primary.status === 'partial')) {
        this.node.classList.add('viz-primary-map');
      }
      const layerData = await this._loadLayers(primary, fetchData);
      const frame = renderVisual(this.canvas, primary, layerData, {
        onDrill: (feature, layer, centroid) => this._openDrill(primary, feature, layer, centroid),
        rawUrl: (ref) => this.stage.opts.rawUrl && this.stage.opts.rawUrl(ref, this.envelope),
        preferLeaflet: this.stage.opts.preferLeaflet,
      });
      frame.classList.add('viz-enter');
      if (alt) {
        this.node.classList.add('viz-chapter-split');
        const altData = await this._loadLayers(alt, fetchData);
        const altFrame = renderVisual(this.canvas, alt, altData, {
          onDrill: (feature, layer, centroid) => this._openDrill(alt, feature, layer, centroid),
          rawUrl: (ref) => this.stage.opts.rawUrl && this.stage.opts.rawUrl(ref, this.envelope),
          preferLeaflet: this.stage.opts.preferLeaflet,
        });
        altFrame.classList.add('viz-enter');
        supporting = supporting.filter((v) => v !== alt);
      }
    }

    this.supportRail.replaceChildren();
    for (const v of supporting) {
      const card = document.createElement('button');
      card.className = 'viz-support-card';
      const t = document.createElement('span');
      t.className = 'viz-support-title';
      t.textContent = v.title || v.visual_type;
      card.appendChild(t);
      const s = document.createElement('span');
      s.className = 'viz-support-meta';
      s.textContent = `${v.visual_type} · ${v.status}`;
      card.appendChild(s);
      card.addEventListener('click', async () => {
        // Promote the supporting visual to the canvas (crossfade, no jump).
        this.canvas.replaceChildren();
        const data = await this._loadLayers(v, fetchData);
        const frame = renderVisual(this.canvas, v, data, {
          onDrill: (feature, layer, centroid) => this._openDrill(v, feature, layer, centroid),
          rawUrl: (ref) => this.stage.opts.rawUrl && this.stage.opts.rawUrl(ref, this.envelope),
          preferLeaflet: this.stage.opts.preferLeaflet,
        });
        frame.classList.add('viz-enter');
      });
      this.supportRail.appendChild(card);
    }
  }

  async _loadLayers(visual, fetchData) {
    const layerData = new Map();
    await Promise.all((visual.layers || []).map(async (layer) => {
      if (!layer.data_ref) return;
      try {
        const parsed = await fetchData(layer.data_ref, this.envelope);
        if (parsed) layerData.set(layer.layer_id, parsed);
      } catch (err) {
        console.warn('visual layer fetch failed', layer.layer_id, err);
      }
    }));
    return layerData;
  }

  async _openDrill(visual, feature, layer, centroid) {
    const drills = (visual.drilldowns || []);
    const props = (feature && feature.properties) || {};
    if (this.stage.opts.onMarkClick) {
      const preId = props.event_id || props.source_row || props.cell_id || props.location_id
        || (centroid ? `at:${centroid.lat.toFixed(5)}:${centroid.lon.toFixed(5)}` : '');
      this.stage.opts.onMarkClick({ visual, layer, props, markId: preId, envelope: this.envelope });
    }
    const panel = this._panel();
    panel.title.textContent = layer.legend?.label || evidenceLabel(layer.evidence_class);
    panel.body.replaceChildren();
    // "Why this?" — instant deterministic lineage plus a narrated chat explanation.
    // Identity: explicit ids first; otherwise the clicked location names the mark
    // (at:<lat>:<lon>) so the explain service resolves the SAME cell the user
    // clicked — never a silent fallback to a different mark.
    const markId = props.event_id || props.source_row || props.cell_id || props.location_id
      || (centroid ? `at:${centroid.lat.toFixed(5)}:${centroid.lon.toFixed(5)}` : '');
    const whyRow = document.createElement('div');
    whyRow.className = 'viz-why-row';
    const whyBtn = document.createElement('button');
    whyBtn.className = 'viz-action-chip';
    whyBtn.textContent = 'Why this value?';
    whyBtn.addEventListener('click', () => this._showLineage(panel, visual, layer, markId, whyBtn));
    whyRow.appendChild(whyBtn);
    const askBtn = document.createElement('button');
    askBtn.className = 'viz-action-chip';
    askBtn.textContent = 'Explain in chat';
    askBtn.addEventListener('click', () => {
      const what = layer.legend?.label || layer.layer_id;
      const where = markId || props.label || props.event_date || 'the largest mark in the layer';
      const q = `Explain how the ${what} value at mark ${where} (layer ${layer.layer_id}) in result `
        + `${this.resultId} was computed — which source rows and what aggregation.`;
      if (this.stage.opts.onAction) {
        this.stage.opts.onAction({ action_id: 'explain', kind: 'follow_up', label: q }, this.envelope);
      }
    });
    whyRow.appendChild(askBtn);
    const estBtn = document.createElement('button');
    estBtn.className = 'viz-action-chip viz-estimate-chip';
    estBtn.textContent = 'Estimate here…';
    estBtn.addEventListener('click', () => this._openEstimate(panel, layer, markId, props));
    whyRow.appendChild(estBtn);
    panel.body.appendChild(whyRow);
    // Clicked mark first: its own facts, no black box.
    const factRows = Object.keys(props).map((k) => ({ field: k.replace(/_/g, ' '), value: props[k] }));
    if (factRows.length) renderTable(panel.body, factRows);
    // Then the declared drilldown rows, filtered client-side where an obvious key matches.
    for (const d of drills) {
      const h = document.createElement('h3');
      h.className = 'viz-panel-subhead';
      h.textContent = d.label || 'Rows';
      panel.body.appendChild(h);
      try {
        let rows = await this.stage.opts.fetchData(d.data_ref, this.envelope);
        if (Array.isArray(rows)) {
          const keys = ['source_row', 'event_id', 'location_id'];
          const key = keys.find((k) => props[k] !== undefined && rows[0] && rows[0][k] !== undefined);
          if (key) {
            const filtered = rows.filter((r) => r[key] === props[key]);
            if (filtered.length) rows = filtered;
          }
          renderTable(panel.body, rows);
        }
      } catch (err) {
        const fail = document.createElement('div');
        fail.className = 'viz-empty-note';
        fail.textContent = 'Rows unavailable.';
        panel.body.appendChild(fail);
      }
    }
    panel.open();
  }

  async _showLineage(panel, visual, layer, markId, btn) {
    btn.disabled = true;
    const host = document.createElement('div');
    host.className = 'viz-lineage';
    panel.body.insertBefore(host, panel.body.children[1] || null);
    const explainFn = this.stage.opts.explain;
    if (!explainFn) {
      host.textContent = 'Lineage service not available on this endpoint.';
      return;
    }
    try {
      const lineage = await explainFn(this.resultId, layer.layer_id, markId, this.envelope);
      host.replaceChildren();
      // idli-explain/1: computation.statement is the plain-language aggregation;
      // source_rows are the exact contributing rows.
      const comp = lineage.computation || {};
      const capId = (lineage.capability && (lineage.capability.capability_id || lineage.capability.id))
        || lineage.capability_id;
      const capLine = document.createElement('p');
      capLine.className = 'viz-lineage-head';
      capLine.textContent = cleanText(comp.statement || lineage.summary
        || `Computed by ${capId || 'a registered capability'} over ${
          (lineage.source_versions || []).length} source version(s).`);
      host.appendChild(capLine);
      const mark = lineage.mark || {};
      if (mark.auto_selected) {
        const auto = document.createElement('p');
        auto.className = 'viz-lineage-agg';
        auto.textContent = 'Showing the layer’s largest mark (none was selected).';
        host.appendChild(auto);
      }
      const rows = lineage.source_rows || lineage.rows;
      if (Array.isArray(rows) && rows.length) {
        renderTable(host, rows, { limit: 25 });
        if (comp.truncated) {
          const t = document.createElement('p');
          t.className = 'viz-lineage-lim';
          t.textContent = `Showing ${comp.rows_returned} of ${comp.contributing_rows} contributing rows.`;
          host.appendChild(t);
        }
      }
      for (const lim of lineage.limitations || []) {
        const l = document.createElement('p');
        l.className = 'viz-lineage-lim';
        l.textContent = typeof lim === 'string' ? lim : lim.message || lim.code || '';
        host.appendChild(l);
      }
    } catch (err) {
      host.textContent = 'Lineage unavailable for this result.';
    }
  }

  _openEstimate(panel, layer, markId, props) {
    // Mini-dialog: collect what/why, then hand a structured estimation request to
    // the conversation. The system (not the user) proposes concrete approaches
    // from the pack's data, runs gates and a model, and must report confidence,
    // data used, and what would improve it.
    panel.title.textContent = 'Estimate for this cell';
    panel.body.replaceChildren();
    const form = document.createElement('div');
    form.className = 'viz-estimate-form';
    const intro = document.createElement('p');
    intro.className = 'viz-estimate-intro';
    intro.textContent = 'Say what you want estimated for this location. The system will suggest '
      + 'estimation approaches based on the data it actually has, run the checks, and state its confidence.';
    form.appendChild(intro);
    const whatLab = document.createElement('label');
    whatLab.textContent = 'What do you want to estimate?';
    const what = document.createElement('input');
    what.type = 'text';
    what.placeholder = 'e.g. fire risk, likely record density, expected wage level';
    whatLab.appendChild(what);
    form.appendChild(whatLab);
    const whyLab = document.createElement('label');
    whyLab.textContent = 'What is it for? (optional — helps pick the method)';
    const why = document.createElement('input');
    why.type = 'text';
    why.placeholder = 'e.g. planning next survey, a proposal, prioritising patrols';
    whyLab.appendChild(why);
    form.appendChild(whyLab);
    const go = document.createElement('button');
    go.className = 'viz-action-chip';
    go.textContent = 'Suggest approaches & estimate';
    go.addEventListener('click', () => {
      const target = what.value.trim();
      if (!target) { what.focus(); return; }
      const where = markId || 'this location';
      const purpose = why.value.trim();
      const q = `Estimate ${target} for the cell at ${where} in result ${this.resultId}.`
        + (purpose ? ` Purpose: ${purpose}.` : '')
        + ' First list the estimation approaches actually supported by the available data'
        + ' and pick the best one; then run it, state whether confidence is low or high and why,'
        + ' list exactly which data was used, and what additional data would most improve the estimate.';
      if (this.stage.opts.onAction) {
        this.stage.opts.onAction({ action_id: 'estimate', kind: 'run_capability', label: q }, this.envelope);
      }
      panel.node.classList.remove('on');
    });
    form.appendChild(go);
    panel.body.appendChild(form);
    what.focus();
  }

  _openAudit() {
    const env = this.envelope;
    const panel = this._panel();
    panel.title.textContent = 'Provenance & audit';
    panel.body.replaceChildren();
    const audit = env.audit || {};
    const rows = [];
    rows.push({ field: 'result id', value: env.result_id });
    rows.push({ field: 'revision', value: env.revision });
    rows.push({ field: 'status', value: env.status });
    if (audit.audit_id) rows.push({ field: 'audit id', value: audit.audit_id });
    if (audit.query_hash) rows.push({ field: 'query hash', value: audit.query_hash });
    if (env.site) rows.push({ field: 'pack digest', value: env.site.pack_digest });
    if (env.question && env.question.resolved) rows.push({ field: 'resolved question', value: env.question.resolved });
    renderTable(panel.body, rows);
    const sv = audit.source_versions || [];
    if (sv.length) {
      const h = document.createElement('h3');
      h.className = 'viz-panel-subhead';
      h.textContent = 'Source versions';
      panel.body.appendChild(h);
      renderTable(panel.body, sv.map((s) => (typeof s === 'string' ? { source: s } : s)));
    }
    panel.open();
  }

  _panel() {
    if (this.panelObj) return this.panelObj;
    const wrap = document.createElement('aside');
    wrap.className = 'viz-evidence-panel';
    wrap.setAttribute('role', 'dialog');
    wrap.setAttribute('aria-label', 'Evidence');
    const head = document.createElement('div');
    head.className = 'viz-panel-head';
    const title = document.createElement('h2');
    title.className = 'viz-panel-title';
    head.appendChild(title);
    const close = document.createElement('button');
    close.className = 'viz-panel-close';
    close.textContent = '×';
    close.setAttribute('aria-label', 'Close evidence panel');
    close.addEventListener('click', () => wrap.classList.remove('on'));
    head.appendChild(close);
    wrap.appendChild(head);
    const body = document.createElement('div');
    body.className = 'viz-panel-body';
    wrap.appendChild(body);
    this.node.appendChild(wrap);
    this.panelObj = { node: wrap, title, body, open: () => wrap.classList.add('on') };
    return this.panelObj;
  }
}

function evidenceChip(cls) {
  const chip = document.createElement('span');
  chip.className = 'viz-evidence-chip';
  chip.dataset.cls = cls;
  const dot = document.createElement('span');
  dot.className = 'viz-chip-dot';
  dot.style.setProperty('--sw', evidenceColor(cls));
  chip.appendChild(dot);
  const lab = document.createElement('span');
  lab.textContent = evidenceLabel(cls);
  chip.appendChild(lab);
  return chip;
}

function limitationBanner(lim) {
  const b = document.createElement('div');
  b.className = `viz-limitation viz-sev-${lim.severity || 'info'}`;
  const icon = document.createElement('span');
  icon.className = 'viz-lim-icon';
  icon.textContent = lim.severity === 'error' ? '⛔' : lim.severity === 'warning' ? '⚠' : 'ℹ';
  b.appendChild(icon);
  const msg = document.createElement('span');
  msg.textContent = lim.message || lim.code || '';
  b.appendChild(msg);
  return b;
}

function provenanceFooter(env, onAudit) {
  const f = document.createElement('div');
  f.className = 'viz-prov-footer';
  const site = document.createElement('span');
  site.textContent = (env.site && env.site.label) || '';
  f.appendChild(site);
  const audit = env.audit || {};
  const nSources = (audit.source_versions || []).length;
  if (nSources) {
    const s = document.createElement('span');
    s.textContent = `${nSources} source version${nSources > 1 ? 's' : ''}`;
    f.appendChild(s);
  }
  const btn = document.createElement('button');
  btn.className = 'viz-audit-link';
  btn.textContent = 'Provenance';
  btn.addEventListener('click', onAudit);
  f.appendChild(btn);
  return f;
}
