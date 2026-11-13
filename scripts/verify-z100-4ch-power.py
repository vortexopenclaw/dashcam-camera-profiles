#!/usr/bin/env python3
"""Verify the separate owner 4CH power cohort without changing prior evidence."""
import argparse
import csv
from decimal import Decimal
import functools
import http.server
import json
from pathlib import Path
import subprocess
import threading
from urllib.parse import urlencode

R = Path(__file__).resolve().parents[1]
BASELINE = 'd670c96'
SID = 'vortex-owner-z100-master-4ch-dc009-12v6'
PATH = 'docs/data/ddpai-z100-master-4ch-power-evidence.json'
QUOTE = "testing next with a 4CH setup, adding the 4K rear cam and 3K cabin cam. i'll send card scans in a bit. here's some power draw figures. same hardwire cable, cloud off, 12.6v. rear cam firmware: 9.0.0.17 driving recording: 964 mA timelapse parking mode: 632 mA collision detection parking mode (idle): not yet recorded collision detection parking mode (recording): not yet recorded"
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--browser', action='store_true')
parser.add_argument('--url')
a = parser.parse_args()
def load(path): return json.loads((R/path).read_text())
def old(path): return json.loads(subprocess.check_output(['git','show',f'{BASELINE}:{path}'],cwd=R))
e = load(PATH)
assert e['source_id'] == SID and e['provenance']['source_quote'] == QUOTE
assert e['component_firmware'] == {'front':None,'telephoto':None,'rear':'9.0.0.17','cabin':None}
assert e['main_unit_firmware'] is None
assert e['owner_declared_resolution'] == {'rear':'4K','cabin':'3K'}
assert e['video_scan_status'] == 'promised, not yet received'
assert len(e['measurements']) == 2 and len(e['pending_measurements']) == 2
for pending,state in zip(e['pending_measurements'],['idle','recording']):
    assert pending == {'mode_name':f'Collision detection parking mode ({state})','status':'not yet recorded','current_ma':None,'power_w':None}
expected = [('driving-4ch-front-telephoto-rear-cabin',964,'12.1464',None,'driving'),('timelapse',632,'7.9632','time-lapse','time-lapse')]
nulls = ['firmware','power_w_min','power_w_max','current_ma_min','current_ma_max','recording_fps','recording_seconds_per_frame','wake_seconds','wake_seconds_min','wake_seconds_max','reported_startup_seconds','reported_startup_seconds_min','reported_startup_seconds_max','prebuffer_s','hdr','quality','lighting','meter_hardware']
for row,(suffix,ma,watts,category,state) in zip(e['measurements'],expected):
    assert row['id'] == SID+'-'+suffix and row['source_id'] == SID
    assert row['current_ma'] == ma and Decimal(str(row['power_w'])) == Decimal(watts)
    assert Decimal(str(row['voltage_v']))*Decimal(ma)/Decimal(1000) == Decimal(watts)
    assert row['power_is_derived'] is True and row['installed_channels'] == 4
    assert row['power_path'] == 'DC009 hardwire cable' and row['connectivity'] == 'no cloud'
    assert (row['category'],row['state']) == (category,state)
    assert row['active_channels'] == (['front','telephoto','rear','cabin'] if state == 'driving' else None)
    assert row['source_url'] == e['evidence_url'] and row['source_url'].endswith('/data/ddpai-z100-master-4ch-power-evidence.json')
    assert all(row.get(k) is None for k in nulls)
from z100_post_update import prior_power_profile, without_post_update
rows = without_post_update(load('parking/measurements.json'))
sources = without_post_update(load('parking/sources.json'), source_index=True)
assert len(rows) == 619 and len(old('parking/measurements.json')) == 618
assert rows[:-1] == old('parking/measurements.json')
assert rows[-1] == e['measurements'][1]
assert sources[:-1] == old('parking/sources.json')
assert sources[-1]['id'] == SID and sources[-1]['measurement_count'] == 1
# Keep power bytes exact; only the explicit later video-attribution amendment
# is normalized, never measurements, configuration, firmware or occurrence IDs.
from z100_attribution import prior_video_provenance
path = 'docs/data/ddpai-z100-master-power-evidence.json'
assert (R/path).read_bytes() == subprocess.check_output(['git','show',f'{BASELINE}:{path}'],cwd=R),path
path = 'docs/data/ddpai-z100-master-evidence.json'
assert prior_video_provenance(load(path)) == old(path), path
p = prior_power_profile(load('profiles/ddpai-z100-master.json'))
# Later 3CH video additions have their own exact-prefix and source-parity validator.
current_profile = p
pre_3ch = json.loads(subprocess.check_output(['git','show','b9f1536:profiles/ddpai-z100-master.json'],cwd=R))
# Power facts remain exact; only the unrelated official capability note changed.
assert [f for f in p['technical_facts'] if 'power' in f['label'].lower() or 'idle' in f['label'].lower()] == [f for f in pre_3ch['technical_facts'] if 'power' in f['label'].lower() or 'idle' in f['label'].lower()]
p = pre_3ch
prior = old('profiles/ddpai-z100-master.json')
assert {k:v for k,v in p.items() if k not in ['technical_facts','sources']} == {k:v for k,v in prior.items() if k not in ['technical_facts','sources']}
assert p['technical_facts'][:-1] == prior['technical_facts']
assert p['sources'][:-1] == prior['sources']
p = current_profile
index = load('docs/data/cameras.json')
assert next(c for c in index['cameras'] if c['id']==p['id']) == load('profiles/ddpai-z100-master.json')
assert [c for c in index['cameras'] if c['id']!=p['id']] == [c for c in old('docs/data/cameras.json')['cameras'] if c['id']!=p['id']]
export = load('docs/data/parking-measurements.json')
export['measurements'] = without_post_update(export['measurements'])
assert {r['id']:r for r in export['measurements']} == {r['id']:r for r in rows}
csv_rows = without_post_update(list(csv.DictReader((R/'docs/data/parking-measurements.csv').open())))
old_csv = list(csv.DictReader(subprocess.check_output(['git','show',f'{BASELINE}:docs/data/parking-measurements.csv'],cwd=R,text=True).splitlines()))
assert [r for r in csv_rows if r['source_id']!=SID] == old_csv
new_csv = [r for r in csv_rows if r['source_id']==SID]
assert len(new_csv)==1 and new_csv[0]['current_ma']=='632' and new_csv[0]['power_w']=='7.9632'
assert all(new_csv[0][k]=='' for k in nulls)
node = """const assert=require('assert');const C=require('./docs/assets/parking-charts.js');const rows=require('./docs/data/parking-measurements.json').measurements;const id=process.argv[1];for(const metric of ['watts','current']){const found=C.eligibleRows(rows,{metric,group:'time-lapse',family:'time-lapse',condition:''}).filter(r=>r.source_id===id);assert.deepEqual(found.map(r=>r.id),[id+'-timelapse']);}for(const metric of ['watts','current','delay','wake']){const found=C.eligibleRows(rows,{metric,group:'low-power',family:'low-power',condition:''}).filter(r=>r.source_id===id);assert.equal(found.length,0);}for(const metric of ['delay','wake'])assert.equal(C.eligibleRows(rows,{metric,group:'time-lapse',family:'time-lapse',condition:''}).filter(r=>r.source_id===id).length,0);console.log('Production 4CH timelapse eligibility and missing collision/timing exclusion passed');"""
subprocess.run(['node','-e',node,SID],cwd=R,check=True)
print('4CH exact source/math/components/pending states/exports verified; all 618 prior parking rows, sources, 2CH dossier, complete video evidence and other cameras unchanged')
if a.browser or a.url:
    from playwright.sync_api import sync_playwright
    server = None
    if a.url:
        base = a.url.rstrip('/')+'/'
    else:
        class Handler(http.server.SimpleHTTPRequestHandler):
            def log_message(self,*args): pass
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(R/'docs')))
        threading.Thread(target=server.serve_forever,daemon=True).start()
        base=f'http://127.0.0.1:{server.server_port}/'
    query=urlencode(dict(selection='1',id=SID+'-timelapse',group='time-lapse',family='time-lapse',condition='time-lapse',metric='watts',highlight='DDPAI Z100 Master'))
    with sync_playwright() as pw:
        browser=pw.chromium.launch(channel='chrome',headless=True)
        page=browser.new_page()
        errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(base+'#camera=ddpai-z100-master')
        page.wait_for_selector('.detail-title')
        assert page.locator('.detail-title').inner_text()=='Z100 Master'
        page.locator('details.technical-details > summary').click()
        text=page.locator('body').inner_text()
        for fragment in ['964 mA','12.1464 W derived','632 mA','7.9632 W derived','Rear firmware only: 9.0.0.17','main unit, front, cabin and telephoto firmware unknown','were pending in that earlier test','front/telephoto/rear/cabin']:
            assert fragment.casefold() in text.casefold(), fragment
        page.goto(base+'parking-charts.html?'+query)
        page.wait_for_function("()=>document.querySelector('#chart-canvas').getAttribute('aria-busy')==='false'")
        for metric,value in [('watts','7.9632'),('current','632')]:
            page.locator('#chart-metric').select_option(metric)
            bar=page.locator(f'#chart-canvas [data-measurement="{SID}-timelapse"]')
            assert bar.count()==1 and bar.get_attribute('data-highlight')=='true'
            assert Decimal(bar.get_attribute('data-max'))==Decimal(value)
            assert page.locator(f'#chart-canvas [data-measurement^="{SID}"]').count()==1
        page.locator('#chart-metric').select_option('delay')
        assert page.locator(f'#chart-canvas [data-measurement^="{SID}"]').count()==0
        page.goto(base+'data/ddpai-z100-master-4ch-power-evidence.json')
        assert json.loads(page.locator('body').inner_text())==e
        assert not errors,errors
        browser.close()
    if server: server.shutdown()
    print('Browser verified 4CH model/component/pending display, dossier, watts/current chart and absent timing: '+base+'parking-charts.html?'+query)
