#!/usr/bin/env python3
"""Verify owner E1 Pro S power import without borrowing other testers' evidence."""
import argparse
import csv
import importlib.util
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    34: (91, 1.13, 'hybrid', 'time-lapse', 1),
    35: (202, 2.50, 'hybrid', 'event-recording', 1),
    36: (45, 0.56, 'hybrid', 'time-lapse', 2),
    37: (202, 2.50, 'hybrid', 'event-recording', 2),
    38: (92, 1.14, 'time-lapse', 'time-lapse', 1),
    40: (10, 0.12, 'impact-sleep', 'monitoring', None),
    41: (247, 3.06, 'unbuffered-event', 'event-recording', None),
}
URL = 'https://vortexopenclaw.github.io/dashcam-camera-profiles/parking-mode.html#vortex-radar-testing'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, help='Optional private read-only sheet snapshot')
    parser.add_argument('--baseline-ref', help='Optional git ref predating this import')
    args = parser.parse_args()
    rows = json.loads((ROOT / 'parking/measurements.json').read_text())
    sources = json.loads((ROOT / 'parking/sources.json').read_text())
    by_id = {r['id']: r for r in rows}
    assert len(rows) == len(by_id), 'Duplicate measurement IDs'
    imported = {f'vortex-sheet-row-{n}' for n in EXPECTED}
    owner = [r for r in rows if r['tester'] == 'Vortex Radar' and r['model'] == 'E1 Pro S']
    assert {r['id'] for r in owner} == imported, 'Unexpected or missing owner rows'
    nulls = ['wake_seconds', 'wake_seconds_min', 'wake_seconds_max', 'reported_startup_seconds',
             'reported_startup_seconds_min', 'reported_startup_seconds_max', 'prebuffer_s',
             'prebuffer_motion_s', 'prebuffer_impact_s', 'date', 'connectivity']
    for n, (ma, watts, category, state, interval) in EXPECTED.items():
        r = by_id[f'vortex-sheet-row-{n}']
        assert (r['brand'], r['model'], r['installed_channels'], r['active_channels']) == ('Vantrue', 'E1 Pro S', 1, ['front'])
        assert (r['current_ma'], r['power_w'], r['category'], r['state']) == (ma, watts, category, state)
        assert r['voltage_v'] is None and r['reported_parking_voltage_v'] == 12.6
        assert r['firmware'] == 'VT-EFI242' and r['power_path'] == 'VP03(II)'
        assert r['source_is_private'] is True and r['source_url'] == URL
        assert r['image_url'] is None and r['power_is_derived'] is False
        assert r['test_status'] == 'unknown' and r['review_status'] == 'verified'
        assert r['superseded'] is False and r['measurement_statistic'] == 'reported'
        assert all(r.get(k) is None for k in nulls)
        assert r.get('recording_seconds_per_frame') == interval
        assert 'inconsistent' in r['notes'] and r['power_consistency_note']
        assert r['source_review_date'] == '2026-10-21'
        if category == 'hybrid':
            assert r['behavior_observation_status'] == 'provisional'
            assert 'within a file' in r['behavior_observation']
    assert not any(f'vortex-sheet-row-{n}' in by_id for n in [39, 42, 43, 44, 45])
    source = next(s for s in sources if s['id'] == 'vortex-sheet')
    assert source['private'] is True and source['url'] == URL
    assert source['measurement_count'] == sum(r['id'].startswith('vortex-sheet-row-') for r in rows)
    if args.snapshot:
        sheet = json.loads(args.snapshot.read_text())[0]['rows']
        measured = {n for n, r in enumerate(sheet, 1) if r and r[0].startswith('Vantrue E1 Pro S,') and len(r) > 1 and r[1]}
        assert measured == set(EXPECTED)
        for n in EXPECTED:
            s, r = sheet[n - 1], by_id[f'vortex-sheet-row-{n}']
            assert (int(s[1]), float(s[2]), s[4], float(s[5]), s[6]) == (r['current_ma'], r['power_w'], r['firmware'], r['reported_parking_voltage_v'], r['power_path'])
            assert r['source_configuration'] == s[0]
        print('Private snapshot parity: exactly seven measured rows, no blank-current imports')
    if args.baseline_ref:
        def baseline(path):
            return json.loads(subprocess.check_output(['git', 'show', f'{args.baseline_ref}:{path}'], cwd=ROOT))
        old = baseline('parking/measurements.json')
        assert [r for r in rows if r['id'] not in imported] == old, 'Existing measurement changed'
        assert len(rows) == len(old) + 7
        old_sources = baseline('parking/sources.json')
        assert len(sources) == len(old_sources)
        for old_s, new_s in zip(old_sources, sources):
            if old_s['id'] == 'vortex-sheet':
                assert {k: v for k, v in old_s.items() if k not in ['notes', 'measurement_count']} == {k: v for k, v in new_s.items() if k not in ['notes', 'measurement_count']}
            else:
                assert old_s == new_s
        assert baseline('parking/metadata.json') == json.loads((ROOT / 'parking/metadata.json').read_text())
        print(f'Baseline preservation: all {len(old)} prior measurements and unrelated sources unchanged')
    spec = importlib.util.spec_from_file_location('parking_build', ROOT / 'scripts/build-parking-data.py')
    assert spec is not None and spec.loader is not None
    build = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build)
    build.validate(rows, sources)
    paths = [ROOT / 'docs/data/parking-measurements.json', ROOT / 'docs/data/parking-measurements.csv']
    before = [p.read_bytes() for p in paths]
    payload = build.build()
    assert before == [p.read_bytes() for p in paths], 'Stale exports'
    assert {r['id']: r for r in payload['measurements']} == by_id
    exports = list(csv.DictReader(paths[1].open(newline='')))
    assert len(exports) == len(rows) and {r['id'] for r in exports} == set(by_id)
    csv_rows = {r['id']: r for r in exports}
    for row in owner:
        assert all(csv_rows[row['id']][k] == build.csv_cell(row.get(k)) for k in csv_rows[row['id']])
    assert set().union(*(set(r) for r in rows)) <= set(exports[0])
    for text in [p.read_text() for p in paths] + [json.dumps(sources)]:
        assert 'docs.google.com/spreadsheets' not in text and 'sheets.google.com' not in text
    print(f'E1 Pro S owner power verification passed: 7 imports, {len(rows)} total measurements, {payload["coverage"]["models"]} models, {len(sources)} sources')


if __name__ == '__main__':
    main()
