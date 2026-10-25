#!/usr/bin/env python3
"""Source-exact regression for the owner-confirmed rcg530 T340 chart."""
import json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
e=json.loads((R/'docs/data/t340-1.0_261023T2-rcg530-evidence.json').read_text())
expected=[(515,598,551,6.49,7.54,6.94),(573,654,608,7.22,8.24,7.66),(544,626,581,6.85,7.89,7.32),(600,690,643,7.56,8.69,8.1),(34,37,35,.43,.47,.44),(34,38,35,.43,.48,.44),(505,587,532,6.36,7.4,6.7),(559,635,588,7.04,8,7.41),(493,577,511,6.21,7.27,6.44),(557,641,573,7.02,8.08,7.22),(7,9,8,.09,.11,.1),(5,7,6,.06,.09,.08)]
assert len(e['measurements'])==12
assert e['contributor']=='rcg530' and e['test_date'] is None and e['source_url'] is None
assert e['measurements'][10]['mode']=='power_button_off_model_text_T140'
assert e['measurements'][10]['reviewed_model']=='Viofo T340' and e['owner_confirmation']
rows=json.loads((R/'parking/measurements.json').read_text())
new=[r for r in rows if r['id'].startswith('rcg530-t340-1.0_261023T2-')]
assert len(new)==6
for m,values in zip(e['measurements'],expected):
    assert tuple(m[f][k] for f in ('current_ma','power_w') for k in ('min','max','avg'))==values
    if not m['parking_comparison_eligible']: continue
    r=next(r for r in new if r['source_mode']==m['mode'] and r['lighting']==m['lighting'])
    for f in ('current_ma','power_w'):
        assert (r[f+'_min'],r[f+'_max'],r[f])==tuple(m[f][k] for k in ('min','max','avg'))
    assert r['firmware']=='1.0_261023T2' and r['tester']=='rcg530' and r['voltage_v']==12.6
    assert r['source_url']==e['evidence_url'] and r['ir']=='unknown' and r['test_status']=='unknown'
    assert r['wake_seconds'] is None and r['reported_startup_seconds'] is None and not r['power_is_derived']
timed=[r for r in new if r['source_mode']=='LPID_monitoring']
assert len(timed)==2
assert len({r['reported_startup_timing_group'] for r in timed})==1
for r in timed:
    assert (r['reported_startup_seconds_min'],r['reported_startup_seconds_max'])==(1.76,1.85)
    assert r['reported_startup_method']=='Impact event to start of recording (source-reported)'
    assert r['reported_startup_source']==e['evidence_url']
assert all(r.get('reported_startup_seconds_min') is None for r in new if r not in timed)
assert len([r for r in rows if r['model']=='T340' and r not in new])==7
assert e['timings']['reported_LPID_recording_start_after_impact_event_s']['first_saved_frame_verified'] is False
assert len(e['video_observations'])==3 and len(e['timings'])==9
assert 'pending clarification' not in json.dumps(e) and 'No contributor' not in json.dumps(e)
print('Verified 12 full source rows, six parking rows, seven historical T340 rows and separated timing/video evidence')
