#!/usr/bin/env python3
"""Validate anonymous 3CH evidence; optional parity uses saved JSON only, never media."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

R = Path(__file__).resolve().parents[1]
FIELDS = ('fileSizeBytes', 'durationSeconds', 'videoBitrate', 'width', 'height', 'nominalFrameRate')

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

def project(directory):
    rows = [json.loads(line) for line in (directory/'files.jsonl').read_text().splitlines()]
    native = json.loads((directory/'native-before-rear-fix.json').read_text())
    ns = {s['folder']+'/'+s['filename']: {k:s[k] for k in FIELDS} for g in native['videoSpecSummaries'] for s in g['storageRateSamples']}
    groups = {}
    for r in rows:
        streams = [s for s in r.get('mediaMetadata', {}).get('streams', []) if s.get('codec_type') == 'video']
        if not streams:
            continue
        assert len(streams) == 1 and r['sourceUnchanged']
        s = streams[0]
        f = r['mediaMetadata']['format']
        path = Path(r['path'])
        role = {'front':'front', 'inside':'telephoto', 'rear':'rear'}[path.parent.name]
        mode = 'time-lapse (owner-confirmed)' if path.name.startswith(('S_', 'Q_')) else 'driving-inferred'
        length = 'full-length' if float(s['duration']) >= 59.9 else 'short/partial'
        key = (role, mode, length, s['codec_name'], s['width'], s['height'], s['r_frame_rate'])
        sample = {'fileSizeBytes':int(f['size']), 'durationSeconds':s['duration'], 'videoBitrate':int(s['bit_rate']), 'width':s['width'], 'height':s['height'], 'nominalFrameRate':s['r_frame_rate'], 'averageFrameRate':s['avg_frame_rate'], 'containerDurationSeconds':f['duration'], 'containerBitrate':int(f['bit_rate']), 'videoFrameCount':s['nb_frames']}
        assert sample['fileSizeBytes'] == r['size']
        entry = {'source_sample':sample}
        if r['path'] in ns:
            entry['native_observation'] = ns[r['path']]
        groups.setdefault(key, []).append(entry)
    result = []
    index = 0
    for key, samples in sorted(groups.items()):
        role, mode, length, codec, width, height, fps = key
        samples.sort(key=lambda s: json.dumps(s, sort_keys=True))
        for s in samples:
            s['clip_index'] = index
            index += 1
        rates = [s['source_sample']['videoBitrate'] for s in samples]
        result.append(dict(physical_role=role, sample_mode=mode, length_class=length, codec=codec, width=width, height=height, nominalFrameRate=fps, sample_count=len(samples), video_bitrate_bps_min=min(rates), video_bitrate_bps_max=max(rates), video_bitrate_bps_sum=sum(rates), samples=samples))
    return result


def verify(e, p):
    groups = e['groups']
    clips = [s for g in groups for s in g['samples']]
    assert len(clips) == e['physical_clip_count'] == 72
    assert sum('native_observation' in s for s in clips) == e['native_observation_count'] == 64
    assert sorted(s['clip_index'] for s in clips) == list(range(72))
    assert Counter({role:sum(g['sample_count'] for g in groups if g['physical_role']==role) for role in ('front','telephoto','rear')}) == {'front':28,'telephoto':13,'rear':31}
    assert {(role, mode):sum(g['sample_count'] for g in groups if (g['physical_role'],g['sample_mode'])==(role,mode)) for role,mode in [('front','driving-inferred'),('front','time-lapse (owner-confirmed)'),('telephoto','driving-inferred'),('rear','driving-inferred'),('rear','time-lapse (owner-confirmed)')]} == {('front','driving-inferred'):13,('front','time-lapse (owner-confirmed)'):15,('telephoto','driving-inferred'):13,('rear','driving-inferred'):13,('rear','time-lapse (owner-confirmed)'):18}
    assert digest(groups) == e['numeric_projection_sha256'] == '93caa75df7f16a982438790bd7d939c3eeded0252f93e9496692aa3f6848c774'
    assert digest(p['video_samples'][:18]) == '6b0ff2c45dda3e333318656a2925f698a30c2fc7398a41125d137495f28bc2c4'
    assert len(p['video_samples']) == 18+len(groups)
    for g,row in zip(groups,p['video_samples'][18:]):
        rates = [s['source_sample']['videoBitrate'] for s in g['samples']]
        assert g['sample_count'] == len(rates)
        assert (min(rates),max(rates),sum(rates)) == tuple(g[k] for k in ('video_bitrate_bps_min','video_bitrate_bps_max','video_bitrate_bps_sum'))
        assert row['storageRateSamples'] == [s['source_sample'] for s in g['samples']]
        assert row['bitrate'] == f'{min(rates)/1e6:.6f}-{max(rates)/1e6:.6f} Mbps'
        for s in g['samples']:
            v = s['source_sample']
            assert g['codec'] == 'hevc'
            assert (float(v['durationSeconds']) >= 59.9) == (g['length_class']=='full-length')
    print('3CH verified: 72 canonical clips, 64 alternate native observations, exact bounds, old 18-row prefix preserved.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--private-data', type=Path)
    args = parser.parse_args()
    e = json.loads((R/'docs/data/ddpai-z100-master-3ch-evidence.json').read_text())
    p = json.loads((R/'profiles/ddpai-z100-master.json').read_text())
    verify(e,p)
    if args.private_data:
        assert project(args.private_data) == e['groups']
        print('Saved-source exact parity passed: all 72 ffprobe samples and 64 paired native observations; no media opened.')
