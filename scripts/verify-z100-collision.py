#!/usr/bin/env python3
"""Verify anonymous collision-test measurements; optional saved-JSON source parity.

Never opens media or inventory paths. --private-data accepts only the current
owner cohort's saved probe/native/receipt JSON directory, not historical data.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

R = Path(__file__).resolve().parents[1]
FIELDS = ('fileSizeBytes', 'durationSeconds', 'videoBitrate', 'width', 'height', 'nominalFrameRate')
PROBE_FIELDS = set(FIELDS) | {'averageFrameRate', 'containerDurationSeconds', 'containerBitrate', 'videoFrameCount'}

def numeric(sample):
    return {k: sample[k] for k in FIELDS}

def verify(c, profile):
    # Hash only explicitly allowlisted anonymous measurement fields, never source bytes/identities.
    import hashlib
    values = [[{k: s['source_sample'][k] for k in PROBE_FIELDS}, numeric(s['native_observation'])] for g in c['groups'] for s in g['samples']]
    values += [numeric(o['source_sample']) for o in c['submitted_occurrences']]
    assert hashlib.sha256(json.dumps(values, sort_keys=True, separators=(',', ':')).encode()).hexdigest() == '2410184de309607e24b5edbfd93fc8599728b5190fc0909948071fcb1c22969f'
    assert c['physical_clip_count'] == c['canonical_probe_count'] == c['native_observation_count'] == 40
    assert c['submitted_sample_occurrences'] == c['uniquely_linked_submitted_occurrences'] == 15
    assert c['configuration'] == '2CH: front/telephoto'
    assert c['configured_parking_mode'] == 'collision detection wake-record-sleep (owner-reported)'
    assert all(c[k] is None for k in ('firmware', 'quality', 'hdr', 'capture_cadence'))
    assert c['inventory'] == {'video_file_count': 40, 'front_video_count': 20, 'telephoto_video_count': 20}
    groups = c['groups']
    assert len(groups) == 4
    assert [(g['physical_role'], g['length_class'], g['sample_count']) for g in groups] == [('front', 'full-length', 16), ('front', 'short/partial', 4), ('telephoto', 'full-length', 16), ('telephoto', 'short/partial', 4)]
    clips = {}
    for g, row in zip(groups, profile['video_samples'][14:18]):
        assert g['sample_mode'] == 'unresolved driving/parking' and g['codec'] == 'hevc'
        samples = g['samples']
        assert g['sample_count'] == len(samples)
        rates = [s['source_sample']['videoBitrate'] for s in samples]
        assert (min(rates), max(rates), sum(rates), sum(rates)/len(rates)) == tuple(g[k] for k in ('video_bitrate_bps_min', 'video_bitrate_bps_max', 'video_bitrate_bps_sum', 'video_bitrate_bps_mean'))
        assert row['bitrate'] == f'{min(rates)/1e6:.6f}-{max(rates)/1e6:.6f} Mbps'
        assert row['channel'] == g['physical_role'] + ' (collision-test cohort)'
        assert row['mode'] == g['sample_mode'] + ' ' + g['length_class']
        assert row['resolution'] == f"{g['width']}x{g['height']}"
        for s in samples:
            assert set(s) == {'clip_index', 'source_sample', 'native_observation'}
            assert s['clip_index'] not in clips
            clips[s['clip_index']] = (g['physical_role'], s)
            probe, native = s['source_sample'], s['native_observation']
            assert set(probe) == PROBE_FIELDS and set(native) == set(FIELDS)
            assert (float(probe['durationSeconds']) >= 59.9) == (g['length_class'] == 'full-length')
            for key in ('fileSizeBytes', 'width', 'height'):
                assert probe[key] == native[key]
            assert (probe['width'], probe['height'], probe['nominalFrameRate']) == (g['width'], g['height'], g['nominalFrameRate'])
            assert abs(float(probe['durationSeconds']) - native['durationSeconds']) < 0.0011
            num, den = map(float, probe['nominalFrameRate'].split('/'))
            assert abs(num/den - native['nominalFrameRate']) < 0.04
    assert set(clips) == set(range(40))
    assert len(c['submitted_groups']) == 2
    for gi, g in enumerate(c['submitted_groups']):
        assert g['group_index'] == gi and g['fileCount'] == 20
        assert g['physical_role'] == ('front' if gi == 0 else 'telephoto')
        assert g['scanner_mode'] == 'continuous' and g['scanner_display_mode'] == 'Driving'
        assert g['sampleCodecs'] == []  # original receipt did not retain per-file codecs
    assert Counter(o['group_index'] for o in c['submitted_occurrences']) == {0: 8, 1: 7}
    for gi in (0, 1):
        assert [o['sample_index'] for o in c['submitted_occurrences'] if o['group_index'] == gi] == list(range(8 if gi == 0 else 7))
    for o in c['submitted_occurrences']:
        assert set(o['source_sample']) == set(FIELDS)
        role = 'front' if o['group_index'] == 0 else 'telephoto'
        candidates = [i for i, (r, s) in clips.items() if r == role and s['native_observation'] == o['source_sample']]
        assert len(candidates) == 1 and candidates == o['matching_clip_indices']
    return clips

def private_parity(directory, c, clips):
    def load(name):
        return json.loads((directory/name).read_text())
    native = load('patched-native-snapshot.json')
    stored = load('patched-offline-stored-record.json')['scan']
    original = load('submitted-scan.json')['scan']
    def by_path(scan):
        entries = [s for g in scan['videoSpecSummaries'] for s in g['storageRateSamples']]
        result = {s['folder']+'/'+s['filename']: s for s in entries}
        assert len(entries) == len(result) == 40
        return result
    ns = by_path(native)
    role_by_path = {}
    for g in native['videoSpecSummaries']:
        assert g['channel'] in ('front', 'interior')
        # Owner confirms the second observed main-unit channel is telephoto.
        for s in g['storageRateSamples']:
            role_by_path[s['folder']+'/'+s['filename']] = 'front' if g['channel'] == 'front' else 'telephoto'
    assert ns == by_path(stored)
    actual = {}
    for p in load('card-video-probes.json'):
        assert p['returncode'] == 0 and p['unchanged']
        vs = [s for s in p['probe']['streams'] if s['codec_type'] == 'video']
        assert len(vs) == 1 and vs[0]['codec_name'] == 'hevc'
        v, f = vs[0], p['probe']['format']
        probe = {'fileSizeBytes': int(f['size']), 'durationSeconds': v['duration'], 'videoBitrate': int(v['bit_rate']), 'width': v['width'], 'height': v['height'], 'nominalFrameRate': v['r_frame_rate'], 'averageFrameRate': v['avg_frame_rate'], 'containerDurationSeconds': f['duration'], 'containerBitrate': int(f['bit_rate']), 'videoFrameCount': int(v['nb_frames'])}
        assert p['size'] == probe['fileSizeBytes']
        matches = [i for i, (_, s) in clips.items() if s['source_sample'] == probe and s['native_observation'] == numeric(ns[p['path']])]
        assert len(matches) == 1
        assert clips[matches[0]][0] == role_by_path[p['path']]
        actual[p['path']] = matches[0]
    assert len(actual) == len(set(actual.values())) == 40
    for gi, g in enumerate(original['videoSpecSummaries']):
        public_group = c['submitted_groups'][gi]
        assert public_group['scanner_channel'] == g['channel']
        assert public_group['scanner_mode'] == g['mode'] and public_group['scanner_display_mode'] == g['displayMode']
        for key in ('fileCount', 'totalFileSizeBytes', 'minFileSizeBytes', 'maxFileSizeBytes', 'sampleBitrateMin', 'sampleBitrateMax', 'sampleDurationMin', 'sampleDurationMax', 'sampleFrameRates', 'sampleResolutions', 'sampleCodecs'):
            assert public_group[key] == g[key]
    occurrences = [{'group_index': gi, 'sample_index': si, 'source_sample': numeric(s)} for gi, g in enumerate(original['videoSpecSummaries']) for si, s in enumerate(g['storageRateSamples'])]
    assert occurrences == [{k: o[k] for k in ('group_index', 'sample_index', 'source_sample')} for o in c['submitted_occurrences']]
    # Recompute unique correspondence from retained names and original numeric values, never array order.
    for o in c['submitted_occurrences']:
        role = 'front' if o['group_index'] == 0 else 'telephoto'
        matches = [actual[path] for path, s in ns.items() if numeric(s) == o['source_sample'] and clips[actual[path]][0] == role]
        assert matches == o['matching_clip_indices']
    public = json.dumps(c)
    for path in ns:
        assert path not in public and Path(path).name not in public
    print('Saved source parity: 40/40 exact ffprobe pairs, 40/40 native-to-stored observations, 15/15 uniquely linked original occurrences. No media opened.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--private-data', type=Path)
    args = parser.parse_args()
    evidence = json.loads((R/'docs/data/ddpai-z100-master-evidence.json').read_text())
    profile = json.loads((R/'profiles/ddpai-z100-master.json').read_text())
    cohort = evidence['collision_test_scan']
    clips = verify(cohort, profile)
    if args.private_data:
        private_parity(args.private_data, cohort, clips)
    print('Collision-test cohort verified: 40 canonical clips, 4 summary groups, 40 alternate observations, 15 submitted occurrences; modes unresolved and settings scoped.')
