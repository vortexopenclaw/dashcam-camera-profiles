#!/usr/bin/env python3
"""Read-only identity, privacy and exact historical-retention regression.

Optional --card-root and --private-evidence perform source comparisons without
printing original filenames, private paths or settings contents. No generator runs.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import runpy

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
VIDEO_SHA256 = '517991a812356a09c9272b1757c64a763f1bd37286aa71e6bdbb147236273eec'
HISTORICAL_SHA256 = '3ddb3769bd183a1a51a79a757958d4629763815980426eda6dce55e179096df7'


def check(condition, label):
    if not condition:
        raise AssertionError(label)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--card-root', type=Path)
    parser.add_argument('--private-evidence', type=Path)
    args = parser.parse_args()
    pp = ROOT / 'profiles/vantrue-e1-pro-s.json'
    dp = ROOT / 'docs/data/e1-pro-s-card-identity.json'
    hp = ROOT / 'docs/data/e1-pro-s-vt-efi242-evidence.json'
    profile = json.loads(pp.read_text())
    dossier = json.loads(dp.read_text())
    historical = json.loads(hp.read_text())
    schema = json.loads((ROOT / 'schemas/profile.schema.json').read_text())
    jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker()).validate(profile)
    validation = runpy.run_path(str(ROOT / 'scripts/build-index.py'))
    validation['validate'](profile, pp)  # Validation only; never calls build/main.
    check(profile['id'] == dossier['model_id'] == 'vantrue-e1-pro-s', 'stable identity')
    check(profile['model'] == 'E1 Pro S', 'canonical short name')
    check(profile['evidence']['level'] == 'card-validated', 'real-card boundary')
    identity = dossier['identity']
    check(identity['observed_exact_marker'] == 'GPS/E1PROS_Settings.ini', 'exact S marker')
    check(identity['older_documented_marker'] == 'GPS/E1PRO_Settings.ini', 'older marker distinct')
    check(identity['complete_basename_required'] is True, 'complete basename policy')
    check(identity['shared_media_layout_is_model_identity'] is False, 'shared layout not identity')
    check(identity['firmware']['independently_extracted'] is False, 'no firmware extraction claim')
    check(identity['firmware']['owner_confirmed_historical_configurations'] == 'VT-EFI242', 'owner firmware retained')
    check(profile['channel_variants'] == [{'channels': 1, 'roles': ['front'], 'variant': 'Front-only', 'validation': 'owner_confirmed'}], 'channel scope retained')
    folders = {f['path']: f for group in ('driving_folders', 'parking_folders', 'other_folders') for f in profile['recording'][group]}
    check(set(folders) == {'Normal', 'Parking', 'Event', 'Photo', 'GPS'}, 'observed folders')
    check(not folders['GPS']['importable'], 'support not importable')
    check(folders['Event']['validation'] == 'real_card_directory_observed_empty', 'empty Event boundary')
    for name, scope in [('Normal', 'submitted_scan_inventory'), ('Parking', 'submitted_scan_inventory_and_owner_context'), ('Photo', 'submitted_scan_inventory')]:
        check(folders[name]['validation'] == scope, 'historical folder observation scope')
    grammar = dossier['filename_grammar']
    check(len(profile['filename_patterns']) == 1, 'one shared grammar')
    check(profile['filename_patterns'][0]['pattern'] == grammar['pattern'], 'grammar consistency')
    check(set(profile['filename_patterns'][0]['modes']) == set('NPET'), 'token set')
    check(grammar['shared_between_models'] is True, 'grammar not identity')
    pattern = re.compile(grammar['pattern'])
    # Synthetic tokens only; do not embed or print original capture names.
    prefix = '0' * 8 + '_' + '0' * 6 + '_' + '0' * 5
    for mode in 'NPET':
        for extension in ('MP4', 'JPG'):
            check(pattern.fullmatch(f'{prefix}_{mode}_A.{extension}') is not None, 'valid synthetic grammar')
    for suffix in ('_X_A.MP4', '_N_B.MP4', '_N_A.MP4.extra'):
        check(pattern.fullmatch(prefix + suffix) is None, 'reject nonmatching grammar')
    check(dossier['media_totals'] == {'video': 12, 'photo': 3}, 'media totals')
    check(grammar['current_card_mode_channel_counts'] == {'N_A': 9, 'P_A': 6}, 'current token counts')
    check(hashlib.sha256(hp.read_bytes()).hexdigest() == HISTORICAL_SHA256, 'entire historical dossier byte-exact')
    serialized_video = json.dumps(profile['video_samples'], sort_keys=True, separators=(',', ':')).encode()
    check(hashlib.sha256(serialized_video).hexdigest() == VIDEO_SHA256, 'all video sample fields exact')
    # Reuse the original regression's exact source constants, not a new estimate.
    old = runpy.run_path(str(ROOT / 'scripts/verify-e1-pro-s-scans.py'))
    actual = [[r['configuration'], [[g['folder'], g['mode'], g['channel'], [[s[k] for k in old['FIELDS']] for s in g['storageRateSamples']]] for g in r['observed_video_groups']]] for r in historical['reports']]
    check(actual == old['EXPECTED'], '42 exact paired metadata measurements')
    configs = [[r['configuration']] + [r['owner_assertions'][k] for k in ('quality', 'hdr', 'aov_seconds_per_frame', 'configured_parking_mode', 'turboboot_enabled')] for r in historical['reports']]
    check(configs == old['CONFIGS'], 'five exact configuration cohorts')
    check(len(profile['video_samples']) == 17, 'historical sample-row count')
    check(any('mixed modes within files are unverified' in n for n in profile['notes']), 'mixed-mode limit')
    urls = {s['url'] for s in profile['sources']}
    check(any(u.endswith('/docs/card-profiles/vantrue-e1-pro-s.md') for u in urls), 'companion source reference')
    cp = ROOT / 'docs/data/e1-sibling-card-comparison.json'
    comparison = json.loads(cp.read_text())
    cards = {c['model_id']: c for c in comparison['cards']}
    check(set(cards) == {'vantrue-e1-pro', 'vantrue-e1-pro-s'}, 'separate sibling evidence')
    for model_id, marker, firmware, count in [
        ('vantrue-e1-pro-s', 'E1PROS_Settings.ini', 'VT-EFI242', 12),
        ('vantrue-e1-pro', 'E1PRO_Settings.ini', 'VT-EFH112', 4),
    ]:
        card = cards[model_id]
        check(card['exact_settings_basenames'] == [marker], 'direct sibling exact marker')
        check(card['owner_reported_current_firmware'] == firmware and card['firmware_independently_extracted'] is False, 'owner-only current firmware')
        check(card['all_inventoried_videos_probed'] and card['videos_probed'] == count, 'complete bounded sibling probes')
        check(sum(g['video_track_samples'] for g in card['video_groups']) == count, 'sibling grouped totals')
    check(comparison['capture_firmware'].startswith('Unknown'), 'clip firmware remains unknown')
    check(comparison['quality_hdr_settings'].startswith('Unknown'), 'no controlled quality comparison')
    check(any(u.endswith('/docs/data/e1-sibling-card-comparison.json') for u in urls), 'sibling source reference')
    for path in (pp, dp, cp):
        text = path.read_text()
        for label, private_pattern in validation['PRIVATE_PATTERNS'].items():
            check(not private_pattern.search(text), 'public privacy: ' + label)
        check(not re.search(r'\d{8}_\d{6}|\d{4}-\d{2}-\d{2}T|receivedAt|createdAt|sampleRelativePaths|firstTimestamp|lastTimestamp|receipt(?:Id|_id)', text), 'no original names, timestamps or receipts')
    if args.private_evidence:
        private = json.loads(args.private_evidence.read_text())
        check(dossier['card_inventory'] == private['card_inventory'], 'private source inventory')
        check(identity['observed_exact_marker'] == private['identity']['observed_exact_safe_marker'], 'private source exact marker')
        check(identity['older_documented_marker'] == private['identity']['older_profile_documented_marker'], 'private source older-marker provenance')
        check(private['identity']['firmware_observed_in_inspected_support_or_container_headers'] is False, 'private source firmware limit')
        source_pattern = re.compile(private['grammar']['pattern'])
        for token in 'NPET':
            for extension in ('MP4', 'JPG'):
                synthetic = f'{prefix}_{token}_A.{extension}'
                check(source_pattern.fullmatch(synthetic) is not None and pattern.fullmatch(synthetic) is not None, 'private source grammar parity')
        print('PASS retained private research comparison; no private data printed')
    if args.card_root:
        inventory = {}
        tokens = Counter()
        matching = nonmatching = 0
        for name in dossier['card_inventory']:
            directory = args.card_root / name
            check(directory.is_dir(), 'card folder present')
            files = [p for p in directory.iterdir() if p.is_file() and not p.name.startswith('.')]
            inventory[name] = {'file_count': len(files), 'extension_counts': dict(Counter(p.suffix.lower() for p in files))}
            for file in files:
                if file.suffix.lower() in ('.mp4', '.jpg'):
                    match = pattern.fullmatch(file.name)
                    if match:
                        matching += 1
                        tokens[match[4] + '_' + match[5]] += 1
                    else:
                        nonmatching += 1
        check(inventory == dossier['card_inventory'], 'live card inventory exact')
        check((args.card_root / identity['observed_exact_marker']).is_file(), 'live exact marker')
        check(not (args.card_root / identity['older_documented_marker']).exists(), 'older marker absent on reviewed S card')
        check(dict(tokens) == grammar['current_card_mode_channel_counts'], 'live token counts')
        check(matching == grammar['current_card_matching_media_count'] == 15 and nonmatching == grammar['current_card_nonmatching_media_count'] == 0, 'live grammar coverage')
        print('PASS mounted card: 12 videos, 3 photos, 5 folders, exact S marker; no payload read')
    print('PASS schema + privacy + identity boundaries; historical dossier byte-exact, 42 paired samples, 5 cohorts and 17 video rows unchanged')


if __name__ == '__main__':
    main()
