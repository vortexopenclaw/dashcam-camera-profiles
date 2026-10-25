#!/usr/bin/env python3
"""Real browser metric-aware picker regressions, local or --url public URL."""
import argparse
import functools
import http.server
import json
import pathlib
import subprocess
import threading
import urllib.parse
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser()
parser.add_argument('--url')
parser.add_argument('--baseline', action='store_true')
args = parser.parse_args()
root = pathlib.Path(__file__).resolve().parents[1]
data = json.loads((root/'docs/data/parking-measurements.json').read_text())
server = None
if args.url:
    url = args.url.split('?')[0]
else:
    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, format, *args): pass
    server = http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(root/'docs')))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    url = 'http://127.0.0.1:%s/parking-charts.html' % server.server_port

def ready(page):
    page.wait_for_function("()=>document.querySelector('#chart-canvas').getAttribute('aria-busy')==='false'")
def ids(page):
    return page.locator('#chart-canvas [data-measurement]').evaluate_all('es=>es.map(e=>e.dataset.measurement)')
def load(page, **values):
    page.goto(url+'?'+urllib.parse.urlencode(values, doseq=True)); ready(page)

with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome',headless=True)
    page = browser.new_page(viewport={'width':1440,'height':1000})
    errors=[]
    page.on('pageerror',lambda error: errors.append(str(error)))
    if args.baseline:
        baseline = subprocess.check_output(['git','show','f5c1b83:docs/assets/parking-charts.js'],cwd=root,text=True)
        page.route('**/assets/parking-charts.js*',lambda route:route.fulfill(body=baseline,content_type='text/javascript'))
        load(page,group='low-power',family='low-power',metric='delay')
        print(json.dumps({'baseline_models':page.locator('.chart-model-choice').count(),'baseline_missing_variants':page.locator('#chart-picker .chart-metric-reading').filter(has_text='Not measured').count(),'baseline_missing_model_names':page.locator('.chart-model-choice').evaluate_all("es=>es.filter(e=>e.textContent.includes('Not measured for this metric')).map(e=>e.dataset.model)")}))
        browser.close()
        if server: server.shutdown()
        raise SystemExit()
    load(page,group='low-power',family='low-power',metric='delay')
    print('Delay low-power: '+page.locator('#picker-count').text_content()+'; '+page.locator('#chart-group-count').text_content())
    assert page.locator('.chart-model-choice[data-model="Viofo T340"]').count()==1
    families=page.evaluate('Object.keys(ParkingCharts.families)')
    metrics=page.evaluate('Object.keys(ParkingCharts.metrics)')
    checks=0
    for width in [1440,375]:
        page.set_viewport_size({'width':width,'height':1000})
        for metric in metrics:
            for family in families:
                # Explicit loads also verify URL initialization for every criteria combination.
                load(page,selection='1',group=family,family=family,metric=metric,condition='')
                page.locator('#chart-advanced').evaluate('e=>e.open=true')
                conditions=['','monitoring','event-recording','time-lapse','continuous'] if width==1440 else ['monitoring']
                for condition in conditions:
                    page.locator('#chart-condition').select_option(condition)
                    expected=page.evaluate("({rows,metric,group,condition})=>ParkingCharts.eligibleRows(rows,{metric,group,condition}).map(r=>({id:r.id,model:ParkingUI.modelLabel(r)}))",{'rows':data['measurements'],'metric':metric,'group':family,'condition':condition})
                    allowed={r['id'] for r in expected}
                    actual=set(page.locator('#chart-picker input[data-id]').evaluate_all('es=>es.map(e=>e.dataset.id)'))
                    assert actual==allowed,(width,metric,family,condition,actual^allowed)
                    assert set(page.locator('.chart-model-choice').evaluate_all('es=>es.map(e=>e.dataset.model)'))=={r['model'] for r in expected}
                    variants=page.locator('select[data-test] option').evaluate_all('es=>es.map(e=>e.value)')
                    assert set(variants)<=allowed
                    assert page.locator('select[data-channels]').evaluate_all('es=>es.every(e=>e.value && [...e.options].some(o=>o.value===e.value))')
                    page.locator('#chart-clear').click() if page.locator('#chart-clear').is_enabled() else None
                    if expected:
                        page.locator('.chart-model-choice input[type=checkbox]').first.check()
                        assert len(ids(page))==1,(width,metric,family,condition,page.locator('#chart-notice').text_content())
                        assert set(ids(page))<=allowed
                    else:
                        assert not ids(page)
                        assert 'No camera models have plottable data' in page.locator('#chart-model-picker').text_content()
                    checks+=1
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    t340='rcg530-t340-1.0_261023T2-LPID_monitoring-day'
    load(page,selection='1',group='low-power',family='low-power',metric='delay',condition='monitoring',id=[t340,'evil','vortex-sheet-row-12'])
    assert ids(page)==[t340]
    assert page.locator('[data-measurement] [data-kind=value]').text_content()=='1.76–1.85 s'
    page.locator('#chart-highlight').select_option('Viofo T340')
    shared=page.url
    page.locator('#chart-metric').select_option('watts')
    assert ids(page)==[t340]
    page.locator('#chart-search').fill('NO SUCH CAMERA')
    assert ids(page)==[t340] and page.locator('.chart-model-choice').count()==0
    page.locator('#chart-search').fill('')
    page.locator('#chart-metric').select_option('wake')
    assert not ids(page) and page.locator('#chart-highlight option').count()==1
    page.locator('#chart-metric').select_option('delay')
    assert not ids(page),'Pruned IDs must not silently reappear'
    page.evaluate("url=>{history.pushState(null,'',url);dispatchEvent(new PopStateEvent('popstate'))}",shared)
    assert ids(page)==[t340]
    page.reload();ready(page); assert ids(page)==[t340]
    # Real browser back and forward must restore controls, selections, and highlights.
    page.evaluate("()=>history.pushState(null,'','?selection=1&group=buffered&family=buffered&metric=wake&condition=monitoring')")
    page.evaluate("()=>dispatchEvent(new PopStateEvent('popstate'))")
    assert not ids(page)
    page.go_back();ready(page);assert ids(page)==[t340]
    page.go_forward();ready(page);assert not ids(page)
    # Compatible multi-test selections survive metric changes without collapsing.
    sibling=next(r['id'] for r in data['measurements'] if r['id']!=t340 and r.get('reported_startup_seconds_min')==1.76 and r.get('model')=='T340' and r.get('state')=='monitoring')
    load(page,selection='1',group='low-power',family='low-power',metric='delay',condition='monitoring',id=[t340,sibling])
    assert set(ids(page))=={t340,sibling}
    page.locator('#chart-metric').select_option('watts')
    assert set(ids(page))=={t340,sibling}
    page.locator('#chart-search').fill(t340)
    assert page.locator('select[data-test] option').count()==1
    assert page.locator('select[data-test] option').get_attribute('value')==t340
    assert set(ids(page))=={t340,sibling}
    page.locator('#chart-search').fill('')
    page.locator('#chart-clear').click()
    page.locator('#chart-group').select_option('buffered')
    page.locator('#chart-group').select_option('low-power')
    assert not ids(page),'Clear must not be undone by mode changes'
    # Adversarial data travels through the actual fetch/DOM/render pipeline.
    fixture=json.loads(json.dumps(data))
    base=next(r for r in fixture['measurements'] if r['id']==t340)
    fixture['measurements']=[dict(base,id='fixture-'+str(i),power_w=value,power_w_min=None,power_w_max=None) for i,value in enumerate([0,None,''])]
    fixture['measurements']+=[dict(base,id='fixture-range',power_w=None,power_w_min=1,power_w_max=2),dict(base,id='fixture-invalid',power_w=3,power_w_min=4,power_w_max=2),dict(base,id='fixture-disabled',power_w=3,disabled=True)]
    page.route('**/data/parking-measurements.json',lambda route:route.fulfill(json=fixture))
    load(page,selection='1',group='low-power',family='low-power',metric='watts',condition='monitoring',id=[r['id'] for r in fixture['measurements']])
    assert set(ids(page))=={'fixture-0','fixture-range'}
    assert page.locator('#chart-picker input[data-id]').count()==2
    assert page.locator('[data-kind=zero]').count()==1
    assert not errors,errors
    print(json.dumps({'criteria_browser_checks':checks,'viewports':[1440,375],'url_restore':True,'back_forward':True,'range_only_T340':True,'null_blank_zero_disabled_invalid_range_fixture':True,'page_errors':errors}))
    browser.close()
if server: server.shutdown()
