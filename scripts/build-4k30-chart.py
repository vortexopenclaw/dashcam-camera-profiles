#!/usr/bin/env python3
"""Compare only measured driving, primary-front 3840x2160 / 30 fps samples."""
import csv
import hashlib
import html
import json
import re
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/assets/4k30'
OUT.mkdir(parents=True, exist_ok=True)
rows = []
for path in sorted((ROOT / 'profiles').glob('*.json')):
    camera = json.loads(path.read_text())
    if camera['id'] == 'viofo-t340':
        continue
    if any(f['label'] == 'Front capture classification' and f['value'] == 'upscaled_4k' for f in camera['technical_facts']):
        continue
    samples = camera['video_samples']
    if camera['id'] == 'viofo-a329s':
        # Prefer the confirmed Maximum 2CH scan for this comparison; retain
        # the older unknown-setting 3CH evidence in the canonical profile.
        samples = [s for s in samples if (s.get('settings_note') or '').startswith('Maximum bitrate')]
    for sample in samples:
        channel = sample['channel'].lower()
        primary_front = 'telephoto' not in channel and ('front' in channel or re.match(r'^(f|mf|nf)\b', channel))
        driving_only = 'driving' in sample['mode'].lower().split(' / ') and 'parking' not in sample['mode'].lower()
        fps30 = any(abs(float(fps) - 30) < .15 for fps in re.findall(r'\d+(?:\.\d+)?', sample['fps']))
        if not (driving_only and primary_front and sample['resolution'] == '3840x2160' and fps30):
            continue
        rates = [float(v) for v in re.findall(r'\d+(?:\.\d+)?', sample['bitrate'])]
        if not rates:
            continue
        name = f"{camera['manufacturer']} {camera['model']}"
        rows.append(dict(id=camera['id'], camera=name, lowMbps=min(rates), highMbps=max(rates), codec=sample['codec'], configuration=sample.get('recording_configuration') or 'Not recorded', settings=sample.get('settings_note') or 'Quality setting not recorded', source=sample['source']))

data = json.loads((ROOT / 'docs/data/t340-quality-comparison.json').read_text())
for row in data['rows']:
    if row['setting'] not in ['Low', 'Normal', 'High', 'Maximum']:
        continue
    value = next(c['videoMbps'] for c in row['channels'] if c['channel'] == 'front')
    setting = row['setting'].replace(' 3CH', '')
    rows.append(dict(id='viofo-t340', camera=f"VIOFO T340 • {setting}", lowMbps=value, highMbps=value, codec='H.264', configuration=f"{row['channelCount']} cameras; firmware {data['firmware']}", settings=setting, source='Reviewed T340 front-camera measurements'))

rows.sort(key=lambda r: (-r['highMbps'], r['camera']))
assert rows, 'No measured 4K30 front-camera data'
assert all(a['highMbps'] >= b['highMbps'] for a, b in zip(rows, rows[1:]))
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 12, 'svg.fonttype': 'none'})
fig, axis = plt.subplots(figsize=(13, max(12, len(rows) * .5 + 2)))
fig.subplots_adjust(left=.31, right=.91, top=.87, bottom=.15)
for i, row in enumerate(rows):
    highlight = row['id'] == 'viofo-t340'
    axis.barh(i, row['highMbps'], height=.65, color='#dc7732' if highlight else '#277c9c')
    if row['lowMbps'] != row['highMbps']:
        axis.plot([row['lowMbps'], row['highMbps']], [i, i], color='#182733', linewidth=2, marker='|', markersize=12)
    label = f"{row['highMbps']:.2f}" if highlight else f"{row['lowMbps']:g}–{row['highMbps']:g}" if row['lowMbps'] != row['highMbps'] else f"≈{row['highMbps']:g}"
    axis.text(row['highMbps'] + .8, i, label, va='center', fontsize=11, fontweight='bold' if highlight else 'normal')
axis.set_yticks(range(len(rows)), [r['camera'] for r in rows])
axis.invert_yaxis()
axis.set_xlim(0, 78)
axis.set_xlabel('Video bitrate (Mbps)', labelpad=12)
axis.grid(axis='x', alpha=.15)
axis.set_axisbelow(True)
for spine in axis.spines.values():
    spine.set_visible(False)
for label, row in zip(axis.get_yticklabels(), rows):
    if row['id'] == 'viofo-t340':
        label.set_fontweight('bold')
fig.suptitle('4K30 front-camera bitrate comparison', fontsize=22, fontweight='bold', y=.97)
fig.text(.5, .923, 'Measured driving video • Highest observed bitrate first • T340 highlighted', ha='center', fontsize=12)
fig.text(.06, .092, f'{len({r["id"] for r in rows})} cameras with measured front 4K30 data • Known upscaled models excluded • Audio excluded.', fontsize=11)
fig.text(.06, .064, 'Ranges use the upper end for ordering; dark marks show the range. Unknown quality settings are not “Maximum.”', fontsize=11)
fig.text(.06, .036, 'Codecs, HDR, scenes and camera configurations differ. Higher bitrate alone does not establish better image quality.', fontsize=11)
for extension in ['png', 'svg']:
    fig.savefig(OUT / f'comparison.{extension}', dpi=160, facecolor='white')
plt.close(fig)
svg = OUT / 'comparison.svg'
svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines()) + '\n')
with (OUT / 'measurements.csv').open('w', newline='') as file:
    writer = csv.DictWriter(file, fieldnames=list(rows[0]), lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
(ROOT / 'docs/data/4k30-comparison.json').write_text(json.dumps(rows, indent=2) + '\n')
def asset(extension):
    digest = hashlib.sha256((OUT / f'comparison.{extension}').read_bytes()).hexdigest()[:12]
    return f'assets/4k30/comparison.{extension}?v={digest}'

SECTION = f'<section id="4k30-comparison"><h2>4K30 front-camera comparison</h2><a href="{asset("png")}"><img src="{asset("png")}" alt="Descending measured 4K30 front-camera video bitrates, highlighting T340 configurations" loading="lazy"></a><p>Measured driving video, not advertised maximums. Audio excluded. <a href="4k30-comparison.html">Settings, codecs and measurement notes</a> · <a href="{asset("png")}">PNG</a> · <a href="{asset("svg")}">SVG</a> · <a href="assets/4k30/measurements.csv">CSV</a></p></section>'
unranked = json.loads((ROOT / 'docs/data/4k30-unranked.json').read_text())
pending = '<section id="unranked"><h2>Additional 4K models not yet ranked</h2><p>These known models are not silently omitted or assigned borrowed values. They need a comparable front-camera, driving-only video bitrate at 4K30. This covers our reviewed library and research, not every dashcam on the market.</p><ul>' + ''.join(f'<li><strong>{html.escape(r["camera"])}</strong>: {html.escape(r["reason"])} <a href="{html.escape(r["source"])}">Evidence</a></li>' for r in unranked) + '</ul></section>'
SECTION = SECTION.replace('</section>', '<p><a href="4k30-comparison.html#unranked">Additional 4K models still awaiting comparable measurements</a></p></section>')
table = ''.join('<tr>' + ''.join(f'<td>{html.escape(str(value))}</td>' for value in [r['camera'], f"{r['lowMbps']:g}–{r['highMbps']:g}", r['codec'], r['configuration'], r['settings'], r['source']]) + '</tr>' for r in rows)
(ROOT / 'docs/4k30-comparison.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>4K30 front-camera bitrate comparison</title><style>body{font:16px system-ui;max-width:1100px;margin:32px auto;padding:0 18px;line-height:1.6;color:#182733}img{width:100%;height:auto}.scroll{overflow:auto}table{border-collapse:collapse}td,th{padding:10px;text-align:left;border-bottom:1px solid #ddd}</style><a href="t340-comparison.html">T340 charts</a>' + SECTION + '<p>Includes cameras in the reviewed library with measured primary-front 3840×2160 at 30 fps driving bitrates, excluding known upscaled models such as the Rove R2-4K Dual. File dimensions alone do not prove native 4K capture. Models without those measurements and samples with an unidentified camera position are excluded. This is not a list of every 4K30 dashcam on the market.</p><p>Ranges are sorted by their upper observed endpoint, not a verified maximum-quality setting. T340 rows use the reviewed, configuration-specific front-camera measurements rather than mixed-quality scan ranges. Other quality settings remain unknown unless captured. Codecs, scenes, HDR and connected-camera counts differ; bitrate alone is not an image-quality ranking.</p><div class="scroll"><table><tr><th>Camera</th><th>Video Mbps</th><th>Codec</th><th>Configuration</th><th>Settings / notes</th><th>Measurement source</th></tr>' + table + '</table></div><p><a href="data/4k30-comparison.json">Reviewed data JSON</a> · <a href="./">Camera reference and sources</a></p></html>\n')
print(f'Rendered 4K30 comparison: {len(rows)} rows, {len({r["id"] for r in rows})} cameras')
page = ROOT / 'docs/4k30-comparison.html'
page.write_text(page.read_text().replace('</html>', pending + '</html>'))
