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
args = parser.parse_args()
e = json.loads((R/'docs/data/ddpai-z100-master-evidence.json').read_text())
p = json.loads((R/'profiles/ddpai-z100-master.json').read_text())
index = json.loads((R/'docs/data/cameras.json').read_text())

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

assert digest(e['cohorts']) == '561ea7b7a8a4b451e619a284cfc268cdbf46ea484893b93bab390f448f6a227a'
assert digest(e['scanner_samples']) == 'b4f2abdc64360f5de429781d086a977c38e3f9c20f078b96c01358f552301855'
assert e['camera_id'] == p['id'] == 'ddpai-z100-master'
assert next(c for c in index['cameras'] if c['id'] == p['id']) == p
assert e['firmware'] is None and all(v is None for v in e['unreported_settings'].values())
assert e['inventory'] == {'video_file_count':401, 'jpeg_file_count':440, 'excluded_appledouble_mp4_sidecars':23}
assert len(e['cohorts']) == len(p['video_samples']) == 10
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
        assert c['physical_role'] is None and 'unknown' in row['channel']
assert codec_counts == e['codec_counts'] == {'hevc':391, 'h264':10}
assert channel_counts == {'front':284, 'inside':117}
assert not p['recording']['parking_modes']

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
    assert [c for c in index['cameras'] if c['id'] != p['id']] == b['index']['cameras']
    for name, sha in b['trackedHashes'].items():
        if name not in {'docs/data/cameras.json','.github/workflows/validate.yml'}:
            assert hashlib.sha256((R/name).read_bytes()).hexdigest() == sha, name
    if args.private_audit:
        for name, sha in b['auditHashes'].items():
            assert hashlib.sha256((args.private_audit/name).read_bytes()).hexdigest() == sha, name
    print('All existing camera records and unrelated tracked bytes unchanged; private originals immutable.')
print('Z100 Master verified: 401 exact probes, 19 separate scanner occurrences, 10 observational cohorts, unknown firmware/roles/settings retained.')
