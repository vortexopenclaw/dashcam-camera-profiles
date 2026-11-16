"""Apply only reviewed filename corrections to historical preservation fixtures."""
import json

# Keep historical comparisons exact outside these two literal replacements.
CORRECTIONS = {
    'rove-r2-4k-pro': (
        r'^(\\d{4})_(\\d{4})_(\\d{6})_(\\d+)\\.(MP4)$',
        r'^(\d{4})_(\d{4})_(\d{6})_(\d+)\.(MP4)$',
    ),
    'vantrue-e1-pro': (
        r'^(\\d{8})_(\\d{6})_(\\d{5})_([NPET])_([A])\\.(MP4|JPG)$',
        r'^(\d{8})_(\d{6})_(\d{5})_([NPET])_([A])\.(MP4|JPG)$',
    ),
}


def corrected_baseline(path, data):
    """Return baseline bytes with just the approved regex literals corrected."""
    if path == 'docs/data/cameras.json':
        identities = CORRECTIONS
        profiles = json.loads(data)['cameras']
    elif path in {f'profiles/{identity}.json' for identity in CORRECTIONS}:
        profiles = [json.loads(data)]
        identities = [path.removeprefix('profiles/').removesuffix('.json')]
    else:
        return data
    for identity in identities:
        profile, = [p for p in profiles if p['id'] == identity]
        old, new = CORRECTIONS[identity]
        assert profile['filename_patterns'][0]['pattern'] == old, identity
        old_bytes, new_bytes = (json.dumps(pattern).encode() for pattern in (old, new))
        assert data.count(old_bytes) == 1, identity
        data = data.replace(old_bytes, new_bytes, 1)
    return data
