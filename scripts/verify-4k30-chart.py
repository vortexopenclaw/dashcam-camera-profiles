#!/usr/bin/env python3
"""Verify the two measured T340 Maximum cohorts in the generated comparison."""
import csv
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
rows = json.loads((root / 'docs/data/4k30-comparison.json').read_text())
evidence = json.loads((root / 'docs/data/storage-evidence.json').read_text())
t340 = [row for row in rows if row['id'] == 'viofo-t340']
assert len(t340) == 5, 'Expected historical Low/Normal/High plus Maximum A/B'
assert not any(row['camera'] == 'VIOFO T340 • Maximum' for row in rows)
for label, cohort in [('B', 'bench_tested_4ch'), ('A', 'owner_installed_4ch')]:
    matches = [row for row in rows if row['camera'] == f'VIOFO T340 {label} • Maximum']
    assert len(matches) == 1, f'Expected exactly one T340 {label} Maximum row'
    source = [sample for sample in evidence['pairedSamples']
              if sample.get('model') == 'T340' and sample.get('cameraCohort') == cohort
              and sample.get('settingsLabel') == 'maximum_driving'
              and sample.get('channel') == 'front' and sample.get('mode') in {'continuous', 'protected'}
              and sample.get('width') == 3840 and sample.get('height') == 2160
              and sample.get('nominalFrameRate') == 30 and sample.get('durationSeconds') == 60]
    assert source
    rates = [sample['estimatedBitrate'] / 1_000_000 for sample in source]
    assert matches[0]['lowMbps'] == min(rates)
    assert matches[0]['highMbps'] == max(rates)
    assert matches[0]['codec'] == 'H.264'
    for path in ['docs/4k30-comparison.html', 'docs/t340-comparison.html', 'docs/assets/4k30/comparison.svg']:
        assert f'T340 {label}' in (root / path).read_text(), path
assert all(a['highMbps'] >= b['highMbps'] for a, b in zip(rows, rows[1:]))
with (root / 'docs/assets/4k30/measurements.csv').open(newline='') as file:
    csv_rows = list(csv.DictReader(file))
assert len(csv_rows) == len(rows)
for expected, actual in zip(rows, csv_rows):
    for key, value in expected.items():
        assert str(value) == actual[key], (key, value, actual[key])
assert 'id="maximum-camera-cohorts"' in (root / 'docs/t340-comparison.html').read_text()
assert 'A/B are unit labels, not product revisions' in (root / 'docs/4k30-comparison.html').read_text()
print('Verified T340 A/B source-exact Maximum rates, descending order, HTML/SVG labels, CSV parity and retained cohort notes')
