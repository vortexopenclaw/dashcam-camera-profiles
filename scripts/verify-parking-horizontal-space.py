#!/usr/bin/env python3
"""Measure chart/export width use, including fixed YouTube frames.

--baseline runs the pre-fix renderer as a negative control. --url exercises
published assets; --output-dir retains downloaded images and geometry evidence.
Synthetic adversaries are intercepted only in the browser, never saved as data.
"""
import argparse
import functools
import http.server
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
from urllib.parse import urlencode
import xml.etree.ElementTree as ET
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url')
    parser.add_argument('--baseline', action='store_true')
    parser.add_argument('--browser', default='chromium', choices=['chromium', 'webkit'])
    parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args()
    OUT = args.output_dir or Path(tempfile.mkdtemp(prefix='chart-horizontal-', dir=os.environ['TMPDIR']))
    OUT.mkdir(parents=True, exist_ok=True)
    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, format, *args): pass
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Handler, directory=str(ROOT / 'docs')))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = args.url or 'http://127.0.0.1:%s/parking-charts.html' % server.server_port
    report = []
    prefix = ('before' if args.baseline else 'after') + '-' + args.browser
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='chrome') if args.browser == 'chromium' else p.webkit.launch()
        page = browser.new_page(accept_downloads=True, viewport={'width': 1440, 'height': 1000})
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        if args.baseline:
            source = subprocess.check_output(['git', 'show', '6ebff93:docs/assets/parking-charts.js'], cwd=ROOT, text=True)
            page.route('**/assets/parking-charts.js*', lambda route: route.fulfill(body=source, content_type='text/javascript'))
        for metric in ['watts', 'wake', 'delay', 'current']:
            for fmt in ['video', 'auto']:
                page.goto(url + '?' + urlencode(dict(group='low-power', family='low-power', condition='monitoring', metric=metric, format=fmt)))
                page.wait_for_function("()=>document.querySelector('#chart-canvas').getAttribute('aria-busy')==='false'")
                page.locator('#chart-apply-group').click()
                # Current can legitimately switch to watts for mixed voltages.
                if metric == 'current':
                    page.locator('#preset-current').click()
                    page.locator('#chart-format').select_option(fmt)
                for details in [False, True] if fmt == 'video' else [False]:
                    page.locator('#chart-details').set_checked(details)
                    page.evaluate('document.fonts.ready')
                    g = page.locator('#chart-canvas svg').evaluate('''s=>{
                      const box=e=>{const b=e.getBBox(),m=s.getCTM().inverse().multiply(e.getCTM());const a=new DOMPoint(b.x,b.y).matrixTransform(m),z=new DOMPoint(b.x+b.width,b.y+b.height).matrixTransform(m);return {left:a.x,right:z.x,top:a.y,bottom:z.y};};
                      const groups=[...s.querySelectorAll('[data-measurement]')];
                      const bars=groups.flatMap(g=>[...g.querySelectorAll('[data-kind=bar],[data-kind=scalar]')]).map(box);
                      const values=groups.map(g=>box(g.querySelector('[data-kind=value]')));
                      const labels=groups.flatMap(g=>[...g.querySelectorAll('text:not([data-kind=value])')]).map(box);
                      const texts=[...s.querySelectorAll('text')].filter(t=>!t.hasAttribute('transform')).map(box);
                      const width=+s.getAttribute('width'),height=+s.getAttribute('height');
                      const left=Math.min(...bars.map(b=>b.left)),end=Math.max(...bars.map(b=>b.right));
                      const axisLines=[...s.querySelectorAll('g>line')].filter(e=>e.getAttribute('x1')===e.getAttribute('x2'));
                      const gridEnd=Math.max(...axisLines.map(e=>box(e).right));
                      return {width,height,rows:groups.length,plotLeft:left,barEnd:end,barWidth:end-left,
                        labelLeft:Math.min(...labels.map(b=>b.left)),valueRight:Math.max(...values.map(b=>b.right)),
                        rightPadding:width-Math.max(...values.map(b=>b.right)),axisHeadroomPixels:gridEnd-end,
                        clipped:texts.some(b=>b.left<0||b.right>width+1||b.top<0||b.bottom>height+1),
                        values:groups.map(g=>({id:g.dataset.measurement,min:g.dataset.min,max:g.dataset.max,text:g.querySelector('[data-kind=value]').textContent})),
                        samples:groups.flatMap(g=>{const b=g.querySelector('[data-kind=bar],[data-kind=scalar]');if(!b)return [];const m=s.getCTM().inverse().multiply(b.getCTM());const x=+b.getAttribute('x')+ +b.getAttribute('width')*.1,y=+b.getAttribute('y')+4;const q=new DOMPoint(x,y).matrixTransform(m);return [{x:q.x*2,y:q.y*2,color:b.getAttribute('fill')}];})};}''')
                    name = '%s-%s-%s%s' % (prefix, metric, fmt, '-details' if details else '')
                    for ext in ['svg', 'png']:
                        with page.expect_download() as d: page.locator('#chart-' + ext).click()
                        d.value.save_as(OUT / (name + '.' + ext))
                    raw = (OUT / (name + '.png')).read_bytes()
                    exported = ET.parse(OUT / (name + '.svg')).getroot()
                    exported_groups = exported.findall('.//{http://www.w3.org/2000/svg}g[@data-measurement]')
                    assert [(g.attrib['data-measurement'], g.attrib['data-min'], g.attrib['data-max']) for g in exported_groups] == [(v['id'], v['min'], v['max']) for v in g['values']]
                    assert int.from_bytes(raw[16:20], 'big') == g['width'] * 2
                    assert int.from_bytes(raw[20:24], 'big') == g['height'] * 2
                    import base64
                    pixels = page.evaluate('''async ({image,samples})=>{const i=new Image();i.src='data:image/png;base64,'+image;await i.decode();const c=document.createElement('canvas');c.width=i.width;c.height=i.height;const x=c.getContext('2d');x.drawImage(i,0,0);return samples.map(s=>{const p=[...x.getImageData(Math.floor(s.x),Math.floor(s.y),1,1).data];return {p,color:s.color};});}''', {'image': base64.b64encode(raw).decode(), 'samples': g.pop('samples')})
                    assert all(max(abs(a-b) for a,b in zip(x['p'][:3], ([239,138,44] if x['color'] == '#ef8a2c' else [85,155,212]))) <= 24 for x in pixels), pixels
                    assert not g['clipped'], g
                    if args.baseline and fmt == 'video' and metric in ['watts', 'wake'] and not details:
                        assert g['rightPadding'] > 400 and g['barWidth'] / g['width'] < .4, g
                    if not args.baseline:
                        assert 24 <= g['rightPadding'] <= 125, g
                        assert g['barWidth'] / g['width'] > .5, g
                        assert g['axisHeadroomPixels'] <= 1, g
                        if fmt == 'video': assert (g['width'],g['height']) == (1920,1080)
                    report.append(dict(name=name, **g))
        if not args.baseline:
            # Browser-only, explicitly synthetic adversaries. Never edit data.
            data = json.loads((ROOT / 'docs/data/parking-measurements.json').read_text())
            for metric, key in dict(watts='power_w', current='current_ma', delay='reported_startup_seconds', wake='wake_seconds').items():
                for lo, hi in [(0, 0), (0.0001, 0.000234), (1234567.1234567, 2345678.1234567)]:
                    fixture = json.loads(json.dumps(data))
                    row = fixture['measurements'][0]
                    row.update(model='Synthetic camera with an intentionally very long model label for wrapping',
                               mode_name='Synthetic mode label for long-label layout coverage', voltage_v=12.6,
                               disabled=False, measurement_statistic=None,
                               reported_startup_method='Impact detection to start of recording')
                    row.update({key: None, key + '_min': lo, key + '_max': hi})
                    page.route('**/data/parking-measurements.json', lambda route: route.fulfill(json=fixture))
                    for fmt in ['auto', 'video']:
                        page.goto(url + '?' + urlencode(dict(selection=1, id=row['id'], metric=metric, group='all', family='all', condition='', format=fmt, details=1, modeLabels=1)))
                        page.wait_for_selector('#chart-canvas [data-measurement]')
                        assert page.locator('#chart-canvas [data-measurement]').count() == 1
                        assert page.locator('#chart-canvas svg').evaluate('''s=>[...s.querySelectorAll('text')].every(t=>{const b=t.getBoundingClientRect(),r=s.getBoundingClientRect();return b.left>=r.left-1&&b.right<=r.right+1&&b.top>=r.top-1&&b.bottom<=r.bottom+1;})''')
                        assert page.locator('[data-kind=value]').text_content() == page.evaluate('r=>ParkingCharts.valueLabel(r,ParkingCharts.interval(r,"' + metric + '"),"' + metric + '")', row)
                        if hi == 0: assert page.locator('[data-kind=zero]').count() == 1
                    page.unroute('**/data/parking-measurements.json')
        assert not errors, errors
        browser.close()
    server.shutdown()
    (OUT / (prefix + '.json')).write_text(json.dumps(report, indent=2))
    print(json.dumps([{k:v for k,v in g.items() if k != 'values'} for g in report], indent=2))
    print('PASS: actual SVG and PNG downloads, shared-scale geometry, no clipped labels, and PNG bar pixels')

if __name__ == '__main__': main()
