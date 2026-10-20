"""Verify mode-specific titles, filtered lists, and retained camera selection."""
import sys
from urllib.parse import urlencode, parse_qs, urlsplit
from playwright.sync_api import sync_playwright
base=sys.argv[1] if len(sys.argv)>1 else 'http://127.0.0.1:8896/'
params=[('selection','1'),('group','low-power'),('family','low-power'),('metric','watts'),('title','Parking Mode Power Draw Comparison')]+[('id',f'vortex-sheet-row-{n}') for n in [4,6,9,15,21,11]]+[('id','rcg530-664217-1')]
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page()
    errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto(base+'parking-charts.html?'+urlencode(params));page.wait_for_selector('#chart-canvas svg')
    rows=page.request.get(base+'data/parking-measurements.json').json()['measurements']
    selected=lambda:set(page.locator('#chart-model-picker input:checked').evaluate_all('es=>es.map(e=>e.dataset.model)'))
    initial=selected();assert len(initial)==7
    assert page.locator('#chart-title').input_value()=='Low Power Parking Mode Power Draw Comparison'
    for group in ['buffered-motion','radar','low-power']:
        page.locator('#chart-group').select_option(group)
        eligible=set(page.evaluate('a=>[...new Set(a.rows.filter(r=>window.ParkingCharts.matchesFamily(r,a.group)&&r.state===window.ParkingCharts.defaultCondition(a.group)).map(window.ParkingUI.modelLabel))]',{'rows':rows,'group':group}))
        shown=set(page.locator('#chart-model-picker input').evaluate_all('es=>es.map(e=>e.dataset.model)'))
        assert shown==eligible,(group,shown^eligible)
        assert selected()==initial&eligible,(group,selected(),initial&eligible)
        pending=set(parse_qs(urlsplit(page.url).query).get('missingModel',[]))
        assert pending==initial-eligible
        ids=page.locator('#chart-picker input[data-id]').evaluate_all('es=>es.map(e=>e.dataset.id)')
        assert page.evaluate('a=>a.rows.filter(r=>a.ids.includes(r.id)).every(r=>window.ParkingCharts.matchesFamily(r,a.group))',{'rows':rows,'ids':ids,'group':group})
        page.reload();page.wait_for_function("document.querySelector('#chart-canvas').getAttribute('aria-busy')==='false'")
        assert selected()==initial&eligible
    assert selected()==initial
    for metric in ['current','delay','wake','watts']:
        page.locator('#chart-metric').select_option(metric)
        assert selected()==initial,(metric,selected())
        assert page.locator('#chart-title').input_value().startswith('Low Power Parking Mode ')
    page.locator('#chart-title').fill('My custom comparison')
    page.wait_for_function("new URL(location.href).searchParams.get('title')==='My custom comparison'")
    page.locator('#chart-group').select_option('buffered-motion')
    assert page.locator('#chart-title').input_value()=='My custom comparison'
    page.locator('#chart-metric').select_option('delay')
    assert page.locator('#chart-title').input_value()=='My custom comparison'
    # Exact owner-shared low-power power-draw selection must filter on load too.
    owner_ids=['vortex-sheet-row-15','vortex-sheet-row-11','vortex-sheet-row-21','vortex-sheet-row-4','vortex-sheet-row-6','vortex-sheet-row-9','rcg530-660569-2','rcg530-664217-1']
    owner_params=[('selection','1'),('group','low-power'),('family','low-power'),('condition','monitoring'),('metric','watts'),('sort','desc'),('highlight','Viofo T340'),('title','Low Power Parking Mode Power Draw Comparison'),('details','0'),('format','video')]+[('id',id) for id in owner_ids]
    page.goto(base+'parking-charts.html?'+urlencode(owner_params));page.wait_for_selector('#chart-model-picker input')
    expected=set(page.evaluate('rows=>[...new Set(rows.filter(r=>window.ParkingCharts.matchesFamily(r,"low-power")&&r.state==="monitoring").map(window.ParkingUI.modelLabel))]',rows))
    shown=set(page.locator('#chart-model-picker input').evaluate_all('nodes=>nodes.map(n=>n.dataset.model)'))
    assert shown==expected,(shown^expected)
    total=page.evaluate('rows=>new Set(rows.map(window.ParkingUI.modelLabel)).size',rows)
    assert len(shown)<total
    assert set(parse_qs(urlsplit(page.url).query)['id'])==set(owner_ids)
    assert not errors,errors
    browser.close()
print('Passed: supplied generic title upgrades, mode-filtered primary/advanced lists, camera retention across modes and metrics, unavailable-model recovery after reload, and custom-title preservation.')
