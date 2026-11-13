#!/usr/bin/env python3
"""Source-exact Z100 current import, preservation, exports and optional real browser acceptance."""
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
SID = 'vortex-owner-z100-master-dc009-12v6'
BASELINE = '13bb139'
SOURCE_QUOTE = 'DDPAI Z100 Master power draw figures at 12.6v, no cloud. all testing done with the DC009 hardwire cable: Driving mode, 2CH front/telephoto: 435 mA; timelapse parking mode: 282 mA; collision detection parking mode (idle): 52 mA; collision detection parking mode (recording): 424 mA'
EXPECTED = [('driving-2ch-front-telephoto',435,'5.481',None,'driving'), ('timelapse',282,'3.5532','time-lapse','time-lapse'), ('collision-idle',52,'0.6552','impact-sleep','monitoring'), ('collision-recording',424,'5.3424','impact-sleep','event-recording')]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--browser', action='store_true')
parser.add_argument('--url', help='Optional public website base URL for browser acceptance')
a = parser.parse_args()
def load(path): return json.loads((R/path).read_text())
def old(path): return json.loads(subprocess.check_output(['git','show',f'{BASELINE}:{path}'],cwd=R))
e = load('docs/data/ddpai-z100-master-power-evidence.json')
p = load('profiles/ddpai-z100-master.json')
rows = load('parking/measurements.json')
sources = load('parking/sources.json')
# The separate later 4CH cohort has its own full-baseline preservation regression.
rows = [r for r in rows if r.get('source_id') != 'vortex-owner-z100-master-4ch-dc009-12v6']
sources = [s for s in sources if s['id'] != 'vortex-owner-z100-master-4ch-dc009-12v6']
assert e['source_id'] == SID and e['provenance']['source_quote'] == SOURCE_QUOTE
assert e['provenance']['original_public_url'] is None
assert len(e['measurements']) == 4
nulls = ['firmware','hdr','quality','lighting','meter_hardware','recording_fps','recording_seconds_per_frame','wake_seconds','wake_seconds_min','wake_seconds_max','reported_startup_seconds','reported_startup_seconds_min','reported_startup_seconds_max','prebuffer_s','prebuffer_motion_s','prebuffer_impact_s','date','image_url','power_w_min','power_w_max','current_ma_min','current_ma_max']
for row, (suffix,ma,watts,category,state) in zip(e['measurements'],EXPECTED):
    assert row['id'] == SID+'-'+suffix and row['source_id'] == SID
    assert row['current_ma'] == ma and Decimal(str(row['power_w'])) == Decimal(watts)
    assert Decimal(str(row['voltage_v'])) * Decimal(ma) / Decimal(1000) == Decimal(watts)
    assert row['power_is_derived'] is True
    assert (row['category'],row['state']) == (category,state)
    assert row['power_path'] == 'DC009 hardwire cable' and row['connectivity'] == 'no cloud'
    assert row['installed_channels'] == 2 and row['source_is_private'] is True
    assert row['source_url'] == e['evidence_url'] and row['source_url'].endswith('/data/ddpai-z100-master-power-evidence.json')
    assert all(row.get(k) is None for k in nulls)
    assert row['active_channels'] == (['front','telephoto'] if state=='driving' else None)
    assert any(str(ma)+' mA' in f['value'] and watts+' W derived' in f['value'] for f in p['technical_facts'])
imported = [row for row in rows if row.get('source_id') == SID]
assert imported == e['measurements'][1:]
assert len(rows) == 618 and len(old('parking/measurements.json')) == 615
assert [row for row in rows if row.get('source_id') != SID] == old('parking/measurements.json')
assert sources[:-1] == old('parking/sources.json')
assert sources[-1]['id'] == SID and sources[-1]['measurement_count'] == 3
video = load('docs/data/ddpai-z100-master-evidence.json')
assert {k: v for k, v in video.items() if k != 'collision_test_scan'} == old('docs/data/ddpai-z100-master-evidence.json')
# Later 3CH video additions have their own exact-prefix and source-parity validator.
current_profile = p
pre_3ch = json.loads(subprocess.check_output(['git','show','b9f1536:profiles/ddpai-z100-master.json'],cwd=R))
# Power facts remain exact; only the unrelated official capability note changed.
assert [f for f in p['technical_facts'] if 'power' in f['label'].lower() or 'idle' in f['label'].lower()] == [f for f in pre_3ch['technical_facts'] if 'power' in f['label'].lower() or 'idle' in f['label'].lower()]
p = pre_3ch
prior = old('profiles/ddpai-z100-master.json')
for key in set(prior)-{'notes','technical_facts','sources','evidence','recording','video_samples'}:
    assert p[key] == prior[key], key
assert p['video_samples'][:len(prior['video_samples'])] == prior['video_samples']
assert {k: v for k, v in p['recording'].items() if k != 'parking_modes'} == {k: v for k, v in prior['recording'].items() if k != 'parking_modes'}
assert p['recording']['parking_modes'][:-1] == prior['recording']['parking_modes']
# The dedicated video validator checks every new cohort and its summary rows.
import runpy
runpy.run_path(str(R/'scripts/verify-z100-collision.py'))['verify'](video['collision_test_scan'], p)
p = current_profile
index = load('docs/data/cameras.json')
assert next(c for c in index['cameras'] if c['id']==p['id']) == p
assert [c for c in index['cameras'] if c['id']!=p['id']] == [c for c in old('docs/data/cameras.json')['cameras'] if c['id']!=p['id']]
export = load('docs/data/parking-measurements.json')
assert {r['id']:r for r in export['measurements'] if r.get('source_id') != 'vortex-owner-z100-master-4ch-dc009-12v6'} == {r['id']:r for r in rows}
csv_rows = {r['id']:r for r in csv.DictReader((R/'docs/data/parking-measurements.csv').open())}
for row in imported:
    c = csv_rows[row['id']]
    assert c['current_ma']==str(row['current_ma']) and Decimal(c['power_w'])==Decimal(str(row['power_w']))
    assert c['power_is_derived']=='True' and c['source_id']==SID
    assert all(c[k]=='' for k in nulls)
assert not any(r['power_w']==0.135 for r in imported)
# Production eligibility, not a duplicate implementation of chart criteria.
node = """const assert=require('assert');const C=require('./docs/assets/parking-charts.js');const rows=require('./docs/data/parking-measurements.json').measurements;const id=process.argv[1];for(const metric of ['watts','current']){let found=C.eligibleRows(rows,{metric,group:'low-power',family:'low-power',condition:'monitoring'}).filter(r=>r.source_id===id);assert.equal(found.length,1);assert.equal(found[0].id,id+'-collision-idle');}for(const metric of ['delay','wake'])assert.equal(C.eligibleRows(rows,{metric,group:'low-power',family:'low-power',condition:'monitoring'}).filter(r=>r.source_id===id).length,0);console.log('Production watts/current eligibility and unknown timing exclusion passed');"""
subprocess.run(['node','-e',node,SID],cwd=R,check=True)
# Historical manual claim parser and implementation remain exactly unchanged.
for path in ['docs/assets/parking-charts.js','docs/assets/parking.js']:
    assert (R/path).read_bytes() == subprocess.check_output(['git','show',f'{BASELINE}:{path}'],cwd=R)
print('Z100 power verified: 4 exact currents and derived watts; 3 parking rows; all 615 prior rows, other cameras and video evidence unchanged')
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
    query=urlencode(dict(selection='1',id=SID+'-collision-idle',group='low-power',family='low-power',condition='monitoring',metric='watts',highlight='DDPAI Z100 Master'))
    with sync_playwright() as pw:
        browser=pw.chromium.launch(channel='chrome',headless=True)
        page=browser.new_page()
        errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(base+'#camera=ddpai-z100-master')
        page.wait_for_selector('.detail-title')
        # Model selection is represented by the existing camera URL fragment.
        assert page.locator('.detail-title').inner_text()=='Z100 Master'
        text=page.locator('body').inner_text()
        for _, ma, watts, _, _ in EXPECTED:
            assert (str(ma)+' mA').casefold() in text.casefold() and (watts+' W derived').casefold() in text.casefold()
        page.goto(base+'parking-charts.html?'+query)
        page.wait_for_function("()=>document.querySelector('#chart-canvas').getAttribute('aria-busy')==='false'")
        for metric, value in [('watts','0.6552'),('current','52')]:
            page.locator('#chart-metric').select_option(metric)
            bar=page.locator(f'#chart-canvas [data-measurement="{SID}-collision-idle"]')
            assert bar.count()==1 and bar.get_attribute('data-highlight')=='true'
            assert Decimal(bar.get_attribute('data-max'))==Decimal(value)
            assert 'collision-recording' not in page.locator('#chart-canvas').inner_text()
        page.locator('#chart-metric').select_option('delay')
        assert page.locator(f'#chart-canvas [data-measurement="{SID}-collision-idle"]').count()==0
        page.goto(base+'data/ddpai-z100-master-power-evidence.json')
        assert json.loads(page.locator('body').inner_text())==e
        assert not errors, errors
        browser.close()
    if server: server.shutdown()
    print('Browser verified model all-four display, source readback, exact highlighted watts/current, monitoring-only and no invented delay: '+base+'parking-charts.html?'+query)
