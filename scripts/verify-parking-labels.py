"""Real-browser acceptance for editable parking chart text."""
import sys
from pathlib import Path
from urllib.parse import urlencode, parse_qs, urlsplit
from playwright.sync_api import sync_playwright
base=sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:8896/'
params=[('selection','1'),('family','buffered'),('group','buffered'),('metric','current'),('highlight','Viofo T340')]+[('id',f'vortex-sheet-row-{n}') for n in [19,5,7,16,3,14,10]]
out=Path.home()/'.hermes/cache/scratch/parking-text-tests';out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page(accept_downloads=True)
    errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto(base+'parking-charts.html?'+urlencode(params));page.wait_for_selector('#chart-canvas svg')
    assert page.locator('#chart-format').input_value()=='video'
    assert page.locator('#chart-canvas svg').get_attribute('viewBox')=='0 0 1920 1080'
    assert float(page.locator('#chart-canvas g[data-measurement] rect').first.get_attribute('x'))<=330
    assert page.locator('#chart-subtitle').input_value()=='Current Draw While Idle, 12.4 V (Lower is Better)'
    assert page.locator('#chart-xLabel').input_value()=='Power Draw (mA)'
    assert page.locator('#chart-yLabel').input_value()=='Dash Cameras'
    assert 'Blackvue Elite 8' in page.locator('#chart-canvas').text_content()
    assert 'BlackVue' not in page.locator('#chart-canvas svg > g').text_content()
    values={'title':'My parking test','subtitle':'My subtitle <test> & idle','xLabel':'Current (mA)','yLabel':'Camera models'}
    for key,value in values.items():
        page.locator('#chart-'+key).fill(value)
        page.wait_for_function('(a)=>new URL(location.href).searchParams.get(a.key)===a.value',arg={'key':key,'value':value})
    page.reload();page.wait_for_selector('#chart-canvas svg')
    for key,value in values.items():
        assert page.locator('#chart-'+key).input_value()==value
        assert value in page.locator('#chart-canvas').text_content()
    for ext in ['svg','png']:
        with page.expect_download() as d:page.locator('#chart-'+ext).click()
        assert d.value.suggested_filename==f'buffered-motion-impact-parking-current-draw-16x9.{ext}'
        file=out/('custom.'+ext);d.value.save_as(file)
        if ext=='svg':
            import xml.etree.ElementTree as ET
            content=''.join(ET.parse(file).getroot().itertext())
            assert all(value in content for value in values.values())
        else:
            import struct
            assert struct.unpack('>II',file.read_bytes()[16:24])==(3840,2160)
    page.locator('#chart-format').select_option('auto')
    page.reload();page.wait_for_selector('#chart-canvas svg')
    assert page.locator('#chart-format').input_value()=='auto'
    page.locator('#chart-format').select_option('video')
    assert page.locator('#chart-canvas svg').get_attribute('viewBox')=='0 0 1920 1080'
    page.locator('#chart-metric').select_option('watts')
    for key,value in values.items():assert page.locator('#chart-'+key).input_value()==value
    for width in [320,390,768,1440]:
        page.set_viewport_size({'width':width,'height':1000})
        assert page.locator('#chart-subtitle').is_visible()
        page.screenshot(path=str(out/f'custom-{width}.png'),full_page=True)
    for key in ['subtitle','xLabel','yLabel']:page.locator('#chart-'+key).fill('')
    page.reload();page.wait_for_selector('#chart-canvas svg')
    for key in ['subtitle','xLabel','yLabel']:assert page.locator('#chart-'+key).input_value()==''
    assert page.locator('#chart-canvas [data-role="chart-y-axis"]').count()==0
    mode_params=[('selection','1'),('family','low-power'),('group','low-power'),('metric','watts'),('title','Parking Mode Power Draw Comparison')]+[('id',f'vortex-sheet-row-{n}') for n in [4,6,9,15,21,11]]+[('id','rcg530-664217-1')]
    page.goto(base+'parking-charts.html?'+urlencode(mode_params));page.wait_for_selector('#chart-canvas svg')
    assert page.locator('#chart-title').input_value()=='Low Power Parking Mode Power Draw Comparison'
    page.locator('#chart-metric').select_option('current')
    assert page.locator('#chart-title').input_value()=='Low Power Parking Mode Current Draw Comparison'
    page.locator('#chart-group').select_option('buffered-motion')
    page.locator('#chart-apply-group').click()
    assert page.locator('#chart-title').input_value()=='Buffered Motion Detection Parking Mode Power Draw Comparison'
    page.locator('#chart-title').fill('Keep my custom title')
    page.locator('#chart-metric').select_option('delay')
    assert page.locator('#chart-title').input_value()=='Keep my custom title'
    import json
    data=page.request.get(base+'data/parking-measurements.json').json()['measurements']
    unknown=next(r for r in data if isinstance(r.get('current_ma'),(int,float)) and not r.get('voltage_v'))
    other_voltage=next(r for r in data if isinstance(r.get('current_ma'),(int,float)) and r.get('voltage_v') and r['voltage_v']!=12.4)
    test_params=[('selection','1'),('metric','current'),('id','vortex-sheet-row-5'),('id',unknown['id']),('id',other_voltage['id'])]
    page.goto(base+'parking-charts.html?'+urlencode(test_params))
    page.wait_for_function("document.querySelector('#chart-notice').textContent.includes('Missing test voltage:')")
    notice=page.locator('#chart-notice').inner_text()
    assert unknown['model'] in notice and 'Different test voltages:' in notice
    assert 'Viofo T340' in notice and str(other_voltage['voltage_v'])+' V' in notice
    assert not errors,errors
    browser.close()
print('Passed: screenshot defaults, Blackvue styling, editable title/subtitle/X/Y labels, shared reload, custom text in SVG/PNG exports, metric changes, mobile controls, and blank labels.')
