"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
global.document = { addEventListener() {} };
const root = path.join(__dirname, "..");
const source = fs.readFileSync(path.join(root, "docs/assets/app.js"), "utf8");
const cameras = JSON.parse(fs.readFileSync(path.join(root, "docs/data/cameras.json"))).cameras;
eval(`${source}
const camera = cameras.find(item => item.id === "ddpai-z100-master");
const before = JSON.stringify(camera);
const html = renderDetail(camera);
const summary = renderZ100Specs(camera);
assert(html.indexOf("Video specs") < html.indexOf("Recording evidence and technical details"));
assert(html.includes('<details class="technical-details"><summary>'));
assert(!html.includes('<details class="technical-details" open'));
assert.equal((summary.match(/<tbody>/g) || []).length, 6);
assert.equal((summary.match(/<tr><th scope="row">/g) || []).length, 14);
assert(!summary.includes("inside"));
assert(!summary.includes("individual clips"));
assert(!summary.includes("short/partial"));
assert(summary.includes("no measured 4CH video specs yet"));
assert(summary.includes("unresolved driving/parking"));
const three = camera.video_samples.filter(s => s.recording_configuration === "3CH: front/telephoto/rear" && s.mode.startsWith("driving"));
assert.deepEqual(z100SpecRows(three), [
 {camera:"Front", resolution:"3840 × 2160", fps:"30", bitrate:"41.82–42.03", codec:"H.265"},
 {camera:"Telephoto", resolution:"2560 × 1440", fps:"25", bitrate:"8.72–9.35", codec:"H.265"},
 {camera:"Rear", resolution:"3840 × 2160", fps:"25", bitrate:"29.68–29.93", codec:"H.265"}
]);
const historical = camera.video_samples.filter(s => s.recording_configuration.startsWith("Two observed labels:") && s.mode.startsWith("driving"));
assert.equal(z100SpecRows(historical).length, 4, "codec variants remain separate");
assert.equal(z100SpecRows([{channel:"front",resolution:"3840x2160",codec:"Unknown",fps:"Unknown",bitrate:"Unknown"}])[0].bitrate, "Not measured");
assert.equal(JSON.stringify(camera), before, "rendering cannot mutate source occurrences");
assert.equal((html.match(/<div class="card"><div class="card-head"><strong>/g) || []).length >= camera.video_samples.length, true);
for (const other of cameras.filter(item => item.id !== camera.id)) {
 assert(!renderDetail(other).includes('class="technical-details"'), other.id);
 assert(renderDetail(other).includes(renderVideoSamples(other.video_samples)), other.id);
}
console.log(JSON.stringify({groups:6,rows:14,driving:z100SpecRows(three)}, null, 2));
`);
console.log("Reader-first summary verification passed; source samples and other models preserved");
