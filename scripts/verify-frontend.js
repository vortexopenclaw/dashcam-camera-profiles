"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

global.document = { addEventListener() {} };
const source = fs.readFileSync(path.join(__dirname, "..", "docs", "assets", "app.js"), "utf8");
const cameras = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "docs", "data", "cameras.json"), "utf8")).cameras;
eval(`${source}
assert.equal(bitrateMaximum("~25.1 Mbps at 60 fps"), 25.1);
assert.equal(bitrateMaximum("~53-66 Mbps"), 66);
assert.equal(bitrateMaximum("Unknown"), 0);
const rows = [
  { camera: { manufacturer: "VIOFO", model: "Sixty FPS" }, sample: { bitrate: "~25.1 Mbps at 60 fps" } },
  { camera: { manufacturer: "BlackVue", model: "Range" }, sample: { bitrate: "~53-66 Mbps" } }
];
state.qualitySort = "bitrate_desc";
assert.equal(rows.sort(qualityCompare)[0].camera.model, "Range");
state.qualitySort = "brand";
assert.equal(rows.sort(qualityCompare)[0].camera.model, "Range");`);

eval(`${source}
state.cameras = cameras;
state.qualityChannel = "front";
const measured = drivingSamples();
assert(measured.some(item => item.camera.id === "vueroid-s1-4k-infinite" && item.role === "front"));
assert.equal(measured.filter(item => item.camera.id === "escort-m1").length, 2);
assert.equal(measured.find(item => item.camera.id === "escort-m1").sample.bitrate, "11.9–16.4 Mbps");
assert(measured.some(item => item.camera.id === "escort-m1" && item.sample.source === "reviewed archive metadata" && item.sample.bitrate === "10.0-11.9 Mbps"));
assert.equal(formatBitrate("53.622752 Mbps"), "53.6 Mbps");
assert.equal(formatBitrate("53.262752 Mbps", 0), "53 Mbps");
for (const camera of cameras) assert(measured.some(item => item.camera.id === camera.id && item.role === "front") || unmeasuredCameras().some(item => item.id === camera.id));
state.qualityBrand = "70mai";
assert(measured.some(item => item.camera.id === "70mai-t800" && item.role === "front"));
assert(measured.some(item => item.camera.id === "70mai-x800" && item.role === "front"));
assert(!cameras.find(camera => camera.id === "escort-m2").video_samples.some(sample => sample.resolution === "3840x2160"));
assert.equal(label("real_card_sampled"), "Card sampled");`);
eval(`${source}
state.cameras = cameras;
const normalFront = drivingSamples().find(item => item.camera.id === "viofo-t340" && item.role === "front" && configurationSetting(item.sample) === "Normal");
assert.deepEqual(configurationCompanions(normalFront).map(sample => cameraRole(sample.channel)).sort(), ["front_telephoto", "interior", "rear"]);
assert(configurationCompanions(normalFront).every(sample => configurationSetting(sample) === "Normal"));`);

console.log("Frontend verification passed: bitrate parsing ignores resolution and frame-rate numbers");
eval(`${source}
state.cameras = cameras;
state.qualityBrand = "";
state.qualityChannel = "front";
state.qualityResolution = "3840x2160";
state.qualityFps = "30";
assert(!qualityMatches().some(item => item.camera.id === "metadata-only-rove-r2-4k-dual"));
assert(!qualityMatches().some(item => item.camera.id === "metadata-only-rove-r2-4k"));
assert(!qualityMatches().some(item => item.camera.id === "rexing-v1-4k"));
assert(qualityMatches().some(item => item.camera.id === "rove-r2-4k-pro"));
assert(drivingSamples().some(item => item.camera.id === "metadata-only-rove-r2-4k-dual"));`);
eval(`${source}
state.cameras = cameras;
state.qualityResolution = "3840x2160";
state.qualityFps = "30";
for (const id of ["70mai-t800", "70mai-x800", "vantrue-e1-pro", "thinkware-u1000-plus", "thinkware-arc-800", "cansonic-ultradash-z4-standard", "metadata-only-wolfbox-g900-pro"]) {
  assert(qualityMatches().some(item => item.camera.id === id), id);
}
assert(!drivingSamples().some(item => item.sample.mode.includes("parking")));
assert(!qualityMatches().some(item => item.camera.id === "blackvue-dr970x-lte-plus"));`);
