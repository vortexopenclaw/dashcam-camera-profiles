#!/usr/bin/env python3
"""Real Chrome acceptance for default models, measured setups, and T340 units."""
import json
from pathlib import Path
import struct
import sys
from urllib.parse import parse_qs, urlsplit
import xml.etree.ElementTree as ET
from playwright.sync_api import sync_playwright
base=sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:8896/'
out=Path.home()/'.hermes/cache/scratch/bitrate-chart-tests';out.mkdir(parents=True,exist_ok=True)
defaults={'viofo-a329s','blackvue-elite-10','nextbase-622gw','viofo-t340','vueroid-s1-4k-infinite','viofo-a119m-pro','vantrue-e1-pro-s','viofo-a229-pro','vantrue-n4-pro-s','thinkware-arc-800','vantrue-e1-pro','thinkware-u3000-pro'}
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page(viewport={'width':1400,'height':1000},accept_downloads=True)
    errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto(base+'bitrate-charts.html');page.wait_for_selector('#chart svg')
    assert set(parse_qs(urlsplit(page.url).query)['camera'])==defaults
    assert page.locator('#choices input[data-model]:checked').count()==12
    assert '41.0 – 53.3' in page.locator('#chart').inner_text()
    assert page.locator('#chart g[data-variant="viofo-t340"]').count()==1
    assert page.locator('#chart g[data-variant="t340-a"]').count()==0
    assert 'Viofo A329S · 2CH' in page.locator('#chart').inner_text()
    assert 'Blackvue Elite 10 · 2CH' in page.locator('#chart').inner_text()
    assert 'Viofo A229 Pro · 3CH' in page.locator('#chart').inner_text()
    assert 'Viofo A119M Pro · 1CH' in page.locator('#chart').inner_text()
    assert not any(row['id']=='viofo-a229-pro' and row['channels']==2 for row in page.request.get(base+'data/bitrate-variants.json').json())
    assert 'Vantrue E1 Pro S' in page.locator('#chart').inner_text() and 'Prototype' in page.locator('#chart').inner_text()
    assert page.locator('#choices input[data-model="rove-r2-4k-pro"]').count()==0
    assert 'Rove R2-4K Pro' in page.locator('main > p.note').inner_text()
    variants=page.request.get(base+'data/bitrate-variants.json').json()
    assert all(row['id']!='rove-r2-4k-pro' for row in variants)
    assert len({row['key'] for row in variants})==len(variants)
    assert page.locator('#subtitle').input_value()=='Front Camera Bitrates at Maximum Quality'
    page.locator('#search').fill('A329S');assert page.locator('.camera-choice:visible').count()==1
    page.locator('#search').fill('')
    page.locator('#t340').click();assert page.locator('#chart g[data-variant]').count()==1
    card=page.locator('.camera-choice[data-model="viofo-t340"]');card.locator('summary').click()
    card.locator('input[data-variant="viofo-t340"]').uncheck()
    card.locator('input[data-variant="t340-a"]').check();card.locator('input[data-variant="t340-b"]').check()
    assert page.locator('#chart g[data-variant]').count()==2
    assert '53.3' in page.locator('#chart').inner_text() and '41.0' in page.locator('#chart').inner_text()
    page.locator('input[data-model="viofo-a329s"]').check();page.locator('#sort').select_option('low')
    custom='Custom <subtitle> & quality';page.locator('#subtitle').fill(custom)
    page.wait_for_function("new URL(location.href).searchParams.get('subtitle')==='Custom <subtitle> & quality'")
    page.reload();page.wait_for_selector('#chart svg')
    assert page.locator('#chart g[data-variant]').count()==3
    assert page.locator('#subtitle').input_value()==custom and page.locator('#sort').input_value()=='low'
    assert page.locator('#chart g[data-variant]').first.get_attribute('data-variant')=='t340-b'
    for ext in ['svg','png']:
        with page.expect_download() as info:page.locator('#'+ext).click()
        assert info.value.suggested_filename==f'front-camera-bitrates-4k30-16x9.{ext}'
        file=out/('selected.'+ext);info.value.save_as(file)
        if ext=='svg':
            root=ET.parse(file).getroot();metadata=root.find('{http://www.w3.org/2000/svg}metadata')
            assert metadata is not None and metadata.text
            records=json.loads(metadata.text)
            assert {row['key'] for row in records}=={'t340-a','t340-b','viofo-a329s'}
            units={row['key']:row for row in records if row['id']=='viofo-t340'}
            assert units['t340-a']['highMbps']>units['t340-b']['highMbps']
            assert custom in ''.join(root.itertext())
        else:
            raw=file.read_bytes();assert raw[:8]==b'\x89PNG\r\n\x1a\n'
            width,height=struct.unpack('>II',raw[16:24]);assert (width,height)==(3840,2160)
    page.locator('#t340').click()
    card=page.locator('.camera-choice[data-model="viofo-t340"]')
    if not card.locator('details').evaluate('node=>node.open'):card.locator('summary').click()
    card.locator('input[data-variant="viofo-t340:3ch"]').check()
    assert page.locator('#chart g[data-variant]').count()==2
    assert 'Viofo T340 · 3CH' in page.locator('#chart').inner_text()
    page.reload();page.wait_for_selector('#chart svg')
    assert set(parse_qs(urlsplit(page.url).query)['camera'])=={'viofo-t340','viofo-t340:3ch'}
    page.locator('#format').select_option('auto')
    page.reload();page.wait_for_selector('#chart svg')
    assert page.locator('#format').input_value()=='auto'
    assert page.locator('#chart svg').get_attribute('width')=='1120'
    page.locator('#format').select_option('video')
    assert page.locator('#chart svg').get_attribute('viewBox')=='0 0 1920 1080'
    page.locator('#all').click();models=page.locator('#choices input[data-model]').count()
    assert page.locator('#chart g[data-variant]').count()==models
    assert '60.0' in page.locator('#chart').inner_text()
    vue=page.locator('.camera-choice[data-model="vueroid-s1-4k-infinite"]');vue.locator('summary').click()
    vue.locator('input[data-variant="vueroid-s1-4k-infinite:archive"]').check()
    assert '44.3 – 48.0' in page.locator('#chart').inner_text()
    assert page.evaluate('''() => [...document.querySelectorAll('#chart svg text')].every(t=>{const b=t.getBoundingClientRect(),s=document.querySelector('#chart svg').getBoundingClientRect();return b.left>=s.left-1&&b.right<=s.right+1&&b.top>=s.top-1&&b.bottom<=s.bottom+1;})''')
    page.locator('#clear').click();assert page.locator('#chart svg').count()==0 and page.locator('#png').is_disabled()
    page.reload();page.wait_for_function("document.querySelector('#status').textContent.includes('Choose a camera')")
    assert page.locator('#choices input[data-model]:checked').count()==0
    page.locator('#defaults').click();assert set(parse_qs(urlsplit(page.url).query)['camera'])==defaults
    for width in [390,760,1400]:
        page.set_viewport_size({'width':width,'height':1000});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.screenshot(path=str(out/f'width-{width}.png'),full_page=True)
    page.goto(base+'bitrate-charts.html?selection=1&camera=__proto__&camera=t340-a&camera=t340-a&sort=evil');page.wait_for_selector('#chart svg')
    assert page.locator('#chart g[data-variant]').count()==1 and page.locator('#chart g[data-variant="t340-a"]').count()==1
    assert page.locator('#sort').input_value()=='high'
    assert not errors,errors
    browser.close()
print(f'Passed: {models} models, requested 12-model default, T340 range/individual units, channel labels, upscaled exclusion, legacy links, selection/search, sort, shared reload, PNG/SVG downloads, label bounds, clear, and mobile layout. Artifacts: {out}')
