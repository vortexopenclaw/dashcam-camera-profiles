#!/usr/bin/env python3
"""Check generated setup catalog, source-exact alternatives, and native-4K gate."""
import json
import re
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
subprocess.run(['python3',str(ROOT/'scripts/build-bitrate-variants.py'),'--check'],check=True)
rows=json.loads((ROOT/'docs/data/bitrate-variants.json').read_text())
bykey={row['key']:row for row in rows}
assert len(bykey)==len(rows)
assert bykey['blackvue-dr970x-plus']['camera']=='Blackvue DR970X Plus'
assert bykey['blackvue-dr970x-box-plus']['camera']=='Blackvue DR970X Box Plus'
assert all('+' not in row['camera'] for row in rows if row['camera'].startswith('Blackvue '))
assert 'rove-r2-4k-pro' not in {row['id'] for row in rows}
assert all(row['id']!='rove-r2-4k-pro' for row in json.loads((ROOT/'docs/data/4k30-comparison.json').read_text()))
rove=json.loads((ROOT/'profiles/rove-r2-4k-pro.json').read_text())
assert any(fact['label']=='Front capture classification' and fact['value']=='upscaled_4k' for fact in rove['technical_facts'])
assert any('2K sensor' in note and 'not native 4K' in note for note in rove['notes'])
combined=bykey['viofo-t340'];a=bykey['t340-a'];b=bykey['t340-b']
assert combined['lowMbps']==b['lowMbps'] and combined['highMbps']==a['highMbps']
assert combined['channels']==a['channels']==b['channels']==4
assert combined['default'] and not a['default'] and not b['default']
assert len(combined['members'])==2
assert bykey['viofo-a229-pro']['channels']==3
assert not any(row['id']=='viofo-a229-pro' and row['channels']==2 for row in rows)
assert bykey['viofo-a229-pro']['unmeasuredSetups'][0]['channels']==2
assert bykey['viofo-a329s']['channels']==2 and bykey['viofo-a329s:3ch']['channels']==3
assert bykey['viofo-a119m-pro']['channels']==1
assert bykey['vueroid-s1-4k-infinite']['channels']==3
assert bykey['vueroid-s1-4k-infinite:archive']['channels'] is None
assert bykey['thinkware-u3000-pro:1ch']['channels']==1
assert bykey['thinkware-u3000-pro']['channelScope']=='cohort'
for row in rows:
    assert row['channels'] in [None,1,2,3,4]
    assert 0<row['lowMbps']<=row['highMbps']
    if row['channels']:assert row.get('channelSource'),row['key']
for row in json.loads((ROOT/'docs/data/bitrate-setup-evidence.json').read_text())['alternatives']:
    match=re.search(r'(profiles/[a-z0-9-]+\.json) video_samples\[(\d+)\]',row['source'])
    assert match,row['key']
    sample=json.loads((ROOT/match[1]).read_text())['video_samples'][int(match[2])]
    assert sample['mode']=='driving' and sample['resolution']=='3840x2160' and sample['fps']=='30'
    numbers=[float(value) for value in re.findall(r'\d+(?:\.\d+)?',sample['bitrate'])]
    assert row['lowMbps']==min(numbers) and row['highMbps']==max(numbers),row['key']
print('Verified native-4K exclusion, T340 combined/unit ranges, channel provenance, source-exact alternatives, and absent A229 Pro 2CH driving measurement.')
