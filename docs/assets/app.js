"use strict";

const state = { cameras: [], selectedId: null, query: "", brand: "", evidence: "", qualityChannel: "front", qualityResolution: "", qualityFps: "", qualityCompanionChannel: "", qualityCompanionResolution: "", qualityCompanionFps: "" };
const elements = {};

document.addEventListener("DOMContentLoaded", async () => {
  Object.assign(elements, {
    list: document.querySelector("#camera-list"),
    detail: document.querySelector("#camera-detail"),
    search: document.querySelector("#search"),
    brand: document.querySelector("#brand-filter"),
    evidence: document.querySelector("#evidence-filter"),
    resultCount: document.querySelector("#result-count"),
    qualityChannel: document.querySelector("#quality-channel"),
    qualityResolution: document.querySelector("#quality-resolution"),
    qualityFps: document.querySelector("#quality-fps"),
    qualityCompanionChannel: document.querySelector("#quality-companion-channel"),
    qualityCompanionResolution: document.querySelector("#quality-companion-resolution"),
    qualityCompanionFps: document.querySelector("#quality-companion-fps"),
    qualityResultCount: document.querySelector("#quality-result-count"),
    qualityResults: document.querySelector("#quality-results")
  });

  try {
    const response = await fetch("data/cameras.json");
    if (!response.ok) throw new Error(`Reference request failed: ${response.status}`);
    const data = await response.json();
    state.cameras = data.cameras;
    populateStats(data);
    populateFilters();
    bindControls();
    populateQualityFilters();
    const hashId = decodeURIComponent(location.hash.replace(/^#camera=/, ""));
    state.selectedId = state.cameras.some(camera => camera.id === hashId) ? hashId : null;
    render();
  } catch (error) {
    elements.detail.innerHTML = `<div class="empty-state"><h2>Reference unavailable</h2><p>${escapeHtml(error.message)}</p></div>`;
  }
});

function populateStats(data) {
  document.querySelector("#camera-count").textContent = data.camera_count;
  document.querySelector("#measured-count").textContent = data.cameras.filter(camera => camera.video_samples.length).length;
  document.querySelector("#manual-count").textContent = data.cameras.filter(camera => camera.sources.some(source => source.kind === "manual")).length;
}

function populateFilters() {
  const brands = [...new Set(state.cameras.map(camera => displayManufacturer(camera.manufacturer)))].sort(naturalCompare);
  const levels = [...new Set(state.cameras.map(camera => camera.evidence.level))].sort(naturalCompare);
  elements.brand.insertAdjacentHTML("beforeend", brands.map(brand => `<option>${escapeHtml(brand)}</option>`).join(""));
  elements.evidence.insertAdjacentHTML("beforeend", levels.map(level => `<option value="${escapeHtml(level)}">${escapeHtml(label(level))}</option>`).join(""));
}

function bindControls() {
  elements.search.addEventListener("input", event => { state.query = event.target.value.toLowerCase().trim(); render(); });
  elements.brand.addEventListener("change", event => { state.brand = event.target.value; render(); });
  elements.evidence.addEventListener("change", event => { state.evidence = event.target.value; render(); });
  elements.qualityChannel.addEventListener("change", event => { state.qualityChannel = event.target.value; populateQualityFilters(); renderQualityExplorer(); });
  elements.qualityResolution.addEventListener("change", event => { state.qualityResolution = event.target.value; renderQualityExplorer(); });
  elements.qualityFps.addEventListener("change", event => { state.qualityFps = event.target.value; renderQualityExplorer(); });
  elements.qualityCompanionChannel.addEventListener("change", event => { state.qualityCompanionChannel = event.target.value; populateQualityFilters(); renderQualityExplorer(); });
  elements.qualityCompanionResolution.addEventListener("change", event => { state.qualityCompanionResolution = event.target.value; renderQualityExplorer(); });
  elements.qualityCompanionFps.addEventListener("change", event => { state.qualityCompanionFps = event.target.value; renderQualityExplorer(); });
  window.addEventListener("hashchange", () => {
    const id = decodeURIComponent(location.hash.replace(/^#camera=/, ""));
    if (state.cameras.some(camera => camera.id === id)) { state.selectedId = id; render(); }
  });
}

function filteredCameras() {
  return state.cameras.filter(camera => {
    if (state.brand && displayManufacturer(camera.manufacturer) !== state.brand) return false;
    if (state.evidence && camera.evidence.level !== state.evidence) return false;
    if (!state.query) return true;
    const searchable = [
      camera.manufacturer, camera.model, camera.evidence.level, camera.evidence.status,
      ...allFolders(camera).flatMap(folder => [folder.path, folder.mode]),
      ...camera.filename_patterns.map(pattern => pattern.pattern),
      ...camera.video_samples.flatMap(sample => Object.values(sample)),
      ...camera.technical_facts.flatMap(fact => [fact.label, fact.value])
    ].join(" ").toLowerCase();
    return searchable.includes(state.query);
  });
}

function render() {
  const cameras = filteredCameras();
  elements.resultCount.textContent = `${cameras.length} camera${cameras.length === 1 ? "" : "s"}`;
  elements.list.innerHTML = cameras.map(camera => `
    <button class="camera-button ${camera.id === state.selectedId ? "active" : ""}" data-id="${escapeHtml(camera.id)}" role="option" aria-selected="${camera.id === state.selectedId}">
      <strong>${escapeHtml(camera.model)}</strong>
      <small>${escapeHtml(displayManufacturer(camera.manufacturer))}</small>
      <span class="mini-badge">${escapeHtml(label(camera.evidence.level))}</span>
    </button>`).join("");
  elements.list.querySelectorAll("button").forEach(button => button.addEventListener("click", () => selectCamera(button.dataset.id)));

  const selected = state.cameras.find(camera => camera.id === state.selectedId);
  if (selected && cameras.includes(selected)) {
    elements.detail.innerHTML = renderDetail(selected);
  } else {
    state.selectedId = null;
    elements.detail.innerHTML = cameras.length ? renderOverview(qualityMatches()) : `<div class="empty-state"><h2>No cameras match</h2><p>Try a different search or filter.</p></div>`;
  }
  renderQualityExplorer();
  bindChartClicks();
}

function drivingSamples() {
  return state.cameras.flatMap(camera => camera.video_samples
    .filter(sample => sample.mode === "driving")
    .map(sample => ({ camera, sample, role: cameraRole(sample.channel) }))
    .filter(item => item.role));
}

function cameraRole(channel) {
  const value = channel.toLowerCase();
  if (value.includes("telephoto")) return "front_telephoto";
  if (value.includes("interior")) return "interior";
  if (value.includes("rear") || /^r\b|^b \(rear\)|^c \(rear\)|^nr\b/.test(value)) return "rear";
  if (value.includes("front") || /^f\b|^a \(front\)|^mf\b|^nf\b/.test(value)) return "front";
  return null;
}

function populateQualityFilters() {
  const allSamples = drivingSamples();
  const roles = [...new Set(allSamples.map(item => item.role))].sort(roleCompare);
  updateSelectOptions(elements.qualityChannel, roles, state.qualityChannel, "No measured camera positions");
  state.qualityChannel = elements.qualityChannel.value || roles[0] || "";
  const samples = allSamples.filter(item => item.role === state.qualityChannel);
  const resolutions = [...new Set(samples.map(item => item.sample.resolution))].sort(resolutionCompare);
  const fps = [...new Set(samples.flatMap(item => fpsValues(item.sample.fps)))].sort(fpsCompare);
  updateSelectOptions(elements.qualityResolution, resolutions, state.qualityResolution, "Any resolution");
  updateSelectOptions(elements.qualityFps, fps, state.qualityFps, "Any frame rate");
  state.qualityResolution = elements.qualityResolution.value;
  state.qualityFps = elements.qualityFps.value;
  const companionRoles = roles.filter(role => role !== state.qualityChannel);
  updateSelectOptions(elements.qualityCompanionChannel, companionRoles, state.qualityCompanionChannel, "No additional camera requirement");
  state.qualityCompanionChannel = elements.qualityCompanionChannel.value;
  const companionSamples = allSamples.filter(item => item.role === state.qualityCompanionChannel);
  const companionEnabled = Boolean(state.qualityCompanionChannel);
  elements.qualityCompanionResolution.disabled = !companionEnabled;
  elements.qualityCompanionFps.disabled = !companionEnabled;
  updateSelectOptions(elements.qualityCompanionResolution, [...new Set(companionSamples.map(item => item.sample.resolution))].sort(resolutionCompare), state.qualityCompanionResolution, "Any resolution");
  updateSelectOptions(elements.qualityCompanionFps, [...new Set(companionSamples.flatMap(item => fpsValues(item.sample.fps)))].sort(fpsCompare), state.qualityCompanionFps, "Any frame rate");
  state.qualityCompanionResolution = companionEnabled ? elements.qualityCompanionResolution.value : "";
  state.qualityCompanionFps = companionEnabled ? elements.qualityCompanionFps.value : "";
}

function updateSelectOptions(element, values, selected, defaultLabel) {
  element.innerHTML = `<option value="">${escapeHtml(defaultLabel)}</option>${values.map(value => `<option value="${escapeHtml(value)}" ${value === selected ? "selected" : ""}>${escapeHtml(selectLabel(element, value))}</option>`).join("")}`;
}

function qualityMatches() {
  return drivingSamples()
    .filter(item => item.role === state.qualityChannel)
    .filter(item => !state.qualityResolution || item.sample.resolution === state.qualityResolution)
    .filter(item => !state.qualityFps || fpsValues(item.sample.fps).includes(state.qualityFps))
    .filter(item => !state.qualityCompanionChannel || configurationCompanions(item).some(companion => cameraRole(companion.channel) === state.qualityCompanionChannel
      && (!state.qualityCompanionResolution || companion.resolution === state.qualityCompanionResolution)
      && (!state.qualityCompanionFps || fpsValues(companion.fps).includes(state.qualityCompanionFps))))
    .sort((a, b) => bitrateMaximum(b.sample.bitrate) - bitrateMaximum(a.sample.bitrate) || naturalCompare(a.camera.model, b.camera.model));
}

function renderQualityExplorer() {
  const matches = qualityMatches();
  elements.qualityResultCount.textContent = `${matches.length} measured ${state.qualityChannel} driving sample${matches.length === 1 ? "" : "s"}`;
  elements.qualityResults.innerHTML = matches.length ? matches.map(({ camera, sample }) => {
    const item = { camera, sample, role: cameraRole(sample.channel) };
    const companions = configurationCompanions(item);
    const configuration = sample.recording_configuration || "Configuration not recorded";
    const setting = sample.settings_note ? `<small class="quality-setting">${escapeHtml(sample.settings_note)}</small>` : "";
    return `<button class="quality-result" data-id="${escapeHtml(camera.id)}"><span class="quality-camera"><strong>${escapeHtml(displayManufacturer(camera.manufacturer))} ${escapeHtml(camera.model)}</strong><small>${escapeHtml(sample.channel)} · ${escapeHtml(sample.codec)}</small></span><span class="quality-spec">${escapeHtml(sample.resolution)}<small>${escapeHtml(sample.fps)} FPS</small></span><span class="bitrate-bar"><i style="width:${bitrateWidth(sample.bitrate)}%"></i><strong>${escapeHtml(sample.bitrate)}</strong></span><span class="quality-companions"><strong>${escapeHtml(configuration)}</strong><small>${companions.length ? companions.map(companion => `${roleLabel(cameraRole(companion.channel))} ${companion.resolution} ${companion.fps}fps`).join(" · ") : "No additional same-configuration channel recorded"}</small>${setting}</span></button>`;
  }).join("") : `<div class="quality-empty">No measured driving samples match those filters.</div>`;
  elements.qualityResults.querySelectorAll("button").forEach(button => button.addEventListener("click", () => selectCamera(button.dataset.id)));
  if (!state.selectedId) {
    elements.detail.innerHTML = renderOverview(matches);
    bindChartClicks();
  }
}

function bindChartClicks() {
  elements.detail.querySelectorAll(".bitrate-chart-row").forEach(button => button.addEventListener("click", () => selectCamera(button.dataset.id)));
}

function configurationCompanions({ camera, sample }) {
  if (!sample.recording_configuration) return [];
  return camera.video_samples.filter(item => item.mode === "driving" && item !== sample && item.recording_configuration === sample.recording_configuration);
}

function bitrateMaximum(value) {
  const values = String(value).match(/\d+(?:\.\d+)?/g) || [];
  return Math.max(0, ...values.map(Number));
}

function bitrateWidth(value) { return Math.max(8, Math.min(100, bitrateMaximum(value) / 70 * 100)); }
function fpsValues(value) { return [...new Set((String(value).match(/\d+(?:\.\d+)?/g) || []))]; }
function roleLabel(value) { return ({ front: "Front", front_telephoto: "Telephoto front", rear: "Rear", interior: "Interior" })[value] || "Unknown"; }
function roleCompare(a, b) { return ["front", "front_telephoto", "rear", "interior"].indexOf(a) - ["front", "front_telephoto", "rear", "interior"].indexOf(b); }
function selectLabel(element, value) {
  if (element === elements.qualityChannel || element === elements.qualityCompanionChannel) return roleLabel(value);
  if (element === elements.qualityFps || element === elements.qualityCompanionFps) return `${value} FPS`;
  return value;
}
function resolutionCompare(a, b) { return pixelCount(b) - pixelCount(a) || naturalCompare(a, b); }
function pixelCount(value) { const match = String(value).match(/(\d+)x(\d+)/); return match ? Number(match[1]) * Number(match[2]) : 0; }
function fpsCompare(a, b) { return bitrateMaximum(b) - bitrateMaximum(a) || naturalCompare(a, b); }

function selectCamera(id) {
  state.selectedId = id;
  history.replaceState(null, "", `#camera=${encodeURIComponent(id)}`);
  render();
  if (window.matchMedia("(max-width: 900px)").matches) elements.detail.scrollIntoView({ behavior: "smooth" });
}

function renderOverview(matches) {
  return `<header>
    <p class="detail-kicker">LIBRARY OVERVIEW</p>
    <h1 class="detail-title">Measured driving bitrate</h1>
    <p class="section-intro">Select a camera on the left for its full storage reference. Until then, this chart follows the comparison filters above.</p>
  </header>
  ${renderBitrateChart(matches)}`;
}

function renderBitrateChart(matches) {
  if (!matches.length) return `<div class="empty-state"><h2>No measured samples match</h2><p>Adjust the driving-video filters above.</p></div>`;
  const maximum = Math.max(...matches.map(item => bitrateMaximum(item.sample.bitrate)));
  return `<section class="section bitrate-chart-section"><h2>Observed bitrate by camera</h2>
    <p class="section-intro">Bars scale to the upper end of each recorded range. That is a charting value, not a manufacturer maximum or a high-quality setting.</p>
    <div class="bitrate-chart">${matches.map(({ camera, sample }) => `<button class="bitrate-chart-row" data-id="${escapeHtml(camera.id)}">
      <span class="chart-label"><strong>${escapeHtml(displayManufacturer(camera.manufacturer))} ${escapeHtml(camera.model)}</strong><small>${escapeHtml(sample.channel)} · ${escapeHtml(sample.resolution)} · ${escapeHtml(sample.fps)} FPS</small></span>
      <span class="chart-track"><i style="width:${Math.max(3, bitrateMaximum(sample.bitrate) / maximum * 100)}%"></i><strong>${escapeHtml(sample.bitrate)}</strong></span>
      <small class="chart-configuration">${escapeHtml(sample.recording_configuration || "Configuration not recorded")}</small>
    </button>`).join("")}</div>
  </section>`;
}

function renderDetail(camera) {
  const folders = camera.recording;
  const manual = camera.sources.some(source => source.kind === "manual");
  return `
    <header>
      <p class="detail-kicker">${escapeHtml(displayManufacturer(camera.manufacturer).toUpperCase())}</p>
      <h1 class="detail-title">${escapeHtml(camera.model)}</h1>
      <div class="badges">
        <span class="badge evidence">${escapeHtml(label(camera.evidence.level))}</span>
        <span class="badge">Confidence: ${escapeHtml(label(camera.evidence.confidence))}</span>
        ${manual ? '<span class="badge">Manual linked</span>' : ""}
      </div>
      <div class="coverage">
        ${coverage("Folder map", allFolders(camera).length > 0)}
        ${coverage("Filename rules", camera.filename_patterns.length > 0)}
        ${coverage("Measured video", camera.video_samples.length > 0)}
        ${coverage("Manual", manual)}
      </div>
      ${camera.evidence.note ? `<p class="callout">${escapeHtml(camera.evidence.note)}</p>` : ""}
    </header>
    ${renderVariants(camera.channel_variants)}
    ${renderFolderSection("Driving recordings", folders.driving_folders)}
    ${renderParking(camera)}
    ${renderFolderSection("Photos, GPS, and support folders", folders.other_folders)}
    ${renderPatterns(camera.filename_patterns)}
    ${renderVideoSamples(camera.video_samples)}
    ${renderFacts(camera.technical_facts)}
    ${renderNotes(camera.notes)}
    ${renderSources(camera.sources)}
    <p class="section-intro">Only documented or observed details are shown. Firmware, settings, region, and connected-camera configuration can change the files a dashcam records.</p>`;
}

function coverage(name, available) { return `<span class="${available ? "yes" : ""}">${available ? "●" : "○"} ${escapeHtml(name)}</span>`; }

function renderVariants(variants) {
  if (!variants.length) return "";
  return section("Camera configurations", `<div class="cards">${variants.map(variant => `
    <div class="card"><div class="card-head"><strong>${escapeHtml(variant.channels ? `${variant.channels}-channel` : "Channel count unknown")}${variant.variant ? ` · ${escapeHtml(variant.variant)}` : ""}</strong><span class="mode">${escapeHtml(label(variant.validation || "not stated"))}</span></div>
    <div class="meta">${escapeHtml(variant.roles.length ? variant.roles.map(label).join(", ") : "Camera positions not recorded")}</div></div>`).join("")}</div>`);
}

function renderFolderSection(title, folders) {
  if (!folders.length) return "";
  return section(title, `<div class="cards">${folders.map(folder => `
    <div class="card"><div class="card-head"><strong><code>${escapeHtml(folder.path)}</code></strong><span class="mode">${escapeHtml(label(folder.mode))}</span></div>
    ${folder.validation ? `<div class="meta">Evidence: ${escapeHtml(label(folder.validation))}</div>` : ""}
    ${folder.notes.map(note => `<div class="meta">${escapeHtml(note)}</div>`).join("")}</div>`).join("")}</div>`);
}

function renderParking(camera) {
  const folders = camera.recording.parking_folders;
  const modes = camera.recording.parking_modes;
  if (!folders.length && !modes.length) return "";
  return section("Parking recordings", `${modes.length ? `<p class="section-intro"><strong>Documented modes:</strong> ${escapeHtml(modes.map(label).join(", "))}</p>` : ""}${folders.length ? `<div class="cards">${folders.map(folder => `<div class="card"><div class="card-head"><strong><code>${escapeHtml(folder.path)}</code></strong><span class="mode">${escapeHtml(label(folder.mode))}</span></div>${folder.notes.map(note => `<div class="meta">${escapeHtml(note)}</div>`).join("")}</div>`).join("")}</div>` : ""}`);
}

function renderPatterns(patterns) {
  if (!patterns.length) return "";
  return section("Filename conventions", `<div class="cards">${patterns.map(pattern => `
    <div class="card"><code class="pattern">${escapeHtml(pattern.pattern)}</code><dl class="token-grid">
      ${pattern.applies_to.length ? row("Folders", pattern.applies_to.join(", ")) : ""}
      ${pattern.timestamp_format ? row("Timestamp", pattern.timestamp_format) : ""}
      ${Object.keys(pattern.modes).length ? row("Recording tokens", mapText(pattern.modes)) : ""}
      ${Object.keys(pattern.channels).length ? row("Channel tokens", mapText(pattern.channels)) : pattern.default_channel ? row("Channel", label(pattern.default_channel)) : ""}
    </dl></div>`).join("")}</div>`);
}

function renderVideoSamples(samples) {
  if (!samples.length) return "";
  return section("Measured video samples", `<div class="sample-grid">${samples.map(sample => `
    <div class="card"><div class="card-head"><strong>${escapeHtml(sample.channel)}</strong><span class="mode">${escapeHtml(label(sample.mode))}</span></div>
    <div class="meta">${escapeHtml([sample.codec, sample.resolution, `${sample.fps} FPS`, sample.bitrate].filter(value => value && value !== "Unknown").join(" · "))}</div>
    <div class="meta">${escapeHtml(`${sample.container} · ${sample.source}`)}</div>
    ${sample.recording_configuration ? `<div class="meta"><strong>Recorded configuration:</strong> ${escapeHtml(sample.recording_configuration)}</div>` : ""}
    ${sample.settings_note ? `<div class="meta"><strong>Settings note:</strong> ${escapeHtml(sample.settings_note)}</div>` : ""}</div>`).join("")}</div>`);
}

function renderFacts(facts) {
  if (!facts.length) return "";
  return section("Additional technical facts", `<dl class="fact-grid">${facts.map(fact => row(fact.label.split(" › ").map(label).join(" › "), fact.value)).join("")}</dl>`);
}

function renderNotes(notes) {
  if (!notes.length) return "";
  return section("Known caveats", `<div class="cards">${notes.map(note => `<div class="card">${escapeHtml(note)}</div>`).join("")}</div>`);
}

function renderSources(sources) {
  return section("Manuals and research sources", sources.length ? `<div class="source-list">${sources.map(source => `<a href="${escapeHtml(source.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(source.label)} ↗</a>`).join("")}</div>` : '<p class="section-intro">No direct source link is recorded yet.</p>');
}

function section(title, body) { return `<section class="section"><h2>${escapeHtml(title)}</h2>${body}</section>`; }
function row(term, description) { return `<dt>${escapeHtml(term)}</dt><dd>${escapeHtml(label(description))}</dd>`; }
function mapText(map) { return Object.keys(map).sort(naturalCompare).map(key => `${key} = ${label(map[key])}`).join(", "); }
function allFolders(camera) { return [...camera.recording.driving_folders, ...camera.recording.parking_folders, ...camera.recording.other_folders]; }
function displayManufacturer(value) { return ({ blackvue: "BlackVue", viofo: "VIOFO", gopro: "GoPro", dji: "DJI" })[value.toLowerCase()] || value; }
function label(value) { return String(value ?? "").replaceAll("_", " ").replace(/\b\w/g, character => character.toUpperCase()); }
function naturalCompare(a, b) { return a.localeCompare(b, undefined, { numeric: true, sensitivity: "base" }); }
function escapeHtml(value) { return String(value ?? "").replace(/[&<>"]/g, character => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[character]); }
