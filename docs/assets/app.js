"use strict";

const state = { cameras: [], selectedId: null, query: "", brand: "", evidence: "" };
const elements = {};

document.addEventListener("DOMContentLoaded", async () => {
  Object.assign(elements, {
    list: document.querySelector("#camera-list"),
    detail: document.querySelector("#camera-detail"),
    search: document.querySelector("#search"),
    brand: document.querySelector("#brand-filter"),
    evidence: document.querySelector("#evidence-filter"),
    resultCount: document.querySelector("#result-count")
  });

  try {
    const response = await fetch("data/cameras.json");
    if (!response.ok) throw new Error(`Reference request failed: ${response.status}`);
    const data = await response.json();
    state.cameras = data.cameras;
    populateStats(data);
    populateFilters();
    bindControls();
    const hashId = decodeURIComponent(location.hash.replace(/^#camera=/, ""));
    state.selectedId = state.cameras.some(camera => camera.id === hashId) ? hashId : state.cameras[0]?.id;
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

  let selected = state.cameras.find(camera => camera.id === state.selectedId);
  if (!selected || !cameras.includes(selected)) {
    selected = cameras[0];
    state.selectedId = selected?.id || null;
  }
  elements.detail.innerHTML = selected ? renderDetail(selected) : `<div class="empty-state"><h2>No cameras match</h2><p>Try a different search or filter.</p></div>`;
}

function selectCamera(id) {
  state.selectedId = id;
  history.replaceState(null, "", `#camera=${encodeURIComponent(id)}`);
  render();
  if (window.matchMedia("(max-width: 900px)").matches) elements.detail.scrollIntoView({ behavior: "smooth" });
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
    <div class="meta">${escapeHtml([sample.codec, sample.resolution, `${sample.fps} FPS`, sample.bitrate].filter(value => value && value !== "—").join(" · "))}</div>
    <div class="meta">${escapeHtml(`${sample.container} · ${sample.source}`)}</div></div>`).join("")}</div>`);
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
