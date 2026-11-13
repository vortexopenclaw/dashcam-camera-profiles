"""Narrow correction allowlist; full baseline/negative controls in retest regression."""
from copy import deepcopy
SID = 'vortex-owner-z100-master-4ch-retest-dc009-12v6'
OLD = 'vortex-owner-z100-master-4ch-dc009-12v6-timelapse'
FACT = {'label': 'Current owner driving and timelapse power (explicit retest)', 'value': 'Driving: 1185 mA (14.931 W derived). Timelapse: 589 mA (7.4214 W derived). Explicit owner retest corrects current driving and timelapse only, superseding earlier 964 mA / 12.1464 W driving and 632 mA / 7.9632 W timelapse; original dossiers remain immutable history. Collision idle 44 mA / 0.5544 W and event recording 935 mA / 11.781 W remain current and unchanged. Installed front/telephoto/rear/MINI3X cabin (4 cameras). Owner tentatively reports front/rear indicated on the timelapse display and telephoto/cabin not seen saving; no clip verification establishes active recording views. Cabin LEDs being on does not prove saved footage. Whole-system supply-DC measurement, not isolated camera consumption. Main firmware 8.0.0.23 observed in fresh physical-card tracklog; MINI3X 9.0.1.10 observed in paired current-card product logs, not intrinsic clip metadata. Rear 9.0.0.17 belongs only to older cohort; current rear version unknown. 12.6 V and DC009 carried from standing current owner-test context, not restated in these messages. Cloud off belongs to earlier context; current connectivity unknown. Watts derived from current with Decimal. No capture FPS/SPF, wake/start timing or definitive recorded roles inferred.'}
SOURCE = {'kind': 'source', 'label': 'Vortex Radar test unit; corrected driving and timelapse owner retest', 'url': 'https://vortexopenclaw.github.io/dashcam-camera-profiles/data/ddpai-z100-master-4ch-retest-power-evidence.json'}
PRIOR_FACT = 'Earlier 4CH test, before the latest owner-reported firmware update: Driving recording: 964 mA (12.1464 W derived). Timelapse parking: 632 mA (7.9632 W derived). Installed 4CH; active parking views not separately established. 12.6 V, cloud off, same DC009 hardwire cable. Rear firmware only: 9.0.0.17; main unit, front, cabin and telephoto firmware unknown. Rear 4K / cabin 3K are owner-declared, not measured card metadata. Collision detection idle and recording were pending in that earlier test; see the separate post-update readings below. Card scans pending; no new 4CH bitrate/FPS or timing measurements. Earlier 2CH power and video cohorts are unchanged.'
CURRENT_FACT = 'Historical — driving and timelapse superseded by explicit owner retest; original readings retained: Earlier 4CH test, before the latest owner-reported firmware update: Driving recording: 964 mA (12.1464 W derived). Timelapse parking: 632 mA (7.9632 W derived). Installed 4CH; active parking views not separately established. 12.6 V, cloud off, same DC009 hardwire cable. Rear firmware only: 9.0.0.17; main unit, front, cabin and telephoto firmware unknown. Rear 4K / cabin 3K are owner-declared, not measured card metadata. Collision detection idle and recording were pending in that earlier test; see the separate post-update readings below. Card scans pending; no new 4CH bitrate/FPS or timing measurements. Earlier 2CH power and video cohorts are unchanged.'
OLD_NOTES = 'Separate owner-confirmed installed 4CH front/telephoto/rear/cabin configuration; rear 4K and cabin 3K are owner-declared, not card-scan measurements. Same DC009 hardwire cable explicitly inherited from preceding 2CH test; cloud off; 12.6 V. Rear firmware only: 9.0.0.17; main unit, front, telephoto and cabin firmware unknown. Current is source-reported; watts derived exactly with Decimal as 12.6 V × mA / 1000. Active parking views not separately established. Both collision states are pending, not zero or measured. Card scans promised but not received for this cohort; no new bitrate, playback FPS, capture cadence, timing, HDR or quality evidence. Earlier 2CH/video cohorts remain separate.'
NEW_NOTES = 'Separate owner-confirmed installed 4CH front/telephoto/rear/cabin configuration; rear 4K and cabin 3K are owner-declared, not card-scan measurements. Same DC009 hardwire cable explicitly inherited from preceding 2CH test; cloud off; 12.6 V. Rear firmware only: 9.0.0.17; main unit, front, telephoto and cabin firmware unknown. Current is source-reported; watts derived exactly with Decimal as 12.6 V × mA / 1000. Active parking views not separately established. Both collision states are pending, not zero or measured. Card scans promised but not received for this cohort; no new bitrate, playback FPS, capture cadence, timing, HDR or quality evidence. Earlier 2CH/video cohorts remain separate. Historical: explicitly superseded by owner retest vortex-owner-z100-master-4ch-retest-dc009-12v6-timelapse (589 mA / 7.4214 W); original source values and dossier preserved.'

def restore_profile(value):
    value = deepcopy(value)
    assert value['technical_facts'].pop() == FACT
    assert value['sources'].pop() == SOURCE
    assert value['technical_facts'][7]['value'] == CURRENT_FACT
    value['technical_facts'][7]['value'] = PRIOR_FACT
    return value

def restore_rows(values, source_index=False):
    values = deepcopy(values)
    key = 'id' if source_index else 'source_id'
    values = [v for v in values if v.get(key) != SID]
    if not source_index:
        for row in values:
            if row['id'] == OLD:
                assert row['notes'] == NEW_NOTES
                assert row['superseded'] in (True, 'True')
                row['notes'] = OLD_NOTES
                row['superseded'] = 'False' if isinstance(row['superseded'],str) else False
    return values

def restore_loaded(path, value):
    if path == 'parking/measurements.json': return restore_rows(value)
    if path == 'parking/sources.json': return restore_rows(value, True)
    if path == 'profiles/ddpai-z100-master.json': return restore_profile(value)
    if path == 'docs/data/cameras.json':
        value = deepcopy(value)
        value['cameras'] = [restore_profile(c) if c['id']=='ddpai-z100-master' else c for c in value['cameras']]
    if path == 'docs/data/parking-measurements.json':
        value = deepcopy(value)
        value['measurements'] = restore_rows(value['measurements'])
        value['sources'] = restore_rows(value['sources'], True)
        for k in ['measurements','sources','source_reviews_completed','superseded_measurements']: value['coverage'][k] -= 1
    return value
