#!/usr/bin/env python3
"""Verify current A119M Pro Medium/Low Bitrate evidence and owner power tests."""
import json
import math
import sys
from pathlib import Path
from urllib.parse import urlencode
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
base=sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:8896/'
key='viofo-a119m-pro:medium-fw1.2_20260817'
e=json.loads((ROOT/'docs/data/a119m-pro-medium-1.2_20260817.json').read_text())
assert e['ownerAssertions']['firmware']=='1.2_20260817'
assert e['ownerAssertions']['quality']=='medium' and e['ownerAssertions']['parkingMode']=='low-bitrate'
assert len(e['samples'])==5 and e['inventory']['mediaCount']==7
assert all(s['channel']==s['mode']=='unknown' for s in e['samples'])
driving=[e['samples'][i] for i in e['review']['drivingSampleIndices']]
parking=[e['samples'][i] for i in e['review']['parkingSampleIndices']]
assert len(driving)==2 and len(parking)==3
assert all((s['width'],s['height'])==(3840,2160) and s['durationSeconds']>=60 for s in driving)
assert all((s['width'],s['height'])==(2560,1440) and math.isclose(s['fps'],30) for s in parking)
rows=json.loads((ROOT/'docs/data/bitrate-variants.json').read_text());row=next(r for r in rows if r['key']==key)
assert not row['default'] and row['status']=='current' and row['quality']=='medium'
assert row['lowMbps']==min(s['bitrateKbps']/1000 for s in driving)
assert row['highMbps']==max(s['bitrateKbps']/1000 for s in driving)
high=next(r for r in rows if r['key']=='viofo-a119m-pro');assert high['default'] and high['quality']=='high' and high['firmware']==row['firmware']
assert sum(r['key']==key for r in rows)==1
expected={'vortex-sheet-row-26':('buffered-event','monitoring',252,3.12),'vortex-sheet-row-27':('buffered-event','event-recording',252,3.12),'vortex-sheet-row-28':('low-bitrate','continuous',256,3.17)}
canonical=json.loads((ROOT/'parking/measurements.json').read_text())
for ident,(category,state,ma,watts) in expected.items():
    matches=[r for r in canonical if r['id']==ident];assert len(matches)==1
    r=matches[0];assert r['model']=='A119M Pro' and r['firmware']=='1.2_20260817'
    assert (r['category'],r['state'],r['current_ma'],r['power_w'],r['voltage_v'])==(category,state,ma,watts,12.4)
    assert r['installed_channels']==1 and r['active_channels']==['front']
    assert 'HK6-F' in r['power_path'] and r['source_is_private'] and not r['power_is_derived']
    assert r['wake_seconds'] is None and r['reported_startup_seconds'] is None
    assert r['prebuffer_s'] is None and r['date'] is None
assert 'docs.google.com' not in json.dumps(canonical)
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True);page=browser.new_page(accept_downloads=True)
    page.goto(base+'bitrate-charts.html?'+urlencode([('selection','1'),('camera',key)]));page.wait_for_selector('#chart svg')
    assert page.locator('[data-kind=model-label]').all_text_contents()==['Viofo A119M Pro · 1CH']
    assert page.locator('[data-kind=configuration-label]').all_text_contents()==['Medium Bitrate · H.264']
    assert page.locator('[data-kind=value]').text_content()=='51.2 Mbps'
    assert page.locator('[data-role=chart-y-axis]').all_text_contents()==['Dash Cameras']
    page.locator('#defaults').click()
    assert page.locator('#chart g[data-variant="viofo-a119m-pro"]').count()==1
    assert page.locator('#chart g[data-variant="'+key+'"]').count()==0
    page.goto(base+'bitrate-charts.html?'+urlencode([('selection','1'),('camera','viofo-a119m-pro'),('camera',key)]));page.wait_for_selector('#chart svg')
    assert page.locator('#chart g[data-variant]').count()==2
    assert set(page.locator('[data-kind=configuration-label]').all_text_contents())=={'High Bitrate · H.264','Medium Bitrate · H.264'}
    for ident,(_,_,ma,watts) in expected.items():
        group='low-bitrate' if ident.endswith('28') else 'buffered'
        condition='event-recording' if ident.endswith('27') else 'continuous' if ident.endswith('28') else 'monitoring'
        page.goto(base+'parking-charts.html?'+urlencode([('selection','1'),('group',group),('family',group),('condition',condition),('metric','watts'),('id',ident)]));page.wait_for_selector('#chart-canvas svg')
        assert f'{watts:.2f}' in page.locator('#chart-canvas').text_content()
        assert 'A119M Pro' in page.locator('#chart-canvas').text_content()
    browser.close()
print('Verified: one unique Medium/Low Bitrate set, exact paired metadata, current-firmware High default, Medium label, three distinct owner power tests, confirmed voltage/firmware/cable, and live-rendered bitrate and parking charts.')
