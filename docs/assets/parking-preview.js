/* Preview-only enhancement. The unchanged parking.js owns filters, selection, sources, and URLs. */
(() => {
  'use strict';
  const numeric = value => typeof value === 'number' && Number.isFinite(value) && value >= 0;
  function interval(row, key) {
    if (numeric(row[key])) return { min: row[key], max: row[key], range: false };
    const min = row[`${key}_min`], max = row[`${key}_max`];
    return numeric(min) && numeric(max) && max >= min ? { min, max, range: true } : null;
  }
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const metrics = [
    { key: 'power_w', title: 'Power draw', unit: 'W', note: 'Power draw for the selected parking modes, on one linear scale.' },
    { key: 'recording_delay_seconds', title: 'Recording delay after impact detection', unit: 's', note: 'Impact detection to start of recording, as described in the source chart.' },
    { key: 'reported_startup_seconds', title: 'Reported startup · method unconfirmed', unit: 's', note: "The source doesn't document the timing method. These aren't verified impact-to-first-frame measurements." },
    { key: 'wake_seconds', title: 'Impact to first recorded frame', unit: 's', note: 'Timing method documented in the source. Camera scope is shown where reported.' }
  ];
  function metricInterval(row, metric) {
    if (metric.key === 'recording_delay_seconds') return row.reported_startup_method === 'Impact detection to start of recording' ? interval(row, 'reported_startup_seconds') : null;
    if (metric.key === 'reported_startup_seconds' && row.reported_startup_method) return null;
    return interval(row, metric.key);
  }
  if (typeof module !== 'undefined' && module.exports) module.exports = { interval, metricInterval };
  if (typeof document === 'undefined') return;
  const $ = id => document.getElementById(id);
  // Show the comparison before the detailed camera picker and its filters.
  document.querySelector('.parking-explorer > .explorer-heading').before($('comparison'));
  const initial = new URL(location.href);
  const seeded = !initial.searchParams.has('compare');
  if (seeded) {
    for (const id of ['vortex-sheet-row-4', 'vortex-sheet-row-9', 'vortex-sheet-row-17']) initial.searchParams.append('compare', id);
    history.replaceState(null, '', initial);
    $('starting-comparison').hidden = false;
  }
  let rows = new Map(), photos = [], dataState = 'loading';
  const openModels = new Map();
  let view = 'charts';
  try { view = sessionStorage.getItem('parking-preview-view') === 'cameras' ? 'cameras' : 'charts'; } catch { /* Storage is optional. */ }
  function setView(next) {
    view = next;
    document.body.dataset.view = view;
    for (const button of document.querySelectorAll('[data-view-choice]')) button.setAttribute('aria-pressed', String(button.dataset.viewChoice === view));
    try { sessionStorage.setItem('parking-preview-view', view); } catch { /* Storage is optional. */ }
  }
  setView(view);
  for (const button of document.querySelectorAll('[data-view-choice]')) button.addEventListener('click', () => setView(button.dataset.viewChoice));
  // Observe only the existing app's direct render targets. Never observe our own chart/photo writes.
  const cards = $('comparison-cards');
  const results = $('parking-results');
  const modelsObserver = new MutationObserver(() => {
    for (const entry of results.querySelectorAll('.parking-model-entry')) {
      const details = entry.querySelector('.parking-model-tests');
      if (openModels.has(entry.dataset.model)) details.open = openModels.get(entry.dataset.model);
    }
  });
  modelsObserver.observe(results, { childList: true });
  results.addEventListener('toggle', event => {
    if (event.target.matches('.parking-model-tests')) openModels.set(event.target.closest('[data-model]').dataset.model, event.target.open);
  }, true);
  function safePhoto(photo) {
    // Catalog files must be local preview assets, never remote tracking URLs or traversal paths.
    return typeof photo.file === 'string' && /^assets\/parking-preview\/[a-z0-9_.-]+\.(png|webp|jpg)$/i.test(photo.file);
  }
  function decoratePhoto(card, row) {
    if (card.querySelector('.preview-photo')) return;
    const modelLabel = card.querySelector('h4').textContent;
    const match = photos.find(photo => photo.brand === row.brand && (photo.model === row.model || `${photo.brand} ${photo.model}` === modelLabel) && photo.channels === row.installed_channels && safePhoto(photo));
    const container = document.createElement('div');
    container.className = 'preview-photo';
    if (match) {
      const image = document.createElement('img');
      image.src = match.file;
      image.alt = `${card.querySelector('h4').textContent}, ${row.installed_channels}-channel kit`;
      image.width = 800;
      image.height = 480;
      image.addEventListener('error', () => { container.textContent = 'Photo not added yet'; }, { once: true });
      container.append(image);
    } else container.textContent = 'Photo not added yet';
    card.prepend(container);
  }
  function chosen() {
    return [...cards.querySelectorAll('.comparison-card')].map(card => {
      const id = card.querySelector('[data-remove]').dataset.remove;
      const row = rows.get(id);
      // Labels come from the shared renderer, preserving its aliases and expanded mode/setup copy.
      return { id, row, card, name: card.querySelector('h4').textContent,
        mode: card.querySelector(':scope > p:not(.parking-muted)')?.innerText.replace(/\n/g, ' · ') || '',
        setup: card.querySelector(':scope > p.parking-muted')?.textContent || '' };
    });
  }
  function chart(metric, selected) {
    const intervals = selected.map(item => item.row ? metricInterval(item.row, metric) : null);
    const maximum = Math.max(0, ...intervals.filter(Boolean).map(value => value.max));
    const scale = maximum > 0 ? maximum : 1;
    const number = value => String(Number(value.toPrecision(8)));
    return `<section class="preview-chart" data-metric="${metric.key}" aria-labelledby="chart-${metric.key}"><h4 id="chart-${metric.key}">${metric.title}</h4><p class="parking-muted">${metric.note}</p>${maximum > 0 ? `<div class="preview-axis" aria-hidden="true"><span>0 ${metric.unit}</span><span>${number(maximum / 2)} ${metric.unit}</span><span>${number(maximum)} ${metric.unit}</span></div>` : ''}<div class="preview-chart-rows">${selected.map((item, index) => {
      const value = intervals[index];
      const format = v => metric.key === 'power_w' && item.row.power_is_derived ? String(Number(v.toFixed(2))) : String(v);
      const label = value ? `${metric.key === 'power_w' && item.row.power_is_derived ? 'Approximately ' : ''}${format(value.min)}${value.range ? `–${format(value.max)}` : ''} ${metric.unit}${value.range ? ' (range)' : ''}` : item.row ? 'Not reported' : 'Measurement unavailable';
      const scope = metric.key === 'wake_seconds' && item.row?.wake_camera ? ` · ${item.row.wake_camera}` : '';
      const mode = metric.key === 'power_w' ? item.mode : item.mode.replace(/ · (Idle power draw|Recording an event)/g, '');
      return `<div class="preview-chart-row" data-measurement="${escape(item.id)}"><div class="preview-chart-label"><strong>${escape(item.name)}</strong><span>${escape(mode)}</span><small>${escape(item.setup + scope)}</small></div><div class="preview-reading"><strong class="preview-value">${escape(label)}</strong>${value ? `<div class="preview-bar-track" aria-hidden="true"><span class="preview-bar${value.range ? ' is-range' : ''}" data-min="${value.min}" data-max="${value.max}" style="left:${value.range ? value.min / scale * 100 : 0}%;width:${(value.range ? value.max - value.min : value.max) / scale * 100}%"></span></div>` : '<div class="preview-no-value">No bar: no numeric measurement</div>'}</div></div>`;
    }).join('')}</div></section>`;
  }
  function refresh() {
    if (dataState === 'loading') return;
    if (dataState === 'unavailable') {
      $('preview-charts').innerHTML = '<p class="parking-empty">Comparison charts are unavailable. No estimated measurements are shown. Use the dataset retry below.</p>';
      return;
    }
    const selected = chosen();
    $('starting-comparison').hidden = !seeded || selected.map(item => item.id).join(',') !== 'vortex-sheet-row-4,vortex-sheet-row-9,vortex-sheet-row-17';
    for (const item of selected) if (item.row) decoratePhoto(item.card, item.row);
    const relevantMetrics = metrics.filter(metric => metric.key === 'power_w' || selected.some(item => item.row && metricInterval(item.row, metric)));
    $('preview-charts').innerHTML = selected.length ? relevantMetrics.map(metric => chart(metric, selected)).join('') : '<p class="parking-empty">Choose measurements below to compare their power draw and timing.</p>';
  }
  const comparisonObserver = new MutationObserver(refresh);
  comparisonObserver.observe(cards, { childList: true });
  async function loadMeasurements() {
    try {
      const response = await fetch('data/parking-measurements.json', { cache: 'no-store' });
      if (!response.ok) throw new Error('Unavailable dataset');
      const data = await response.json();
      if (data.version !== 1 || !Array.isArray(data.measurements)) throw new Error('Unsupported dataset');
      rows = new Map(data.measurements.map(row => [row.id, row]));
      dataState = 'ready';
    } catch { rows = new Map(); dataState = 'unavailable'; }
    refresh();
  }
  // Keep enhancement recovery aligned with the unchanged app's native retry button.
  results.addEventListener('click', event => { if (event.target.closest('#retry-load')) loadMeasurements(); });
  fetch('assets/parking-preview/photos.json').then(response => response.ok ? response.json() : []).then(data => {
    photos = Array.isArray(data) ? data : [];
    for (const photo of cards.querySelectorAll('.preview-photo')) photo.remove();
    refresh();
  }).catch(() => { /* Missing catalog is a quiet, truthful photo placeholder. */ });
  loadMeasurements();
})();
