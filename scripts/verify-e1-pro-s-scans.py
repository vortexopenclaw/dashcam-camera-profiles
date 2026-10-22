#!/usr/bin/env python3
"""Read-only checks for five reviewed E1 Pro S configurations and exact samples.

Run with optional --private-source PATH for direct intake comparison. No private
source location or identifiers are embedded or printed. No generators are run.
"""
import argparse
import json
import re
from pathlib import Path
import jsonschema

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = json.loads('[["platepix-aov-1s-timelapse", [["Normal", "normal", "front", [[272629760, 60, 3840, 2160, 30, 36041820], [138412032, 29.733333333333334, 3840, 2160, 30, 36139380], [272629760, 60, 3840, 2160, 30, 36044004], [100663296, 21.6, 3840, 2160, 30, 36254900]]], ["Parking", "timelapse", "front", [[29360128, 10.2, 3840, 2160, 30, 20494788], [79691776, 30, 3840, 2160, 30, 20478184], [75497472, 29.1, 3840, 2160, 30, 20481574]]]]], ["platepix-hdr-off-aov-2s-collision", [["Normal", "normal", "front", [[272629760, 60, 3840, 2160, 30, 36039524], [180355072, 39.4, 3840, 2160, 30, 36058644], [41943040, 15.033333333333333, 3840, 2160, 30, 20623706], [272629760, 60, 3840, 2160, 30, 36041576], [272629760, 60, 3840, 2160, 30, 36043884], [54525952, 12, 3840, 2160, 30, 36048256]]], ["Parking", "event", "front", [[79691776, 30, 3840, 2160, 30, 20477934], [79691776, 30, 3840, 2160, 30, 20479974], [79691776, 30, 3840, 2160, 30, 20475654]]], ["Parking", "timelapse", "front", [[4259840, 0.4666666666666667, 3840, 2160, 30, 20624486]]]]], ["standard-aov-1s-collision", [["Normal", "continuous", "channel_a", [[41943040, 8.466666666666667, 3840, 2160, 30, 36058328], [12648448, 2.466666666666667, 3840, 2160, 30, 36081116], [272629760, 60, 3840, 2160, 30, 36040860], [272629760, 60, 3840, 2160, 30, 36046368], [272629760, 60, 3840, 2160, 30, 36043920], [29360128, 6.433333333333334, 3840, 2160, 30, 36118468]]], ["Parking", "driving_event", "channel_a", [[79691776, 30, 3840, 2160, 30, 20475808], [79691776, 30, 3840, 2160, 30, 20478332]]], ["Parking", "parking", "channel_a", [[4259840, 0.5666666666666667, 3840, 2160, 30, 20793472]]]]], ["unspecified-aov-2s-timelapse", [["Normal", "normal", "front", [[272629760, 60, 3840, 2160, 30, 36042440], [272629760, 60, 3840, 2160, 30, 36044344], [272629760, 60, 3840, 2160, 30, 36044296], [113246208, 24.566666666666666, 3840, 2160, 30, 36249288]]], ["Parking", "parking_timelapse", "front", [[79691776, 30, 3840, 2160, 30, 20479242], [79691776, 30, 3840, 2160, 30, 20480250], [79691776, 30, 3840, 2160, 30, 20488014], [67108864, 25.133333333333333, 3840, 2160, 30, 20426854]]]]], ["unspecified-collision-turboboot", [["Normal", "normal", "front", [[272629760, 60, 3840, 2160, 30, 36041940], [272629760, 60, 3840, 2160, 30, 36045944], [272629760, 60, 3840, 2160, 30, 36044836], [192937984, 42.233333333333334, 3840, 2160, 30, 36115936]]], ["Parking", "event", "front", [[79691776, 30.033333333333335, 3840, 2160, 30, 20524496], [79691776, 30.033333333333335, 3840, 2160, 30, 20510378], [79691776, 30.033333333333335, 3840, 2160, 30, 20527250], [79691776, 30.033333333333335, 3840, 2160, 30, 20532790]]]]]]')
CONFIGS = json.loads('[["platepix-aov-1s-timelapse", "PlatePix", null, 1, "Timelapse", null], ["platepix-hdr-off-aov-2s-collision", "PlatePix", false, 2, "Collision detection", null], ["standard-aov-1s-collision", "Standard", null, 1, "Collision detection", null], ["unspecified-aov-2s-timelapse", null, null, 2, "Timelapse", null], ["unspecified-collision-turboboot", null, null, null, "Collision detection", true]]')
FIELDS = ('fileSizeBytes', 'durationSeconds', 'width', 'height', 'nominalFrameRate', 'videoBitrate')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--private-source', type=Path)
    args = parser.parse_args()
    ep = ROOT / 'docs/data/e1-pro-s-vt-efi242-evidence.json'
    pp = ROOT / 'profiles/vantrue-e1-pro-s.json'
    evidence = json.loads(ep.read_text())
    profile = json.loads(pp.read_text())
    schema = json.loads((ROOT / 'schemas/profile.schema.json').read_text())
    jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(profile)
    assert profile['id'] == evidence['model_id'] == 'vantrue-e1-pro-s'
    assert profile['model'] == 'E1 Pro S'
    # A separate real-card review validated shared grammar, not sibling identity.
    assert len(profile['filename_patterns']) == 1
    assert profile['filename_patterns'][0]['pattern'] == r'^(\d{8})_(\d{6})_(\d{5})_([NPET])_(A)\.(MP4|JPG)$'
    assert set(profile['filename_patterns'][0]['modes']) == set('NPET')
    assert profile['channel_variants'][0]['roles'] == ['front']
    assert evidence['owner_correction_provenance']['model_label_correction_count'] == 3
    assert evidence['owner_correction_provenance']['already_matching_model_label_count'] == 2
    assert len(evidence['reports']) == len(CONFIGS) == 5
    actual = []
    total = included = anomaly = 0
    for report, config in zip(evidence['reports'], CONFIGS):
        key, quality, hdr, interval, mode, turbo = config
        assert report['configuration'] == key
        a = report['owner_assertions']
        assert (a['model'], a['firmware'], a['channels'], a['roles']) == ('E1 Pro S', 'VT-EFI242', 1, ['front'])
        assert [a['quality'], a['hdr'], a['aov_seconds_per_frame'], a['configured_parking_mode'], a['turboboot_enabled']] == [quality, hdr, interval, mode, turbo]
        assert a['hardware_status'] is None
        groups = []
        for g in report['observed_video_groups']:
            assert g['folder'] in ('Normal', 'Parking')
            if g['folder'] == 'Parking':
                assert g['reviewed_context'] == 'parking'
            pairs = []
            for s in g['storageRateSamples']:
                total += 1
                pairs.append([s[k] for k in FIELDS])
                qualifies = g['folder'] == 'Normal' and s['durationSeconds'] >= 30 and s['videoBitrate'] > 30000000
                assert s['driving_aggregate_included'] == qualifies
                included += qualifies
                if g['folder'] == 'Normal' and s['videoBitrate'] < 30000000:
                    anomaly += 1
                    assert not qualifies and s['reviewed_sample_context'] == 'potential TurboBoot, unverified'
            groups.append([g['folder'], g['mode'], g['channel'], pairs])
        actual.append([key, groups])
    assert actual == EXPECTED, 'Exact sample context or numeric pair changed'
    assert total == 42 and included == 16 and anomaly == 1
    assert evidence['driving_aggregate_policy']['minimum_playback_duration_seconds'] == 30
    assert evidence['driving_aggregate_policy']['video_bitrate_strictly_greater_than_bps'] == 30000000
    assert len(profile['video_samples']) == 17
    import runpy
    runpy.run_path(str(ROOT / 'scripts/build-index.py'))['validate'](profile, pp)
    expected_rows = []
    for report in evidence['reports']:
        for g in report['observed_video_groups']:
            buckets = {}
            for s in g['storageRateSamples']:
                kind = 'driving' if s['driving_aggregate_included'] else ('potential TurboBoot / unverified' if 'TurboBoot' in s['reviewed_sample_context'] else ('short normal-folder sample / unverified' if g['folder'] == 'Normal' else 'parking / raw ' + g['mode']))
                buckets.setdefault(kind, []).append(s['videoBitrate'] / 1000000)
            for kind, rates in buckets.items():
                rate = f'{min(rates):.6f}-{max(rates):.6f} Mbps' if min(rates) != max(rates) else f'{rates[0]:.6f} Mbps'
                expected_rows.append((report['configuration'], kind, rate))
    assert [(r['recording_configuration'], r['mode'], r['bitrate']) for r in profile['video_samples']] == expected_rows
    for row in profile['video_samples']:
        assert row['recording_configuration'] in {c[0] for c in CONFIGS}
        assert 'VT-EFI242' in row['settings_note']
    if args.private_source:
        private = json.loads(args.private_source.read_text())
        assert len(private) == 5
        for original, report in zip(private, evidence['reports']):
            scan = original['record']['scan']
            assert scan['folderSummaries'] == report['folder_inventory']
            assert len(scan['videoSpecSummaries']) == len(report['observed_video_groups'])
            for source, public in zip(scan['videoSpecSummaries'], report['observed_video_groups']):
                for k, v in public.items():
                    if k in ('reviewed_context', 'review_note', 'storageRateSamples'):
                        continue
                    assert source[k] == v
                assert len(source['storageRateSamples']) == len(public['storageRateSamples'])
                for source_sample, public_sample in zip(source['storageRateSamples'], public['storageRateSamples']):
                    assert source_sample == {k: public_sample[k] for k in FIELDS}
        print('PASS direct private intake comparison: all inventories, groups and 42 numeric pairs')
    text = ep.read_text() + pp.read_text()
    assert not re.search(r'/Users/|receivedAt|createdAt|sampleRelativePaths|firstTimestamp|lastTimestamp|contact|[0-9a-f]{8}-[0-9a-f]{4}-', text)
    assert not re.search(r'\d{8}_\d{6}|\d{4}-\d{2}-\d{2}T', text)
    assert {g['mode'] for r in evidence['reports'] for g in r['observed_video_groups']} >= {'driving_event', 'parking_timelapse', 'event'}
    print(f'PASS profile schema + privacy + 5 configurations, 12 groups, {total} exact samples, {included} driving-eligible, {anomaly} separate anomaly')


if __name__ == '__main__':
    main()
