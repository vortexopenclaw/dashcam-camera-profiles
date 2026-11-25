#!/usr/bin/env python3
"""Source-exact regression for the 2026-11-24 rcg530 refresh plus full pre-import preservation."""
from copy import deepcopy
import csv
from decimal import Decimal
import json
from pathlib import Path
import subprocess
import rcg530_20261124 as later

R = Path(__file__).resolve().parents[1]
def load(path): return json.loads((R/path).read_text())
def old(path): return json.loads(subprocess.check_output(['git', 'show', f'{later.BASELINE}:{path}'], cwd=R))

T330 = [(31,'0.39'),(32,'0.40'),(31,'0.39'),(31,'0.39'),(462,'5.82'),(565,'7.12'),(353,'4.45'),(358,'4.51'),
        (442,'5.57'),(548,'6.91'),(331,'4.17'),(328,'4.13'),(455,'5.73'),(559,'7.04'),(340,'4.28'),(336,'4.23'),
        (443,'5.58'),(548,'6.91'),(332,'4.18'),(339,'4.27'),(417,'5.25'),(523,'6.59'),(314,'3.96'),(319,'4.02'),
        (393,'4.95'),(497,'6.26'),(299,'3.77'),(305,'3.84'),(248,'3.13'),(339,'4.27'),(194,'2.44'),(195,'2.46')]
T340 = [(34,'0.43'),(35,'0.44'),(33,'0.42'),(33,'0.42'),(530,'6.68'),(591,'7.45'),(503,'6.34'),(501,'6.31'),
        (525,'6.62'),(576,'7.26'),(491,'6.19'),(490,'6.17'),(540,'6.80'),(590,'7.43'),(502,'6.33'),(502,'6.33'),
        (511,'6.44'),(566,'7.13'),(493,'6.21'),(492,'6.20'),(469,'5.91'),(533,'6.72'),(464,'5.85'),(463,'5.83'),
        (445,'5.61'),(510,'6.43'),(439,'5.53'),(440,'5.54'),(315,'3.97'),(368,'4.64'),(299,'3.77'),(297,'3.74')]
A229 = {'LBR-all-day': (664,'8.37'), 'LBR-all-night': (796,'10.03'), 'LBR-icoff-day': (535,'6.74'), 'LBR-icoff-night': (538,'6.78'),
        'TLR10-all-day': (594,'7.48'), 'TLR10-all-night': (728,'9.17'), 'TLR10-icoff-day': (481,'6.06'), 'TLR10-icoff-night': (484,'6.10')}
STATES = {'LPID_monitoring': ('impact-sleep','monitoring'), 'LPID_unbuffered_recording': ('impact-sleep','event-recording'),
          'AED_monitoring': ('buffered-event','monitoring'), 'AED_buffered_recording': ('buffered-event','event-recording'),
          'LBR': ('low-bitrate','continuous'), 'TLR_10fps': ('time-lapse','time-lapse'), 'TLR_1fps': ('time-lapse','time-lapse'),
          'TLR_1fps_NV': ('time-lapse','time-lapse')}


def within_display_precision(ma, watts, volts=Decimal('12.6')):
    return abs(Decimal(watts) - Decimal(ma) * volts / 1000) <= volts * Decimal('0.5') / 1000 + Decimal('0.005')


def verify(rows, sources):
    by_id = {r['id']: r for r in rows}
    for post, model, values, roles in [('674502','T330',T330,['front','interior','rear']), ('674496','T340',T340,['front','interior','rear','telephoto'])]:
        cohort = [r for r in rows if r['id'].startswith(f'rcg530-{post}-')]
        assert len(cohort) == 32, (post, len(cohort))
        for r, (ma, watts) in zip(cohort, values):
            assert (r['current_ma'], Decimal(str(r['power_w']))) == (ma, Decimal(watts)), r['id']
            assert within_display_precision(ma, watts), r['id']
            assert r['model'] == model and r['firmware'] == 'v1.0_261030' and r['voltage_v'] == 12.6 and r['tester'] == 'rcg530'
            assert (r['category'], r['state']) == STATES[r['source_mode']], r['id']
            assert r['installed_channels'] == len(roles) and r['measurement_statistic'] == 'average'
            assert r['active_channels'] == ([c for c in roles if c != 'interior'] if '-icoff-' in r['id'] else roles), r['id']
            assert r['ir'] == 'unknown' and r['test_status'] == 'unknown' and r['power_path'] is None
            assert r['wake_seconds'] is None and r['reported_startup_seconds'] is None and not r['power_is_derived']
            assert r['lighting'] in ('day', 'night') and r['id'].endswith(r['lighting'])
    for key, (ma, watts) in A229.items():
        r = by_id[f'rcg530-677657-{key}']
        assert (r['current_ma'], Decimal(str(r['power_w']))) == (ma, Decimal(watts)) and within_display_precision(ma, watts)
        assert r['firmware'] == 'V1.2_260813 (front) / 4K_V1.1_260126 (rear)' and r['power_path'] == 'VIOFO HK6-F hardwire kit, 12-volt side'
        assert r['active_channels'] == (['front','rear'] if 'icoff' in key else ['front','rear','interior'])
    assert len([r for r in rows if r['id'].startswith('rcg530-677657-')]) == 8
    e = by_id['rcg530-675957-12']
    assert (e['current_ma'], e['power_w'], e['recording_seconds_per_frame'], e['recording_fps']) == (45, 0.57, 2, None)
    assert (e['category'], e['state'], e['test_status']) == ('hybrid', 'time-lapse', 'prototype')
    # Refreshed links only: every earlier A900 Ultra / E1 Pro S value is unchanged.
    for prefix, (_, new) in later.IMAGE_LINKS.items():
        assert all(r['image_url'] == new for r in rows if r['id'].startswith(prefix))
    src = {s['id']: s for s in sources}
    assert [src[i]['measurement_count'] for i in later.NEW_SOURCE_IDS] == [32, 32, 8, 0, 0, 0, 0]
    assert src['rcg530-675957']['measurement_count'] == 12 and src['rcg530-675874']['measurement_count'] == 13
    # Whole-file preservation against the pinned pre-import commit.
    assert later.restore_rows(rows) == old('parking/measurements.json')
    assert later.restore_rows(sources, True) == old('parking/sources.json')
    for path in ['parking/metadata.json', 'profiles/viofo-t340.json',
                 'profiles/viofo-a229-ultra.json', 'docs/data/cameras.json', 'docs/data/parking-measurements.json']:
        assert later.restore_loaded(path, load(path)) == old(path), path
    csv_rows = list(csv.DictReader((R/'docs/data/parking-measurements.csv').open()))
    old_csv = list(csv.DictReader(subprocess.check_output(['git','show',f'{later.BASELINE}:docs/data/parking-measurements.csv'],cwd=R,text=True).splitlines()))
    assert later.restore_rows(csv_rows) == old_csv
    dossier = load(later.DOSSIER)
    assert [c['model'] for c in dossier['charts']] == ['70mai A900 Ultra', 'Viofo T330', 'Viofo T340', 'Viofo A229 Ultra']
    assert len(dossier['charts'][0]['rows']) == 24 and dossier['charts'][0]['firmware'] == 'v1.3.88ww'


rows, sources = load('parking/measurements.json'), load('parking/sources.json')
verify(rows, sources)
# Negative controls: a value mutation in a new row or any earlier row must fail.
for target in ['rcg530-674496-LPID_monitoring-all-day', 'rcg530-675874-2', 'rcg530-660405-1']:
    bad = deepcopy(rows)
    next(r for r in bad if r['id'] == target)['power_w'] += 0.01
    try:
        verify(bad, sources)
    except AssertionError:
        continue
    raise AssertionError(f'mutation accepted: {target}')
print('rcg530 2026-11-24 refresh verified: 73 new rows source-exact, 24 refreshed links value-identical, all prior data exact')
