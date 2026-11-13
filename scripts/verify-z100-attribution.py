#!/usr/bin/env python3
"""Confirm owner attribution while preserving all existing recording occurrences."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import subprocess
from z100_post_update import prior_power_profile, without_post_update
from z100_attribution import BASELINE, ATTRIBUTION, PROFILE_CHANGES, prior_video_provenance, restore_leaves

R = Path(__file__).resolve().parents[1]


def old(path):
    return json.loads(subprocess.check_output(['git', 'show', f'{BASELINE}:{path}'], cwd=R))


def load(path):
    return json.loads((R/path).read_text())


def occurrences(value):
    """Every full numeric sample object, including duplicate occurrences/context."""
    found = Counter()
    def visit(node, context=()):
        if isinstance(node, dict):
            if {'fileSizeBytes', 'durationSeconds', 'videoBitrate'} <= node.keys():
                found[json.dumps([context, node], sort_keys=True, separators=(',', ':'))] += 1
            else:
                for key, child in node.items():
                    visit(child, context+(key,))
        elif isinstance(node, list):
            for child in node:
                visit(child, context)
    visit(value)
    return found


def verify():
    path = 'docs/data/ddpai-z100-master-evidence.json'
    video = load(path)
    assert prior_video_provenance(video) == old(path), 'Only the explicit attribution metadata may change'
    three_path = 'docs/data/ddpai-z100-master-3ch-evidence.json'
    three = load(three_path)
    restored = deepcopy(three)
    assert restored.pop('recording_attribution') == ATTRIBUTION
    assert restored == old(three_path)
    profile_path = 'profiles/ddpai-z100-master.json'
    profile = load(profile_path)
    assert restore_leaves(prior_power_profile(profile), PROFILE_CHANGES) == old(profile_path)
    assert profile['video_samples'] == old(profile_path)['video_samples']
    for name, value in [(path, video), (three_path, three), (profile_path, profile)]:
        assert occurrences(value) == occurrences(old(name)), name
    index_path = 'docs/data/cameras.json'
    index = load(index_path)
    assert next(c for c in index['cameras'] if c['id'] == profile['id']) == profile
    restored_index = deepcopy(index)
    restored_index['cameras'] = [restore_leaves(prior_power_profile(c), PROFILE_CHANGES) if c['id'] == profile['id'] else c for c in index['cameras']]
    assert restored_index == old(index_path), 'Other models and index metadata stay exact'
    # New append-only power rows/exports are pinned completely by the post-update regression.
    assert without_post_update(load('parking/measurements.json')) == old('parking/measurements.json')
    assert without_post_update(load('parking/sources.json'), source_index=True) == old('parking/sources.json')
    for name in ['docs/data/ddpai-z100-master-power-evidence.json', 'docs/data/ddpai-z100-master-4ch-power-evidence.json']:
        assert (R/name).read_bytes() == subprocess.check_output(['git', 'show', f'{BASELINE}:{name}'], cwd=R), name
    assert video['recording_attribution'] == three['recording_attribution'] == ATTRIBUTION
    for name in ['docs/z100-master-measurements.md', 'docs/z100-master-3ch-measurements.md']:
        text = (R/name).read_text()
        assert text.count('All recordings: Vortex Radar’s test unit.') == 1
        assert 'anonymous' not in text.lower()
    print('Attribution confirmed: all existing Z100 recording batches use Vortex Radar’s test unit; exact numeric occurrence multisets, configurations, null firmware, power bytes, batch identifiers, links and other models preserved.')


if __name__ == '__main__':
    verify()
    # Negative controls prove the guards still reject altered measurements and
    # falsely generalized settings; attribution is not an excuse to drop pins.
    video = load('docs/data/ddpai-z100-master-evidence.json')
    changed = deepcopy(video)
    changed['cohorts'][0]['storageRateSamples'][0]['videoBitrate'] += 1
    assert occurrences(changed) != occurrences(video)
    changed = deepcopy(video)
    changed['firmware'] = 'same firmware across tests'
    assert prior_video_provenance(changed) != old('docs/data/ddpai-z100-master-evidence.json')
    changed = deepcopy(video)
    changed['recording_attribution']['contributor'] = 'Unknown contributor'
    try:
        prior_video_provenance(changed)
    except AssertionError:
        pass
    else:
        raise AssertionError('Unknown contributor must fail confirmed attribution')
    print('Negative controls passed: changed numeric occurrence, generalized firmware and unknown contributor rejected.')
