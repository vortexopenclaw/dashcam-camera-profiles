/* Plain-JavaScript parking measurement explorer. No accounts or external dependencies. */
(() => {
  'use strict';
  const categories = {
    'impact-sleep': ['Low-power impact detection', 'No pre-event footage while asleep. Compare wake delay as well as standby power.'],
    'buffered-event': ['Buffered parking recording', 'Pre-event footage is retained for the supported trigger.'],
    'unbuffered-event': ['Non-buffered parking recording', 'Recording begins after detection, without a pre-event buffer.'],
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
  const channels = row => numeric(row.installed_channels) ? `${row.installed_channels} channel${row.installed_channels === 1 ? '' : 's'}` : '';
  const electrical = row => `${rangeValue(row, 'current_ma', 'mA')} · ${numeric(row.voltage_v) ? `${row.voltage_v} V` : 'Voltage not reported'}`;
  const category = row => Object.hasOwn(categories, row.category) ? row.category : 'unknown';
  const provisional = row => row.review_status === 'needs-review' || /double\s*check\s+video/i.test(row.notes || '');
  const safeURL = raw => { try { const url = new URL(raw); return ['https:', 'http:'].includes(url.protocol) ? url.href : ''; } catch { return ''; } };
  const link = (url, text) => safeURL(url) ? `<a href="${escape(safeURL(url))}" target="_blank" rel="noopener noreferrer">${escape(text)} <span aria-label="opens in new tab">↗</span></a>` : escape(text);
  // Presentation only. Canonical rows, source strings and IDs stay untouched.
  const known = value => value != null && value !== '' && !/^(unknown|not applicable|not reported)$/i.test(String(value));
  const modelName = row => row.brand === 'Vueroid' && ['S1-4K', 'S1-4K Infinite'].includes(row.model) ? 'S1-4K Infinite' : row.model;
  const modelLabel = row => `${row.brand} ${modelName(row)}`;
  const condition = row => row.state === 'monitoring' ? 'Idle power draw' : row.state === 'event-recording' ? 'Recording an event' : '';
  function modeLabel(row) {
    const raw = row.mode_name || '';
    const has = pattern => pattern.test(raw);
    // Expand documented source shorthand without inferring buffering or wake behavior.
    if (has(/CD\/MD\/TLR|CD.*MD.*Time-Lapse|Time-Lapse.*Collision.*Motion/i)) return 'Collision and motion detection + time-lapse';
    if (has(/CDR?\/TL|Collision.*Time-Lapse/i)) return 'Collision detection + time-lapse';
    if (has(/CD.*MD/i)) return 'Collision and motion detection';
    if (has(/Extreme Low Power/i)) return has(/Time.?Lapse/i) ? 'Extreme low power + impact and time-lapse' : has(/Motion/i) ? 'Extreme low power + impact and motion' : 'Extreme low power';
    if (has(/\bLPID\b|low power impact/i)) return 'Low power impact detection';
    if (has(/\bLBR\b|low.?bitrate/i)) return 'Low bitrate recording';
    if (has(/\bLFR\b|Low Frame Rate/i)) return 'Low frame rate recording';
    if (has(/Impact\s*[+&]\s*Time.?Lapse/i)) return 'Impact + time-lapse';
    if (has(/^15 FPS/i)) return 'Mode awaiting review';
    if (has(/\bTLR\b|Time[ -]?Lapse/i)) return has(/Smart Time/i) ? 'Smart time-lapse' : 'Time-lapse recording';
    if (has(/\bAED\b|Auto Event Detection/i)) return 'Auto event detection';
    if (has(/\bM&I\b|Motion\/Impact|Impact\s*[+&]\s*Motion/i)) return 'Motion and impact detection';
    if (has(/Collision|\bCD\b/i)) {
      if (has(/\bPS\b|Power Saving/i)) return 'Collision detection · Power Saving';
      if (has(/\bQS\b|Quick Start/i)) return 'Collision detection · Quick Start';
      if (has(/Always On Event/i)) return 'Collision detection · Always On Event';
      return 'Collision detection';
    }
    if (has(/Energy Saving/i)) return 'Energy saving';
    if (has(/Power Saving/i)) return 'Power saving';
    if (has(/Low Power Mode/i)) return 'Low power';
    if (has(/Radar/i)) return has(/Impact/i) ? 'Radar impact detection' : 'Radar detection';
    if (has(/\bMD\b|Motion/i)) return 'Motion detection';
    if (has(/Impact/i)) return 'Impact detection';
    return 'Mode awaiting review';
  }
  function cabinIR(row) {
    const views = row.active_channels || [];
    return row.installed_channels !== 1 && views.some(view => /interior|cabin/i.test(view)) && /^(on|off|auto)$/i.test(row.ir || '') ? `Cabin IR ${row.ir}` : '';
  }
  function setup(row) {
    const raw = row.mode_name || '';
    const values = [channels(row), (row.active_channels || []).join(' + '), known(row.firmware) ? `Firmware ${row.firmware}` : '', cabinIR(row)];
    if (known(row.connectivity) && /LTE/i.test(row.connectivity)) values.push(row.connectivity);
    const settings = [raw.match(/H\.26[45]/i)?.[0], raw.match(/Wi[ -]?Fi\s+(?:Off|On)/i)?.[0], raw.match(/HDR\s+(?:Off|On)/i)?.[0], raw.match(/MicroSD|SSD/i)?.[0], raw.match(/\d+\s*fps/i)?.[0]];
    const resolution = [...new Set(raw.match(/\d{3,4}p/ig) || [])].join(' + ');
    if (resolution) settings.push(resolution);
    const nightSetting = raw.match(/\bSNV\b|\bNV\b/i);
    if (nightSetting) settings.push(`Source setting ${nightSetting[0]} (awaiting review)`);
    if (/Cam Off|only on while driving/i.test(raw)) settings.push('Some cameras off while parked (see source)');
    if (/Pre-Recording On/i.test(raw)) settings.push('Pre-recording settings (see source)');
    const sensitivity = raw.match(/Sensitivity\s*=\s*(Medium|Ultra High)/i);
    if (sensitivity) settings.push(`Sensitivity ${sensitivity[1]}`);
    if (/Suspicious Person Detection/i.test(raw)) settings.push('Suspicious person detection');
    return [...new Set([...values, ...settings].filter(Boolean))].join(' · ');
  }
  function groupModels(items) {
    const groups = new Map();
    for (const row of items) {
      const key = modelLabel(row);
      if (!groups.has(key)) groups.set(key, { label: key, rows: [] });
      groups.get(key).rows.push(row);
    }
    return [...groups.values()];
  }
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
    return rows.filter(row => (!search || `${modelLabel(row)} ${row.model}`.toLocaleLowerCase().includes(search))
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
  const api = { readState, query, filterRows, sortRows, toCSV, csvCell, safeURL, provisional, rangeValue, watts, wake, modelName, modelLabel, modeLabel, condition, setup, cabinIR, groupModels };
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
  const tags = row => `${row.test_status === 'prototype' ? '<span class="parking-tag warning">Prototype</span>' : ''}${provisional(row) ? '<span class="parking-tag warning">Provisional · needs review</span>' : ''}${row.superseded ? '<span class="parking-tag warning">Superseded</span>' : ''}`;
  function facts(row) {
    const entries = [
      ['Source model', `${row.brand} ${row.model}`], ['Source mode name', row.mode_name],
      ['Power condition', condition(row)], ['Channels', channels(row)], ['Active views', (row.active_channels || []).join(', ')],
      ['Cabin IR', cabinIR(row)], ['Firmware', row.firmware],
      ['Connectivity', known(row.connectivity) && /LTE/i.test(row.connectivity) ? row.connectivity : ''],
      ['Current at stated voltage', `${rangeValue(row, 'current_ma', 'mA')} / ${valueWithUnit(row.voltage_v, 'V')}`],
      ['Measurement statistic', row.measurement_statistic],
      ['Impact to first frame / camera scope', wake(row)], ['Reported startup (method unconfirmed)', valueWithUnit(row.reported_startup_seconds, 's')],
      ['Impact pre-event buffer', valueWithUnit(row.prebuffer_impact_s, 's')], ['Motion pre-event buffer', valueWithUnit(row.prebuffer_motion_s, 's')],
      ...(!numeric(row.prebuffer_impact_s) && !numeric(row.prebuffer_motion_s) ? [['Pre-event buffer (source unqualified)', valueWithUnit(row.prebuffer_s, 's')]] : []),
      ['Power adapter', row.power_path], ['Tester', row.tester], ['Source date', row.date], ['Measurement ID', row.id]
    ].filter(([, value]) => known(value));
    return `<dl class="parking-facts">${entries.map(([key, value]) => `<div><dt>${escape(key)}</dt><dd>${escape(value)}</dd></div>`).join('')}</dl><p class="parking-muted">${escape(row.notes || 'See the original source for test conditions.')}${row.source_power_precision ? ` ${escape(row.source_power_precision)}` : ''}</p>${link(row.source_url, 'Original source')}${row.image_url ? ` · ${link(row.image_url, 'Measurement image')}` : ''}`;
  }
  function measurement(row, scale) {
    return `<article class="parking-measurement" data-id="${escape(row.id)}"><div class="parking-row"><div><label class="parking-select"><input type="checkbox" data-select="${escape(row.id)}" ${selected.has(row.id) ? 'checked' : ''} aria-label="Compare ${escape(`${modelLabel(row)}, ${modeLabel(row)}, ${condition(row)}, ${row.id}`)}"><span>Compare measurement</span></label><strong class="parking-mode-name">${escape(modeLabel(row))}</strong>${condition(row) ? `<small>${escape(condition(row))}</small>` : ''}${tags(row)}</div><div><span class="parking-watts">${escape(watts(row))}</span><div class="parking-track${numeric(row.power_w) ? '' : ' unknown'}" aria-hidden="true">${numeric(row.power_w) ? `<span style="width:${scale ? row.power_w / scale * 100 : 0}%"></span>` : ''}</div><small>${escape(electrical(row))}</small></div><div><small>${escape(setup(row))}</small>${known(row.power_path) ? `<small>Power adapter: ${escape(row.power_path)}</small>` : ''}${known(wake(row)) ? `<small>Wake to first frame: ${escape(wake(row))}</small>` : ''}<small>Tested by ${escape(shown(row.tester))}</small></div></div><details><summary>Source details</summary>${facts(row)}</details></article>`;
  }
  function modelEntry(group, scale) {
    const modes = [...new Set(group.rows.map(modeLabel))];
    const selectedHere = group.rows.some(row => selected.has(row.id));
    return `<section class="parking-group parking-model-entry" data-model="${escape(group.label)}"><h3 class="parking-model">${escape(group.label)}</h3><p class="parking-muted">${escape(modes.join(' · '))}</p><details class="parking-model-tests" ${selectedHere ? 'open' : ''}><summary>Mode and setup choices · ${group.rows.length} measurements</summary>${group.rows.map(row => measurement(row, scale)).join('')}</details></section>`;
  }
  function renderComparison(visible) {
    const visibleIds = new Set(visible.map(row => row.id));
    $('selection-count').textContent = `${selected.size} / 4`;
    $('clear-comparison').disabled = selected.size === 0;
    $('comparison-cards').innerHTML = [...selected].map(id => {
      const row = rows.find(item => item.id === id);
      if (!row) return `<article class="comparison-card"><h4>Measurement unavailable</h4><p>${escape(id)}</p><p class="parking-muted">This ID is not in the current dataset.</p><button data-remove="${escape(id)}">Remove selection</button></article>`;
      return `<article class="comparison-card"><h4>${escape(modelLabel(row))}</h4><span class="parking-tag${visibleIds.has(id) ? '' : ' warning'}">${visibleIds.has(id) ? 'In current results' : 'Outside current filters'}</span>${tags(row)}<span class="parking-watts">${escape(watts(row))}</span><p>${escape(modeLabel(row))}${condition(row) ? `<br>${escape(condition(row))}` : ''}</p><p class="parking-muted">${escape(setup(row))}</p><details><summary>Source details</summary>${facts(row)}</details><button data-remove="${escape(id)}">Remove selection</button></article>`;
    }).join('');
  }
  function render() {
    if (!ready) return;
    const visible = filterRows(rows, state);
    const scale = Math.max(0, ...visible.filter(row => numeric(row.power_w)).map(row => row.power_w));
    $('result-count').textContent = `${visible.length} of ${rows.length} measurements · ${visible.filter(row => numeric(row.power_w)).length} with known watts · ${selected.size} selected`;
    $('download-csv').disabled = visible.length === 0;
    const groups = groupModels(sortRows(visible, state.sort));
    $('result-count').textContent = `${groups.length} models · ${visible.length} of ${rows.length} measurements · ${selected.size} selected`;
    const legacy = $('legacy-tester-note');
    legacy.hidden = !state.tester;
    legacy.textContent = state.tester ? `This shared link filters tests by ${state.tester}. Reset filters to show all testers.` : '';
    $('parking-results').innerHTML = visible.length ? groups.map(group => modelEntry(group, scale)).join('') : '<p class="parking-empty">No measurements match these filters. Try another function or reset the filters. Missing measurements aren’t zero-power results.</p>';
    renderComparison(visible);
    syncURL();
  }
  const testerControl = $('filter-tester');
  testerControl.closest('label').hidden = true;
  const testerNote = document.createElement('p');
  testerNote.id = 'legacy-tester-note';
  testerNote.className = 'parking-muted';
  testerNote.hidden = true;
  form.after(testerNote);
  // Keep legacy parameter support while removing the tester picker from the UI.
  const stateControl = $('filter-state');
  for (const option of stateControl.options) {
    if (option.value === 'monitoring') option.textContent = 'Idle power draw';
    if (option.value === 'event-recording') option.textContent = 'Recording an event';
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
    const current = filterRows(rows, state);
    $('result-count').textContent = `${groupModels(current).length} models · ${current.length} of ${rows.length} measurements · ${selected.size} selected`;
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
      $('dataset-meta').textContent = `${groupModels(rows).length} models · ${rows.length} measurements · Dataset updated ${shown(data.updated)}`;
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
