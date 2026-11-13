"""Exact, narrowly scoped later power additions for historical preservation guards."""
from copy import deepcopy

BASELINE = '5597fe88b6f52e75f5dd6932c3a5bed5b6a2465c'
SID = 'vortex-owner-z100-master-4ch-post-update-dc009-12v6'
DOSSIER = 'docs/data/ddpai-z100-master-4ch-post-update-power-evidence.json'
URL = 'https://vortexopenclaw.github.io/dashcam-camera-profiles/data/ddpai-z100-master-4ch-post-update-power-evidence.json'
QUOTE = 'back to power draw measurements with the z100 master. ive got it in parking mode, 4ch with the mini3x connected, collision detection mode. 12.6v. latest firmware that we updated to yesterday, same hardwire cable. idle: 44 mA recording: 935 mA'
OLD_4CH_VALUE = 'Driving recording: 964 mA (12.1464 W derived). Timelapse parking: 632 mA (7.9632 W derived). Installed 4CH; active parking views not separately established. 12.6 V, cloud off, same DC009 hardwire cable. Rear firmware only: 9.0.0.17; main unit, front, cabin and telephoto firmware unknown. Rear 4K / cabin 3K are owner-declared, not measured card metadata. Collision detection idle and recording: not yet recorded (pending, not zero). Card scans pending; no new 4CH bitrate/FPS or timing measurements. Earlier 2CH power and video cohorts are unchanged.'
NEW_4CH_VALUE = 'Earlier 4CH test, before the latest owner-reported firmware update: ' + OLD_4CH_VALUE.replace('Collision detection idle and recording: not yet recorded (pending, not zero).', 'Collision detection idle and recording were pending in that earlier test; see the separate post-update readings below.')
FACT = {
    'label': 'Latest owner 4CH collision parking power (post-update)',
    'value': 'Idle monitoring: 44 mA (0.5544 W derived). Event recording: 935 mA (11.781 W derived). 12.6 V, same DC009 hardwire cable; installed front + telephoto + 4K rear + 3K MINI3X cabin. Owner reports latest firmware updated yesterday; exact version is unknown. Cloud off was prior setup context, not restated or independently verified after the update. Active parking views and startup/wake timings remain unknown. This separate cohort does not revise earlier power or video measurements or establish a firmware power reduction.'
}
SOURCE = {'kind': 'source', 'label': 'Vortex Radar test unit; latest post-update 4CH collision parking power readings', 'url': URL}


def prior_power_profile(profile):
    """Undo only the exact authorized appended facts/source and pending-note wording."""
    result = deepcopy(profile)
    assert result['technical_facts'].pop() == FACT
    assert result['sources'].pop() == SOURCE
    assert result['technical_facts'][7] == {'label': 'Separate owner 4CH power cohort: front/telephoto/rear/cabin', 'value': NEW_4CH_VALUE}
    result['technical_facts'][7]['value'] = OLD_4CH_VALUE
    return result


def without_post_update(rows, source_index=False):
    """Exclude only this source, whose complete contents have a dedicated regression."""
    key = 'id' if source_index else 'source_id'
    return [row for row in rows if row.get(key) != SID]
