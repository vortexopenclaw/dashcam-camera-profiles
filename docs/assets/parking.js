/* Plain-JavaScript parking measurement explorer. No accounts or external dependencies. */
(() => {
  'use strict';
  const categories = {
    'impact-sleep': ['Impact-triggered sleep', 'No pre-event footage while asleep. Compare wake delay as well as standby power.'],
    'buffered-event': ['Buffered event recording', 'Monitoring retains pre-event footage; event-recording draw is a separate state.'],
    'unbuffered-event': ['Unbuffered event recording', 'Recording begins after detection, without a pre-event buffer.'],
    'time-lapse': ['Time-lapse recording', 'Ongoing frame capture, not sleeping standby.'],
    'low-bitrate': ['Low-bitrate recording', 'Ongoing recording at a reduced bitrate, not sleeping standby.'],
    radar: ['Radar-triggered', 'Radar detection and recording behavior depend on the tested configuration.'],
    hybrid: ['Hybrid behavior', 'Check the source for how detection, buffering, and sleep interact.'],
    unknown: ['Function not established', 'The available evidence does not establish the recording functionality.']
  };
  const defaults = { q: '', brand: '', category: '', channels: '', tester: '', state: 'parked', sort: 'watts', prototype: true, superseded: false, provisional: false };
  const numeric = value => typeof value === 'number' && Number.isFinite(value) && value >= 0;
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const shown = value => value === null || value === undefined || value === '' ? 'Not reported' : Array.isArray(value) ? (value.length ? value.join(', ') : 'Not reported') : String(value);
  const valueWithUnit = (value, unit) => numeric(value) ? `${value} ${unit}` : 'Not reported';
  const rangeValue = (row, key, unit, format = String) => numeric(row[key]) ? `${format(row[key])} ${unit}` : numeric(row[`${key}_min`]) && numeric(row[`${key}_max`]) ? `${format(row[`${key}_min`])}–${format(row[`${key}_max`])} ${unit} (range)` : 'Not reported';
  const watts = row => {
    const derived = row.power_is_derived === true;
    const value = rangeValue(row, 'power_w', 'W', derived ? value => String(Number(value.toFixed(2))) : String);
    return value === 'Not reported' ? 'Watts unknown' : `${derived ? 'Approximately ' : ''}${value}`;
  };
  const wake = row => `${rangeValue(row, 'wake_seconds', 's')}${row.wake_camera ? ` · ${row.wake_camera}` : ''}`;
  const channels = row => numeric(row.installed_channels) ? `${row.installed_channels} installed channel${row.installed_channels === 1 ? '' : 's'}` : 'Installed channels not reported';
  const electrical = row => `${rangeValue(row, 'current_ma', 'mA')} · ${numeric(row.voltage_v) ? `${row.voltage_v} V` : 'Voltage not reported'}`;
  const category = row => Object.hasOwn(categories, row.category) ? row.category : 'unknown';
  const provisional = row => row.review_status === 'needs-review' || /double\s*check\s+video/i.test(row.notes || '');
  const safeURL = raw => { try { const url = new URL(raw); return ['https:', 'http:'].includes(url.protocol) ? url.href : ''; } catch { return ''; } };
  const link = (url, text) => safeURL(url) ? `<a href="${escape(safeURL(url))}" target="_blank" rel="noopener noreferrer">${escape(text)} <span aria-label="opens in new tab">↗</span></a>` : escape(text);
  function readState(search) {
    const params = new URLSearchParams(search);
    const state = { ...defaults };
    for (const key of Object.keys(defaults)) {
      if (params.has(key)) state[key] = typeof defaults[key] === 'boolean' ? params.get(key) === '1' : params.get(key);
    }
    if (!['parked', 'all', 'monitoring', 'time-lapse', 'continuous', 'event-recording'].includes(state.state)) state.state = defaults.state;
    if (!['watts', 'model', 'wake'].includes(state.sort)) state.sort = defaults.sort;
    if (state.category && !Object.hasOwn(categories, state.category)) state.category = defaults.category;
    return { state, selected: [...new Set(params.getAll('compare'))].slice(0, 4) };
  }
  function query(state, selected) {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(state)) if (value !== defaults[key]) params.set(key, typeof value === 'boolean' ? (value ? '1' : '0') : value);
    for (const id of selected) params.append('compare', id);
    return params.toString();
  }
  function filterRows(rows, state) {
    const search = state.q.trim().toLocaleLowerCase();
    return rows.filter(row => (!search || `${row.brand} ${row.model}`.toLocaleLowerCase().includes(search))
      && (!state.brand || row.brand === state.brand)
      && (!state.category || category(row) === state.category)
      && (!state.channels || String(row.installed_channels) === state.channels)
      && (!state.tester || row.tester === state.tester)
      && (state.state === 'all' || (state.state === 'parked' ? ['monitoring', 'time-lapse', 'continuous'].includes(row.state) : row.state === state.state))
      && (state.prototype || row.test_status !== 'prototype')
      && (state.superseded || !row.superseded)
      && (state.provisional || !provisional(row)));
  }
  function sortRows(rows, sort) {
    return [...rows].sort((a, b) => {
      if (sort !== 'model') {
        const key = sort === 'wake' ? 'wake_seconds' : 'power_w';
        const av = numeric(a[key]) ? a[key] : Infinity;
        const bv = numeric(b[key]) ? b[key] : Infinity;
        if (av !== bv) return av < bv ? -1 : 1;
      }
      return `${a.brand} ${a.model}`.localeCompare(`${b.brand} ${b.model}`) || String(a.id).localeCompare(String(b.id));
    });
  }
  function csvCell(value) {
    let text = value == null ? '' : typeof value === 'object' ? JSON.stringify(value) : String(value);
    if (/^[\s\u0000-\u001f]*[=+@-]/.test(text) || /^[\t\r\n]/.test(text)) text = `'${text}`;
    return `"${text.replace(/"/g, '""')}"`;
  }
  function toCSV(rows) {
    const fields = [...new Set(['id', 'brand', 'model', 'category', 'mode_name', 'state', 'power_w', 'current_ma', 'voltage_v', 'installed_channels', 'active_channels', 'ir', 'firmware', 'wake_seconds', 'prebuffer_s', 'tester', 'source_url', 'image_url', 'date', 'notes', 'test_status', 'review_status', 'power_path', 'superseded', ...rows.flatMap(row => Object.keys(row))])];
    return '\uFEFF' + [fields.map(csvCell).join(','), ...rows.map(row => fields.map(field => csvCell(row[field])).join(','))].join('\r\n');
  }
  const api = { readState, query, filterRows, sortRows, toCSV, csvCell, safeURL, provisional, rangeValue, watts, wake };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (typeof document === 'undefined') return;
  const $ = id => document.getElementById(id);
  let rows = [], sources = [], state = defaults, selected = new Set(), ready = false;
  const parsed = readState(location.search);
  state = parsed.state;
  selected = new Set(parsed.selected);
  const form = $('parking-filters');
  // Provisional data is an explicit opt-in, separate from prototype hardware.
  const provisionalLabel = document.createElement('label');
  provisionalLabel.innerHTML = '<input id="filter-provisional" name="provisional" type="checkbox"> Include provisional data';
  form.querySelector('.parking-toggles').append(provisionalLabel);
  function controlsFromState() {
    for (const key of Object.keys(defaults)) {
      const control = $(`filter-${key}`);
      if (typeof defaults[key] === 'boolean') control.checked = state[key];
      else control.value = state[key];
    }
  }
  function syncURL() {
    const search = query(state, [...selected]);
    history.replaceState(null, '', `${location.pathname}${search ? `?${search}` : ''}${location.hash}`);
  }
  const tags = row => `${row.test_status === 'prototype' ? '<span class="parking-tag warning">Prototype</span>' : ''}${row.test_status === 'unknown' || !row.test_status ? '<span class="parking-tag">Hardware status unknown</span>' : ''}${provisional(row) ? '<span class="parking-tag warning">Provisional · needs review</span>' : ''}${row.superseded ? '<span class="parking-tag warning">Superseded</span>' : ''}`;
  function facts(row) {
    const entries = [
      ['Source mode name', shown(row.mode_name)], ['Measured state', shown(row.state)],
      ['Installed channels', shown(row.installed_channels)], ['Active views', shown(row.active_channels)], ['Interior IR', shown(row.ir)],
      ['Firmware', shown(row.firmware)], ['Connectivity', shown(row.connectivity)], ['Current at stated voltage', `${rangeValue(row, 'current_ma', 'mA')} / ${valueWithUnit(row.voltage_v, 'V')}`], ['Measurement statistic', shown(row.measurement_statistic)],
      ['Impact to first frame / camera scope', wake(row)], ['Reported startup (method unconfirmed)', valueWithUnit(row.reported_startup_seconds, 's')],
      ['Impact pre-event buffer', valueWithUnit(row.prebuffer_impact_s, 's')], ['Motion pre-event buffer', valueWithUnit(row.prebuffer_motion_s, 's')],
      ...(!numeric(row.prebuffer_impact_s) && !numeric(row.prebuffer_motion_s) ? [['Pre-event buffer (source unqualified)', valueWithUnit(row.prebuffer_s, 's')]] : []),
      ['Power path / measured side', shown(row.power_path)], ['Tester / source date', `${shown(row.tester)} / ${shown(row.date)}`], ['Hardware / review status', `${shown(row.test_status)} / ${provisional(row) ? 'needs-review' : 'verified'}`]
    ];
    return `<dl class="parking-facts">${entries.map(([key, value]) => `<div><dt>${escape(key)}</dt><dd>${escape(value)}</dd></div>`).join('')}</dl><p class="parking-muted"><strong>Caveats:</strong> ${escape(row.notes || 'No additional caveats transcribed. See the original source for test conditions.')}${row.source_power_precision ? ` ${escape(row.source_power_precision)}` : ''}</p>${link(row.source_url, 'Original source')}${row.image_url ? ` · ${link(row.image_url, 'Measurement image')}` : ''}`;
  }
  function measurement(row, scale) {
    return `<article class="parking-measurement" data-id="${escape(row.id)}"><div class="parking-row"><div><label class="parking-select"><input type="checkbox" data-select="${escape(row.id)}" ${selected.has(row.id) ? 'checked' : ''} aria-label="Compare ${escape(`${row.brand} ${row.model}, ${row.mode_name}, ${row.state}, ${row.id}`)}"><span>Compare measurement</span></label><strong class="parking-model">${escape(row.brand)} ${escape(row.model)}</strong><small>${escape(row.mode_name)} · ${escape(row.state)}</small>${tags(row)}</div><div><span class="parking-watts">${escape(watts(row))}</span><div class="parking-track${numeric(row.power_w) ? '' : ' unknown'}" aria-hidden="true">${numeric(row.power_w) ? `<span style="width:${scale ? row.power_w / scale * 100 : 0}%"></span>` : ''}</div><small>${escape(electrical(row))}</small></div><div><strong>${escape(channels(row))}</strong><small>Active views: ${escape(shown(row.active_channels))}</small><small>Firmware: ${escape(shown(row.firmware))} · IR: ${escape(shown(row.ir))}</small><small>Tester: ${escape(shown(row.tester))}</small><small>Connectivity: ${escape(shown(row.connectivity))}</small><small>Power path / measured side: ${escape(shown(row.power_path))}</small><small>Wake to first frame: ${escape(wake(row))}</small>${numeric(row.reported_startup_seconds) ? `<small>Reported startup: ${escape(valueWithUnit(row.reported_startup_seconds, 's'))} (method unconfirmed)</small>` : ''}</div></div><details><summary>Configuration, source &amp; caveats</summary>${facts(row)}</details></article>`;
  }
  function renderComparison(visible) {
    const visibleIds = new Set(visible.map(row => row.id));
    $('selection-count').textContent = `${selected.size} / 4`;
    $('clear-comparison').disabled = selected.size === 0;
    $('comparison-cards').innerHTML = [...selected].map(id => {
      const row = rows.find(item => item.id === id);
      if (!row) return `<article class="comparison-card"><h4>Measurement unavailable</h4><p>${escape(id)}</p><p class="parking-muted">This ID is not in the current dataset.</p><button data-remove="${escape(id)}">Remove selection</button></article>`;
      return `<article class="comparison-card"><h4>${escape(row.brand)} ${escape(row.model)}</h4><span class="parking-tag${visibleIds.has(id) ? '' : ' warning'}">${visibleIds.has(id) ? 'In current results' : 'Outside current filters'}</span>${tags(row)}<span class="parking-watts">${escape(watts(row))}</span><p>${escape(categories[category(row)][0])}<br>${escape(row.mode_name)} · ${escape(row.state)}</p>${facts(row)}<button data-remove="${escape(id)}">Remove selection</button></article>`;
    }).join('');
  }
  function render() {
    if (!ready) return;
    const visible = filterRows(rows, state);
    const scale = Math.max(0, ...visible.filter(row => numeric(row.power_w)).map(row => row.power_w));
    $('result-count').textContent = `${visible.length} of ${rows.length} measurements · ${visible.filter(row => numeric(row.power_w)).length} with known watts · ${selected.size} selected`;
    $('download-csv').disabled = visible.length === 0;
    $('parking-results').innerHTML = visible.length ? Object.entries(categories).map(([key, [title, note]]) => {
      const group = sortRows(visible.filter(row => category(row) === key), state.sort);
      return group.length ? `<section class="parking-group" aria-label="${escape(title)}"><h3>${escape(title)} <span class="parking-tag">${group.length} measurements</span></h3><p class="parking-muted">${escape(note)}</p>${group.map(row => measurement(row, scale)).join('')}</section>` : '';
    }).join('') : '<p class="parking-empty">No measurements match these filters. Try another function or reset the filters. Missing measurements are not zero-power results.</p>';
    renderComparison(visible);
    syncURL();
  }
  controlsFromState();
  form.addEventListener('submit', event => event.preventDefault());
  form.addEventListener('input', () => {
    for (const key of Object.keys(defaults)) state[key] = typeof defaults[key] === 'boolean' ? $(`filter-${key}`).checked : $(`filter-${key}`).value;
    render();
  });
  form.addEventListener('reset', event => { event.preventDefault(); state = { ...defaults }; controlsFromState(); render(); });
  $('parking-results').addEventListener('change', event => {
    const control = event.target.closest('[data-select]');
    if (!control) return;
    const id = control.dataset.select;
    if (control.checked && selected.size >= 4) { control.checked = false; $('action-status').textContent = 'Choose up to four measurements. Remove a selection before adding another.'; return; }
    if (control.checked) selected.add(id); else selected.delete(id);
    // Keep the active checkbox and open details in place for keyboard users.
    renderComparison(filterRows(rows, state));
    $('result-count').textContent = `${filterRows(rows, state).length} of ${rows.length} measurements · ${selected.size} selected`;
    $('action-status').textContent = `${selected.size} of 4 comparison slots selected.`;
    syncURL();
  });
  $('comparison-cards').addEventListener('click', event => {
    const button = event.target.closest('[data-remove]');
    if (!button) return;
    selected.delete(button.dataset.remove); render(); $(selected.size ? 'clear-comparison' : 'copy-link').focus();
  });
  $('clear-comparison').addEventListener('click', () => { selected.clear(); render(); $('copy-link').focus(); });
  $('copy-link').addEventListener('click', async () => {
    syncURL();
    try { await navigator.clipboard.writeText(location.href); $('action-status').textContent = 'Comparison link copied, including filters and selected measurements.'; }
    catch { $('action-status').textContent = 'Copy the current address from your browser to share these filters and selections.'; }
  });
  $('download-csv').addEventListener('click', () => {
    const url = URL.createObjectURL(new Blob([toCSV(sortRows(filterRows(rows, state), state.sort))], { type: 'text/csv;charset=utf-8' }));
    const anchor = document.createElement('a'); anchor.href = url; anchor.download = 'parking-measurements-filtered.csv'; anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    $('action-status').textContent = 'Filtered CSV downloaded with all measurement metadata. Formula-like text is escaped for spreadsheet safety.';
  });
  window.addEventListener('popstate', () => { const restored = readState(location.search); state = restored.state; selected = new Set(restored.selected); controlsFromState(); render(); });
  function populate(key, values, label = value => value) {
    const control = $(`filter-${key}`);
    const available = [...new Set(values.filter(value => value !== null && value !== undefined && value !== '').map(String))].sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
    if (state[key] && !available.includes(state[key])) available.push(state[key]);
    for (const value of available) control.add(new Option(label(value), value));
  }
  function coverageText(value) {
    if (value === null || value === undefined) return '';
    if (Array.isArray(value)) return value.map(coverageText).filter(Boolean).join(' · ');
    if (typeof value === 'object') return Object.entries(value).map(([key, item]) => `${key.replace(/_/g, ' ')}: ${coverageText(item)}`).join(' · ');
    return String(value);
  }
  async function load() {
    try {
      const response = await fetch('data/parking-measurements.json');
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      if (data.version !== 1 || !Array.isArray(data.measurements)) throw new Error('Unsupported dataset format');
      rows = data.measurements;
      sources = Array.isArray(data.sources) ? data.sources : [];
      populate('brand', rows.map(row => row.brand)); populate('category', rows.map(category), key => categories[key][0]);
      populate('channels', rows.map(row => row.installed_channels)); populate('tester', rows.map(row => row.tester));
      controlsFromState();
      $('dataset-meta').textContent = `${rows.length} source-backed measurements · ${sources.length} indexed sources · Dataset updated ${shown(data.updated)}`;
      $('coverage-notes').textContent = coverageText(data.coverage) || 'Coverage is incomplete. Refer to the indexed sources for extraction status and limitations.';
      $('source-index').innerHTML = sources.length ? sources.map(source => {
        const url = source.source_url || source.url;
        const count = source.measurement_count ?? rows.filter(row => row.source_url === url).length;
        return `<li>${link(url, source.title || source.label || source.post_id || url || 'Source')}<small>${escape(source.tester || source.author || 'Tester not specified')} · ${escape(source.status || source.review_status || 'Indexed')} · ${escape(count)} transcribed measurements${count === 0 ? ' (no transcribed measurements)' : ''}</small><small>${escape(coverageText(source.notes || source.reason || ''))}</small>${Array.isArray(source.images) && source.images.length ? `<details><summary>Original source images (${source.images.length})</summary>${source.images.map((image, index) => link(typeof image === 'string' ? image : image.url, `Original image ${index + 1}`)).join(' · ')}</details>` : ''}</li>`;
      }).join('') : '<li>No source index entries are available yet. Measurement details link directly to original sources.</li>';
      ready = true; render();
    } catch (error) {
      $('dataset-meta').textContent = 'Dataset currently unavailable.';
      $('result-count').textContent = 'Measurements could not be loaded.';
      $('parking-results').innerHTML = '<div class="parking-empty"><p>The measurement dataset is unavailable or not yet published. No estimated or example measurements are shown.</p><button id="retry-load" type="button">Retry loading</button></div>';
      $('retry-load').addEventListener('click', load);
      $('source-index').innerHTML = '<li>Source index unavailable until the dataset can be loaded.</li>';
      renderComparison([]);
    } finally { $('parking-results').setAttribute('aria-busy', 'false'); }
  }
  load();
})();
