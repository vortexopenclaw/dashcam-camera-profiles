#!/usr/bin/env python3
"""Check transformed text bounds, not anchors, on native chart exports."""
import argparse
import functools
import http.server
import json
from pathlib import Path
import subprocess
import threading
from urllib.parse import urlencode
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
QUERY = 'selection=1&group=low-power&family=low-power&condition=monitoring&metric=watts&sort=desc&highlight=Vueroid+S1-4K+Infinite&title=Low+Power+Parking+Mode+Power+Draw+Comparison&details=0&format=video&id=vortex-sheet-row-4&id=vortex-sheet-row-6&id=vortex-sheet-row-9&id=vortex-sheet-row-11&id=vortex-sheet-row-15&id=vortex-sheet-row-21&id=rcg530-662070-1&id=vortex-sheet-row-40&id=rcg530-674505-1'
IDS = [part[3:] for part in QUERY.split('&') if part.startswith('id=')]
GEOMETRY = '''s=>{
  const box=e=>{const b=e.getBBox(),m=s.getCTM().inverse().multiply(e.getCTM());
    const p=[[b.x,b.y],[b.x+b.width,b.y],[b.x,b.y+b.height],[b.x+b.width,b.y+b.height]].map(([x,y])=>new DOMPoint(x,y).matrixTransform(m));
    return {left:Math.min(...p.map(q=>q.x)),right:Math.max(...p.map(q=>q.x)),top:Math.min(...p.map(q=>q.y)),bottom:Math.max(...p.map(q=>q.y))};};
  const title=box(s.querySelector('[data-role=chart-y-axis]'));
  const rows=[...s.querySelectorAll('[data-measurement]')];
  const labels=rows.flatMap(r=>[...r.querySelectorAll('text:not([data-kind=value])')]).map(box);
  const bars=rows.flatMap(r=>[...r.querySelectorAll('[data-kind=bar],[data-kind=scalar]')]).map(box);
  const values=rows.map(r=>box(r.querySelector('[data-kind=value]')));
  const width=+s.getAttribute('width'),height=+s.getAttribute('height');
  return {width,height,title,labelLeft:Math.min(...labels.map(b=>b.left)),edgeGap:title.left,
    titleLabelGap:Math.min(...labels.map(b=>b.left))-title.right,
    plotWidth:Math.max(...bars.map(b=>b.right))-Math.min(...bars.map(b=>b.left)),
    rightGap:width-Math.max(...values.map(b=>b.right)),
    clipped:[...s.querySelectorAll('text')].map(box).some(b=>b.left<0||b.right>width+1||b.top<0||b.bottom>height+1),
    rows:rows.map(r=>({id:r.dataset.measurement,min:r.dataset.min,max:r.dataset.max,highlight:r.dataset.highlight,value:r.querySelector('[data-kind=value]').textContent}))};}'''


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--browser', choices=['chromium','webkit'], default='chromium')
    p.add_argument('--baseline', action='store_true')
    p.add_argument('--url')
    p.add_argument('--output-dir', required=True, type=Path)
    args = p.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a): pass
    server = http.server.ThreadingHTTPServer(('127.0.0.1',0), functools.partial(Handler,directory=str(ROOT/'docs')))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    url = args.url or 'http://127.0.0.1:%s/parking-charts.html' % server.server_port
    prefix = ('before' if args.baseline else 'after')+'-'+args.browser
    report=[]
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel='chrome') if args.browser=='chromium' else pw.webkit.launch()
        page=browser.new_page(accept_downloads=True,viewport={'width':1440,'height':1000})
        errors=[]
        page.on('pageerror',lambda e: errors.append(str(e)))
        if args.baseline:
            source=subprocess.check_output(['git','show','31a459b:docs/assets/parking-charts.js'],cwd=ROOT,text=True)
            page.route('**/assets/parking-charts.js*',lambda r:r.fulfill(body=source,content_type='text/javascript'))
        cases=[('exact',QUERY),('auto',QUERY.replace('format=video','format=auto')),
               ('details',QUERY.replace('details=0','details=1')),
               ('sparse',QUERY.split('&id=')[0]+'&id='+IDS[0]),
               ('many','group=low-power&family=low-power&condition=monitoring&metric=watts&format=video&details=1'),
               ('many-auto','group=low-power&family=low-power&condition=monitoring&metric=watts&format=auto&details=1'),
               ('synthetic-video','selection=1&group=all&family=all&metric=watts&format=video&details=1'),
               ('synthetic-auto','selection=1&group=all&family=all&metric=watts&format=auto&details=1'),
               ('descriptive',QUERY+'&modeLabels=1&subtitle='+urlencode({'s':'Monitoring comparison with full camera mode labels'}).split('=',1)[1])]
        for name,query in cases:
            if name.startswith('synthetic'):
                fixture=json.loads((ROOT/'docs/data/parking-measurements.json').read_text())
                row=fixture['measurements'][0]
                row.update(model='Synthetic camera with a long descriptive model name to exercise multiline labels', mode_name='Synthetic long descriptive parking mode with wrapped text', power_w=1, power_w_min=None, power_w_max=None, disabled=False, measurement_statistic=None)
                query+='&id='+row['id']+'&title='+urlencode({'t':'Synthetic multiline chart heading with descriptive camera names and mode labels'}).split('=',1)[1]
                page.route('**/data/parking-measurements.json',lambda r:r.fulfill(json=fixture))
            page.goto(url+'?'+query)
            page.wait_for_function("()=>document.querySelector('#chart-canvas').getAttribute('aria-busy')==='false'")
            if name.startswith('many'): page.locator('#chart-apply-group').click()
            page.evaluate('document.fonts.ready')
            g=page.locator('#chart-canvas svg').evaluate(GEOMETRY)
            if name in ['exact','auto','details','descriptive']:
                assert sorted(r['id'] for r in g['rows'])==sorted(IDS),g
                assert [r['id'] for r in g['rows'] if r['highlight']=='true']==['vortex-sheet-row-9'],g
            assert not g['clipped'],g
            if args.baseline:
                if name=='exact': assert g['edgeGap']<24 and g['titleLabelGap']<20,g
            else:
                assert g['edgeGap']>=36 and g['titleLabelGap']>=24,g
                assert g['plotWidth']/g['width']>.5,g
                assert g['rightGap']>=24,g
            if name=='exact':
                assert (g['width'],g['height'])==(1920,1080),g
                for ext in ['svg','png']:
                    with page.expect_download() as d: page.locator('#chart-'+ext).click()
                    d.value.save_as(args.output_dir/(prefix+'-exact.'+ext))
                png=(args.output_dir/(prefix+'-exact.png')).read_bytes()
                assert (int.from_bytes(png[16:20],'big'),int.from_bytes(png[20:24],'big'))==(3840,2160)
                # Verify the downloaded SVG, not only the original preview DOM.
                svg=(args.output_dir/(prefix+'-exact.svg')).read_text()
                export=browser.new_page()
                export.set_content(svg)
                eg=export.locator('svg').evaluate(GEOMETRY)
                assert eg['rows']==g['rows'],(eg,g)
                assert all(abs(eg[k]-g[k])<1 for k in ['edgeGap','titleLabelGap','plotWidth','rightGap']),(eg,g)
                g['exportGeometry']={k:eg[k] for k in ['edgeGap','titleLabelGap','plotWidth','rightGap']}
                export.close()
                page.screenshot(path=str(args.output_dir/(prefix+'-preview.png')),full_page=True)
            report.append(dict(case=name,**g))
            if name.startswith('synthetic'): page.unroute('**/data/parking-measurements.json')
        assert not errors,errors
        browser.close()
    server.shutdown()
    (args.output_dir/(prefix+'.json')).write_text(json.dumps(report,indent=2))
    print(json.dumps([{k:v for k,v in r.items() if k!='rows'} for r in report],indent=2))
    print('PASS: transformed text bounds, exact IDs/highlight, downloaded SVG/PNG, wide plot')


if __name__=='__main__': main()
