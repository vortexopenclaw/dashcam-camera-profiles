#!/usr/bin/env python3
"""Verify source-exact A119M Pro Low / 1 fps Night Vision scan evidence."""
import argparse
import hashlib
import json
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('--mirror',type=Path)
args=parser.parse_args()
root=Path(__file__).resolve().parents[1]
e=json.loads((root/'docs/data/a119m-pro-low-1.2_20260817.json').read_text())
assert e['ownerAssertions']['firmware']=='1.2_20260817'
assert e['ownerAssertions']['quality']=='low' and e['ownerAssertions']['parkingMode']=='time-lapse'
assert e['ownerAssertions']['timeLapseFps']==1 and e['review']['ownerConfirmedNightVision']
assert 'omitted' in e['review']['firmwareProvenance']
assert e['inventory']['completed'] and e['inventory']['fileCount']==6 and e['inventory']['mediaCount']==4
samples=e['samples'];assert len(samples)==3
assert [(s['sizeBytes'],s['durationSeconds']) for s in samples]==[(746474728,180),(439695744,132),(451368968,108.46666666666668)]
assert all(s['channel']=='front' and s['mode']=='unknown' and s['fps']==30 for s in samples)
keys=['channel','mode','width','height','fps','bitrateKbps','containerBitrateKbps','sizeBytes','durationSeconds','codec']
numeric=[{k:s[k] for k in keys} for s in samples]
assert hashlib.sha256(json.dumps(numeric,sort_keys=True,separators=(',',':')).encode()).hexdigest()==e['evidenceDigest']
driving=[samples[i] for i in e['review']['drivingSampleIndices']];parking=[samples[i] for i in e['review']['parkingSampleIndices']]
assert len(driving)==2 and len(parking)==1
assert all((s['width'],s['height'])==(3840,2160) for s in driving)
assert (parking[0]['width'],parking[0]['height'])==(2560,1440)
rows=json.loads((root/'docs/data/bitrate-variants.json').read_text());low=next(r for r in rows if r['key']=='viofo-a119m-pro:low-fw1.2_20260817')
assert low['quality']=='low' and not low['default']
assert low['lowMbps']==min(s['bitrateKbps']/1000 for s in driving)
assert low['highMbps']==max(s['bitrateKbps']/1000 for s in driving)
assert next(r for r in rows if r['key']=='viofo-a119m-pro')['quality']=='high'
db=json.loads((root/'docs/data/storage-evidence.json').read_text())
pairs=[r for r in db['pairedSamples'] if r['sourceDigest']==e['evidenceDigest']]
assert len(pairs)==3
for original,pair in zip(samples,pairs):
 assert original['sizeBytes']==pair['fileSizeBytes'] and original['durationSeconds']==pair['durationSeconds']
 assert original['bitrateKbps']*1000==pair['estimatedBitrate']
park=next(p for p in pairs if p['mode']=='parking')
assert park['captureFrameRate']==1 and park['nominalFrameRate']==30 and park['durationBasis']=='playback' and park['excludeFromRealtimeEstimates']
if args.mirror:assert args.mirror.read_bytes()==(root/'docs/data/storage-evidence.json').read_bytes()
print('Verified: Windows receipt evidence, three exact measurement pairs, separate Low driving and 1 fps Night Vision parking, unchanged firmware attribution, playback/capture distinction, Low chart variant, preserved High default and matching storage mirrors.')
