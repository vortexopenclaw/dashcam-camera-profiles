#!/usr/bin/env python3
"""Synthetic filename grammar regressions; no card or private media access."""
import json
from pathlib import Path
import re
import runpy
import unittest
from filename_pattern_history import CORRECTIONS, corrected_baseline

ROOT = Path(__file__).resolve().parents[1]


class FilenamePatterns(unittest.TestCase):
    def test_preservation_allows_only_exact_reviewed_corrections(self):
        for identity, (old, new) in CORRECTIONS.items():
            path = f'profiles/{identity}.json'
            current = (ROOT / path).read_bytes()
            baseline = current.replace(json.dumps(new).encode(), json.dumps(old).encode())
            self.assertNotEqual(baseline, current)
            self.assertEqual(corrected_baseline(path, baseline), current)
            changed = json.loads(current)
            changed['model'] += ' changed'
            self.assertNotEqual(corrected_baseline(path, baseline), json.dumps(changed).encode())
            with self.assertRaises(AssertionError):
                corrected_baseline(path, baseline.replace(json.dumps(old).encode(), b'"wrong"'))
            self.assertEqual(corrected_baseline('unrelated.json', baseline), baseline)
        current = (ROOT / 'docs/data/cameras.json').read_bytes()
        baseline = current
        for old, new in CORRECTIONS.values():
            baseline = baseline.replace(json.dumps(new).encode(), json.dumps(old).encode(), 1)
        self.assertEqual(corrected_baseline('docs/data/cameras.json', baseline), current)

    def test_e1_siblings(self):
        for identity in ('vantrue-e1-pro', 'vantrue-e1-pro-s'):
            profile = json.loads((ROOT / f'profiles/{identity}.json').read_text())
            pattern = re.compile(profile['filename_patterns'][0]['pattern'])
            for mode in 'NPET':
                for extension in ('MP4', 'JPG'):
                    with self.subTest(identity=identity, mode=mode, extension=extension):
                        self.assertIsNotNone(pattern.fullmatch(f'20300101_120000_00001_{mode}_A.{extension}'))
            for name in ('20300101_120000_00001_X_A.MP4', '20300101_120000_00001_N_B.MP4', '20300101_120000_00001_N_AxMP4', '20300101_120000_00001_N_A.MP4.extra'):
                self.assertIsNone(pattern.fullmatch(name))

    def test_index_validation_rejects_preescaped_regex(self):
        path = ROOT / 'profiles/vantrue-e1-pro.json'
        profile = json.loads(path.read_text())
        profile['filename_patterns'][0]['pattern'] = r'^(\\d{8})_N_A\\.MP4$'
        validate = runpy.run_path(str(ROOT / 'scripts/build-index.py'))['validate']
        with self.assertRaisesRegex(ValueError, 'overescaped filename pattern'):
            validate(profile, path)

    def test_rove(self):
        profile = json.loads((ROOT / 'profiles/rove-r2-4k-pro.json').read_text())
        pattern = re.compile(profile['filename_patterns'][0]['pattern'])
        self.assertIsNotNone(pattern.fullmatch('2030_0101_120000_001.MP4'))
        for name in ('2030_0101_120000_001xMP4', '2030_0101_120000_001.MP4.extra', '2030_0101_120000_001.JPG'):
            self.assertIsNone(pattern.fullmatch(name))


if __name__ == '__main__':
    unittest.main()
