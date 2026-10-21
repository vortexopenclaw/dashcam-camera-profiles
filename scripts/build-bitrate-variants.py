#!/usr/bin/env python3
"""Build measured front-camera variants without inventing channel setups."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'docs/data'

def clean(value):
    value = re.sub(r'\\u([0-9a-fA-F]{4})', lambda m: chr(int(m[1], 16)), value)
    value = value.replace('VIOFO ', 'Viofo ').replace('BlackVue ', 'Blackvue ')
    return value.replace('+', ' Plus') if value.startswith('Blackvue ') else value

def channel_count(configuration):
    match = re.search(r'\b([1-4])(?:\s*-?\s*(?:channel|cameras?)|CH\b)', configuration, re.I)
    if match:
        return int(match[1])
    for word, count in [('one', 1), ('two', 2), ('three', 3), ('four', 4)]:
        if re.search(r'\b'+word+r'-channel\b', configuration, re.I):
            return count
    return None

def build(check=False):
    evidence = json.loads((DATA / 'bitrate-setup-evidence.json').read_text())
    raw = json.loads((DATA / '4k30-comparison.json').read_text())
    reviewed = json.loads((DATA / 'bitrate-channel-evidence.json').read_text())
    rows = []
    for original in raw:
        if original['id'] == 'viofo-t340' and 'Maximum' not in original['camera']:
            continue
        profile_path = ROOT / 'profiles' / (original['id'] + '.json')
        if profile_path.exists():
            profile = json.loads(profile_path.read_text())
            if any(f['label'] == 'Front capture classification' and f['value'] in {'upscaled_4k', 'native_4k_unverified'} for f in profile['technical_facts']):
                continue
        row = dict(original)
        row['camera'] = re.sub(r'\s*•\s*Maximum$', '', clean(row['camera']))
        row['configuration'] = clean(row['configuration'])
        row['channels'] = channel_count(row['configuration'])
        row['key'] = row['id']
        row['default'] = True
        row['channelSource'] = 'Recorded measurement configuration' if row['channels'] else None
        if row['id'] == 'viofo-t340':
            row['key'] = 't340-a' if 'T340 A' in row['camera'] else 't340-b'
            row['default'] = False
        override = evidence.get('defaults', {}).get(row['id'], {})
        if override:
            row['channels'] = override['channels']
            row['channelSource'] = override['source']
            if override.get('channelScope'): row['channelScope'] = override['channelScope']
            if override.get('unmeasuredSetups'): row['unmeasuredSetups'] = override['unmeasuredSetups']
        rows.append(row)
    units = [r for r in rows if r['id'] == 'viofo-t340']
    assert len(units) == 2 and all(r['channels'] == 4 for r in units)
    combined = dict(units[0], key='viofo-t340', camera='Viofo T340', default=True,
                    lowMbps=min(r['lowMbps'] for r in units), highMbps=max(r['highMbps'] for r in units),
                    configuration='4CH; two units; firmware 1.0_260911',
                    settings='Maximum bitrate. Range spans the two measured 4CH units, not a change of channel count.',
                    source='Vortex Radar unit A and unit B measurements', members=units)
    rows.append(combined)
    for alternative in evidence.get('alternatives', []):
        assert all(key in alternative for key in ['id','key','camera','channels','lowMbps','highMbps','codec','configuration','settings','source'])
        if alternative.get('default'):
            previous = next(r for r in rows if r['id'] == alternative['id'] and r['default'])
            if alternative.get('replacesBase'):
                rows.remove(previous)
            else:
                previous['key'] = previous['id'] + ':archive'
                previous['default'] = False
                previous['variantLabel'] = 'Archive measurements'
        rows.append(dict(alternative, camera=clean(alternative['camera']), default=alternative.get('default', False)))
    for alternative in reviewed.get('alternatives', []):
        base = next(r for r in rows if r['id'] == alternative['id'] and r['default'])
        rows.append(dict(base, **alternative, default=False))
    assert len({r['key'] for r in rows}) == len(rows), 'Variant keys must be unique'
    assert len({r['id'] for r in rows if r['default']}) == sum(r['default'] for r in rows)
    verified_channels = reviewed['configurations']
    for row in rows:
        channel_evidence = verified_channels.get(row['key'], verified_channels.get(row['id']))
        assert channel_evidence, f"Missing original-file/card-scan channel evidence: {row['key']}"
        measurement = channel_evidence.get('measurement', {})
        assert set(measurement) <= {'lowMbps','highMbps','codec','variantLabel','settings','source','configuration'}
        row.update(measurement)
        row['channels'] = channel_evidence['channels']
        row['channelRoles'] = channel_evidence['roles']
        row['channelSource'] = channel_evidence['source']
        recorded_count = channel_count(row['configuration'])
        assert recorded_count in {None, row['channels']}, f"Configuration conflicts with verified channels: {row['key']}"
        if recorded_count is None:
            row['configuration'] = f"{row['channels']}CH: " + ', '.join(role.replace('_', ' ') for role in row['channelRoles'])
        row.pop('channelScope', None)
        if channel_evidence.get('codec'): row['codec'] = channel_evidence['codec']
        if channel_evidence.get('codecSource'): row['codecSource'] = channel_evidence['codecSource']
        if 'channel count unrecorded' in row.get('variantLabel', ''):
            row['variantLabel'] = f"{row['channels']}CH, archive measurements"
        assert row['channels'] in {1, 2, 3, 4}
        assert len(set(row['channelRoles'])) == row['channels'], row['key']
        assert 0 < row['lowMbps'] <= row['highMbps']
    output = json.dumps(rows, indent=2) + '\n'
    if check:
        assert (DATA / 'bitrate-variants.json').read_text() == output, 'Bitrate variants are stale. Run scripts/build-bitrate-variants.py.'
    else:
        (DATA / 'bitrate-variants.json').write_text(output)
    print(f'Built {len(rows)} measured bitrate variants for {len({r["id"] for r in rows})} camera models')

if __name__ == '__main__':
    import sys
    build(check='--check' in sys.argv)
