#!/usr/bin/env python3
"""Fixture-only exhaustive leaf controls for the frozen-history allowlist."""
from copy import deepcopy
from functools import lru_cache
import json
from pathlib import Path
import subprocess
import unittest
from filename_pattern_history import CORRECTIONS, corrected_baseline

ROOT = Path(__file__).resolve().parents[1]
BASE = '32081d49092a67613de7fc7332e20186fb767ff9'


@lru_cache(None)
def before(path):
    return subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT)


def leaves(value, path=()):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from leaves(child, path + (key,))
    elif isinstance(value, list):
        for key, child in enumerate(value):
            yield from leaves(child, path + (key,))
    else:
        yield path


def changed(value, path):
    value = deepcopy(value)
    target = value
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = '__unauthorized_mutation__'
    return value


def encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode()


class FilenamePatternHistory(unittest.TestCase):
    def test_exact_pinned_profiles_and_index(self):
        for path in ['docs/data/cameras.json'] + [f'profiles/{key}.json' for key in CORRECTIONS]:
            with self.subTest(path=path):
                self.assertEqual(corrected_baseline(path, before(path)), (ROOT/path).read_bytes())

    def test_every_profile_leaf_still_participates_in_equality(self):
        for key in CORRECTIONS:
            path = f'profiles/{key}.json'
            historical = json.loads(before(path))
            current = json.loads((ROOT/path).read_bytes())
            expected = json.loads(corrected_baseline(path, before(path)))
            for leaf in leaves(current):
                with self.subTest(profile=key, leaf=leaf):
                    # An unrelated current-field change must not become accepted.
                    self.assertNotEqual(changed(current, leaf), expected)
                    # Nor may the helper discard a mutation to historical evidence.
                    bad = changed(historical, leaf)
                    try:
                        restored = json.loads(corrected_baseline(path, encoded(bad)))
                    except (AssertionError, KeyError, ValueError):
                        continue
                    self.assertNotEqual(restored, current)

    def test_index_identity_evidence_metadata_order_and_extra_pattern(self):
        path = 'docs/data/cameras.json'
        current = json.loads((ROOT/path).read_bytes())
        expected = json.loads(corrected_baseline(path, before(path)))
        for i, camera in enumerate(current['cameras']):
            for field in ('model', 'evidence'):
                with self.subTest(camera=camera['id'], field=field):
                    self.assertNotEqual(changed(current, ('cameras', i, field)), expected)
        for field in current.keys() - {'cameras'}:
            self.assertNotEqual(changed(current, (field,)), expected)
        bad = deepcopy(current)
        bad['cameras'].reverse()
        self.assertNotEqual(bad, expected)
        for key in CORRECTIONS:
            bad = deepcopy(current)
            camera = next(c for c in bad['cameras'] if c['id'] == key)
            camera['filename_patterns'].append(deepcopy(camera['filename_patterns'][0]))
            self.assertNotEqual(bad, expected)

    def test_only_exact_historical_pattern_is_accepted(self):
        for key, (old, reviewed) in CORRECTIONS.items():
            path = f'profiles/{key}.json'
            for pattern in (reviewed, old + 'x', '.*', old.replace('\\\\d', '[0-9]')):
                with self.subTest(profile=key, pattern=pattern):
                    bad = json.loads(before(path))
                    bad['filename_patterns'][0]['pattern'] = pattern
                    with self.assertRaises(AssertionError):
                        corrected_baseline(path, encoded(bad))

    def test_byte_formatting_is_preserved_not_normalized(self):
        for key in CORRECTIONS:
            path = f'profiles/{key}.json'
            self.assertEqual(corrected_baseline(path, before(path) + b'\n'), (ROOT/path).read_bytes() + b'\n')
            self.assertNotEqual(corrected_baseline(path, before(path) + b'\n'), (ROOT/path).read_bytes())

    def test_e1_pro_s_and_unrelated_paths_are_not_allowlisted(self):
        path = 'profiles/vantrue-e1-pro-s.json'
        raw = (ROOT/path).read_bytes()
        self.assertEqual(raw, before(path))
        self.assertEqual(corrected_baseline(path, raw), raw)
        bad = encoded(changed(json.loads(raw), ('filename_patterns', 0, 'pattern')))
        self.assertEqual(corrected_baseline(path, bad), bad)
        self.assertNotEqual(corrected_baseline(path, bad), raw)
        for path in ('parking/measurements.json', 'docs/data/ddpai-mini3x-evidence.json'):
            raw = (ROOT/path).read_bytes()
            self.assertEqual(corrected_baseline(path, raw), raw)


if __name__ == '__main__':
    unittest.main(verbosity=2)
