#!/usr/bin/env python3
"""Real Chrome design acceptance for the shared parking/bitrate chart conventions."""
import json
from pathlib import Path
import struct
import sys
from urllib.parse import parse_qs, urlsplit
import xml.etree.ElementTree as ET
from playwright.sync_api import sync_playwright

BASE = (sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8896/').rstrip('/') + '/'
OUT = Path.home() / '.hermes/cache/scratch/bitrate-design-tests'
OUT.mkdir(parents=True, exist_ok=True)
NS = {'s': 'http://www.w3.org/2000/svg'}
BOUNDS = """() => [...document.querySelectorAll('#chart svg text')].every(t=>{
 const b=t.getBoundingClientRect(),s=document.querySelector('#chart svg').getBoundingClientRect();
 return b.left>=s.left-1&&b.right<=s.right+1&&b.top>=s.top-1&&b.bottom<=s.bottom+1;
})"""

def download(page, ext, name, video=True):
    with page.expect_download() as info:
        page.locator('#' + ext).click()
    expected = 'front-camera-bitrates-4k30' + ('-16x9' if video else '') + '.' + ext
    assert info.value.suggested_filename == expected
    target = OUT / (name + '.' + ext)
    info.value.save_as(target)
    if ext == 'png':
        raw = target.read_bytes()
        assert raw[:8] == b'\x89PNG\r\n\x1a\n'
        if video:
            assert struct.unpack('>II', raw[16:24]) == (3840, 2160)
    else:
        root = ET.parse(target).getroot()
        if video:
            assert (root.attrib['width'], root.attrib['height']) == ('1920', '1080')
        background = root.find('s:rect', NS)
        metadata = root.find('s:metadata', NS)
        assert background is not None and background.attrib['fill'] == '#ffffff'
        assert metadata is not None and metadata.text and json.loads(metadata.text)
    return target

with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True)
    page = browser.new_page(viewport={'width': 1400, 'height': 1000}, accept_downloads=True)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(BASE + 'bitrate-charts.html')
    page.wait_for_selector('#chart svg')
    assert page.locator('#choices input[data-model]:checked').count() == 12
    assert page.locator('#t340').count() == 0
    assert page.locator('#highlight').input_value() == ''
    assert page.locator('#chart g[data-highlight="true"]').count() == 0
    assert page.locator('#chart rect[fill="#559bd4"]').count() > 0
    assert 'Prototype' in page.locator('#chart').inner_text()
    assert '41.0 – 53.3 Mbps' in page.locator('#chart').inner_text()
    assert page.evaluate(BOUNDS)
    for ext in ['svg', 'png']:
        download(page, ext, 'default')
    page.evaluate('window.scrollTo(0,0)')
    page.screenshot(path=str(OUT / 'desktop.png'), full_page=True)
    page.locator('#chart').screenshot(path=str(OUT / 'default-preview.png'))
    page.locator('#highlight').select_option('viofo-a329s')
    assert page.locator('#chart g[data-highlight="true"]').count() == 1
    assert page.locator('#chart g[data-variant="viofo-a329s"] rect').get_attribute('fill') == '#ef8a2c'
    texts = {'title': 'Custom <title> & comparison', 'subtitle': 'Custom <subtitle> & quality',
             'xLabel': 'Video <bitrate> & Mbps', 'yLabel': 'Tested <cameras>'}
    for key, value in texts.items():
        page.locator('#' + key).fill(value)
    page.wait_for_function("new URL(location.href).searchParams.get('yLabel')==='Tested <cameras>'")
    page.reload()
    page.wait_for_selector('#chart svg')
    for key, value in texts.items():
        assert page.locator('#' + key).input_value() == value
        assert value in page.locator('#chart').inner_text()
    assert page.locator('#highlight').input_value() == 'viofo-a329s'
    assert page.locator('#chart script').count() == 0
    for ext in ['svg', 'png']:
        download(page, ext, 'custom-highlight')
    root = ET.parse(OUT / 'custom-highlight.svg').getroot()
    for value in texts.values():
        assert value in ''.join(root.itertext())
    page.locator('#highlight').select_option('')
    for key in texts:
        page.locator('#' + key).fill('')
    page.wait_for_function("new URL(location.href).searchParams.get('yLabel')===''")
    page.reload(); page.wait_for_selector('#chart svg')
    assert all(page.locator('#' + key).input_value() == '' for key in texts)
    assert page.locator('#chart [data-role="chart-heading"]').count() == 0
    assert page.locator('#chart [data-role="chart-axis"]').count() == 0
    page.goto(BASE + 'bitrate-charts.html'); page.wait_for_selector('#chart svg')
    page.locator('#search').fill('T340')
    assert page.locator('.camera-choice:visible').count() == 1
    page.locator('#clear').click()
    assert page.locator('#chart svg').count() == 0 and page.locator('#png').is_disabled()
    page.locator('input[data-model="viofo-t340"]').check()
    card = page.locator('.camera-choice[data-model="viofo-t340"]')
    card.locator('summary').click()
    card.locator('input[data-variant="t340-a"]').check()
    card.locator('input[data-variant="t340-b"]').check()
    card.locator('input[data-variant="viofo-t340:3ch"]').check()
    page.locator('#highlight').select_option('viofo-t340')
    assert page.locator('#chart g[data-highlight="true"]').count() == 4
    page.locator('#sort').select_option('low')
    page.reload(); page.wait_for_selector('#chart svg')
    assert set(parse_qs(urlsplit(page.url).query)['camera']) == {'viofo-t340', 't340-a', 't340-b', 'viofo-t340:3ch'}
    assert page.locator('#chart g[data-variant]').count() == 4
    for key in texts:
        page.locator('#' + key).fill('Long unbroken ' + 'W' * 100)
    assert page.evaluate(BOUNDS)
    page.locator('#format').select_option('auto')
    page.reload(); page.wait_for_selector('#chart svg')
    assert page.locator('#format').input_value() == 'auto'
    assert page.locator('#chart svg').get_attribute('width') == '1200'
    assert page.evaluate(BOUNDS)
    for ext in ['svg', 'png']:
        download(page, ext, 'auto-long-labels', video=False)
    page.goto(BASE + 'bitrate-charts.html'); page.wait_for_selector('#chart svg')
    page.locator('#all').click()
    assert page.locator('#chart g[data-variant]').count() == page.locator('#choices input[data-model]').count()
    assert page.evaluate(BOUNDS)
    page.locator('#defaults').click()
    for width in [320, 390, 760, 1400]:
        page.set_viewport_size({'width': width, 'height': 1000})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.evaluate('window.scrollTo(0,0)')
        page.screenshot(path=str(OUT / f'width-{width}.png'), full_page=True)
        if width == 390:
            page.wait_for_function("document.querySelector('#chart').scrollLeft>0")
            page.locator('#chart').scroll_into_view_if_needed()
            page.screenshot(path=str(OUT / 'mobile-chart.png'))
            page.locator('#chart').evaluate('(node)=>node.scrollLeft=node.scrollWidth')
            assert page.locator('#chart').evaluate('(node)=>node.scrollLeft+node.clientWidth>=node.scrollWidth-1')
            page.screenshot(path=str(OUT / 'mobile-chart-right.png'))
            setup=page.locator('.camera-choice[data-model="viofo-t340"]')
            setup.locator('summary').click()
            setup.scroll_into_view_if_needed()
            page.screenshot(path=str(OUT / 'mobile-setups.png'))
    page.goto(BASE + 'bitrate-charts.html?selection=1&camera=__proto__&camera=t340-a&camera=t340-a&highlight=toString&sort=evil')
    page.wait_for_selector('#chart svg')
    assert page.locator('#chart g[data-variant]').count() == 1
    assert page.locator('#highlight').input_value() == ''
    assert page.locator('#sort').input_value() == 'high'
    # Fault injection: an invalid channel count must fail clearly, not become 0CH.
    malformed = page.request.get(BASE + 'data/bitrate-variants.json').json()
    malformed[0]['channels'] = 0
    page.route('**/data/bitrate-variants.json', lambda route: route.fulfill(json=malformed))
    page.goto(BASE + 'bitrate-charts.html')
    page.wait_for_function("document.querySelector('#status').textContent.includes('Invalid tested channel count')")
    assert page.locator('#chart svg').count() == 0
    assert page.locator('#png').is_disabled()
    page.unroute('**/data/bitrate-variants.json')
    # Capture the approved parking reference with the same viewport and actual data.
    ref = 'parking-charts.html?selection=1&group=low-power&family=low-power&condition=monitoring&metric=delay&sort=desc&highlight=Viofo+T340&title=Low+Power+Parking+Mode+Recording+Delay+Comparison&details=0&format=auto&subtitle=Wakeup+Times+to+Start+Recording+After+an+Impact+%28Lower+is+Better%29'
    ref += ''.join('&id=vortex-sheet-row-' + str(i) for i in [4, 6, 9, 15, 21, 11, 17])
    page.goto(BASE + ref); page.wait_for_selector('#chart-canvas svg')
    page.evaluate('window.scrollTo(0,0)')
    page.screenshot(path=str(OUT / 'parking-reference-desktop.png'), full_page=True)
    page.locator('#chart-canvas').screenshot(path=str(OUT / 'parking-reference-preview.png'))
    page.set_viewport_size({'width': 390, 'height': 1000})
    page.evaluate('window.scrollTo(0,0)')
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    page.screenshot(path=str(OUT / 'parking-reference-mobile.png'), full_page=True)
    assert not errors, errors
    browser.close()
print('Passed: shared parking design, 12 defaults, no T340 button, optional model highlight, escaped/blank/custom labels, reload, all variants, sorting, search, clear, Auto height, default/custom/Auto PNG+SVG downloads, bounds and responsive layouts.')
print('Artifacts: ' + str(OUT))
