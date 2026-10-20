"""Exercise real codec filtering, retained selections, labels, and exports."""
import json
import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import parse_qs,urlsplit
from playwright.sync_api import sync_playwright

base=sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:8896/'
out=Path('/Users/openclaw/.hermes/cache/scratch/bitrate-codec-tests');out.mkdir(parents=True,exist_ok=True)
NS={'s':'http://www.w3.org/2000/svg'}
def codec(row):
    raw=row['codec'].lower()
    if '265' in raw or 'hevc' in raw:return 'h265'
    if '264' in raw or 'avc' in raw:return 'h264'
    raise AssertionError(row)
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page(accept_downloads=True,viewport={'width':1400,'height':1000})
    errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto(base+'bitrate-charts.html');page.wait_for_selector('#chart svg')
    rows=page.request.get(base+'data/bitrate-variants.json').json();bykey={r['key']:r for r in rows}
    chosen=lambda:set(parse_qs(urlsplit(page.url).query).get('camera',[]))
    shown=lambda:set(page.locator('#chart g[data-variant]').evaluate_all('nodes=>nodes.map(n=>n.dataset.variant)'))
    defaults=chosen();assert len(defaults)==12
    assert page.locator('#codec').input_value()=='all'
    assert bykey['blackvue-elite-10']['codec']=='H.265'
    page.locator('#highlight').select_option('viofo-t340')
    for selected_codec in ['h264','h265']:
        page.locator('#codec').select_option(selected_codec)
        expected={k for k in defaults if codec(bykey[k])==selected_codec}
        assert shown()==expected,(selected_codec,shown(),expected)
        assert chosen()==defaults
        assert page.locator('#highlight').input_value()=='viofo-t340'
        label='H.264' if selected_codec=='h264' else 'H.265'
        assert all(label in text for text in page.locator('#chart g[data-variant]').all_text_contents())
        assert page.locator('#chart rect[data-kind=bar]').count()==len(expected)
        visible_models=set(page.locator('.camera-choice:visible').evaluate_all('nodes=>nodes.map(n=>n.dataset.model)'))
        assert visible_models=={r['id'] for r in rows if codec(r)==selected_codec}
        page.reload();page.wait_for_selector('#chart svg')
        assert page.locator('#codec').input_value()==selected_codec and chosen()==defaults and shown()==expected
        for extension in ['svg','png']:
            with page.expect_download() as d:page.locator('#'+extension).click()
            assert d.value.suggested_filename==f'front-camera-bitrates-4k30-{selected_codec}-16x9.{extension}'
            file=out/f'{selected_codec}.{extension}';d.value.save_as(file)
            if extension=='svg':
                root=ET.parse(file).getroot();metadata=root.find('s:metadata',NS)
                assert metadata is not None and metadata.text is not None
                export=json.loads(metadata.text)
                assert {r['key'] for r in export}==expected
                assert all(codec(r)==selected_codec for r in export)
                assert label in ''.join(root.itertext())
                assert len(root.findall('.//s:rect[@data-kind="bar"]',NS))==len(expected)
            else:assert struct.unpack('>II',file.read_bytes()[16:24])==(3840,2160)
        page.locator('#search').fill('A329S')
        assert page.locator('.camera-choice:visible').count()==(1 if selected_codec=='h264' else 0)
        page.locator('#search').fill('')
    page.locator('#codec').select_option('all')
    assert shown()==defaults and chosen()==defaults
    assert page.locator('#chart g[data-highlight="true"]').count()==1
    page.locator('#codec').select_option('h265');page.locator('#all').click()
    assert all(codec(bykey[k])=='h265' for k in shown())
    assert {k for k in defaults if codec(bykey[k])=='h264'}<=chosen()
    page.locator('#defaults').click();assert page.locator('#codec').input_value()=='all' and chosen()==defaults
    page.goto(base+'bitrate-charts.html?selection=1&camera=viofo-t340&codec=h265')
    page.wait_for_function("document.querySelector('#status').textContent.includes('No selected cameras match')")
    assert chosen()=={'viofo-t340'} and not shown() and page.locator('#png').is_disabled()
    page.reload();page.wait_for_function("document.querySelector('#status').textContent.includes('No selected cameras match')")
    page.locator('#codec').select_option('all');assert shown()=={'viofo-t340'}
    page.goto(base+'bitrate-charts.html?codec=__proto__');page.wait_for_selector('#chart svg')
    assert page.locator('#codec').input_value()=='all'
    for width in [320,390,760,1400]:
        page.set_viewport_size({'width':width,'height':1000})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
    assert not errors,errors
    browser.close()
print('Passed: normalized H.264/H.265 labels, codec-filtered charts/pickers, retained selections and highlighting, shared reload, unchanged measured metadata, filtered PNG/SVG exports and filenames, empty filters, invalid values, and responsive controls.')
print('Artifacts:',out)
