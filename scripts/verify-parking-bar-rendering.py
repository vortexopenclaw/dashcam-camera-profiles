#!/usr/bin/env python3
"""Real-browser geometry, responsive reachability, and downloaded image checks.

Uses canonical public data without writing it. Adversarial data is intercepted
only in the browser. Optional --url verifies the same contracts after deployment.
"""
import argparse
import base64
import functools
import http.server
import json
import math
import os
from pathlib import Path
import tempfile
import threading
from urllib.parse import urlencode
import xml.etree.ElementTree as ET

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
KEYS = {'watts': 'power_w', 'current': 'current_ma',
        'delay': 'reported_startup_seconds', 'wake': 'wake_seconds'}
NS = {'s': 'http://www.w3.org/2000/svg'}


def interval(row, metric):
    def valid(v):
        return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) and v >= 0
    if row.get('disabled') or row.get('measurement_statistic') == 'disabled':
        return None
    if metric == 'delay' and row.get('reported_startup_method') not in (
            'Impact detection to start of recording', 'Impact event to start of recording (source-reported)'):
        return None
    key = KEYS[metric]
    a, b = row.get(key + '_min'), row.get(key + '_max')
    if a is not None or b is not None:
        return (a, b, True) if valid(a) and valid(b) and b >= a else None
    v = row.get(key)
    return (v, v, False) if valid(v) else None


def query(ids, metric, **kwargs):
    return urlencode(list(dict(selection='1', group='all', family='all', condition='',
                              metric=metric, format='auto', **kwargs).items()) + [('id', x) for x in ids])


def ready(page):
    page.wait_for_function("() => document.querySelector('#chart-canvas').getAttribute('aria-busy') === 'false'")
    assert 'could not load' not in page.locator('#chart-data-status').text_content()


def geometry(page, expected):
    actual = page.locator('#chart-canvas [data-measurement]').evaluate_all("""gs=>gs.map(g=>({
      id:g.dataset.measurement,min:+g.dataset.min,max:+g.dataset.max,range:g.dataset.range==='true',
      highlight:g.dataset.highlight==='true',label:g.querySelector('[data-kind=value]').textContent,
      shapes:[...g.querySelectorAll('rect,line,circle')].map(e=>Object.fromEntries([...e.attributes].map(a=>[a.name,a.value])))
    }))""")
    assert {x['id'] for x in actual} == set(expected)
    ratios = []
    for g in actual:
        a, b, ranged = expected[g['id']]
        assert (g['min'], g['max'], g['range']) == (a, b, ranged), g
        color = '#ef8a2c' if g['highlight'] else '#559bd4'
        bars = [s for s in g['shapes'] if s.get('data-kind') in ('bar', 'scalar')]
        zeros = [s for s in g['shapes'] if s.get('data-kind') == 'zero']
        if b > 0:
            assert len(bars) == 1 and not zeros, g
            bar = bars[0]
            assert bar['fill'] == color and float(bar['height']) == 26
            assert float(bar['width']) > 0
            ratios.append(float(bar['width']) / b)
        else:
            assert not bars and len(zeros) == 1 and zeros[0]['fill'] == color, g
        if ranged:
            band = next(s for s in g['shapes'] if s.get('data-kind') == 'range-band')
            marker = next(s for s in g['shapes'] if s.get('data-kind') == 'range')
            caps = [s for s in g['shapes'] if s.get('data-kind') == 'range-endpoint']
            assert len(caps) == 2 and band['fill'] == '#ffffff' and band['fill-opacity'] == '0.4'
            x1, x2 = float(marker['x1']), float(marker['x2'])
            assert float(band['x']) == x1 and abs(float(band['width']) - (x2 - x1)) < 1e-8
            assert [float(c['x1']) for c in caps] == [x1, x2]
            assert all(float(c['y2']) - float(c['y1']) == 24 for c in caps)
            if b > 0:
                baseline = float(bar['x'])
                unit = float(bar['width']) / b
                assert abs(x1 - baseline - a * unit) < 1e-8
                assert abs(x2 - baseline - b * unit) < 1e-8
            assert '–' in g['label'], g
    if ratios:
        assert max(ratios) - min(ratios) < 1e-7, ratios
    assert page.locator('#chart-canvas svg').evaluate("""s=>[...s.querySelectorAll('text')].every(t=>{
      const b=t.getBoundingClientRect(),r=s.getBoundingClientRect();
      return b.left>=r.left-1&&b.right<=r.right+1&&b.top>=r.top-1&&b.bottom<=r.bottom+1;
    })"""), 'SVG labels clipped'
    return actual


def download(page, selector, path):
    with page.expect_download() as info:
        page.locator(selector).click()
    info.value.save_as(path)
    return path


def exports(page, out, name, actual):
    svg = download(page, '#chart-svg', out / (name + '.svg'))
    png = download(page, '#chart-png', out / (name + '.png'))
    root = ET.parse(svg).getroot()
    assert len(root.findall('.//s:g[@data-measurement]', NS)) == len(actual)
    metadata = json.loads(root.find('s:metadata', NS).text)
    assert {r['id'] for r in metadata['measurements']} == {g['id'] for g in actual}
    raw = png.read_bytes()
    assert raw[:8] == b'\x89PNG\r\n\x1a\n'
    assert int.from_bytes(raw[16:20], 'big') == int(root.attrib['width']) * 2
    assert int.from_bytes(raw[20:24], 'big') == int(root.attrib['height']) * 2
    # Sample inside every nonzero downloaded bar, not the grid or range marker.
    samples = []
    for g in actual:
        bar = next((s for s in g['shapes'] if s.get('data-kind') in ('bar', 'scalar')), None)
        if bar and float(bar['width']) > 5:
            x = float(bar['x']) + float(bar['width']) * 0.25
            if g['range'] and g['min'] > 0:
                x = float(bar['x']) + float(bar['width']) * g['min'] / g['max'] * 0.5
            samples.append([round(x * 2), round((float(bar['y']) + 4) * 2),
                            [239, 138, 44, 255] if g['highlight'] else [85, 155, 212, 255]])
    result = page.evaluate("""async ({image,samples})=>{const i=new Image();i.src='data:image/png;base64,'+image;
      await i.decode();const c=document.createElement('canvas');c.width=i.width;c.height=i.height;
      const x=c.getContext('2d');x.drawImage(i,0,0);
      return samples.map(([a,b,want])=>({got:[...x.getImageData(a,b,1,1).data],want}));} """,
                           {'image': base64.b64encode(raw).decode(), 'samples': samples})
    assert all(s['got'] == s['want'] for s in result), result


def mobile(page, out, name):
    evidence = []
    for width in [320, 375, 390, 430, 768, 1440]:
        page.set_viewport_size({'width': width, 'height': 1000})
        canvas = page.locator('#chart-canvas')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert canvas.get_attribute('aria-describedby') == 'chart-scroll-hint'
        assert canvas.evaluate("e=>getComputedStyle(e).overflowX==='auto'")
        # Every value and heading must be fully reachable within the scroll region.
        reach = canvas.evaluate("""e=>{e.scrollLeft=0;const r=e.getBoundingClientRect();
          const texts=[...e.querySelectorAll('[data-kind=value],[data-role=chart-heading]')];
          return {client:e.clientWidth,scroll:e.scrollWidth,
            reachable:texts.every(t=>{const b=t.getBoundingClientRect();
              return b.left-r.left>=-1&&b.right-r.left<=e.scrollWidth+1;})};} """)
        # Headings may span several mobile viewports. They are fully present in
        # the scrollable SVG, while each essential numeric value fits one viewport.
        assert reach['reachable']
        assert canvas.locator('[data-kind=value]').evaluate_all("""es=>es.every(t=>{
          const e=document.querySelector('#chart-canvas'),b=t.getBoundingClientRect(),r=e.getBoundingClientRect();
          return b.left-r.left>=-1&&b.right-r.left<=e.scrollWidth+1&&b.width<=e.clientWidth+1;})""")
        canvas.scroll_into_view_if_needed()
        canvas.focus()
        page.keyboard.press('ArrowRight')
        if reach['scroll'] > reach['client']:
            page.wait_for_function("()=>document.querySelector('#chart-canvas').scrollLeft>0")
        canvas.evaluate('e=>e.scrollLeft=e.scrollWidth')
        actual = canvas.evaluate('e=>({left:e.scrollLeft,max:e.scrollWidth-e.clientWidth})')
        assert abs(actual['left'] - actual['max']) <= 1
        page.screenshot(path=str(out / (name + '-' + str(width) + '-right.png')))
        canvas.evaluate('e=>e.scrollLeft=0')
        page.screenshot(path=str(out / (name + '-' + str(width) + '-left.png')))
        # Exercise actual visibility, not just theoretical scrollWidth. Bring
        # every numeric label into view and check both clipping ancestors.
        def reveal(label):
            # Explicit user-reachable pan positions avoid WebKit's SVG
            # scrollIntoView rounding/ancestor behavior in the test driver.
            label.evaluate("""t=>{const b=t.getBoundingClientRect(),
              e=document.querySelector('#chart-canvas'),r=e.getBoundingClientRect();
              e.scrollLeft+=(b.left+b.right-r.left-r.right)/2;
              window.scrollTo({top:scrollY+b.top-250,behavior:'instant'});
            }""")
            bounds = label.evaluate("""t=>{const b=t.getBoundingClientRect(),
              r=document.querySelector('#chart-canvas').getBoundingClientRect();
              return {left:b.left,right:b.right,top:b.top,bottom:b.bottom,
                clipLeft:r.left,clipRight:r.right,height:innerHeight};
            }""")
            assert bounds['left'] >= bounds['clipLeft'] - 1 and bounds['right'] <= bounds['clipRight'] + 1, bounds
            assert bounds['top'] >= 0 and bounds['bottom'] <= bounds['height'], bounds
        for label in canvas.locator('[data-kind=value]').all():
            reveal(label)
        a329s = canvas.locator('[data-measurement="rcg530-640820-1"] [data-kind=value]')
        reveal(a329s)
        page.screenshot(path=str(out / (name + '-' + str(width) + '-a329s-visible.png')))
        if width == 375 and page.context.browser.browser_type.name == 'chromium':
            # Native touch events, not JS scroll assignment, prove that a
            # horizontal swipe can pan the chart without moving the page.
            canvas.evaluate('e=>e.scrollLeft=0')
            clip = canvas.bounding_box()
            cdp = page.context.new_cdp_session(page)
            cdp.send('Emulation.setTouchEmulationEnabled', {'enabled': True})
            start, end = clip['x'] + clip['width'] - 15, clip['x'] + 15
            cdp.send('Input.dispatchTouchEvent', {'type': 'touchStart', 'touchPoints': [{'x': start, 'y': 255}]})
            for step in range(1, 11):
                cdp.send('Input.dispatchTouchEvent', {'type': 'touchMove', 'touchPoints': [{'x': start + (end - start) * step / 10, 'y': 255}]})
                page.wait_for_timeout(16)
            cdp.send('Input.dispatchTouchEvent', {'type': 'touchEnd', 'touchPoints': []})
            page.wait_for_function("()=>document.querySelector('#chart-canvas').scrollLeft>0")
            actual['nativeTouchScroll'] = canvas.evaluate('e=>e.scrollLeft')
            cdp.send('Emulation.setTouchEmulationEnabled', {'enabled': False})
            cdp.detach()
        evidence.append(dict(width=width, **reach, **actual))
    return evidence


def main():
    args = argparse.ArgumentParser()
    args.add_argument('--url')
    args.add_argument('--browser', choices=['chromium', 'webkit'], default='chromium')
    args = args.parse_args()
    data = json.loads((ROOT / 'docs/data/parking-measurements.json').read_text())
    rows = data['measurements']
    server = None
    if not args.url:
        class Handler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, *args):
                pass
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Handler, directory=str(ROOT / 'docs')))
        threading.Thread(target=server.serve_forever, daemon=True).start()
    url = args.url or ('http://127.0.0.1:%s/parking-charts.html' % server.server_port)
    out = Path(tempfile.mkdtemp(prefix='parking-filled-bars-', dir=os.environ['TMPDIR']))
    report = {'url': url, 'browser': args.browser, 'metrics': {}, 'mobile': {}}
    with sync_playwright() as p:
        browser = (p.chromium.launch(channel='chrome') if args.browser == 'chromium' else p.webkit.launch())
        page = browser.new_page(accept_downloads=True, viewport={'width': 1440, 'height': 1000})
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        for metric in KEYS:
            candidates = [r for r in rows if interval(r, metric) is not None and
                          (metric != 'current' or isinstance(r.get('voltage_v'), (int, float)) and r['voltage_v'] > 0)]
            groups = {}
            for r in candidates:
                groups.setdefault(r.get('voltage_v') if metric == 'current' else 'all', []).append(r)
            for group in groups.values():
                for start in range(0, len(group), 30):
                    batch = group[start:start + 30]
                    page.goto(url + '?' + query([r['id'] for r in batch], metric)); ready(page)
                    geometry(page, {r['id']: interval(r, metric) for r in batch})
            ranged = next(r for r in candidates if interval(r, metric)[2])
            scalar = next(r for r in candidates if not interval(r, metric)[2] and
                          (metric != 'current' or r.get('voltage_v') == ranged.get('voltage_v')))
            batch = [ranged, scalar]
            highlight = page.evaluate('r=>ParkingUI.modelLabel(r)', ranged)
            page.goto(url + '?' + query([r['id'] for r in batch], metric, highlight=highlight)); ready(page)
            actual = geometry(page, {r['id']: interval(r, metric) for r in batch})
            exports(page, out, metric + '-range-scalar', actual)
            report['metrics'][metric] = {'rows': len(candidates), 'ranges': sum(interval(r, metric)[2] for r in candidates)}
        wake = [r for r in rows if interval(r, 'wake') and r['category'] in ('impact-sleep', 'radar') and r['state'] == 'monitoring']
        page.goto(url + '?' + query([r['id'] for r in wake], 'wake')); ready(page)
        actual = geometry(page, {r['id']: interval(r, 'wake') for r in wake})
        a329s_id = next(r['id'] for r in wake if r['model'] == 'A329S')
        a329s = next(g for g in actual if g['id'] == a329s_id)
        assert (a329s['min'], a329s['max']) == (2.75, 3)
        report['a329s'] = a329s
        exports(page, out, 'a329s-wake-comparison', actual)
        report['mobile']['auto'] = mobile(page, out, 'wake-auto')
        page.locator('#chart-format').select_option('video')
        assert page.locator('#chart-canvas svg').get_attribute('width') == '1920'
        assert page.locator('#chart-canvas svg').get_attribute('height') == '1080'
        report['mobile']['video'] = mobile(page, out, 'wake-video')
        # Browser-only fixtures exercise all accepted and rejected interval shapes
        # across every metric. These values never enter canonical data or git.
        for metric, key in KEYS.items():
            fixture = json.loads(json.dumps(data))
            cases = [(0, None, None), (0.001, None, None), (None, 0, 0),
                     (None, 2, 2), (None, 0, 3), (1, 1, None),
                     (1, -1, 3), (1, 3, 1), (1, None, 3), (None, 0.001, 0.002)]
            batch = fixture['measurements'][:len(cases)]
            for r, (v, lo, hi) in zip(batch, cases):
                r.update({key: v, key + '_min': lo, key + '_max': hi,
                          'reported_startup_method': 'Impact detection to start of recording',
                          'voltage_v': 12.6, 'disabled': False, 'measurement_statistic': None})
            page.route('**/data/parking-measurements.json', lambda route: route.fulfill(json=fixture))
            page.goto(url + '?' + query([r['id'] for r in batch], metric)); ready(page)
            expected = {r['id']: interval(r, metric) for r in batch if interval(r, metric)}
            assert len(expected) == 6
            geometry(page, expected)
            page.unroute('**/data/parking-measurements.json')
        assert not errors, errors
        report['page_errors'] = errors
        (out / 'verification.json').write_text(json.dumps(report, indent=2))
        browser.close()
    if server:
        server.shutdown()
    print(json.dumps(report, indent=2))
    print('PASS: filled bars, exact range geometry, every eligible metric row, fixtures, PNG/SVG exports, and mobile reachability')
    print('Artifacts: ' + str(out))


if __name__ == '__main__':
    main()
