#!/usr/bin/env python3
"""Check reviewed A329T scope, exact sample occurrences, and historical preservation."""
import argparse
import hashlib
import json
from pathlib import Path

R = Path(__file__).resolve().parents[1]

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--private-source', type=Path)
parser.add_argument('--baseline', type=Path)
args = parser.parse_args()
e = json.loads((R/'docs/data/a329t-v2.2_260815-1ch-evidence.json').read_text())
p = json.loads((R/'profiles/viofo-a329t.json').read_text())
index = json.loads((R/'docs/data/cameras.json').read_text())
assert next(c for c in index['cameras'] if c['id'] == p['id']) == p
assert e['owner_assertions'] == {'firmware':'V2.2_260815','channel_count':1,'roles':['front']}
assert all(value is None for value in e['unreported_settings'].values())
assert [len(g['storageRateSamples']) for g in e['groups']] == [5, 10, 8]
assert e['sample_occurrences'] == 23
assert [g['fileCount'] for g in e['groups']] == [10, 83, 499]
assert e['inventory'] == {'video_file_count':592,'photo_file_count':65,'front_inventory_item_count':657}
# Public, identity-free source-exact constants: no filenames, receipt IDs or dates.
expected = [
 [(494927872,60,65542536),(492830720,60,65534644),(492830720,60,65532940),(492830720,60,65537224),(492830720,60,65527488)],
 [(33554432,60,4096430),(2228224,0.5666666666666667,12459445),(33554432,60,4096041),(33554432,60,4137037),(20971520,37.63333333333333,4139012),(35651584,60,4341208),(37748736,60,4661181),(511705088,62,65537856),(494927872,60,65534552),(142606336,17.133333333333333,65585360)],
 [(492830720,60,65530372),(492830720,60,65536536),(494927872,60,65580048),(10616832,1.1333333333333333,67643784),(492830720,60,65321988),(44171264,5.3,65990356),(494927872,60,65546416),(230686720,27.833333333333332,65547484)],
]
assert [(g['folder'],g['mode'],g['channel']) for g in e['groups']] == [('DCIM/Movie/RO','driving_event','front'),('DCIM/Movie/RO','parking_impact_detection','front'),('DCIM/Movie','continuous','front')]
for g, values in zip(e['groups'], expected):
    assert [(s['fileSizeBytes'],s['durationSeconds'],s['videoBitrate']) for s in g['storageRateSamples']] == values
    assert all((s['width'],s['height'],s['nominalFrameRate']) == (3840,2160,30) for s in g['storageRateSamples'])
    assert all(set(s) == {'fileSizeBytes','durationSeconds','videoBitrate','width','height','nominalFrameRate'} for s in g['storageRateSamples'])
assert len(p['video_samples']) == 12
assert digest(p['video_samples'][:6]) == '76bbcd1fa54f8c394fa5a7f5ae42ed3a79f2052629b2b9ba369d1ae769826fea'
new = p['video_samples'][6:]
assert len(e['reviewed_cohorts']) == len(new) == 6
covered = []
for c, row in zip(e['reviewed_cohorts'], new):
    group = e['groups'][c['group_index']]
    samples = [group['storageRateSamples'][i] for i in c['sample_indices']]
    covered.extend((c['group_index'], i) for i in c['sample_indices'])
    assert c['sample_count'] == len(samples)
    low, high = min(s['videoBitrate'] for s in samples), max(s['videoBitrate'] for s in samples)
    assert (c['video_bitrate_bps_min'],c['video_bitrate_bps_max']) == (low,high)
    assert row['bitrate'] == f'{low/1e6:.6f}-{high/1e6:.6f} Mbps'
    assert row['mode'] == c['label'] and 'owner-confirmed firmware V2.2_260815' in row['recording_configuration']
    assert row['codec'] == 'Unknown (app-reported group summary: H.264)'
    assert all((s['durationSeconds'] < 60) == ('short/partial' in c['label']) for s in samples)
assert sorted(covered) == [(gi,i) for gi,g in enumerate(e['groups']) for i in range(len(g['storageRateSamples']))]
assert p['evidence']['level'] == 'manual-backed'
assert any(v['channels'] == 1 and v['roles'] == ['front'] for v in p['channel_variants'])
assert any(s['url'] == e['evidence_url'] for s in p['sources'])

if args.private_source:
    scan = json.loads(args.private_source.read_text())[0]['record']['scan']
    assert len(scan['videoSpecSummaries']) == len(e['groups'])
    for source, public in zip(scan['videoSpecSummaries'], e['groups']):
        assert public == {k:source[k] for k in public}
    assert scan['settingSnapshots'] == [] and scan['videoSpecSamples'] == []
    assert scan['extensionCounts'] == {'mp4':592,'jpg':65}

if args.baseline:
    b = json.loads(args.baseline.read_text())
    old = b['profile']
    assert p['video_samples'][:6] == old['video_samples']
    assert p['channel_variants'][:2] == old['channel_variants']
    assert p['sources'][:-1] == old['sources']
    assert p['technical_facts'][:-1] == old['technical_facts']
    assert p['notes'][:-1] == old['notes']
    assert p['recording'] == old['recording'] and p['filename_patterns'] == old['filename_patterns']
    assert {k:v for k,v in p['evidence'].items() if k != 'note'} == {k:v for k,v in old['evidence'].items() if k != 'note'}
    assert [c for c in index['cameras'] if c['id'] != p['id']] == [c for c in b['index']['cameras'] if c['id'] != p['id']]
    allowed = {'profiles/viofo-a329t.json','docs/data/cameras.json','.github/workflows/validate.yml'}
    for name, sha in b['trackedHashes'].items():
        if name not in allowed:
            assert hashlib.sha256((R/name).read_bytes()).hexdigest() == sha, name
    print('Private source-exact comparison passed; all historical A329T rows and all unrelated tracked bytes unchanged.')
print('A329T verified: 3 groups, 23 exact occurrences, 6 separate cohorts, owner firmware/1CH scope, unknown settings and codec limitations.')
