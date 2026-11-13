#!/usr/bin/env python3
"""Explicit correction: exact source history, all unrelated bytes, current chart/UI."""
import argparse, csv, functools, http.server, io, json, os, subprocess, threading
from copy import deepcopy
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlencode
from z100_retest import SID, OLD, restore_loaded, restore_rows, restore_profile, FACT, SOURCE
R=Path(__file__).resolve().parents[1]
BASE='32137d9edc95902a63aac82b287f3793b0d6e486'
DOS='docs/data/ddpai-z100-master-4ch-retest-power-evidence.json'
ART=Path(os.environ.get('Z100_RETEST_ARTIFACTS','/Users/openclaw/.hermes/profiles/dashcam-data-logging/artifacts/z100-current-retest'))
def load(p):return json.loads((R/p).read_text())
def before(p):return subprocess.check_output(['git','show',f'{BASE}:{p}'],cwd=R)
def verify():
    rows=load('parking/measurements.json');src=load('parking/sources.json');e=load(DOS)
    assert len(rows)==622 and len(src)==75
    assert restore_rows(rows)==json.loads(before('parking/measurements.json'))
    assert restore_rows(src,True)==json.loads(before('parking/sources.json'))
    assert restore_profile(load('profiles/ddpai-z100-master.json'))==json.loads(before('profiles/ddpai-z100-master.json'))
    assert restore_loaded('docs/data/cameras.json',load('docs/data/cameras.json'))==json.loads(before('docs/data/cameras.json'))
    # All historical dossiers, video/index datasets and other profiles remain byte exact.
    for p in subprocess.check_output(['git','ls-tree','-r','--name-only',BASE,'profiles','docs/data','docs/z100-master-measurements.md','docs/z100-master-3ch-measurements.md'],cwd=R,text=True).splitlines():
        if p not in {'profiles/ddpai-z100-master.json','docs/data/cameras.json','docs/data/parking-measurements.json','docs/data/parking-measurements.csv'}:
            assert (R/p).read_bytes()==before(p),p
    assert e['source_id']==SID and e['installed_channels']==4 and e['active_channels'] is None
    assert e['display_observation']['confidence']=='owner-observed/tentative; pending clip verification'
    assert e['component_firmware']=={'front':None,'telephoto':None,'rear':None,'cabin':'9.0.1.10'}
    assert e['main_unit_firmware']=='8.0.0.23' and 'Fresh physical-card' in e['firmware_provenance']['main']
    for row,ma,watts,state in zip(e['measurements'],[1185,589],['14.931','7.4214'],['driving','time-lapse']):
        assert row['current_ma']==ma and Decimal(str(row['power_w']))==Decimal(watts)==Decimal('12.6')*ma/1000
        assert row['state']==state and row['installed_channels']==4 and row['active_channels'] is None
        assert row['connectivity'] is None and row['power_path']=='DC009 hardwire cable'
        assert all(row[k] is None for k in ['wake_seconds','reported_startup_seconds','recording_fps','recording_seconds_per_frame'])
    assert rows[-1]==e['measurements'][1] and not any(r['state']=='driving' for r in rows)
    assert any(r['current_ma']==282 and r.get('source_id')=='vortex-owner-z100-master-dc009-12v6' and r['state']=='time-lapse' for r in rows)
    assert src[-1]['id']==SID and src[-1]['measurement_count']==1 and 'corrected driving and timelapse retest' in src[-1]['title']
    historic=next(r for r in rows if r['id']==OLD)
    assert historic['superseded'] is True and historic['review_status']=='verified' and historic['current_ma']==632 and historic['power_w']==7.9632
    exported=load('docs/data/parking-measurements.json')
    assert restore_loaded('docs/data/parking-measurements.json',exported)==json.loads(before('docs/data/parking-measurements.json'))
    csvrows=list(csv.DictReader((R/'docs/data/parking-measurements.csv').open()))
    assert restore_rows(csvrows)==list(csv.DictReader(io.StringIO(before('docs/data/parking-measurements.csv').decode())))
    assert next(r for r in csvrows if r['id']==SID+'-timelapse')['power_w']=='7.4214'
    # Exact allowlist rejects unauthorized older numeric/provenance changes.
    for key,value in [('current_ma',633),('firmware','invented'),('notes','invented')]:
        bad=deepcopy(rows);next(r for r in bad if r['id']==OLD)[key]=value
        try:assert restore_rows(bad)==json.loads(before('parking/measurements.json'))
        except AssertionError:pass
        else:raise AssertionError('negative control accepted '+key)
    print('Retest exact source/math, 621 retained rows, only historical supersession metadata, all unrelated sources/profiles/video bytes and JSON/CSV parity passed')
    return e

def browser(base):
    from playwright.sync_api import sync_playwright
    ART.mkdir(parents=True,exist_ok=True)
    results=[]
    with sync_playwright() as pw:
        b=pw.chromium.launch(channel='chrome',headless=True);p=b.new_page();errors=[]
        p.on('pageerror',lambda e:errors.append(str(e)))
        for width in [1440,375,320]:
            p.set_viewport_size({'width':width,'height':1000});p.goto(base+'#camera=ddpai-z100-master');p.wait_for_selector('.parking-power-summary')
            s=p.locator('.parking-power-summary');text=s.inner_text()
            for value in ['1.185 A','14.931 W','589 mA','7.4214 W','44 mA','935 mA','Timelapse — 4 cameras installed; front/rear indicated']:assert value in text,value
            for value in ['964 mA','632 mA','7.9632 W']:assert value not in text
            assert s.locator('tbody tr').count()==4
            assert not p.locator('details.technical-details').evaluate('e=>e.open')
            if width<600:
                for i,label in enumerate(['Current','Derived power']):assert s.locator('tbody tr').first.locator('td').nth(i).evaluate("e=>getComputedStyle(e,'::before').content")==json.dumps(label)
            assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
            s.screenshot(path=str(ART/f'current-power-{width}.png'))
            p.locator('details.technical-details > summary').click();details=p.locator('details.technical-details').text_content()
            for value in ['589 mA','632 mA','Historical','tentatively','LEDs being on does not prove saved footage']:assert value.casefold() in details.casefold(),value
            for metric,value in [('watts','7.4214'),('current','589')]:
                query=urlencode({'selection':'1','group':'time-lapse','family':'time-lapse','condition':'','metric':metric,'id':SID+'-timelapse'})
                p.goto(base+'parking-charts.html?'+query);p.wait_for_function("()=>document.querySelector('#chart-canvas')?.getAttribute('aria-busy')==='false'")
                bar=p.locator('[data-measurement="'+SID+'-timelapse"]');assert bar.count()==1 and Decimal(bar.get_attribute('data-max'))==Decimal(value)
                assert p.locator('[data-measurement="'+OLD+'"]').count()==0
                for missing in ['delay','wake']:
                    p.locator('#chart-metric').select_option(missing);assert p.locator('[data-measurement="'+SID+'-timelapse"]').count()==0
            p.goto(base+'parking-charts.html?group=time-lapse&family=time-lapse&condition=&metric=watts');p.wait_for_function("()=>document.querySelector('#chart-canvas')?.getAttribute('aria-busy')==='false'")
            p.locator('#chart-apply-group').click()
            assert p.locator('[data-measurement="'+OLD+'"]').count()==0
            # Production seed picks current corrected installed-4-camera result, not historical range.
            assert p.locator('[data-measurement="'+SID+'-timelapse"]').count()==1
            results.append({'width':width,'current_table':True,'selected_watts_current':True,'default_not_632':True,'null_wake':True})
        old2='vortex-owner-z100-master-dc009-12v6-timelapse'
        query=urlencode([('selection','1'),('group','time-lapse'),('family','time-lapse'),('condition',''),('metric','current'),('id',SID+'-timelapse'),('id',old2)])
        p.goto(base+'parking-charts.html?'+query);p.wait_for_function("()=>document.querySelector('#chart-canvas')?.getAttribute('aria-busy')==='false'")
        for id,ma in [(SID+'-timelapse',589),(old2,282)]:assert Decimal(p.locator('[data-measurement="'+id+'"]').get_attribute('data-max'))==ma
        p.goto(base+'parking-mode.html?q=Z100+Master&state=all');p.wait_for_selector('.parking-model-entry')
        assert p.locator('[data-id="'+OLD+'"]').count()==0
        assert p.locator('[data-id="'+SID+'-timelapse"]').count()==1
        response=p.request.get(base+DOS[5:]);assert response.ok and json.loads(response.body())==load(DOS)
        response=p.request.get(base+'data/parking-measurements.json');assert response.ok and json.loads(response.body())==load('docs/data/parking-measurements.json')
        response=p.request.get(base+'data/parking-measurements.csv');assert response.ok and response.body()==(R/'docs/data/parking-measurements.csv').read_bytes()
        response=p.request.get(base+'data/cameras.json');assert response.ok and json.loads(response.body())==load('docs/data/cameras.json')
        response=p.request.get(base+'assets/app.js');assert response.ok and response.body()==(R/'docs/assets/app.js').read_bytes()
        assert not errors,errors
        b.close()
    result={'base':base,'browser':'Chrome','checks':results,'exact_live_json_csv_dossier_index_assets':True}
    (ART/('live-acceptance.json' if base.startswith('https') else 'local-acceptance.json')).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--browser',action='store_true');a.add_argument('--url');args=a.parse_args();verify()
    if args.browser or args.url:
        server=None
        if args.url:base=args.url.rstrip('/')+'/'
        else:
            class Handler(http.server.SimpleHTTPRequestHandler):
                def log_message(self,*args):pass
            server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(R/'docs')));threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}/'
        browser(base)
        if server:server.shutdown()
