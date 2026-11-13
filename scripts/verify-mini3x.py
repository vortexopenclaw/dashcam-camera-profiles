#!/usr/bin/env python3
"""MINI3X identity, exact sample occurrences and unrelated-source preservation."""
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = 'ac73e63e0bd745d2c25ff38d2aee209dfc9cb7d2'
load = lambda path: json.loads((ROOT / path).read_text())
profile = load('profiles/ddpai-mini3x.json')
evidence = load('docs/data/ddpai-mini3x-evidence.json')
assert (profile['id'], profile['manufacturer'], profile['model']) == ('ddpai-mini3x', 'DDPAI', 'MINI3X')
assert evidence['identity']['observed_log_sku_aliases'] == ['DDPAI DM003_Overseas_V2']
assert evidence['identity']['firmware'] == 'v9.0.1.10'
# Synthetic model token: does not encode a retail revision or installation role.
fixture = {'reportedModel': 'DDPAI DM003_Overseas_V2', 'canonicalId': 'ddpai-mini3x', 'role': 'unknown'}
assert fixture['reportedModel'] in evidence['identity']['observed_log_sku_aliases']
assert profile['filename_patterns'][0]['default_channel'] == fixture['role']
assert re.fullmatch(profile['filename_patterns'][0]['pattern'], '20000101000000_0060.mp4')
samples = evidence['samples']
import hashlib
assert hashlib.sha256(json.dumps(samples,sort_keys=True,separators=(',',':')).encode()).hexdigest() == '04b513e16c978d3dcbb27191bd1c4b0dba27e562b909caa6ff02a929a0d9167e', 'Source-reviewed 23 occurrences remain exact'
assert len(samples) == len({s['sample_id'] for s in samples}) == 23
assert evidence['inventory'] == {'relevant_files':303,'videos':23,'jpeg_photos':230,'logs':50,'excluded_housekeeping_sidecars':2}
for sample in samples:
    v, a, s = sample['video'], sample['audio'], sample['submitted_measurement']
    assert (v['codec_name'], v['width'], v['height'], v['r_frame_rate'], v['avg_frame_rate']) == ('hevc',2960,1664,'30/1','30/1')
    assert a['codec_name'] == 'aac'
    assert sample['file_size_bytes'] == s['fileSizeBytes']
    assert abs(float(v['duration']) - s['durationSeconds']) < 0.000001
    assert abs(int(v['bit_rate']) - s['videoBitrate']) <= 2
assert min(s['submitted_measurement']['videoBitrate'] for s in samples) == 7423724
assert max(s['submitted_measurement']['videoBitrate'] for s in samples) == 14849620
assert min(int(s['video']['bit_rate']) for s in samples) == 7423723
serialized = json.dumps(evidence)
assert not re.search(r'\d{14}_\d{4}\.mp4|/Volumes/|/Users/|mtime|serial|latitude|longitude', serialized, re.I)
refs = load('docs/data/ddpai-model-reference.json')['records']
assert len(refs) == 133
assert next(r for r in refs if r['id'] == 'global-mini3x')['canonicalProfileId'] == 'ddpai-mini3x'
assert not any(r['model'] == 'MINI3X (V3)' and 'MINI3X' in r['aliases'] for r in refs)
old_index = json.loads(subprocess.check_output(['git','show',f'{BASELINE}:docs/data/cameras.json'], cwd=ROOT))
from z100_retest import restore_loaded
new_index = restore_loaded('docs/data/cameras.json', load('docs/data/cameras.json'))
assert [c for c in new_index['cameras'] if c['id'] != 'ddpai-mini3x'] == old_index['cameras']
for path in subprocess.check_output(['git','ls-tree','-r','--name-only',BASELINE,'profiles','parking'],cwd=ROOT,text=True).splitlines():
    prior = subprocess.check_output(['git','show',f'{BASELINE}:{path}'],cwd=ROOT)
    if path in {'profiles/ddpai-z100-master.json','parking/measurements.json','parking/sources.json'}:
        assert restore_loaded(path,load(path)) == json.loads(prior), path
    else:
        assert (ROOT/path).read_bytes() == prior, path
assert next(c for c in new_index['cameras'] if c['id']=='ddpai-mini3x') == profile
print('MINI3X passed: 23 paired occurrences, exact video/audio metadata, scoped identity; all prior profiles and parking sources unchanged')
