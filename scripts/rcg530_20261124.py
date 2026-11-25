"""Exact allowlist for the 2026-11-24 rcg530 refresh, used by historical preservation guards.

The refresh appends T330/T340 v1.0_261030, A229 Ultra V1.2_260813 and E1 Pro S AOV CD 2 SPF rows,
seven source-index entries, two profile facts/sources and refreshed chart links for rows whose
original DashCamTalk attachments are no longer served. Everything else must remain byte-exact.
"""
from copy import deepcopy

BASELINE = 'bdd3db85452b37c1cbef5fd80317f801aac14c60'
DOSSIER = 'docs/data/rcg530-20261124-video-evidence.json'
DOSSIER_URL = 'https://vortexopenclaw.github.io/dashcam-camera-profiles/data/rcg530-20261124-video-evidence.json'
NEW_ROW_PREFIXES = ('rcg530-674502-', 'rcg530-674496-', 'rcg530-677657-')
NEW_ROW_IDS = {'rcg530-675957-12'}
NEW_SOURCE_IDS = ['rcg530-674502', 'rcg530-674496', 'rcg530-677657', 'rcg530-677699', 'rcg530-676290', 'rcg530-676269', 'rcg530-677979']
AT = 'https://dashcamtalk.com/forum/attachments/'
IMAGE_LINKS = {  # row-id prefix: (original, refreshed)
    'rcg530-675874-': (AT + '70mai_a900_ultra_2ch_power_consumption_20261015-webp.94821/', AT + '70mai_a900_ultra_2ch_power_consumption_20261116-webp.95925/'),
    'rcg530-675957-': (AT + '1792189574854-webp.94861/', AT + '1792738835809-webp.95141/'),
}
SOURCE_CHANGES = {
    'rcg530-675874': {
        'images': ([AT + '70mai_a900_ultra_2ch_power_consumption_20261015-webp.94821/', AT + '70mai_a900_ultra_2ch_parking_mode_times_20261015-webp.94822/'],
                   [AT + '70mai_a900_ultra_2ch_power_consumption_20261116-webp.95925/', AT + '70mai_a900_ultra_2ch_parking_mode_times_20261116-webp.95924/', AT + '1794931203274-webp.95960/']),
        'notes_suffix': ' 2026-11-24 review: post edited 16/17-Nov-2026. Refreshed power chart 95925 repeats all 13 parking values and FW v1.0.65ww '
                        '(original 94821 attachment no longer served). Added 1-minute driving bitrate chart 95960 is FW v1.3.88ww, a later firmware '
                        'than the power tests; retained in docs/data/rcg530-20261124-video-evidence.json.',
        'measurement_count': (13, 13),
    },
    'rcg530-675957': {
        'images': ([AT + '1792189574854-webp.94861/', AT + '1792189377371-webp.94860/'],
                   [AT + '1792738835809-webp.95141/', AT + '1792738894098-webp.95142/']),
        'notes_suffix': ' 2026-11-24 review: post edited 22/23-Oct-2026. Refreshed chart 95141 repeats the eleven earlier values (original 94861 no longer '
                        'served), relabels AOV CD 1 fps as 1 spf, and adds AOV CD 2 SPF 45 mA / 0.57 W as row 12. Thread now has three pages.',
        'measurement_count': (11, 12),
    },
}
METADATA_UPDATED = ('2026-11-13', '2026-11-24')
SCOPE_SUFFIX = ' 2026-11-24 refresh reviewed rcg530 posts since 2026-10-16 in nine recently active threads found through the public new-posts listing.'
PROFILE_ADDITIONS = {
    'viofo-t340': (
        {'label': 'rcg530 firmware v1.0_261030 4CH bitrate chart', 'value': 'Source-reported 1-minute driving files, unreleased test firmware: front 27.03 / 31.94 / 36.86 / 40.96 Mbps (196 / 232 / 266 / 296 MB) at Low / Normal / High / Maximum; interior, rear and telephoto each 11.87 / 14.33 / 21.29 / 23.75 Mbps (88 / 106 / 154 / 172 MB). Chart does not state fps or codec. Separate from this repository\'s card-measured samples and the 1.0_261023T2 chart.'},
        {'kind': 'research', 'label': 'rcg530 v1.0_261030 bitrate chart transcription', 'url': DOSSIER_URL}),
    'viofo-a229-ultra': (
        {'label': 'rcg530 firmware V1.2_260813 bitrate chart', 'value': 'Source-reported 1-minute driving files. 3CH: front 25.39 / 31.12 / 34.40 / 36.04 Mbps, RNE800 4K rear 22.93 / 27.03 / 31.12 / 34.40, RNF210 1080p interior 8.19 / 12.28 / 13.92 / 15.56 at Low / Normal / High / Maximum. 2CH bitrates match 3CH. 1CH front rises to 27.03 / 37.68 / 42.59 / 49.15 Mbps. Low Bitrate parking files 4.09 Mbps front and rear, 3.93 interior. Chart does not state fps or codec; file sizes are retained in the linked transcription.'},
        {'kind': 'research', 'label': 'rcg530 V1.2_260813 bitrate chart transcription', 'url': DOSSIER_URL}),
}
README_ADDITION = "2026-11-24 rcg530 refresh adds separate cohorts from public posts: T330 3CH and T340 4CH on unreleased firmware v1.0_261030 (32 rows each: eight modes, all cameras versus interior Only On While Driving, day and night), a limited A229 Ultra suite on production V1.2_260813 / 4K_V1.1_260126 (eight low-bitrate and 10 fps time-lapse rows), and the E1 Pro S AOV Collision Detection 2 SPF row. T330/T340 values come from the average-power column of the tester's runtime-estimate charts; runtime estimates are excluded. Night rows keep IR unknown because the charts do not label IR per row. A900 Ultra and E1 Pro S chart links now point to the refreshed attachments; their values are unchanged. Video bitrate charts for the A900 Ultra (FW v1.3.88ww, later than its power tests), T330, T340 and A229 Ultra are transcribed in [rcg530-20261124-video-evidence.json](../docs/data/rcg530-20261124-video-evidence.json).\n\nThe "


def restore_readme(data):
    """Remove only the exact appended documentation paragraph."""
    addition = README_ADDITION.encode()
    assert data.count(addition) == 1
    return data.replace(addition, b'', 1)


TOUCHED = {'parking/measurements.json', 'parking/sources.json', 'parking/metadata.json',
           'profiles/viofo-t340.json', 'profiles/viofo-a229-ultra.json', 'docs/data/cameras.json',
           'docs/data/parking-measurements.json'}


def is_new_row(row_id):
    return row_id in NEW_ROW_IDS or row_id.startswith(NEW_ROW_PREFIXES)


def restore_rows(values, source_index=False):
    """Drop the appended rows/sources and undo only the allowlisted link/note/count changes."""
    values = deepcopy(values)
    if source_index:
        values = [v for v in values if v['id'] not in NEW_SOURCE_IDS]
        for v in values:
            change = SOURCE_CHANGES.get(v['id'])
            if not change:
                continue
            old, new = change['images']
            if v['images'] == new:
                v['images'] = old
            assert v['images'] == old, v['id']
            if v['notes'].endswith(change['notes_suffix']):
                v['notes'] = v['notes'][:-len(change['notes_suffix'])]
            old_count, new_count = change['measurement_count']
            if v['measurement_count'] in (new_count, str(new_count)):
                v['measurement_count'] = type(v['measurement_count'])(old_count)
        return values
    values = [v for v in values if not is_new_row(v['id'])]
    for v in values:
        for prefix, (old, new) in IMAGE_LINKS.items():
            if v['id'].startswith(prefix) and v.get('image_url') == new:
                v['image_url'] = old
    return values


def restore_profile(profile):
    profile = deepcopy(profile)
    addition = PROFILE_ADDITIONS.get(profile.get('id'))
    if addition and profile['technical_facts'] and profile['technical_facts'][-1] == addition[0]:
        profile['technical_facts'].pop()
        assert profile['sources'].pop() == addition[1], profile['id']
    return profile


def restore_metadata(value):
    value = deepcopy(value)
    if value.get('updated') == METADATA_UPDATED[1]:
        value['updated'] = METADATA_UPDATED[0]
    note = value['coverage']['scope_note']
    if note.endswith(SCOPE_SUFFIX):
        value['coverage']['scope_note'] = note[:-len(SCOPE_SUFFIX)]
    return value


def restore_loaded(path, value):
    if path == 'parking/measurements.json':
        return restore_rows(value)
    if path == 'parking/sources.json':
        return restore_rows(value, True)
    if path == 'parking/metadata.json':
        return restore_metadata(value)
    if path.startswith('profiles/'):
        return restore_profile(value)
    if path == 'docs/data/cameras.json':
        value = deepcopy(value)
        value['cameras'] = [restore_profile(c) for c in value['cameras']]
        return value
    if path == 'docs/data/parking-measurements.json':
        value = restore_metadata(value)
        before = len(value['measurements']), len(value['sources'])
        value['measurements'] = restore_rows(value['measurements'])
        value['sources'] = restore_rows(value['sources'], True)
        removed_rows = before[0] - len(value['measurements'])
        removed_sources = before[1] - len(value['sources'])
        if removed_rows or removed_sources:
            value['coverage']['measurements'] -= removed_rows
            value['coverage']['sources'] -= removed_sources
            value['coverage']['source_reviews_completed'] -= removed_sources
        return value
    return value
