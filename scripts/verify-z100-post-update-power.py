#!/usr/bin/env python3
"""Verify exact owner post-update 4CH readings, immutable prior evidence and live UI."""
import argparse
from copy import deepcopy
import csv
from decimal import Decimal
import functools
import http.server
import io
import json
import os
from pathlib import Path
import subprocess
import threading
from urllib.parse import urlencode
from z100_post_update import BASELINE, SID, DOSSIER, URL, QUOTE, FACT, SOURCE, prior_power_profile, without_post_update

R = Path(__file__).resolve().parents[1]
from z100_retest import restore_loaded, restore_rows
def load(path): return restore_loaded(path, json.loads((R/path).read_text()))
def old_bytes(path): return subprocess.check_output(['git','show',f'{BASELINE}:{path}'],cwd=R)
def old(path): return json.loads(old_bytes(path))
EXPECTED = [('collision-idle',44,'0.5544','monitoring'),('collision-recording',935,'11.781','event-recording')]
NULLS = ['active_channels','connectivity','wake_seconds','wake_seconds_min','wake_seconds_max','reported_startup_seconds','reported_startup_seconds_min','reported_startup_seconds_max','prebuffer_s','prebuffer_impact_s','prebuffer_motion_s','recording_fps','recording_seconds_per_frame','hdr','quality','lighting','meter_hardware','date','image_url','power_w_min','power_w_max','current_ma_min','current_ma_max']

def verify():
    e = load(DOSSIER)
    assert e['source_id'] == SID and e['evidence_url'] == URL
    assert e['provenance']['source_quote'] == QUOTE
    assert e['provenance']['attribution'] == 'Vortex Radar' and e['provenance']['unit'] == 'Vortex Radar’s test unit'
    assert e['main_unit_firmware'] == '8.0.0.23' and e['component_firmware'] == dict.fromkeys(['front','telephoto','rear','cabin'])
    assert e['firmware_provenance'] == {'main_model': 'DDPAI DZ2602_GLOBAL_Z100 Master', 'main_soft_version': '8.0.0.23', 'source': 'owner UI-log observation; not intrinsic per-clip metadata', 'observation_evidence_url': 'https://vortexopenclaw.github.io/dashcam-camera-profiles/data/ddpai-z100-master-3ch-evidence.json', 'unit_link': 'same owner-confirmed test unit', 'continuity_source': 'explicit owner confirmation; no intervening firmware updates', 'owner_continuity_quote': 'you should know the exact firmware version. its the one we updated to yesterday. i dont remember it, but you should have it logged. there hasnt been a new firmware update since.', 'scope': 'Only latest post-update 44 mA / 935 mA power cohort; not earlier 964 mA driving or 632 mA timelapse, component firmware, or MINI3X.', 'qualification': 'Observed unit UI-log version plus owner-confirmed continuity, not intrinsic per-clip metadata or a version read from the power receipt; no installation-action receipt claimed.'}
    observed = load('docs/data/ddpai-z100-master-3ch-evidence.json')['firmware_provenance']
    for key in ['main_model','main_soft_version','source']: assert e['firmware_provenance'][key] == observed[key]
    assert 'no installation-action receipt is claimed' in e['firmware_qualifier']
    assert e['installed_configuration'] == {'channels':4,'roles':['front','telephoto','rear','cabin'],'owner_declared_resolution':{'rear':'4K','cabin':'3K'},'cabin_accessory':'MINI3X','power_path':'DC009 hardwire cable','active_parking_views':None}
    assert e['prior_setup_context'] == {'source_id':'vortex-owner-z100-master-4ch-dc009-12v6','cloud':'off in prior test; current state not restated or independently verified after update','rear_firmware':'9.0.0.17 in prior test only; current rear firmware unknown'}
    assert len(e['measurements']) == 2
    for row,(suffix,ma,watts,state) in zip(e['measurements'],EXPECTED):
        assert row['id'] == SID+'-'+suffix and row['source_id'] == SID and row['source_url'] == URL
        assert row['firmware'] == '8.0.0.23'
        assert row['current_ma'] == ma and Decimal(str(row['power_w'])) == Decimal(watts)
        assert Decimal(str(row['voltage_v']))*Decimal(ma)/Decimal(1000) == Decimal(watts)
        assert row['power_is_derived'] is True and row['measurement_statistic'] == 'reported'
        assert row['category'] == 'impact-sleep' and row['state'] == state
        assert row['installed_channels'] == 4 and row['power_path'] == 'DC009 hardwire cable'
        assert row['tester'] == 'Vortex Radar' and row['source_is_private'] is True
        assert all(row.get(k) is None for k in NULLS)
        assert 'post-update' in row['mode_name'] and 'MINI3X' in row['source_configuration']
        assert 'Cloud off belongs to the prior setup context' in row['notes']
    rows = load('parking/measurements.json')
    assert rows == old('parking/measurements.json') + e['measurements'], 'All 619 prior rows exact; append only'
    sources = load('parking/sources.json')
    assert sources[:-1] == old('parking/sources.json')
    assert sources[-1]['id'] == SID and sources[-1]['measurement_count'] == 2 and sources[-1]['url'] == URL
    published = '509afe5765766c8e0ca351e4af508294bb88fa34'
    def published_json(path):
        return json.loads(subprocess.check_output(['git','show',f'{published}:{path}'],cwd=R))
    prior_rows = published_json('parking/measurements.json')
    for current, previous in zip(rows, prior_rows):
        expected = deepcopy(previous)
        if current.get('source_id') == SID:
            expected['firmware'] = '8.0.0.23'
            expected['notes'] = e['scope']
            assert 'UI-log observation' in current['notes'] and 'no intervening updates' in current['notes']
        assert current == expected, 'Exact published rows with only authorized latest firmware/provenance amendments'
    expected_sources = published_json('parking/sources.json')
    expected_sources[-1]['notes'] = 'Two owner-chat currents retained verbatim in separate post-update dossier: idle monitoring and event recording. Main firmware 8.0.0.23 from same-unit owner UI-log observation plus owner-confirmed continuity (no intervening updates), not these clips or the power receipt; no installation-action receipt claimed. No component firmware, settings or timings backfilled. Prior setup cloud off is context, not verified current state. Watts derived with Decimal; no comparison establishes a firmware power reduction.'
    assert sources == expected_sources
    profile = json.loads((R/'profiles/ddpai-z100-master.json').read_text())
    assert prior_power_profile(profile) == old('profiles/ddpai-z100-master.json'), 'Only explicit fact/source/pending-note allowlist'
    assert profile['video_samples'] == old('profiles/ddpai-z100-master.json')['video_samples']
    index = json.loads((R/'docs/data/cameras.json').read_text())
    assert next(c for c in index['cameras'] if c['id']==profile['id']) == profile
    restored = deepcopy(index)
    restored['cameras'] = [prior_power_profile(c) if c['id']==profile['id'] else c for c in restored['cameras']]
    # Independently source-pinned in verify-mini3x.py; exclude only the new model.
    added = [c for c in restored['cameras'] if c['id'] == 'ddpai-mini3x']
    if added:
        assert len(added) == 1 and added[0] == load('profiles/ddpai-mini3x.json')
        restored['cameras'] = [c for c in restored['cameras'] if c['id'] != 'ddpai-mini3x']
        restored['camera_count'] -= 1
        restored['profile_count'] -= 1
    assert restored == old('docs/data/cameras.json'), 'Other models and index metadata exact'
    for path in ['docs/data/ddpai-z100-master-power-evidence.json','docs/data/ddpai-z100-master-4ch-power-evidence.json','docs/data/ddpai-z100-master-evidence.json','docs/data/ddpai-z100-master-3ch-evidence.json','docs/z100-master-measurements.md','docs/z100-master-3ch-measurements.md','docs/assets/parking-charts.js','docs/assets/parking.js']:
        assert (R/path).read_bytes() == old_bytes(path), path
    exported = load('docs/data/parking-measurements.json')
    assert {r['id']:r for r in exported['measurements']} == {r['id']:r for r in rows}
    prior_export = old('docs/data/parking-measurements.json')
    assert [r for r in exported['measurements'] if r.get('source_id') != SID] == prior_export['measurements']
    assert exported['sources'] == sources
    expected_export = deepcopy(prior_export)
    expected_export['updated'] = '2026-11-13'
    expected_export['measurements'] = sorted(rows,key=lambda r:(r['brand'].casefold(),r['model'].casefold(),r['id']))
    expected_export['sources'] = sources
    for key,delta in [('measurements',2),('sources',1),('source_reviews_completed',1)]:
        expected_export['coverage'][key] += delta
    assert exported == expected_export, 'Exact generated export with explicit metadata increments only'
    csv_rows = restore_rows(list(csv.DictReader((R/'docs/data/parking-measurements.csv').open())))
    prior_csv = list(csv.DictReader(io.StringIO(old_bytes('docs/data/parking-measurements.csv').decode())))
    assert [r for r in csv_rows if r.get('source_id') != SID] == prior_csv
    new_csv = [r for r in csv_rows if r.get('source_id')==SID]
    assert len(new_csv)==2
    for row,(_,ma,watts,_) in zip(new_csv,EXPECTED):
        assert row['firmware']=='8.0.0.23'
        assert row['current_ma']==str(ma) and Decimal(row['power_w'])==Decimal(watts)
        assert row['power_is_derived']=='True' and row['source_url']==URL
        assert all(row[k]=='' for k in NULLS)
    # Full-value negative controls, not numeric-only preservation assertions.
    for key,value in [('firmware','8.0.0.23'),('current_ma',45),('notes','changed provenance')]:
        changed=deepcopy(rows);changed[0][key]=value
        assert changed != old('parking/measurements.json')+e['measurements']
    changed=deepcopy(profile);changed['technical_facts'][0]['value']+=' altered'
    assert prior_power_profile(changed) != old('profiles/ddpai-z100-master.json')
    node="""const assert=require('assert');const C=require('./docs/assets/parking-charts.js');const rows=require('./docs/data/parking-measurements.json').measurements;const id=process.argv[1];for(const metric of ['watts','current'])for(const condition of ['', 'monitoring','event-recording']){const expected=rows.filter(r=>r.source_id===id&&(!condition||r.state===condition)).map(r=>r.id);assert.deepEqual(C.eligibleRows(rows,{metric,group:'low-power',family:'low-power',condition}).filter(r=>r.source_id===id).map(r=>r.id),expected);}for(const metric of ['delay','wake'])assert.equal(C.eligibleRows(rows,{metric,group:'low-power',condition:''}).filter(r=>r.source_id===id).length,0);console.log('Post-update production watts/current eligibility and null timing exclusion passed');"""
    subprocess.run(['node','-e',node,SID],cwd=R,check=True)
    print('Post-update source/math/4CH components/same-unit observed firmware plus owner continuity and unknown cloud verified; all 619 prior rows, sources, exact CSV values, video evidence and other models preserved.')
    return e

def browser_check(base, engine):
    from playwright.sync_api import sync_playwright
    out=Path(os.environ.get('Z100_POST_UPDATE_ARTIFACTS', Path(os.environ['TMPDIR'])/'z100-post-update-browser'))
    out.mkdir(parents=True,exist_ok=True)
    query=urlencode([('selection','1'),('group','low-power'),('family','low-power'),('condition',''),('metric','watts'),('highlight','DDPAI Z100 Master'),('title','Z100 Master 4CH post-update collision parking power'),('subtitle','Idle monitoring and event recording'),('yLabel','Parking states')]+[('id',SID+'-'+suffix) for suffix,_,_,_ in EXPECTED])
    with sync_playwright() as pw:
        browser=getattr(pw,engine).launch(**({'channel':'chrome'} if engine=='chromium' else {}),headless=True)
        page=browser.new_page();errors=[]
        page.on('pageerror',lambda error: errors.append(str(error)))
        for width in [1440,375,320]:
            page.set_viewport_size({'width':width,'height':1000})
            page.goto(base+'#camera=ddpai-z100-master')
            page.wait_for_selector('.parking-power-summary')
            assert page.locator('.detail-title').inner_text()=='Z100 Master'
            assert page.locator('.recording-attribution').inner_text()=='All recordings: Vortex Radar’s test unit.'
            summary=page.locator('.parking-power-summary')
            text=summary.inner_text()
            for value in ['44 mA','0.5544 W','935 mA','11.781 W','MINI3X','Post-update','Main firmware 8.0.0.23']: assert value in text,value
            assert 'Cloud off' not in text and 'not yet' not in text
            assert summary.locator('thead th').all_text_contents()==['State','Current','Derived power']
            if width<=600:
                cells=summary.locator('tbody tr').first.locator('td')
                assert cells.nth(0).evaluate("e=>getComputedStyle(e,'::before').content")=='"Current"'
                assert cells.nth(1).evaluate("e=>getComputedStyle(e,'::before').content")=='"Derived power"'
            detail=page.locator('details.technical-details')
            assert not detail.evaluate('(e)=>e.open')
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            summary.screenshot(path=str(out/f'{engine}-model-{width}.png'))
            page.locator('.video-specs').screenshot(path=str(out/f'{engine}-video-specs-{width}.png'))
            detail.locator(':scope > summary').focus();page.keyboard.press('Enter')
            assert detail.evaluate('(e)=>e.open')
            assert 'main firmware: 8.0.0.23' in detail.inner_text().casefold()
            assert 'no intervening updates' in detail.inner_text().casefold()
            assert 'were pending in that earlier test' in detail.inner_text().casefold()
            page.goto(base+'parking-charts.html?'+query)
            page.wait_for_function("()=>document.querySelector('#chart-canvas')?.getAttribute('aria-busy')==='false'")
            for metric in ['watts','current']:
                page.locator('#chart-metric').select_option(metric)
                bars=page.locator(f'#chart-canvas [data-measurement^="{SID}"]')
                assert bars.count()==2
                for suffix,ma,watts,_ in EXPECTED:
                    bar=page.locator(f'#chart-canvas [data-measurement="{SID}-{suffix}"]')
                    assert Decimal(bar.get_attribute('data-max'))==Decimal(watts if metric=='watts' else ma)
                    assert bar.get_attribute('data-highlight')=='true'
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                page.screenshot(path=str(out/f'{engine}-chart-{metric}-{width}.png'),full_page=True)
            for metric in ['delay','wake']:
                page.locator('#chart-metric').select_option(metric)
                assert page.locator(f'#chart-canvas [data-measurement^="{SID}"]').count()==0
            if width==1440:
                page.goto(base+'parking-charts.html?'+query)
                page.wait_for_function("()=>document.querySelector('#chart-canvas')?.getAttribute('aria-busy')==='false'")
                for selector,ext in [('#chart-svg','svg'),('#chart-png','png')]:
                    with page.expect_download() as download:page.locator(selector).click()
                    download.value.save_as(out/f'{engine}-post-update.{ext}')
        # Normal comparison distinguishes idle and triggered-event rows.
        page.goto(base+'parking-mode.html?q=Z100+Master&state=all')
        page.wait_for_selector('.parking-model-entry')
        page.locator('.parking-model-tests > summary').click()
        for suffix,ma,watts,_ in EXPECTED:
            row=page.locator(f'[data-id="{SID}-{suffix}"]')
            assert row.count()==1 and str(ma)+' mA' in row.inner_text()
            assert '8.0.0.23' in row.inner_text()
        response=page.goto(base+DOSSIER.removeprefix('docs/'))
        assert response.ok and json.loads(response.body())==load(DOSSIER)
        assert not errors,errors
        browser.close()
    print(f'{engine} desktop/mobile model attribution/collapsed details, watts/current charts, SVG/PNG downloads, normal comparison, no invented timing and exact dossier passed: '+base+'parking-charts.html?'+query)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser',choices=['chromium','webkit'])
    parser.add_argument('--url')
    args=parser.parse_args();verify()
    if args.browser or args.url:
        server=None
        if args.url:base=args.url.rstrip('/')+'/'
        else:
            class Handler(http.server.SimpleHTTPRequestHandler):
                def log_message(self,*args):pass
            server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(R/'docs')))
            threading.Thread(target=server.serve_forever,daemon=True).start()
            base=f'http://127.0.0.1:{server.server_port}/'
        browser_check(base,args.browser or 'chromium')
        if server:server.shutdown()
