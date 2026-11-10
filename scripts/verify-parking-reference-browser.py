#!/usr/bin/env python3
"""Actual builder/download regressions. Synthetic names and claims only."""
import argparse
import functools
import http.server
import json
from pathlib import Path
import threading
from urllib.parse import quote, urlencode, urlsplit
import xml.etree.ElementTree as ET
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
IDS=['vortex-sheet-row-'+str(n) for n in [4,6,9,11,15,21]]+['rcg530-662070-1','vortex-sheet-row-40','rcg530-674505-1']
REF='manual-reported-reference'
CLAIM='Reported / not independently measured'
p=argparse.ArgumentParser();p.add_argument('--url');p.add_argument('--browser',default='chromium',choices=['chromium','webkit']);p.add_argument('--output-dir',required=True,type=Path);args=p.parse_args()
args.output_dir.mkdir(parents=True,exist_ok=True)
class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self,format,*a):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(ROOT/'docs')))
threading.Thread(target=server.serve_forever,daemon=True).start()
url=args.url or 'http://127.0.0.1:%s/parking-charts.html'%server.server_port
query=urlencode(dict(selection='1',group='low-power',family='low-power',condition='monitoring',metric='watts',format='video',details='0',id=IDS),doseq=True)
def fragment(name='Example Cam',watts=0.123):return '#reference='+quote(json.dumps(dict(name=name,watts=watts),separators=(',',':')),safe='')
def ready(page):page.wait_for_function("()=>document.querySelector('#chart-canvas').getAttribute('aria-busy')==='false'")
def plotted(page):return page.locator('#chart-canvas [data-measurement]').evaluate_all('es=>es.map(e=>e.dataset.measurement)')
with sync_playwright() as pw:
    browser=pw.chromium.launch(channel='chrome') if args.browser=='chromium' else pw.webkit.launch()
    context=browser.new_context(accept_downloads=True,viewport={'width':1440,'height':1000})
    page=context.new_page();errors=[];requests=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('request',lambda r:requests.append({'url':r.url,'method':r.method,'body':r.post_data}))
    page.goto(url+'?'+query);ready(page)
    assert set(plotted(page))==set(IDS)
    baseline=page.locator('#chart-canvas svg').evaluate('e=>new XMLSerializer().serializeToString(e)')
    # Compare identical no-hash export against the reviewed renderer before this feature.
    import subprocess
    prior=subprocess.check_output(['git','show','6501a3e:docs/assets/parking-charts.js'],cwd=ROOT,text=True)
    page.route('**/assets/parking-charts.js*',lambda r:r.fulfill(body=prior,content_type='text/javascript'))
    page.reload();ready(page)
    assert page.locator('#chart-canvas svg').evaluate('e=>new XMLSerializer().serializeToString(e)')==baseline,'No-hash chart changed'
    page.unroute('**/assets/parking-charts.js*')
    shared=url+'?'+query+'&id='+REF+'&highlight='+REF+fragment()
    page.goto(shared);ready(page)
    assert set(plotted(page))==set(IDS+[REF])
    assert page.locator('[data-measurement="'+REF+'"]').get_attribute('data-highlight')=='true'
    assert 'Example' not in urlsplit(page.url).query
    assert page.locator('#chart-canvas').text_content().count(CLAIM)>=2
    assert page.locator('.chart-model-choice[data-model="Example Cam"]').count()==1
    page.add_init_script("navigator.clipboard.writeText = async text => {window.copiedChartLink=text;}")
    page.reload();ready(page)
    page.locator('#chart-share').click()
    page.wait_for_function('()=>window.copiedChartLink===location.href')
    assert urlsplit(page.evaluate('window.copiedChartLink')).fragment==fragment()[1:]
    shared=page.url
    for ext in ['svg','png']:
        with page.expect_download() as d:page.locator('#chart-'+ext).click()
        d.value.save_as(args.output_dir/(args.browser+'-reference.'+ext))
    svg=(args.output_dir/(args.browser+'-reference.svg')).read_text()
    root=ET.fromstring(svg);ns={'s':'http://www.w3.org/2000/svg'}
    assert (root.attrib['width'],root.attrib['height'])==('1920','1080')
    groups={e.attrib['data-measurement']:e for e in root.findall('.//s:g[@data-measurement]',ns)}
    assert set(groups)==set(IDS+[REF])
    data=json.loads((ROOT/'docs/data/parking-measurements.json').read_text())['measurements']
    for row in data:
        if row['id'] in IDS:
            expected=row['power_w_max'] if row.get('power_w_max') is not None else row['power_w']
            assert float(groups[row['id']].attrib['data-max'])==expected
    assert groups[REF].attrib['data-max']=='0.123'
    assert CLAIM in ' '.join(groups[REF].itertext())
    metadata_node=root.find('s:metadata',ns)
    assert metadata_node is not None and metadata_node.text
    metadata=json.loads(metadata_node.text)
    manual=next(r for r in metadata['measurements'] if r['id']==REF)
    assert manual['notes']==CLAIM and manual['power_w']==0.123 and manual['manual_reported']
    assert all(not manual.get(k) for k in ['voltage_v','current_ma','firmware','date','installed_channels','source_url','wake_seconds'])
    png=(args.output_dir/(args.browser+'-reference.png')).read_bytes()
    assert (int.from_bytes(png[16:20],'big'),int.from_bytes(png[20:24],'big'))==(3840,2160)
    exported=browser.new_page();exported.set_content(svg)
    assert exported.locator('[data-measurement]').count()==10
    bounds=exported.locator('svg').evaluate('''s=>[...s.querySelectorAll('text')].map(e=>{const b=e.getBBox(),m=s.getCTM().inverse().multiply(e.getCTM());return [[b.x,b.y],[b.x+b.width,b.y+b.height]].map(([x,y])=>{const p=new DOMPoint(x,y).matrixTransform(m);return [p.x,p.y]})}).every(ps=>ps.every(([x,y])=>x>=0&&x<=1920&&y>=0&&y<=1080))''')
    assert bounds,'Export text clipped'
    exported.close()
    page.locator('#chart-highlight').select_option('Vueroid S1-4K Infinite');assert page.locator('[data-measurement="vortex-sheet-row-9"]').get_attribute('data-highlight')=='true'
    page.locator('#chart-highlight').select_option('Example Cam');assert 'Example' not in urlsplit(page.url).query
    for metric in ['current','delay','wake']:
        page.goto(shared);ready(page);page.locator('#chart-metric').select_option(metric)
        assert REF not in plotted(page) and page.locator('.chart-model-choice[data-model="Example Cam"]').count()==0
    page.goto(shared);ready(page)
    page.locator('#chart-search').fill('Example Cam');assert set(plotted(page))==set(IDS+[REF])
    assert page.locator('#chart-picker input[data-id]').count()==1
    page.locator('#chart-search').fill('')
    page.locator('#chart-advanced').evaluate('e=>e.open=true')
    page.locator('#chart-condition').select_option('event-recording');assert REF not in plotted(page)
    page.goto(shared);ready(page)
    page.evaluate("()=>{history.pushState(null,'','?selection=1&group=low-power&family=low-power&metric=watts');dispatchEvent(new PopStateEvent('popstate'));}")
    assert not plotted(page)
    page.go_back();ready(page);assert set(plotted(page))==set(IDS+[REF])
    page.go_forward();ready(page);assert not plotted(page)
    page.goto(shared.replace(fragment(),fragment(watts=0)));ready(page)
    assert page.locator('[data-measurement="'+REF+'"] [data-kind=zero]').count()==1
    # Literal unsafe-looking text is inert in DOM and in the downloaded metadata.
    hostile='<img src=x onerror=alert(1)>'
    page.goto(url+'?'+query+'&id='+REF+fragment(hostile));ready(page)
    assert page.locator('#chart-canvas img').count()==0 and hostile in page.locator('#chart-canvas').text_content()
    with page.expect_download() as d:page.locator('#chart-svg').click()
    hostile_path=args.output_dir/(args.browser+'-inert-text.svg');d.value.save_as(hostile_path)
    hostile_root=ET.fromstring(hostile_path.read_text())
    hostile_metadata=hostile_root.find('s:metadata',ns)
    assert hostile_metadata is not None and hostile_metadata.text
    assert next(r for r in json.loads(hostile_metadata.text)['measurements'] if r['id']==REF)['model']==hostile
    assert not hostile_root.findall('.//s:script',ns) and not hostile_root.findall('.//s:image',ns)
    for malformed in ['#reference=%','#reference='+quote('{"name":"Example Cam","watts":-1}')]:
        page.goto(url+'?'+query+malformed);ready(page)
        assert set(plotted(page))==set(IDS) and 'Manual reference ignored' in page.locator('#chart-notice').text_content()
    page.goto(url+'?'+query+'&id='+REF+fragment());ready(page)
    # Same-document fragment edits and history restore must reparse local rows.
    page.evaluate("h=>location.hash=h",fragment(watts=0))
    page.wait_for_function("()=>document.querySelector('[data-measurement=manual-reported-reference] [data-kind=zero]')")
    page.go_back();ready(page)
    page.wait_for_function("()=>document.querySelector('[data-measurement=manual-reported-reference]').dataset.max==='0.123'")
    assert not errors,errors
    assert not any('Example' in r['url'] or 'reference=' in r['url'] or r['method']!='GET' or r['body'] for r in requests),requests
    report={'browser':args.browser,'base':url,'regular_nine_id_svg_unchanged':True,'selected_ids':IDS+[REF],'exports':{'svg':[1920,1080],'png':[3840,2160]},'claim_visible_details_0':True,'clipboard_reload_history_hashchange':True,'zero_and_xss':True,'network_fragment_not_sent':True,'errors':errors,'generic_url':shared}
    (args.output_dir/(args.browser+'-report.json')).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
    browser.close()
server.shutdown()
