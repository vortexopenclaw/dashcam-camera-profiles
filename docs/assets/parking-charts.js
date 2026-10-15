/* Standalone chart builder. Only canonical measurement IDs enter shared state. */
(() => {
  'use strict';
  const UI = typeof window === 'undefined' ? require('./parking.js') : window.ParkingUI;
  const valid = value => typeof value === 'number' && Number.isFinite(value) && value >= 0;
  const method = 'Impact detection to start of recording';
  const metrics = {
    current: { key: 'current_ma', unit: 'mA', label: 'Measured current' },
    watts: { key: 'power_w', unit: 'W', label: 'Measured power' },
    delay: { key: 'reported_startup_seconds', unit: 's', label: 'Recording delay after impact detection' },
    wake: { key: 'wake_seconds', unit: 's', label: 'Impact to first frame' }
  };
  const seed = [4, 6, 9, 11, 15, 17, 21].map(n => `vortex-sheet-row-${n}`);
  const titles = {current:'Parking-mode current draw',watts:'Parking-mode power draw',delay:'Recording delay after impact detection',wake:'Impact to first recorded frame'};
  const families = {
    'low-power': 'Low-power parking', buffered: 'Buffered parking',
    'buffered-motion': 'Buffered motion detection', 'buffered-impact': 'Buffered impact detection',
    unbuffered: 'Non-buffered parking', radar: 'Radar parking',
    'time-lapse': 'Time-lapse parking', 'low-bitrate': 'Low-bitrate parking',
    hybrid: 'Hybrid parking', all: 'Selected parking modes'
  };
  // Categories establish behavior. Names identify triggers only, never buffering.
  // The canonical schema has no trigger flags. Trigger-specific durations are
  // stronger evidence than the documented MD, M&I and collision shorthand.
  function matchesFamily(row, family) {
    if (family === 'all') return true;
    if (row.category === 'unknown') return false;
    const raw = row.mode_name || '';
    const positive = key => valid(row[key]) && row[key] > 0;
    const hybridBuffered = row.category === 'hybrid' &&
      (positive('prebuffer_s') || positive('prebuffer_motion_s') || positive('prebuffer_impact_s') || /^Pre-Recording On;/i.test(row.notes || ''));
    const buffered = row.category === 'buffered-event' || hybridBuffered;
    const motion = positive('prebuffer_motion_s') || /\bmotion\b|\bMD\b|\bM&I\b|\bAED\b|Auto Event Detection/i.test(raw);
    const impact = positive('prebuffer_impact_s') || /\bimpact\b|\bcollision\b|\bCD\b|\bM&I\b/i.test(raw);
    switch (family) {
      case 'low-power': return ['impact-sleep', 'radar'].includes(row.category) ||
        (row.category === 'hybrid' && row.state === 'monitoring' && /\b(?:settled sleeping standby|settled sleep measurement)\b/i.test(row.notes || ''));
      case 'buffered': return buffered;
      case 'buffered-motion': return buffered && motion;
      case 'buffered-impact': return buffered && impact;
      case 'unbuffered': return ['impact-sleep', 'unbuffered-event'].includes(row.category);
      case 'radar': return row.category === 'radar';
      default: return row.category === family;
    }
  }
  const defaultCondition = family => family === 'time-lapse' ? 'time-lapse' : family === 'low-bitrate' ? 'continuous' : 'monitoring';
  const preset = metric => ({ ids: seed.filter(id => metric !== 'delay' || id !== 'vortex-sheet-row-12'), metric, sort: 'desc', highlight: '', details: false, title: titles[metric], group: 'low-power', family: 'low-power', condition: 'monitoring' });
  // Keep an existing compatible test. Otherwise use the highest documented
  // channel count, then established status, source date and stable ID. Power
  // never participates in this choice. Unknown dates do not imply recency.
  function representative(items, ids = [], family = 'all', channels = null) {
    let candidates = channels == null ? items : items.filter(row => row.installed_channels === channels);
    const retained = candidates.filter(row => ids.includes(row.id));
    if (retained.length) return retained.sort((a,b) => ids.indexOf(a.id) - ids.indexOf(b.id))[0];
    if (!candidates.length) return null;
    const highest = Math.max(0, ...candidates.map(row => Number.isInteger(row.installed_channels) ? row.installed_channels : 0));
    if (highest) candidates = candidates.filter(row => row.installed_channels === highest);
    if (family === 'low-power' && candidates.some(row => row.category === 'impact-sleep')) candidates = candidates.filter(row => row.category === 'impact-sleep');
    const status = row => Number(!!row.superseded) + Number(UI.provisional(row)) + Number(row.test_status === 'prototype');
    const date = row => /^\d{4}-\d{2}-\d{2}$/.test(row.date || '') ? row.date : '';
    return candidates.slice().sort((a,b) => status(a)-status(b) || date(b).localeCompare(date(a)) || a.id.localeCompare(b.id))[0];
  }
  function interval(row, metric) {
    if (!Object.hasOwn(metrics, metric)) return null;
    if (metric === 'delay' && row.reported_startup_method !== method) return null;
    if (row.disabled === true || row.measurement_statistic === 'disabled') return null;
    const key = metrics[metric].key;
    const min = row[`${key}_min`], max = row[`${key}_max`];
    // A partially reported or invalid range is not a scalar measurement.
    if (min != null || max != null) return valid(min) && valid(max) && max >= min ? { min, max, range: true } : null;
    return valid(row[key]) ? { min: row[key], max: row[key], range: false } : null;
  }
  function readState(search, rows) {
    const p = new URLSearchParams(search), fallback = preset('current');
    const known = new Set(rows.map(r => r.id)), models = new Set(rows.map(UI.modelLabel));
    const ids = p.has('selection') ? [...new Set(p.getAll('id').filter(id => known.has(id)))] : fallback.ids.filter(id => known.has(id));
    return { ids, group: Object.hasOwn(families, p.get('group')) ? p.get('group') : fallback.group, family: Object.hasOwn(families, p.get('family')) ? p.get('family') : (p.has('selection') ? 'all' : fallback.family), condition: ['', 'monitoring', 'event-recording', 'time-lapse', 'continuous'].includes(p.get('condition')) ? p.get('condition') : fallback.condition, details: p.get('details') === '1', metric: Object.hasOwn(metrics, p.get('metric')) ? p.get('metric') : fallback.metric,
      sort: p.get('sort') === 'asc' ? 'asc' : 'desc', highlight: p.has('highlight') ? (models.has(p.get('highlight')) ? p.get('highlight') : '') : fallback.highlight,
      title: p.has('title') ? p.get('title').replace(/[\u0000-\u001f\u007f]/g, ' ').slice(0, 180) : titles[Object.hasOwn(metrics,p.get('metric')) ? p.get('metric') : 'current'] };
  }
  function query(state) {
    const p = new URLSearchParams({ selection: '1', group: state.group || 'all', family: state.family || 'all', condition: state.condition ?? 'monitoring', metric: state.metric, sort: state.sort, highlight: state.highlight, title: state.title, details: state.details ? '1' : '0' });
    state.ids.forEach(id => p.append('id', id));
    return p.toString();
  }
  function prepare(rows, state) {
    const ids = new Set(state.ids);
    const selected = rows.filter(r => ids.has(r.id));
    const plotted = selected.map(row => ({ row, value: interval(row, state.metric) })).filter(item => item.value);
    plotted.sort((a, b) => (state.sort === 'asc' ? 1 : -1) * (a.value.max - b.value.max) || state.ids.indexOf(a.row.id) - state.ids.indexOf(b.row.id));
    const voltages = [...new Set(plotted.map(item => item.row.voltage_v))];
    const blocked = state.metric === 'current' && plotted.length > 0 && (voltages.length !== 1 || !valid(voltages[0]) || voltages[0] === 0);
    return { selected, plotted, excluded: selected.length - plotted.length, blocked, voltage: blocked ? null : voltages[0] };
  }
  const number = (n, metric) => metric === 'delay' ? (Number.isInteger(n * 100) ? n.toFixed(2) : String(n)) : String(n);
  function valueLabel(row, value, metric) {
    const text = value.range ? `${number(value.min, metric)}–${number(value.max, metric)}` : number(value.max, metric);
    return `${metric === 'watts' && row.power_is_derived ? '≈ ' : ''}${text} ${metrics[metric].unit}`;
  }
  const api = { metrics, families, matchesFamily, defaultCondition, representative, seed, preset, interval, readState, query, prepare, valueLabel };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (typeof window === 'undefined') return;
  window.ParkingCharts = api;
  const $ = id => document.getElementById(id);
  const ns = 'http://www.w3.org/2000/svg';
  let rows = [], state, currentSVG, pendingPNG = false;
  const modelChoices = new Map();
  const make = (tag, attributes = {}, text) => {
    const node = document.createElementNS(ns, tag);
    Object.entries(attributes).forEach(([key, value]) => node.setAttribute(key, String(value)));
    if (text != null) node.textContent = text;
    return node;
  };
  const el = (tag, cls, text) => {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text != null) node.textContent = text;
    return node;
  };
  const measure = document.createElement('canvas').getContext('2d');
  function textWidth(text, size = 14, bold = false) {
    measure.font = `${bold ? '700' : '400'} ${size}px Arial, sans-serif`;
    return measure.measureText(text).width;
  }
  function wrapped(text, maxWidth, size = 14, bold = false) {
    const lines = [];
    let line = '';
    // Split long tokens too, so a malicious title cannot escape the canvas.
    for (const char of String(text)) {
      if (textWidth(line + char, size, bold) > maxWidth && line) {
        const space = line.lastIndexOf(' ');
        if (space > line.length / 2) { lines.push(line.slice(0, space)); line = line.slice(space + 1) + char; }
        else { lines.push(line); line = char; }
      } else line += char;
    }
    if (line || !lines.length) lines.push(line);
    return lines;
  }
  function source(row) {
    // Private inputs are never exported, even if a future import forgets to redact its URL.
    if (row.source_is_private) return 'https://vortexopenclaw.github.io/dashcam-camera-profiles/parking-mode.html#vortex-radar-testing';
    const url = UI.safeURL(row.source_url);
    if (!url) return '';
    const parsed = new URL(url);
    return ['dashcamtalk.com', 'www.dashcamtalk.com', 'vortexopenclaw.github.io', 'www.vortexradar.com', 'vortexradar.com'].includes(parsed.hostname) ? url : '';
  }
  function draw(result) {
    const { plotted } = result, metric = metrics[state.metric];
    const axis = `${metric.label} (${metric.unit})${state.metric === 'current' ? ` at ${result.voltage} V` : ''}`;
    const variantKey = row => [UI.modelLabel(row),row.installed_channels,UI.modeLabel(row),row.state].join('|');
    const labels = plotted.map(({ row }, i) => {
      const siblings = plotted.filter(item => UI.modelLabel(item.row) === UI.modelLabel(row));
      const repeated = plotted.filter(item => variantKey(item.row) === variantKey(row)).length > 1;
      const modes = new Set(siblings.map(item => UI.modeLabel(item.row)));
      const flags = [row.test_status === 'prototype' ? 'Prototype' : '', UI.provisional(row) ? 'Provisional' : '', row.superseded ? 'Superseded' : ''].filter(Boolean);
      return {first: `${UI.modelLabel(row)}${row.installed_channels ? ` · ${row.installed_channels}CH` : ''}${flags.length ? ` · ${flags.join(', ')}` : ''}${state.details ? ` [${i + 1}]` : ''}`, second: [modes.size > 1 ? UI.modeLabel(row) : '', repeated ? `${UI.setup(row)} · ${row.id}` : '', siblings.some(item => item.row.state !== row.state) ? (UI.condition(row) || row.state) : '', state.metric === 'wake' ? row.wake_camera : ''].filter(Boolean).join(' · ')};
    });
    const left = 420;
    labels.forEach(label => { label.firstLines = wrapped(label.first, left - 56, 16, true); label.secondLines = label.second ? wrapped(label.second, left - 56, 14) : []; label.height = Math.max(58, label.firstLines.length * 20 + label.secondLines.length * 18 + 18); });
    const right = Math.ceil(Math.max(110, ...plotted.map(({ row, value }) => textWidth(valueLabel(row, value, state.metric), 16, true))) + 35);
    const width = Math.max(1200, left + right + 490), plotWidth = width - left - right;
    const svg = make('svg', { xmlns: ns, width, role: 'img', 'aria-labelledby': 'export-chart-title export-chart-desc', 'font-family': 'Arial, Helvetica, sans-serif', 'font-size': 14, fill: '#263343' });
    svg.append(make('title', { id: 'export-chart-title' }, state.title || metric.label), make('desc', { id: 'export-chart-desc' }, `${axis}. ${plotted.length} measurements. Ranges show endpoints only. Values sorted ${state.sort === 'asc' ? 'low to high' : 'high to low'} by upper endpoint.`));
    const content = make('g');
    const text = (x, y, value, attrs = {}) => content.appendChild(make('text', { x, y, ...attrs }, value));
    let y = 45;
    for (const line of wrapped(state.title || metric.label, width - 72, 28, true)) { text(width / 2, y, line, { 'text-anchor':'middle', 'data-role':'chart-heading', 'font-size': 28, 'font-weight': 700, fill: '#172337' }); y += 35; }
    text(width / 2, y + 8, `${families[state.family] || families.all} · ${axis}`, { 'text-anchor':'middle', 'data-role':'chart-heading', 'font-size': 16, fill: '#516174' });
    const hasRanges = plotted.some(item => item.value.range);
    text(width / 2, y + 34, `Zero baseline · ${state.sort === 'asc' ? 'Low to high' : 'High to low'}${hasRanges ? ' · Ranges sorted by upper endpoint' : ''}`, { 'text-anchor':'middle', 'data-role':'chart-heading', 'font-size': 13, fill: '#637285' });
    const top = y + 66, bottom = top + labels.reduce((sum, label) => sum + label.height, 0);
    const maximum = Math.max(0, ...plotted.map(item => item.value.max));
    const rawStep = maximum > 0 ? maximum / 5 : 0.2;
    const magnitude = 10 ** Math.floor(Math.log10(rawStep));
    const step = [1, 2, 2.5, 5, 10].find(value => value * magnitude >= rawStep) * magnitude;
    const scaleMax = Math.max(step, Math.ceil(maximum / step) * step);
    const scale = value => left + value / scaleMax * plotWidth;
    for (let tick = 0; tick <= Math.round(scaleMax / step); tick++) {
      const value = step * tick, x = scale(value);
      content.append(make('line', { x1: x, x2: x, y1: top - 12, y2: bottom, stroke: tick ? '#e3e8ee' : '#7e8996', 'stroke-width': tick ? 1 : 1.5 }));
      text(x, bottom + 26, String(Number(value.toPrecision(3))), { 'text-anchor': 'middle', 'font-size': 13, fill: '#627084' });
    }
    let rowTop = top;
    plotted.forEach(({ row, value }, index) => {
      const label = labels[index];
      const cy = rowTop + label.height / 2, highlighted = UI.modelLabel(row) === state.highlight;
      rowTop += label.height;
      const group = make('g', { 'data-measurement': row.id, 'data-min': value.min, 'data-max': value.max, 'data-range': value.range, 'data-highlight': highlighted });
      let labelY = cy - (label.firstLines.length * 20 + label.secondLines.length * 18) / 2 + 15;
      label.firstLines.forEach(line => { group.append(make('text', { x: left - 20, y: labelY, 'text-anchor': 'end', 'font-size': 16, 'font-weight': highlighted ? 700 : 600, fill: highlighted ? '#ac520e' : '#23354a' }, line)); labelY += 20; });
      label.secondLines.forEach(line => { group.append(make('text', { x: left - 20, y: labelY, 'text-anchor': 'end', 'font-size': 14, fill: '#566477' }, line)); labelY += 18; });
      const color = highlighted ? '#ef8a2c' : '#559bd4';
      if (value.range) {
        group.append(make('line', { x1: scale(value.min), x2: scale(value.max), y1: cy, y2: cy, stroke: '#243a50', 'stroke-width': 3, 'data-kind': 'range' }));
        for (const endpoint of [value.min, value.max]) group.append(make('line', { x1: scale(endpoint), x2: scale(endpoint), y1: cy - 12, y2: cy + 12, stroke: '#243a50', 'stroke-width': 3 }));
      } else if (value.max > 0) group.append(make('rect', { x: left, y: cy - 13, width: scale(value.max) - left, height: 26, fill: color, 'data-kind': 'scalar' }));
      else group.append(make('circle', { cx: left, cy, r: 3, fill: color, 'data-kind': 'zero' }));
      group.append(make('text', { x: scale(value.max) + 10, y: cy + 5, 'font-size': 16, 'font-weight': highlighted ? 700 : 600, fill: '#23354a', 'data-kind': 'value' }, valueLabel(row, value, state.metric)));
      content.append(group);
    });
    y = bottom + 65;
    content.append(make('line', { x1: 36, x2: width - 36, y1: y - 8, y2: y - 8, stroke: '#dae2eb' }));
    const notes = [
      state.metric === 'watts' && plotted.some(item=>item.row.power_is_derived) ? '≈ marks calculated power.' : '',
      hasRanges ? 'Ranges show measured endpoints, not averages. Firmware and setups remain separate.' : '',

      state.details ? 'Sources and configurations' : ''
    ].filter(Boolean);
    for (const note of notes) { for (const line of wrapped(note, width - 72, 13)) { y += 19; text(36, y, line, { 'font-size': 13, fill: '#536174' }); } y += 5; }
    if (state.details) {
    const sources = new Map();
    plotted.forEach(({ row }, index) => {
      const flags = [row.test_status === 'prototype' ? 'Prototype' : '', UI.provisional(row) ? 'Provisional' : '', row.superseded ? 'Superseded' : ''].filter(Boolean).join(' · ');
      const note = `[${index + 1}] ${UI.modelLabel(row)} · ${row.id} · ${UI.setup(row)} · ${row.mode_name} · ${UI.condition(row) || row.state} · ${row.tester || 'Tester not reported'}${row.date ? ` · ${row.date}` : ''}${flags ? ` · ${flags}` : ''}`;
      for (const line of wrapped(note + (state.metric === 'wake' && row.notes ? ` · Timing context: ${row.notes}` : ''), width - 72, 12)) { y += 17; text(36, y, line, { 'font-size': 12, fill: '#536174' }); }
      const url = source(row);
      const sourceKey = url || 'Source URL not available in the public index.';
      if (!sources.has(sourceKey)) sources.set(sourceKey, []);
      sources.get(sourceKey).push(index + 1);
      y += 8;
    });
    for (const [url, references] of sources) {
      for (const line of wrapped(`Source for [${references.join(', ')}]: ${url}`, width - 72, 12)) { y += 17; text(36, y, line, { 'font-size': 12, fill: '#536174' }); }
      y += 8;
    }
    }
    y += 22;
    const contributors = [...new Set(plotted.map(item => item.row.tester).filter(Boolean))].join(', ');
    for (const line of wrapped(`Sources: ${contributors}. Full measurements and configurations: vortexopenclaw.github.io/dashcam-camera-profiles/parking-mode.html`, width - 72, 12)) {
      text(36, y, line, { 'font-size': 12, fill: '#69778a' }); y += 17;
    }
    const metadata = make('metadata');
    metadata.textContent = JSON.stringify({metric:state.metric,family:state.family,group:state.group,measurements:safeRows(plotted.map(item=>item.row))});
    svg.append(metadata);
    const height = y + 30;
    svg.setAttribute('height', height); svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
    svg.append(make('rect', { x: 0, y: 0, width, height, fill: '#ffffff' }), content);
    return svg;
  }
  function safeRows(items) { return items.map(row => ({ ...row, source_url: source(row), image_url: row.source_is_private ? null : source({ ...row, source_url: row.image_url }) })); }
  function download(blob, filename) {
    const url = URL.createObjectURL(blob), a = document.createElement('a');
    a.href = url; a.download = filename; document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  function serialized() { return new XMLSerializer().serializeToString(currentSVG); }
  async function exportPNG() {
    if (!currentSVG || pendingPNG) return;
    pendingPNG = true; $('chart-png').disabled = true;
    const original = currentSVG, url = URL.createObjectURL(new Blob([serialized()], { type: 'image/svg+xml;charset=utf-8' }));
    try {
      const image = new Image();
      await new Promise((resolve, reject) => { image.onload = resolve; image.onerror = reject; image.src = url; });
      const canvas = document.createElement('canvas');
      canvas.width = Number(original.getAttribute('width')) * 2; canvas.height = Number(original.getAttribute('height')) * 2;
      const context = canvas.getContext('2d');
      context.fillStyle = '#ffffff'; context.fillRect(0, 0, canvas.width, canvas.height);
      context.drawImage(image, 0, 0, canvas.width, canvas.height);
      const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/png'));
      if (!blob) throw new Error('PNG creation failed');
      download(blob, 'parking-comparison-2x.png'); $('chart-action-status').textContent = 'PNG downloaded at 2× with the complete chart and source notes.';
    } catch { $('chart-action-status').textContent = 'PNG export could not finish. Try the SVG download instead.'; }
    finally { URL.revokeObjectURL(url); pendingPNG = false; $('chart-png').disabled = !currentSVG; }
  }
  function syncControls() {
    for (const key of ['title', 'metric', 'sort', 'highlight', 'group', 'condition']) $(`chart-${key}`).value = state[key];
    $('chart-details').checked = !!state.details;
  }
  function renderChart() {
    const result = prepare(rows, state);
    $('chart-count').textContent = `${result.selected.length} selected · ${result.blocked ? 0 : result.plotted.length} plotted`;
    $('chart-clear').disabled = !state.ids.length;
    $('chart-csv').disabled = !state.ids.length;
    $('chart-switch-watts').hidden = !result.blocked;
    const missingModels=[...new Set(result.selected.filter(row=>!interval(row,state.metric)).map(UI.modelLabel))];
    $('chart-notice').textContent = result.blocked ? 'Current comparison blocked: selected measurements have different or unknown measurement voltages. Choose tests at one known voltage, or switch to W.' : (result.excluded ? `No ${metrics[state.metric].label.toLowerCase()} data for: ${missingModels.join(', ')}. ${result.excluded===1?'That selection is':'Those selections are'} not shown.` : (!result.plotted.length ? 'Choose a dashcam with a result for this metric.' : ''));
    currentSVG = !result.blocked && result.plotted.length ? draw(result) : null;
    $('chart-canvas').replaceChildren(...(currentSVG ? [currentSVG] : [el('p', 'charts-empty', result.blocked ? 'No current chart until the voltage comparison is valid.' : 'No measured values to plot.')]));
    $('chart-canvas').setAttribute('aria-busy', 'false');
    $('chart-svg').disabled = !currentSVG; $('chart-png').disabled = !currentSVG || pendingPNG;
    history.replaceState(null, '', `${location.pathname}?${query(state)}`);
  }
  function primaryGroups() {
    const q = $('chart-search').value.toLocaleLowerCase().trim();
    const eligible = rows.filter(row => matchesFamily(row, state.group) && row.state === defaultCondition(state.group));
    return UI.groupModels(eligible).filter(group => !q || group.rows.some(row => `${UI.modelLabel(row)} ${row.brand} ${row.model} ${row.mode_name} ${UI.setup(row)} ${row.id}`.toLocaleLowerCase().includes(q))).sort((a,b) => a.label.localeCompare(b.label));
  }
  function chosenFor(group, channels = null) {
    const remembered = modelChoices.get(group.label);
    return representative(group.rows, remembered ? [remembered] : state.ids, state.group, channels);
  }
  function editModel(group, chosen, checked, focus = 'input[type=checkbox]') {
    modelChoices.set(group.label, chosen.id);
    // A normal model choice follows the requested group, without mixing old modes.
    if (checked) state.ids=state.ids.filter(id=>{const row=rows.find(row=>row.id===id);return matchesFamily(row,state.group)&&row.state===defaultCondition(state.group);});
    state.ids = state.ids.filter(id => UI.modelLabel(rows.find(row => row.id === id)) !== group.label);
    if (checked) state.ids.push(chosen.id);
    state.family = state.ids.every(id => matchesFamily(rows.find(row => row.id === id), state.group)) ? state.group : 'all';
    const useWatts=state.metric==='current' && (prepare(rows,state).blocked || state.ids.some(id=>{const row=rows.find(row=>row.id===id);return !interval(row,'current')&&interval(row,'watts');}));
    if(useWatts){if(Object.values(titles).includes(state.title))state.title=titles.watts;state.metric='watts';}
    render();
    if(useWatts)$('chart-action-status').textContent='Switched to W to compare the selected cameras without assuming a supply voltage.';
    [...document.querySelectorAll('.chart-model-choice')].find(node=>node.dataset.model===group.label)?.querySelector(focus)?.focus({preventScroll:true});
  }
  function renderModels(groups) {
    const open = new Set([...document.querySelectorAll('.chart-model-choice')].filter(node=>node.querySelector('details').open).map(node=>node.dataset.model));
    const fragment = document.createDocumentFragment();
    for (const group of groups) {
      const chosen = chosenFor(group), selected = state.ids.some(id => group.rows.some(row => row.id === id));
      const card = el('div','chart-model-choice'); card.dataset.model = group.label;
      const label = el('label','chart-model-toggle'), input = document.createElement('input');
      input.type='checkbox'; input.dataset.model=group.label; input.checked=selected;
      input.setAttribute('aria-label',group.label); label.append(input,el('strong','',group.label));
      if(chosen.installed_channels)label.append(el('small','chart-default-channels',`${chosen.installed_channels} ${chosen.installed_channels===1?'channel':'channels'}`));
      input.addEventListener('change',() => editModel(group,chosen,input.checked));
      card.append(label);
      const details=el('details','chart-model-setup'), summary=el('summary','','Setup and test details');
      details.append(summary); details.open = open.has(group.label);
      const channelCounts = [...new Set(group.rows.map(row=>row.installed_channels).filter(n=>Number.isInteger(n)&&n>0))].sort((a,b)=>b-a);
      if (channelCounts.length) {
        const channelLabel=el('label','chart-model-channels','Channels'), select=document.createElement('select');
        select.dataset.channels=group.label; select.setAttribute('aria-label',`Channels for ${group.label}`);
        channelCounts.forEach(n=>{const option=el('option','',`${n} ${n===1?'channel':'channels'}`);option.value=n;select.append(option);});
        select.value=chosen.installed_channels || '';
        select.addEventListener('change',()=>editModel(group,chosenFor(group,Number(select.value)),selected,'select[data-channels]'));
        channelLabel.append(select);details.append(channelLabel);
      }
      const setupLabel=el('label','','Test and mode'), setupSelect=document.createElement('select');
      setupSelect.dataset.test = group.label;
      setupSelect.setAttribute('aria-label',`Test and mode for ${group.label}`);
      const variants=group.rows.filter(row=>row.installed_channels===chosen.installed_channels);
      variants.forEach(row=>{const option=el('option','',`${UI.modeLabel(row)} · ${UI.setup(row)} · ${row.id}`);option.value=row.id;setupSelect.append(option);});
      setupSelect.value=chosen.id;
      setupSelect.addEventListener('change',()=>editModel(group,rows.find(row=>row.id===setupSelect.value),selected,'select[data-test]'));
      setupLabel.append(setupSelect);details.append(setupLabel);
      const value=interval(chosen,state.metric);
      details.append(el('small','',`Selected test: ${chosen.id} · ${value?valueLabel(chosen,value,state.metric):'Not measured for this metric'}`),el('small','',`Original mode: ${chosen.mode_name}`),el('small','',`${UI.setup(chosen)} · ${chosen.tester || 'Contributor'}${chosen.date ? ` · ${chosen.date}` : ''}`));
      const flags=[chosen.test_status==='prototype'?'Prototype':'',UI.provisional(chosen)?'Provisional':'',chosen.superseded?'Superseded':''].filter(Boolean);
      if(flags.length)label.append(el('small','',flags.join(' · ')));
      if(chosen.notes)details.append(el('small','',chosen.notes));
      const multiple=state.ids.filter(id=>rows.some(row=>row.id===id&&UI.modelLabel(row)===group.label)).length;
      if(multiple>1)details.append(el('small','',`${multiple} shared measurements retained. Editing this camera replaces only its selected tests.`));
      card.append(details);fragment.append(card);
    }
    if(!groups.length)fragment.append(el('p','charts-muted','No matching camera models. Your chart has not changed.'));
    $('chart-model-picker').replaceChildren(fragment);
  }
  function renderPicker() {
    const open = new Set([...document.querySelectorAll('.chart-model[open]')].map(node => node.dataset.model));
    const selected = new Set(state.ids), q = $('chart-search').value.toLocaleLowerCase().trim(), condition = $('chart-condition').value;
    const visible = rows.filter(row => (!q || `${UI.modelLabel(row)} ${row.brand} ${row.model} ${row.mode_name} ${UI.setup(row)} ${row.id}`.toLocaleLowerCase().includes(q)) && (!condition || row.state === condition) && (!$('chart-only-selected').checked || selected.has(row.id)));
    const groups = UI.groupModels(visible).sort((a, b) => a.label.localeCompare(b.label));
    $('picker-count').textContent = `${visible.length} matching measurements · ${groups.length} models`;
    const models = primaryGroups(); renderModels(models);
    $('chart-apply-group').textContent = `Compare shown models · ${models.length}`;
    $('chart-apply-group').disabled = !models.length;
    $('chart-group-count').textContent = `${families[state.group]} · ${models.length} models`;
    const fragment = document.createDocumentFragment();
    for (const group of groups) {
      const details = el('details', 'chart-model'); details.dataset.model = group.label;
      details.open = open.has(group.label) || !!q || $('chart-only-selected').checked;
      const summary = el('summary', '', group.label);
      summary.append(el('span', 'chart-model-count', `${group.rows.length} measurements · ${group.rows.filter(row => selected.has(row.id)).length} selected`));
      details.append(summary);
      for (const row of group.rows) {
        const label = el('label', 'chart-pick-row'), input = document.createElement('input');
        input.type = 'checkbox'; input.dataset.id = row.id; input.checked = selected.has(row.id); input.setAttribute('aria-label', `${UI.modelLabel(row)}, ${UI.modeLabel(row)}, ${row.id}`);
        const body = el('span'); body.append(el('strong', '', `${UI.modeLabel(row)} · ${UI.condition(row) || (row.state === 'time-lapse' ? 'Time-lapse recording' : 'Continuous recording')}`));
        body.append(el('small', '', UI.setup(row)));
        const value = interval(row, state.metric);
        body.append(el('small', 'chart-metric-reading', `${value ? valueLabel(row, value, state.metric) : 'Not measured for this metric'}${state.metric === 'current' ? ` · ${valid(row.voltage_v) ? `${row.voltage_v} V` : 'Voltage unknown'}` : ''}`));
        if (row.test_status === 'prototype' || UI.provisional(row) || row.superseded) body.append(el('small','', [row.test_status === 'prototype' ? 'Prototype' : '', UI.provisional(row) ? 'Provisional' : '',row.superseded ? 'Superseded' : ''].filter(Boolean).join(' · ')));
        const sourceDetails=el('details','chart-test-details');
        sourceDetails.append(el('summary','','Test details'));
        sourceDetails.append(el('small','',`Original mode: ${row.mode_name}`),el('small','',`${row.tester || 'Contributor'} · ${row.id}${row.date ? ` · ${row.date}` : ''}`));
        if (row.power_path) sourceDetails.append(el('small','',`Power adapter: ${row.power_path}`));
        if (row.wake_camera) sourceDetails.append(el('small','',`First-frame scope: ${row.wake_camera}`));
        if (row.reported_startup_seconds != null && row.reported_startup_method !== method) sourceDetails.append(el('small','',`Other reported startup: ${row.reported_startup_seconds} s, method unconfirmed. Not plotted as impact timing.`));
        body.append(sourceDetails);
        label.append(input, body); details.append(label);
      }
      fragment.append(details);
    }
    if (!groups.length) fragment.append(el('p', 'charts-muted', 'No matching measurements. Your chart selection has not changed.'));
    $('chart-picker').replaceChildren(fragment);
  }
  function render() { syncControls(); renderChart(); renderPicker(); }
  async function init() {
    try {
      const response = await fetch('data/parking-measurements.json', {cache:'no-store'});
      if (!response.ok) throw new Error('Data request failed');
      const data = await response.json(); rows = data.measurements;
      state = readState(location.search, rows);
      $('chart-data-status').textContent = `${rows.length} measurements · ${UI.groupModels(rows).length} models`;
      UI.groupModels(rows).sort((a, b) => a.label.localeCompare(b.label)).forEach(group => { const option = el('option', '', group.label); option.value = group.label; $('chart-highlight').append(option); });
      for (const key of ['title', 'metric', 'sort', 'highlight']) $(`chart-${key}`).addEventListener(key === 'title' ? 'input' : 'change', () => {
        const value=$(`chart-${key}`).value;
        if (key==='metric' && Object.values(titles).includes(state.title)) {state.title=titles[value];$('chart-title').value=state.title;}
        state[key]=value;renderChart();if(key==='metric')renderPicker();
      });
      $('chart-details').addEventListener('change', () => {state.details=$('chart-details').checked;renderChart();});
      $('chart-group').addEventListener('change', () => { state.group = $('chart-group').value; modelChoices.clear(); state.condition = defaultCondition(state.group); $('chart-condition').value = state.condition; renderPicker(); history.replaceState(null, '', `${location.pathname}?${query(state)}`); });
      $('chart-apply-group').addEventListener('click', () => {
        state.ids = primaryGroups().map(group=>chosenFor(group).id);
        state.family = state.group;
        const blocked = prepare(rows, state).blocked;
        if (blocked) { if (Object.values(titles).includes(state.title)) state.title = titles.watts; state.metric = 'watts'; }
        render();
        $('chart-action-status').textContent = `${state.ids.length} camera models selected.${blocked ? ' Switched to W because these tests have different or unknown supply voltages. No mA equivalents were invented.' : ''}`;
      });
      for (const metric of ['current', 'delay']) $(`preset-${metric}`).addEventListener('click', () => { state = preset(metric); modelChoices.clear(); render(); });
      $('chart-clear').addEventListener('click', () => { state.ids = []; render(); });
      $('chart-switch-watts').addEventListener('click', () => {if(Object.values(titles).includes(state.title))state.title=titles.watts;state.metric = 'watts'; render(); });
      for (const key of ['chart-search', 'chart-condition', 'chart-only-selected']) $(key).addEventListener(key === 'chart-search' ? 'input' : 'change', () => { state.condition = $('chart-condition').value; renderPicker(); history.replaceState(null, '', `${location.pathname}?${query(state)}`); });
      $('chart-picker').addEventListener('change', event => {
        const { id } = event.target.dataset;
        if (!id || !rows.some(row => row.id === id)) return;
        modelChoices.delete(UI.modelLabel(rows.find(row => row.id === id)));
        if (event.target.checked && !matchesFamily(rows.find(row => row.id === id), state.family)) state.family = 'all';
        state.ids = event.target.checked ? [...new Set([...state.ids, id])] : state.ids.filter(value => value !== id);
        renderChart();
        renderModels(primaryGroups());
        // Update counts without replacing a focused advanced checkbox.
        document.querySelectorAll('.chart-model').forEach(details => {
          const inputs = [...details.querySelectorAll('input[data-id]')];
          details.querySelector('.chart-model-count').textContent = `${inputs.length} measurements · ${inputs.filter(input => input.checked).length} selected`;
        });
      });
      $('chart-svg').addEventListener('click', () => { if (currentSVG) download(new Blob([serialized()], { type: 'image/svg+xml;charset=utf-8' }), 'parking-comparison.svg'); });
      $('chart-png').addEventListener('click', exportPNG);
      $('chart-csv').addEventListener('click', () => download(new Blob([UI.toCSV(safeRows(prepare(rows, state).selected))], { type: 'text/csv;charset=utf-8' }), 'parking-selected-measurements.csv'));
      $('chart-share').addEventListener('click', async () => {
        try { await navigator.clipboard.writeText(location.href); $('chart-action-status').textContent = 'Share link copied. Selections, metric, sort, highlight, and title are included.'; }
        catch { $('chart-action-status').textContent = `Copy the current address to share this chart: ${location.href}`; }
      });
      render();
    } catch { $('chart-data-status').textContent = 'Measurements could not load. Reload this page or open the public dataset.'; $('chart-canvas').setAttribute('aria-busy', 'false'); }
  }
  init();
})();
