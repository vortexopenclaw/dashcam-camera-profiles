#!/usr/bin/env python3
"""Small negative regressions for collision-test provenance invariants."""
import json
from pathlib import Path
import runpy
import unittest

R = Path(__file__).resolve().parents[1]
verify = runpy.run_path(str(R/'scripts/verify-z100-collision.py'))['verify']

class CollisionEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.c = json.loads((R/'docs/data/ddpai-z100-master-evidence.json').read_text())['collision_test_scan']
        self.p = json.loads((R/'profiles/ddpai-z100-master.json').read_text())

    def test_valid(self):
        self.assertEqual(len(verify(self.c, self.p)), 40)

    def test_reject_changed_source_pair(self):
        self.c['groups'][0]['samples'][0]['source_sample']['videoBitrate'] += 1
        with self.assertRaises(AssertionError): verify(self.c, self.p)

    def test_reject_wrong_occurrence_link(self):
        o = self.c['submitted_occurrences'][0]
        o['matching_clip_indices'] = [(o['matching_clip_indices'][0]+1) % 40]
        with self.assertRaises(AssertionError): verify(self.c, self.p)

    def test_reject_duplicate_clip_identity(self):
        self.c['groups'][0]['samples'][1]['clip_index'] = self.c['groups'][0]['samples'][0]['clip_index']
        with self.assertRaises(AssertionError): verify(self.c, self.p)

    def test_reject_all_collision_attribution(self):
        self.c['groups'][0]['sample_mode'] = 'collision recording'
        with self.assertRaises(AssertionError): verify(self.c, self.p)

    def test_reject_inferred_firmware(self):
        self.c['firmware'] = 'unsupported'
        with self.assertRaises(AssertionError): verify(self.c, self.p)

    def test_reject_dropped_short_sample(self):
        self.c['groups'][1]['samples'].pop()
        with self.assertRaises(AssertionError): verify(self.c, self.p)

    def test_reject_stale_profile_summary(self):
        self.p['video_samples'][14]['bitrate'] = '0 Mbps'
        with self.assertRaises(AssertionError): verify(self.c, self.p)

if __name__ == '__main__':
    unittest.main()
