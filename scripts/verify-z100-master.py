#!/usr/bin/env python3
"""Verify anonymous Z100 Master cohorts and optional retained-source parity."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

R = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--private-audit', type=Path)
parser.add_argument('--baseline', type=Path)
parser.add_argument('--private-scan', type=Path, help='Optional private stored owner scan for exact numeric parity')
args = parser.parse_args()
e = json.loads((R/'docs/data/ddpai-z100-master-evidence.json').read_text())
p = json.loads((R/'profiles/ddpai-z100-master.json').read_text())
index = json.loads((R/'docs/data/cameras.json').read_text())

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

# Pin the original complete cohorts with only the authorized physical-role correction normalized.
original_cohorts = [{**c, 'physical_role': None if c['channel'] == 'inside' else c['physical_role']} for c in e['cohorts']]
assert digest(original_cohorts) == '561ea7b7a8a4b451e619a284cfc268cdbf46ea484893b93bab390f448f6a227a'
# Preserve occurrence multiplicity, exact strings/numbers, and original observed labels.
sample_multiset = Counter(json.dumps([c['channel'], c['mode'], c['codec'], s], sort_keys=True, separators=(',', ':')) for c in e['cohorts'] for s in c['storageRateSamples'])
assert hashlib.sha256(json.dumps(sorted(sample_multiset.items()), separators=(',', ':')).encode()).hexdigest() == 'b632b09d8180d9328f8ad154bec24d03050609346a96a2200908e00ec47ae4e4'
assert e['channel_role_corrections'] == [{'observed_channel': 'inside', 'physical_role': 'telephoto', 'source': 'owner confirmation', 'reason': 'Owner reports a firmware labeling bug in the current firmware.', 'scope': 'Existing owner Z100 Master card cohort only; no other models or contributors.', 'firmware': None}]
assert 'physical_channel_mapping' not in e['unreported_settings']
assert p['channel_variants'][0]['roles'][1] == 'telephoto (observed label: inside; owner-confirmed)'
assert p['filename_patterns'][2]['default_channel'] == 'telephoto (observed label: inside; owner-confirmed)'
assert 'inside (physical role unknown)' not in json.dumps(p)
assert 'firmware labeling bug' in json.dumps(p)
assert e['channel_role_corrections'][0]['firmware'] is None
assert digest(e['scanner_samples']) == 'b4f2abdc64360f5de429781d086a977c38e3f9c20f078b96c01358f552301855'
assert e['camera_id'] == p['id'] == 'ddpai-z100-master'
assert next(c for c in index['cameras'] if c['id'] == p['id']) == p
assert e['firmware'] is None and all(v is None for v in e['unreported_settings'].values())
assert e['inventory'] == {'video_file_count':401, 'jpeg_file_count':440, 'excluded_appledouble_mp4_sidecars':23}
assert len(e['cohorts']) == 10 and len(p['video_samples']) >= 18
# Pin the exact historical prefix while allowing separately verified append-only cohorts.
assert digest(p['video_samples'][:18]) == '6b0ff2c45dda3e333318656a2925f698a30c2fc7398a41125d137495f28bc2c4'
runpy_3ch = __import__('runpy').run_path(str(R/'scripts/verify-z100-3ch.py'))
runpy_3ch['verify'](json.loads((R/'docs/data/ddpai-z100-master-3ch-evidence.json').read_text()), p)
assert sum(c['sample_count'] for c in e['cohorts']) == e['sample_occurrences'] == 401
assert len(e['scanner_samples']) == e['scanner_sample_occurrences'] == 19
assert Counter(x['group_index'] for x in e['scanner_samples']) == {0:10, 1:9}
assert any(s['url'] == e['evidence_url'] for s in p['sources'])
codec_counts = Counter()
channel_counts = Counter()
for c, row in zip(e['cohorts'], p['video_samples']):
    samples = c['storageRateSamples']
    assert c['sample_count'] == len(samples)
    codec_counts[c['codec']] += len(samples)
    channel_counts[c['channel']] += len(samples)
    rates = [s['videoBitrate'] for s in samples]
    assert (min(rates), max(rates), sum(rates)) == (c['video_bitrate_bps_min'], c['video_bitrate_bps_max'], c['video_bitrate_bps_sum'])
    assert c['video_bitrate_bps_mean'] == sum(rates)/len(rates)
    assert row['bitrate'] == f'{min(rates)/1e6:.6f}-{max(rates)/1e6:.6f} Mbps'
    assert row['mode'] == c['mode'] + ' ' + c['length_class']
    assert all(set(s) == {'fileSizeBytes','durationSeconds','videoBitrate','width','height','nominalFrameRate','averageFrameRate','containerDurationSeconds','containerBitrate'} for s in samples)
    assert all((float(s['durationSeconds']) >= 59.9) == (c['length_class'] == 'full-length') for s in samples)
    assert all((s['width'],s['height'],s['nominalFrameRate']) == (c['width'],c['height'],c['nominalFrameRate']) for s in samples)
    assert row['resolution'] == f"{c['width']}x{c['height']}"
    if c['channel'] == 'inside':
        assert c['physical_role'] == 'telephoto'
        assert row['channel'] == 'telephoto (observed label: inside; owner-confirmed)'
        assert (c['width'], c['height'], c['nominalFrameRate']) == (2560, 1440, '25/1')
    else:
        assert row['channel'] == 'front (observed channel)'
assert codec_counts == e['codec_counts'] == {'hevc':391, 'h264':10}
assert channel_counts == {'front':284, 'inside':117}
assert p['recording']['parking_modes'] == ['time-lapse (owner-confirmed new cohort only)', 'collision detection wake-record-sleep (owner-confirmed collision-test cohort only)']

# New-scan settings remain separately scoped. Historical numeric evidence and
# all 19 occurrences retain their pins above, normalizing only the owner role correction.
owner = e['owner_scan']
assert digest([g['storageRateSamples'] for g in owner['groups']]) == '93ccd27d195406f5c8cfdafaf538bdf9ecadb3786fad10a2fa4f6ee22e60f737'
fields = ('fileSizeBytes', 'durationSeconds', 'videoBitrate', 'width', 'height', 'nominalFrameRate')
def numeric_key(sample):
    return tuple(sample[k] for k in fields)

assert numeric_key(dict.fromkeys(fields, 60)) == numeric_key(dict.fromkeys(fields, 60.0))
assert owner['configuration'] == '2CH: front/telephoto'
assert owner['configured_parking_mode'] == 'time-lapse (owner-reported)'
assert all(owner[k] is None for k in ('firmware', 'quality', 'hdr', 'capture_cadence'))
assert owner['sample_occurrences'] == owner['unique_numeric_sample_count'] == 19
assert owner['duplicate_numeric_occurrences'] == 0
assert owner['inventory'] == {'scanned_files':1589, 'copyable_items':1367, 'video_file_count':902, 'jpeg_file_count':440}
assert [g['inventoried_video_entries'] for g in owner['groups']] == [621, 281]
assert [g['physical_role'] for g in owner['groups']] == ['front', 'telephoto']
assert [g['sample_occurrences'] for g in owner['groups']] == [9, 10]
all_keys = set()
row_index = 10
for i, g in enumerate(owner['groups']):
    samples = g['storageRateSamples']
    assert g['group_index'] == i and not g['sample_codecs']
    assert g['scanner_mode'] == 'continuous' and g['scanner_display_mode'] == 'Driving'
    assert 'unresolved' in g['sample_mode']
    assert g['unique_numeric_sample_count'] == len(samples) == len({numeric_key(x) for x in samples})
    assert all(set(x) == set(fields) for x in samples)
    assert [x['sample_index'] for x in g['occurrences']] == list(range(g['sample_occurrences']))
    assert {x['numeric_sample_index'] for x in g['occurrences']} == set(range(len(samples)))
    all_keys.update(numeric_key(x) for x in samples)
    for full in (True, False):
        selected = [x for x in samples if (x['durationSeconds'] >= 59.9) == full]
        row = p['video_samples'][row_index]
        row_index += 1
        rates = [x['videoBitrate'] for x in selected]
        assert row['bitrate'] == f'{min(rates)/1e6:.6f}-{max(rates)/1e6:.6f} Mbps'
        assert row['channel'] == g['physical_role'] + ' (new owner cohort)'
        assert row['codec'] == 'Unknown (not retained)'
        assert row['fps'] == ', '.join(str(x) for x in sorted({x['nominalFrameRate'] for x in selected}))
        assert row['resolution'] == f"{selected[0]['width']}x{selected[0]['height']}"
        assert row['mode'] == 'unresolved driving/parking ' + ('full-length' if full else 'short/partial')
        assert row['settings_note'].startswith(f'{len(selected)} retained numeric pairs.')
assert len(all_keys) == 19
assert not all_keys.intersection(numeric_key(x['source_sample']) for x in e['scanner_samples'])

# Apply the same public privacy denylist to evidence as the index generator,
# plus deny raw media dates/names and private record keys recursively.
import re
import runpy
privacy_patterns = runpy.run_path(str(R/'scripts/build-index.py'))['PRIVATE_PATTERNS']
for public in (e, p):
    serialized = json.dumps(public)
    assert not any(pattern.search(serialized) for pattern in privacy_patterns.values())
    assert not re.search(r'\b\d{14}_\d{4}|\b\d{4}-\d{2}-\d{2}[T ]', serialized)
    def check_keys(value):
        if isinstance(value, dict):
            assert not set(value).intersection({'contact', 'createdAt', 'receivedAt', 'filename', 'relativePath', 'sampleRelativePaths'})
            for child in value.values():
                check_keys(child)
        elif isinstance(value, list):
            for child in value:
                check_keys(child)
    check_keys(public)

if args.private_scan:
    private = json.loads(args.private_scan.read_text())
    scan = private['scan']
    assert scan['scannedFiles'] > 0 and scan['copyableItems'] > 0
    assert len(scan['videoSpecSummaries']) == len(owner['groups'])
    assert not scan['videoSpecSamples']
    assert private['training']['channelSetup'] == owner['configuration']
    for actual, public in zip(scan['videoSpecSummaries'], owner['groups']):
        assert actual['fileCount'] == public['inventoried_video_entries']
        assert actual['channel'] == public['scanner_channel']
        restored = [public['storageRateSamples'][x['numeric_sample_index']] for x in public['occurrences']]
        assert restored == actual['storageRateSamples']
    for k in ('contact', 'id', 'createdAt', 'receivedAt'):
        token = private.get(k)
        if token:
            assert token not in json.dumps(e) and token not in json.dumps(p)
    print('Private stored scan parity: all 19 nested exact numeric pairs and source order retained; private tokens absent.')

if args.private_audit:
    actual = Counter()
    for line in (args.private_audit/'media-probes-v2.jsonl').read_text().splitlines():
        x = json.loads(line)
        if x['suffix'] != '.mp4' or x['status'] != 'ok':
            continue
        assert x['unchanged_size_mtime']
        streams = [s for s in x['probe']['streams'] if s['codec_type'] == 'video']
        assert len(streams) == 1
        s = streams[0]
        f = x['probe']['format']
        path = Path(x['path'])
        mode = 'parking-classified S-prefix' if path.name.startswith('S_') else 'driving-classified'
        sample = {'fileSizeBytes':int(f['size']),'durationSeconds':s['duration'],'videoBitrate':int(s['bit_rate']),'width':s['width'],'height':s['height'],'nominalFrameRate':s['r_frame_rate'],'averageFrameRate':s['avg_frame_rate'],'containerDurationSeconds':f['duration'],'containerBitrate':int(f['bit_rate'])}
        actual[(path.parent.name,mode,s['codec_name'],digest(sample))] += 1
    public = Counter((c['channel'],c['mode'],c['codec'],digest(s)) for c in e['cohorts'] for s in c['storageRateSamples'])
    assert public == actual
    original = json.loads((args.private_audit/'receipt-storage-sample-comparison.json').read_text())
    assert e['scanner_samples'] == [{k:x[k] for k in ['group_index','sample_index','source_sample']} for x in original]
    print('Retained source parity: every successful video and every scanner occurrence preserved exactly.')

if args.baseline:
    b = json.loads(args.baseline.read_text())
    assert [c for c in index['cameras'] if c['id'] != p['id']] == [c for c in b['index']['cameras'] if c['id'] != p['id']]
    allowed_changes = {'profiles/ddpai-z100-master.json', 'docs/data/ddpai-z100-master-evidence.json', 'docs/data/cameras.json', 'scripts/verify-z100-master.py'}
    for name, sha in b['trackedHashes'].items():
        if name not in allowed_changes:
            assert hashlib.sha256((R/name).read_bytes()).hexdigest() == sha, name
    if args.private_audit:
        for name, sha in b['auditHashes'].items():
            assert hashlib.sha256((args.private_audit/name).read_bytes()).hexdigest() == sha, name
    print('All existing camera records and unrelated tracked bytes unchanged; private originals immutable.')
runpy.run_path(str(R/'scripts/verify-z100-collision.py'))['verify'](e['collision_test_scan'], p)
print('Z100 Master verified: unchanged 401 historical probes, 19 historical scanner occurrences and 19 earlier owner pairs; 40 collision-test canonical probes, 40 alternate native observations, 15 uniquely linked submitted occurrences and 4 new summary rows; privacy and index parity passed. Firmware/settings and per-file collision-test modes remain unresolved.')
