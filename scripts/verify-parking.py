#!/usr/bin/env python3
"""Regression checks for the parking dataset and public exports."""
import copy
import csv
import importlib.util
import io
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('parking_build',ROOT/'scripts/build-parking-data.py')
assert spec is not None and spec.loader is not None
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
rows=json.loads((ROOT/'parking/measurements.json').read_text())
sources=json.loads((ROOT/'parking/sources.json').read_text())
mod.validate(rows,sources)
assert rows, 'Empty production dataset'
public=ROOT/'docs/data/parking-measurements.json';csv_path=ROOT/'docs/data/parking-measurements.csv'
before=(public.read_bytes(),csv_path.read_bytes());payload=mod.build()
assert before==(public.read_bytes(),csv_path.read_bytes()),'Public exports were stale; commit rebuilt files'
exports=list(csv.DictReader(io.StringIO(csv_path.read_text())))
assert {r['id'] for r in rows}=={r['id'] for r in exports},'CSV row parity'
assert len(rows)==len(exports)==payload['coverage']['measurements']
assert all(any(r.get(k) is not None for k in ['power_w','current_ma','current_ma_min','power_w_min']) for r in rows)
assert all(r['measurement_statistic']=='range' for r in rows if r['current_ma_min'] is not None or r['power_w_min'] is not None)
assert {'rcg530','Vortex Radar'} <= {r['tester'] for r in rows}
assert all(r.get('source_is_private') for r in rows if r['tester']=='Vortex Radar')
chart_ids={f'vortex-sheet-row-{n}' for n in [4,6,9,11,12,15,17,21]}
chart_rows=[r for r in rows if r['id'] in chart_ids]
assert len(chart_rows)==8 and all(r['voltage_v']==12.4 and r.get('voltage_source') for r in chart_rows)
timed=[r for r in chart_rows if r['id']!='vortex-sheet-row-12']
assert len(timed)==7 and all(r.get('reported_startup_method')=='Impact detection to start of recording' and r['wake_seconds'] is None for r in timed)
buffered_chart={f'vortex-sheet-row-{n}': current for n,current in [(19,646),(5,560),(7,522),(16,439),(3,431),(14,394),(10,317)]}
for row in rows:
    if row['id'] in buffered_chart:
        assert row['voltage_v']==12.4 and row['current_ma']==buffered_chart[row['id']]
        assert row['category']=='buffered-event' and row['state']=='monitoring' and row.get('voltage_source')
a119m_ids={f'vortex-sheet-row-{n}' for n in (26,27,28)}
a119m_rows={r['id']:r for r in rows if r['id'] in a119m_ids}
assert len(a119m_rows)==3, 'Keep all three distinct A119M Pro measurements'
for number,category,state,current,watts in [(26,'buffered-event','monitoring',252,3.12),(27,'buffered-event','event-recording',252,3.12),(28,'low-bitrate','continuous',256,3.17)]:
    row=a119m_rows[f'vortex-sheet-row-{number}']
    assert (row['brand'],row['model'],row['installed_channels'],row['active_channels'])==('Viofo','A119M Pro',1,['front'])
    assert (row['category'],row['state'],row['current_ma'],row['power_w'])==(category,state,current,watts)
    assert row['firmware']=='1.2_20260817', 'Owner-confirmed firmware overrides low-bitrate sheet typo'
    assert row['voltage_v']==12.4 and row.get('voltage_source')
    assert row['power_path']=='Viofo HK6-F hardwire cable'
    assert row['tester']=='Vortex Radar' and row['source_is_private'] is True
    assert row['source_url']=='https://vortexopenclaw.github.io/dashcam-camera-profiles/parking-mode.html#vortex-radar-testing'
    assert row['date'] is None and row['power_is_derived'] is False
    assert all(row.get(field) is None for field in ['wake_seconds','reported_startup_seconds','prebuffer_s','prebuffer_motion_s','prebuffer_impact_s','connectivity'])
    assert row['test_status']=='unknown' and row['review_status']=='verified' and row['superseded'] is False
assert next(s for s in sources if s['id']=='vortex-sheet')['measurement_count']==sum(r['id'].startswith('vortex-sheet-row-') for r in rows)
e1s_ids={f'vortex-sheet-row-{n}' for n in (34,35,36,37,38,40,41)}
assert all(r['voltage_v']==12.6 and r['reported_parking_voltage_v']==12.6 and r.get('voltage_source') for r in rows if r['id'] in e1s_ids)
assert all(r['voltage_v'] is None for r in rows if r['tester']=='Vortex Radar' and r['id'] not in chart_ids | buffered_chart.keys() | a119m_ids | e1s_ids),'No blanket voltage assumption for other contributed rows'
for content in [public.read_text(),csv_path.read_text(),json.dumps(sources)]:
    assert 'docs.google.com/spreadsheets' not in content, 'Private spreadsheet link in public data'
bad=copy.deepcopy(rows);bad[0]['source_url']='https://docs.google.com/spreadsheets/d/private-test-fixture'
try:mod.validate(bad,sources)
except AssertionError:pass
else:raise AssertionError('Private spreadsheet negative control accepted')
assert len([s for s in sources if s['tester']=='rcg530'])==68,'All indexed sources need review entries'
assert not payload['coverage'].get('all_account_posts_exhaustive',True),'Exhaustive account claim unsupported'
assert all('hash=' not in (r.get('image_url') or '') for r in rows),'Prefer stable original attachment URLs'
for k,v in [('power_w',-1),('current_ma',float('nan')),('category','invented-mode'),('state','normal-driving')]:
    bad=copy.deepcopy(rows);bad[0][k]=v
    try:mod.validate(bad,sources)
    except AssertionError:pass
    else:raise AssertionError('Negative control accepted '+k)
bad=copy.deepcopy(rows);bad.append(copy.deepcopy(rows[0]))
try:mod.validate(bad,sources)
except AssertionError:pass
else:raise AssertionError('Duplicate ID negative control accepted')
assert mod.csv_cell('=1+1').startswith("'")
assert mod.csv_cell('  @cmd').startswith("'")
assert mod.csv_cell(None)==''
for value in ['\tformula','\rformula','\nformula','\x00=HYPERLINK(1)','  @cmd']:
    assert mod.csv_cell(value).startswith("'")
assert set().union(*(set(row) for row in rows)) <= set(exports[0]), 'CSV dropped canonical metadata'
by_id={row['id']:row for row in rows}
assert by_id['rcg530-650980-1']['prebuffer_s'] is None
assert by_id['rcg530-650980-1']['prebuffer_motion_s']==8
assert by_id['rcg530-650980-1']['prebuffer_impact_s']==10
assert by_id['rcg530-650980-7']['wake_camera'].startswith('front')
assert by_id['rcg530-640820-1']['wake_seconds_min']==2.75
assert by_id['vortex-sheet-row-17']['wake_seconds'] is None
assert by_id['vortex-sheet-row-17']['reported_startup_seconds']==.83
print(f"Parking verification passed: {len(rows)} rows; JSON/CSV parity, provenance, finite numeric values, coverage boundary, deterministic generation, and negative controls")
