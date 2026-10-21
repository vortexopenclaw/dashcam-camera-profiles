"""Check A119M Pro High/AED scan import without mixing presets or clip types."""
import json
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlencode
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
base=sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:8896/'
key='viofo-a119m-pro'
e=json.loads((ROOT/'docs/data/a119m-pro-high-1.2_20260817.json').read_text())
profile=json.loads((ROOT/'profiles/viofo-a119m-pro.json').read_text())
assert e['ownerAssertions']['firmware']=='1.2_20260817'
assert e['ownerAssertions']['quality']=='high' and e['ownerAssertions']['parkingModeLabel']=='Auto Event Detection'
assert e['ownerAssertions']['channelCount']==1
assert len(e['samples'])==5 and e['inventory']['mediaCount']==6
assert all(s['channel']==s['mode']=='unknown' for s in e['samples'])
assert sum(f['fileCount'] for f in e['inventory']['folders'])==e['inventory']['fileCount']
long=[e['samples'][i] for i in e['review']['drivingSampleIndices']]
assert len(long)==2 and all(s['durationSeconds']>=60 and (s['width'],s['height'])==(3840,2160) for s in long)
assert all(s['codec']=='h264' for s in e['samples'])
park=[e['samples'][i] for i in e['review']['parkingSampleIndices']]
assert len(park)==2 and all((s['width'],s['height'],s['durationSeconds'])==(2560,1440,45) for s in park)
rows=json.loads((ROOT/'docs/data/bitrate-variants.json').read_text());r=next(r for r in rows if r['key']==key)
assert r['quality']=='high' and r['default'] and r['firmware']=='1.2_20260817'
assert r['lowMbps']==min(s['bitrateKbps']/1000 for s in long)
assert r['highMbps']==max(s['bitrateKbps']/1000 for s in long)
legacy=next(r for r in rows if r['key']=='viofo-a119m-pro:archive');assert not legacy['default'] and legacy['status']=='superseded' and legacy['highMbps']<40
assert next(r for r in json.loads((ROOT/'docs/data/4k30-comparison.json').read_text()) if r['id']=='viofo-a119m-pro')['highMbps']==r['highMbps']
assert profile['video_samples'][0]['mode']=='driving'
assert 'firmware 1.2_20260817' in profile['video_samples'][0]['recording_configuration']
assert all('Historical older-firmware' in s['settings_note'] for s in profile['video_samples'][4:])
assert {f['path'] for f in profile['recording']['parking_folders']}=={'DCIM/Parking','DCIM/Parking/RO'}
assert any(s['mode']=='driving (short clip)' for s in profile['video_samples'])
assert profile['filename_patterns'][0]['default_channel'] is None
out=Path('/Users/openclaw/.hermes/cache/scratch/a119m-pro-high-tests');out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True);page=browser.new_page(accept_downloads=True)
    params=[('selection','1'),('camera',key),('format','video'),('subtitle','Front Camera Bitrates at Maximum Quality')]
    page.goto(base+'bitrate-charts.html?'+urlencode(params));page.wait_for_selector('#chart svg')
    assert page.locator('#chart g[data-variant]').count()==1
    group=page.locator('#chart g[data-variant]')
    assert group.get_attribute('data-variant')==key
    text=' '.join(group.locator('text').all_text_contents())
    assert 'High' in text and 'H.264' in text and '61.4 – 61.5 Mbps' in text
    assert page.locator('#subtitle').input_value()=='Front Camera Bitrates at Selected Quality Settings'
    assert page.locator('#chart rect[data-kind=bar]').count()==1
    assert group.locator('[data-kind=model-label]').all_text_contents()==['Viofo A119M Pro · 1CH']
    assert group.locator('[data-kind=configuration-label]').all_text_contents()==['High Bitrate · H.264']
    assert float(group.locator('[data-kind=configuration-label]').get_attribute('font-size'))<float(group.locator('[data-kind=model-label]').get_attribute('font-size'))
    axis=page.locator('[data-role=chart-y-axis]');assert axis.count()==1 and axis.text_content()=='Dash Cameras'
    svgbox=page.locator('#chart svg').bounding_box();axisbox=axis.bounding_box()
    assert axisbox['x']>=svgbox['x'] and axisbox['y']>=svgbox['y']
    assert axisbox['y']+axisbox['height']<=svgbox['y']+svgbox['height']
    old_share=base+'bitrate-charts.html?'+urlencode([('selection','1'),('camera','viofo-a119m-pro:high-fw1.2_20260817')])
    page.goto(old_share);page.wait_for_selector('#chart svg')
    assert page.locator('#chart g[data-variant]').get_attribute('data-variant')==key

    page.reload();page.wait_for_selector('#chart svg')
    assert group.get_attribute('data-variant')==key
    for ext in ['svg','png']:
        with page.expect_download() as d:page.locator('#'+ext).click()
        f=out/('a119m-pro-high.'+ext);d.value.save_as(f)
        if ext=='svg':
            root=ET.parse(f).getroot();metadata=root.find('{http://www.w3.org/2000/svg}metadata');assert metadata is not None and metadata.text
            values=json.loads(metadata.text);assert len(values)==1 and values[0]['firmware']=='1.2_20260817' and values[0]['quality']=='high'
    page.locator('#subtitle').fill('My custom quality comparison');page.reload();page.wait_for_selector('#chart svg')
    assert page.locator('#subtitle').input_value()=='My custom quality comparison'
    page.locator('#defaults').click()
    card=page.locator('.camera-choice[data-model="viofo-a119m-pro"]')
    assert card.locator('input[data-variant="viofo-a119m-pro"]').is_checked()
    assert not card.locator('input[data-variant="viofo-a119m-pro:archive"]').is_checked()
    assert page.locator('#chart g[data-variant="viofo-a119m-pro"]').count()==1
    for layout in ['auto','video']:
        page.goto(base+'bitrate-charts.html?'+urlencode([('selection','1'),('camera',key),('format',layout)]));page.wait_for_selector('#chart svg')
        assert page.locator('[data-role=chart-y-axis]').all_text_contents()==['Dash Cameras']
        assert page.locator('[data-kind=model-label]').all_text_contents()==['Viofo A119M Pro · 1CH']
        assert page.locator('[data-kind=configuration-label]').all_text_contents()==['High Bitrate · H.264']
    page.goto(base+'bitrate-charts.html?'+urlencode([('selection','1'),('camera','viofo-a119m-pro:archive')]));page.wait_for_selector('#chart svg')
    assert page.locator('[data-kind=configuration-label]').all_text_contents()==['Historical firmware · H.264']
    assert page.locator('[data-kind=value]').text_content()=='36.9 Mbps'
    assert page.locator('#subtitle').input_value()=='Front Camera Bitrates at Selected Quality Settings'
    browser.close()
print('Passed: source-exact High/AED firmware measurements, separate driving/parking/short clips, preserved native unknown hints, old default/history, reviewed folder layout, High-labeled shared chart and actual PNG/SVG exports, and truthful/custom subtitles.')
print('Artifacts:',out)
