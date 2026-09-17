"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

global.document = { addEventListener() {} };
const source = fs.readFileSync(path.join(__dirname, "..", "docs", "assets", "app.js"), "utf8");
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

console.log("Frontend verification passed: bitrate parsing ignores resolution and frame-rate numbers");
