"""Verify automatic parking copy, mode placement, and unnumbered timing notes."""
import json
import re
import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlencode,parse_qs,urlsplit
from playwright.sync_api import sync_playwright

base=sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:8896/'
out=Path('/Users/openclaw/.hermes/cache/scratch/parking-metric-copy-tests');out.mkdir(parents=True,exist_ok=True)
ids=['vortex-sheet-row-15','vortex-sheet-row-11','vortex-sheet-row-21','vortex-sheet-row-4','vortex-sheet-row-6','vortex-sheet-row-9','rcg530-600858-1','rcg530-664217-1']
def url(metric,details):
    title='Low Power Parking Mode Power Draw Comparison' if metric=='watts' else 'Low Power Parking Mode Recording Delay Comparison'
    params=[('selection','1'),('group','low-power'),('family','low-power'),('condition','monitoring'),('metric',metric),('sort','desc'),('highlight',''),('title',title),('details',str(details)),('format','auto'),('subtitle','Power Draw While Idle (Lower is Better)')]+[('id',id) for id in ids]
    return base+'parking-charts.html?'+urlencode(params)
NS={'s':'http://www.w3.org/2000/svg'}
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page(accept_downloads=True,viewport={'width':1400,'height':1000})
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(url('watts',0));page.wait_for_selector('#chart-canvas svg')
    assert page.locator('#chart-title').input_value()=='Low Power Parking Mode Power Draw Comparison'
    assert page.locator('#chart-subtitle').input_value()=='Power Draw While Idle (Lower is Better)'
    assert page.locator('#chart-mode-labels').is_checked()
    group=page.locator('#chart-canvas g[data-measurement="vortex-sheet-row-6"]')
    assert 'Low Power Impact Detection' in group.text_content()
    assert 'Collision Detection, Power Saving Mode' in ' '.join(page.locator('#chart-canvas g[data-measurement="vortex-sheet-row-21"] text').all_text_contents())
    selected_models=lambda:set(page.locator('#chart-model-picker input:checked').evaluate_all('nodes=>nodes.map(n=>n.dataset.model)'))
    original_models=selected_models()
    for metric in ['delay','wake','watts','current','delay']:
        page.locator('#chart-metric').select_option(metric)
        expected=page.evaluate('m=>window.ParkingCharts.automaticTitle({family:"low-power",metric:m})',metric)
        assert page.locator('#chart-title').input_value()==expected
        subtitle=page.locator('#chart-subtitle').input_value()
        if metric=='delay':assert subtitle=='How Quick the Dashcam Starts Recording After an Impact (Lower is Better)'
        if metric=='wake':assert subtitle=='Time from Impact to the First Recorded Frame (Lower is Better)'
        if metric=='watts':assert subtitle=='Power Draw While Idle (Lower is Better)'
        assert selected_models()==original_models
    # Load the exact stale power-subtitle timing link, not only metric changes.
    page.goto(url('delay',1));page.wait_for_selector('#chart-canvas svg')
    assert page.locator('#chart-title').input_value()=='Low Power Parking Mode Wakeup Times'
    assert page.locator('#chart-subtitle').input_value()=='How Quick the Dashcam Starts Recording After an Impact (Lower is Better)'
    assert not page.locator('#chart-mode-labels').is_checked()
    text=' '.join(page.locator('#chart-canvas svg > g text').all_text_contents())
    assert 'Low Power Impact Detection' in text and 'Collision Detection, Power Saving Mode' in text
    assert not re.search(r'\[\d+(?:,\s*\d+)*\]',text)
    assert 'Test voltage' not in text and not re.search(r'\b\d+(?:\.\d+)? V\b',text)
    assert 'Low Power Impact Detection' not in page.locator('#chart-canvas g[data-measurement="vortex-sheet-row-6"]').text_content()
    page.locator('#chart-mode-labels').check()
    assert 'Low Power Impact Detection' in page.locator('#chart-canvas g[data-measurement="vortex-sheet-row-6"]').text_content()
    page.reload();page.wait_for_selector('#chart-canvas svg');assert page.locator('#chart-mode-labels').is_checked()
    page.locator('#chart-mode-labels').uncheck()
    for metric,details,stem in [('watts',0,'power'),('delay',1,'wakeup')]:
        page.goto(url(metric,details));page.wait_for_selector('#chart-canvas svg')
        for ext in ['svg','png']:
            with page.expect_download() as d:page.locator('#chart-'+ext).click()
            file=out/(stem+'.'+ext);d.value.save_as(file)
            if ext=='svg':
                root=ET.parse(file).getroot();group=root.find('s:g',NS);assert group is not None
                content=' '.join(group.itertext())
                metadata=root.find('s:metadata',NS);assert metadata is not None and metadata.text
                exported=json.loads(metadata.text);assert all('voltage_v' in r for r in exported['measurements'])
                assert not re.search(r'\[\d+\]',content)
                if metric=='delay':assert 'Test voltage' not in content
            else:
                assert file.read_bytes()[:8]==b'\x89PNG\r\n\x1a\n'
        page.locator('#chart-format').select_option('video')
        assert page.locator('#chart-canvas svg').get_attribute('viewBox')=='0 0 1920 1080'
        with page.expect_download() as d:page.locator('#chart-png').click()
        video=out/(stem+'-16x9.png');d.value.save_as(video)
        assert struct.unpack('>II',video.read_bytes()[16:24])==(3840,2160)
    # Native checkbox label drag selects text without toggling the option.
    label=page.locator('#chart-details-label');label.scroll_into_view_if_needed();box=label.bounding_box();assert box
    before=page.locator('#chart-details').is_checked()
    page.mouse.move(box['x']+2,box['y']+box['height']/2);page.mouse.down()
    page.mouse.move(box['x']+box['width']-2,box['y']+box['height']/2,steps=25);page.mouse.up()
    assert 'Include detailed source notes' in page.evaluate('getSelection().toString()')
    assert page.locator('#chart-details').is_checked()==before
    page.evaluate('getSelection().removeAllRanges()');label.click()
    assert page.locator('#chart-details').is_checked()!=before
    for key,value in [('title','My custom title'),('subtitle','My own custom subtitle')]:page.locator('#chart-'+key).fill(value)
    page.locator('#chart-metric').select_option('watts')
    assert page.locator('#chart-title').input_value()=='My custom title'
    assert page.locator('#chart-subtitle').input_value()=='My own custom subtitle'
    for key in ['title','subtitle']:page.locator('#chart-'+key).fill('')
    page.reload();page.wait_for_selector('#chart-canvas svg')
    assert page.locator('#chart-title').input_value()==page.locator('#chart-subtitle').input_value()==''
    assert not errors,errors
    browser.close()
print('Passed: metric-aware legacy/default titles and subtitles, exact mode/settings placement, unnumbered source notes, no voltage in timing graphics, selectable/clickable checkbox text, retained custom/blank text, shares, metadata, and real Auto/16:9 SVG/PNG downloads.')
print('Artifacts:',out)
