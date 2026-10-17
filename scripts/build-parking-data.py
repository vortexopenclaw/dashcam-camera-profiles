#!/usr/bin/env python3
"""Validate canonical parking data and build static JSON/CSV downloads."""
import csv
import io
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATEGORIES = {'impact-sleep', 'buffered-event', 'unbuffered-event', 'time-lapse', 'low-bitrate', 'radar', 'hybrid', 'unknown'}
STATES = {'monitoring', 'event-recording', 'time-lapse', 'continuous'}
FIELDS = ['id','brand','model','installed_channels','active_channels','firmware','mode_name','category','state','measurement_statistic','power_w','power_w_min','power_w_max','current_ma','current_ma_min','current_ma_max','voltage_v','reported_parking_voltage_v','wake_seconds','reported_startup_seconds','prebuffer_s','tester','source_url','image_url','date','notes','test_status','ir','power_path','superseded','review_status']


def validate(rows, sources):
    ids = set()
    for r in rows:
        assert r['id'] not in ids, f"Duplicate id: {r['id']}"
        ids.add(r['id'])
        assert r['category'] in CATEGORIES, r
        assert r['state'] in STATES, r
        assert r['review_status'] in {'verified','needs-review'}, r
        assert r['superseded'] in (True, False), r
        for k in ['brand','model','mode_name','tester','source_url']:
            assert isinstance(r[k], str) and r[k].strip(), (r['id'],k)
        assert r['source_url'].startswith('https://'), r['id']
        assert 'docs.google.com/spreadsheets' not in r['source_url'], 'Private sheet links must not be published'
        assert 'sheets.google.com' not in r['source_url'], 'Private sheet links must not be published'
        assert r.get('image_url') is None or r['image_url'].startswith('https://'), r['id']
        assert r['installed_channels'] is None or (isinstance(r['installed_channels'],int) and 1 <= r['installed_channels'] <= 6), r['id']
        assert r.get('active_channels') is None or isinstance(r['active_channels'],list), r['id']
        for k in ['power_w','current_ma','voltage_v','wake_seconds','prebuffer_s','power_w_min','power_w_max','current_ma_min','current_ma_max','wake_seconds_min','wake_seconds_max','prebuffer_impact_s','prebuffer_motion_s','reported_startup_seconds','reported_startup_seconds_min','reported_startup_seconds_max','reported_parking_voltage_v']:
            v = r.get(k)
            assert v is None or (isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) and v >= 0), (r['id'],k,v)
        assert any(r.get(k) is not None for k in ['power_w','current_ma','current_ma_min','power_w_min']), f"No measurement: {r['id']}"
        for prefix in ['power_w','current_ma','reported_startup_seconds']:
            low,high=r.get(prefix+'_min'),r.get(prefix+'_max')
            assert (low is None and high is None) or (low is not None and high is not None and low <= high), r['id']
        for k in FIELDS:
            assert k in r, (r['id'],'missing '+k)
    source_ids = [s['id'] for s in sources]
    for source in sources:
        assert 'docs.google.com/spreadsheets' not in (source.get('url') or ''), 'Private sheet source links must not be published'
    assert len(source_ids) == len(set(source_ids)), 'Duplicate source id'


def csv_cell(v):
    if v is None:
        return ''
    if isinstance(v,list):
        v = ' + '.join(map(str,v))
    text = str(v)
    return "'"+text if text.lstrip(''.join(chr(i) for i in range(33))).startswith(('=','+','-','@')) or text.startswith(('\t','\r','\n')) else text


def build():
    rows = json.loads((ROOT/'parking/measurements.json').read_text())
    sources = json.loads((ROOT/'parking/sources.json').read_text())
    metadata = json.loads((ROOT/'parking/metadata.json').read_text())
    validate(rows,sources)
    rows.sort(key=lambda r:(r['brand'].casefold(),r['model'].casefold(),r['id']))
    coverage = dict(metadata['coverage'])
    coverage.update(measurements=len(rows), models=len({(r['brand'],r['model']) for r in rows}), sources=len(sources), source_reviews_completed=sum(s.get('status') != 'needs-review' for s in sources), provisional_measurements=sum(r['review_status']=='needs-review' for r in rows), superseded_measurements=sum(r['superseded'] for r in rows))
    payload = dict(version=1,updated=metadata['updated'],measurements=rows,sources=sources,coverage=coverage)
    target=ROOT/'docs/data';target.mkdir(exist_ok=True)
    (target/'parking-measurements.json').write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n')
    output=io.StringIO(newline='');writer=csv.writer(output,lineterminator='\n')
    fields=FIELDS+sorted({key for row in rows for key in row}-set(FIELDS))
    writer.writerow(fields)
    writer.writerows([[csv_cell(r.get(k)) for k in fields] for r in rows])
    (target/'parking-measurements.csv').write_text(output.getvalue())
    print(f"Validated {len(rows)} parking measurements, {coverage['models']} models, {len(sources)} source entries")
    return payload

if __name__ == '__main__':
    build()
