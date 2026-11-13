#!/usr/bin/env python3
"""Real desktop/mobile acceptance of the Z100 attribution and disclosure layout."""
import argparse
import functools
import http.server
import json
from pathlib import Path
import threading
from playwright.sync_api import sync_playwright

R = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--url', help='Published site base; default serves local docs')
parser.add_argument('--artifacts', type=Path, help='Private screenshot output directory')
a = parser.parse_args()
server = None
if a.url:
    base = a.url.rstrip('/')+'/'
else:
    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Handler, directory=str(R/'docs')))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}/'
if a.artifacts:
    a.artifacts.mkdir(parents=True, exist_ok=True)
results = []
try:
    with sync_playwright() as pw:
        for engine in ['chromium', 'webkit']:
            browser = getattr(pw, engine).launch(**({'channel':'chrome'} if engine == 'chromium' else {}), headless=True)
            for name, viewport in [('desktop', {'width':1440, 'height':1000}), ('mobile', {'width':390, 'height':844})]:
                page = browser.new_page(viewport=viewport, is_mobile=name == 'mobile', device_scale_factor=1)
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                response = page.goto(base+'#camera=ddpai-z100-master', wait_until='networkidle')
                assert response.ok
                page.wait_for_selector('.detail-title')
                assert page.locator('.detail-title').inner_text() == 'Z100 Master'
                attribution = page.locator('.recording-attribution')
                assert attribution.count() == 1
                assert attribution.inner_text() == 'All recordings: Vortex Radar’s test unit.'
                assert attribution.is_visible()
                details = page.locator('details.technical-details')
                assert details.count() == 1 and details.get_attribute('open') is None
                assert page.locator('.video-spec-table').count() == 6
                assert page.locator('.video-spec-table tbody tr').count() == 14
                attribution.scroll_into_view_if_needed()
                geometry = page.evaluate('''() => {
                    const a = document.querySelector('.recording-attribution').getBoundingClientRect();
                    const h = document.querySelector('#video-specs-title').getBoundingClientRect();
                    return {gap:a.top-h.bottom,left:a.left,right:a.right,bottom:a.bottom,top:a.top,width:innerWidth,height:innerHeight,overflow:document.documentElement.scrollWidth-innerWidth};
                }''')
                assert 0 <= geometry['gap'] < 65, geometry
                assert 0 <= geometry['left'] < geometry['right'] <= geometry['width'], geometry
                assert 0 <= geometry['top'] < geometry['bottom'] <= geometry['height'], geometry
                assert geometry['overflow'] <= 1, geometry
                if a.artifacts:
                    page.screenshot(path=str(a.artifacts/f'{engine}-{name}-attribution.png'))
                summary = details.locator('summary').first
                summary.focus()
                page.keyboard.press('Enter')
                assert details.get_attribute('open') is not None
                text = page.locator('body').inner_text()
                assert text.count('All recordings: Vortex Radar’s test unit.') == 1
                assert 'anonymous' not in text.lower() and 'unattributed' not in text.lower()
                assert 'other historical attribution' not in text.lower()
                assert '401 videos' in text.lower() and 'firmware' in text.lower()
                for suffix in ['ddpai-z100-master-evidence.json', 'ddpai-z100-master-3ch-evidence.json']:
                    assert page.locator(f'a[href$="/{suffix}"]').count() >= 1
                page.keyboard.press('Enter')
                assert details.get_attribute('open') is None
                assert not errors, errors
                results.append({'engine':engine, 'viewport':name, 'attribution_count':1, 'tables':6, 'rows':14, 'details_initially_collapsed':True, 'keyboard_toggle':True, 'geometry':geometry})
                page.close()
            browser.close()
finally:
    if server:
        server.shutdown()
print(json.dumps({'base':base, 'checks':results}, indent=2))
