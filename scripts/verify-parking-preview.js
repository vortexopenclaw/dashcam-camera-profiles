#!/usr/bin/env node
'use strict';
// Real Chrome, actual data, and network-isolated adversarial fixtures. No dataset writes.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { interval, metricInterval } = require('../docs/assets/parking-preview.js');
const root = path.resolve(__dirname, '..');
const photoCatalog=JSON.parse(fs.readFileSync(path.join(root,'docs/assets/parking-preview/photos.json'),'utf8'));
assert.equal(photoCatalog.length,3);
for(const photo of photoCatalog){
  assert.match(photo.file,/^assets\/parking-preview\/[a-z0-9-]+\.png$/);
  const bytes=fs.readFileSync(path.join(root,'docs',photo.file));
  assert.equal(bytes.subarray(1,4).toString(),'PNG');
  assert.equal(bytes.readUInt32BE(16),800);assert.equal(bytes.readUInt32BE(20),480);
}
assert.deepEqual(interval({ power_w: 0 }, 'power_w'), { min: 0, max: 0, range: false });
assert.deepEqual(interval({ power_w_min: 1, power_w_max: 3 }, 'power_w'), { min: 1, max: 3, range: true });
for (const row of [{}, { power_w: -1 }, { power_w: '2' }, { power_w_min: 3, power_w_max: 1 }]) assert.equal(interval(row, 'power_w'), null);
const documented = {reported_startup_seconds:2.1,reported_startup_method:'Impact detection to start of recording'};
assert.deepEqual(metricInterval(documented,{key:'recording_delay_seconds'}),{min:2.1,max:2.1,range:false});
assert.equal(metricInterval(documented,{key:'reported_startup_seconds'}),null);
assert.equal(metricInterval({reported_startup_seconds:3},{key:'recording_delay_seconds'}),null);
for (const file of ['docs/parking-preview.html', 'docs/assets/parking-preview.js', 'docs/assets/parking-preview.css']) {
  const content = fs.readFileSync(path.join(root, file), 'utf8');
  assert.ok(!/docs\.google\.com\/spreadsheets|sheets\.googleapis\.com|BEGIN PRIVATE KEY|client_email/.test(content), file);
}
if (!process.argv.includes('--browser')) {
  console.log('Parking preview numeric, timing-method, and public-asset contracts passed.');
  process.exit(0);
}
const python = String.raw`
import functools, http.server, json, threading, urllib.parse
from playwright.sync_api import sync_playwright
class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args): pass
server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Handler,directory='docs'))
threading.Thread(target=server.serve_forever,daemon=True).start()
url = 'http://127.0.0.1:%s/parking-preview.html' % server.server_port
actual = json.load(open('docs/data/parking-measurements.json'))['measurements']
by_id = {r['id']:r for r in actual}
seed = ['vortex-sheet-row-4','vortex-sheet-row-9','vortex-sheet-row-17']
def chartrow(page, key, id): return page.locator('[data-metric="%s"] [data-measurement="%s"]'%(key,id))
def ready(page):
    page.wait_for_function("() => document.querySelector('#parking-results').getAttribute('aria-busy') === 'false'")
    page.wait_for_selector('.preview-chart-row')
def fit(page):
    for width in [320,375,768,1440]:
        page.set_viewport_size({'width':width,'height':1000})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Document overflow %s'%width
        assert page.locator('.preview-value').evaluate_all('els => els.every(e => {const r=e.getBoundingClientRect(); const range=document.createRange(); range.selectNodeContents(e); const t=range.getBoundingClientRect(); return t.left>=r.left-1 && t.right<=r.right+1})'), 'Clipped values %s'%width
with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome',headless=True)
    context = browser.new_context() # No clipboard or other permissions requested.
    page = context.new_page()
    errors=[]
    requests=[]
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('request', lambda r: requests.append(r.url))
    page.goto(url)
    ready(page)
    assert len(actual)==602
    assert page.locator('.comparison-card').count()==3
    assert page.locator('#starting-comparison').is_visible()
    page.wait_for_function("() => document.querySelectorAll('.preview-photo img').length === 3 && [...document.querySelectorAll('.preview-photo img')].every(i=>i.complete && i.naturalWidth===800)")
    for id in seed:
        for key,field,unit in [('power_w','power_w','W'),('recording_delay_seconds','reported_startup_seconds','s')]:
            row=chartrow(page,key,id)
            assert row.locator('.preview-value').inner_text()=='%s %s'%(by_id[id][field],unit) or (by_id[id][field]==1 and row.locator('.preview-value').inner_text()=='1 s')
            bar=row.locator('.preview-bar')
            assert float(bar.get_attribute('data-max'))==by_id[id][field]
        assert '%s channels'%by_id[id]['installed_channels'] in chartrow(page,'power_w',id).inner_text()
        assert 'Idle power draw' in chartrow(page,'power_w',id).inner_text()
    assert page.locator('[data-metric="reported_startup_seconds"]').count()==0
    assert page.locator('[data-metric="wake_seconds"]').count()==0
    assert 'after impact detection' in page.locator('[data-metric="recording_delay_seconds"] h4').inner_text()
    fit(page)
    for view in ['cameras','charts']:
        button=page.locator('[data-view-choice="%s"]'%view)
        button.focus()
        page.keyboard.press('Enter')
        assert button.get_attribute('aria-pressed')=='true'
        first=page.locator('.preview-comparison-content').evaluate('e=>[...e.children].sort((a,b)=>a.getBoundingClientRect().top-b.getBoundingClientRect().top)[0].id')
        assert first==('comparison-cards' if view=='cameras' else 'preview-charts')
        fit(page)
    page.locator('#filter-q').focus()
    page.keyboard.press('Tab')
    assert page.evaluate('document.activeElement.id')=='filter-brand'
    page.locator('#filter-q').fill('S1-QHD Infinite')
    assert page.locator('.parking-model-entry').count()==1
    summary=page.locator('.parking-model-tests > summary')
    summary.focus()
    page.keyboard.press('Enter')
    page.wait_for_function("() => document.querySelector('.parking-model-tests').open")
    pick=page.locator('[data-select]').first.get_attribute('data-select')
    page.locator('[data-select="%s"]'%pick).check()
    page.wait_for_function("() => document.querySelectorAll('.comparison-card').length===4")
    page.locator('#filter-sort').select_option('model')
    assert page.locator('.parking-model-tests').evaluate('e=>e.open')
    page.locator('[data-select="%s"]'%pick).uncheck()
    page.locator('[data-select="%s"]'%pick).check()
    page.locator('#filter-q').fill('NO MATCH')
    assert page.locator('.parking-model-entry').count()==0
    assert page.get_by_text('Outside current filters',exact=True).count()==4
    shared=page.url
    page.reload()
    ready(page)
    assert page.url==shared
    assert page.locator('.comparison-card').count()==4
    page.locator('#copy-link').click()
    page.wait_for_function("() => document.querySelector('#action-status').textContent.length>0")
    assert any(t in page.locator('#action-status').inner_text() for t in ['copied','Copy the current address'])
    page.goto(url+'?state=all&superseded=1&provisional=1')
    ready(page)
    assert page.locator('.parking-model-entry').count()==48
    assert page.locator('.parking-measurement').count()==602
    page.locator('.parking-model-tests').evaluate_all('es=>es.forEach(e=>e.open=true)')
    fit(page)
    print('Actual data: 602 measurements, 48 model groups, 3 seeded real rows, exact numeric values, 3 matching channel-kit photos, both layouts, 320/375/768/1440px, native keyboard, hidden selections, share/reload, and nondefault deselect/reselect passed.')
    # Unknown IDs and explicit compare parameters never get default selections.
    page.goto(url+'?compare=retired-id')
    ready(page)
    assert page.locator('.comparison-card').count()==1
    assert page.get_by_text('Measurement unavailable',exact=True).count()>=1
    assert page.locator('.preview-bar').count()==0
    assert not page.locator('#starting-comparison').is_visible()
    # Isolated fixtures don't touch canonical data.
    base=dict(id='fixture',brand='Fixture',model='Fixture camera',mode_name='Low Power Impact Detection',installed_channels=3,active_channels=['front','rear','interior'],category='impact-sleep',state='monitoring',test_status='production',superseded=False,power_w=None,wake_seconds=None,reported_startup_seconds=None,source_url='https://example.com/test',tester='Fixture tester')
    fixtures=[dict(base,id='range',power_w_min=.2,power_w_max=.8,wake_seconds_min=2,wake_seconds_max=5,wake_camera='rear camera'),dict(base,id='unknown'),dict(base,id='zero',power_w=0,reported_startup_seconds=3),dict(base,id='wake',power_w=1.23456,wake_seconds=7)]
    data=dict(version=1,measurements=fixtures,sources=[])
    page.route('**/data/parking-measurements.json',lambda route:route.fulfill(json=data))
    page.goto(url+'?'+urllib.parse.urlencode([('compare',r['id']) for r in fixtures]))
    ready(page)
    assert chartrow(page,'power_w','range').locator('.preview-value').inner_text()=='0.2–0.8 W (range)'
    assert chartrow(page,'power_w','range').locator('.is-range').count()==1
    assert chartrow(page,'power_w','range').locator('.preview-bar').get_attribute('data-min')=='0.2'
    assert chartrow(page,'power_w','range').locator('.preview-bar').get_attribute('data-max')=='0.8'
    assert chartrow(page,'power_w','unknown').locator('.preview-bar').count()==0
    assert chartrow(page,'power_w','unknown').locator('.preview-value').inner_text()=='Not reported'
    assert chartrow(page,'power_w','zero').locator('.preview-value').inner_text()=='0 W'
    assert chartrow(page,'power_w','zero').locator('.preview-bar').evaluate('e=>e.style.width')=='0%'
    assert chartrow(page,'power_w','wake').locator('.preview-value').inner_text()=='1.23456 W'
    assert chartrow(page,'wake_seconds','range').locator('.preview-value').inner_text()=='2–5 s (range)'
    assert 'rear camera' in chartrow(page,'wake_seconds','range').inner_text()
    assert chartrow(page,'reported_startup_seconds','zero').locator('.preview-value').inner_text()=='3 s'
    assert chartrow(page,'wake_seconds','zero').locator('.preview-bar').count()==0
    assert chartrow(page,'reported_startup_seconds','wake').locator('.preview-bar').count()==0
    assert page.locator('.preview-photo img').count()==0
    fit(page)
    # A matching model with a different installed channel count must not borrow its photo.
    wrong=dict(base,id='wrongkit',brand='Viofo',model='A329S',installed_channels=2,power_w=1)
    data['measurements']=[wrong]+fixtures
    page.goto(url+'?compare=wrongkit')
    ready(page)
    assert page.locator('.preview-photo img').count()==0
    assert page.locator('.preview-photo').inner_text()=='Photo not added yet'
    # Selection cap through native checkboxes.
    page.goto(url+'?compare=range&compare=unknown&compare=zero&compare=wake')
    ready(page)
    page.locator('.parking-model-tests').evaluate_all('es=>es.forEach(e=>e.open=true)')
    page.locator('[data-select="wrongkit"]').click()
    assert not page.locator('[data-select="wrongkit"]').is_checked()
    assert page.locator('.comparison-card').count()==4
    print('Isolated fixtures: unknown, zero, precise scalar, true interval bars, camera-scoped wake ranges, distinct startup methods, wrong-kit photo exclusion, and comparison cap passed.')
    page.unroute('**/data/parking-measurements.json')
    pending=[]
    page.route('**/data/parking-measurements.json',lambda route:pending.append(route))
    page.goto(url,wait_until='domcontentloaded')
    page.wait_for_timeout(100)
    assert len(pending)==2
    assert page.locator('.preview-bar').count()==0
    assert 'Loading comparison charts' in page.locator('#preview-charts').inner_text()
    assert page.locator('.preview-value').count()==0
    public_data=json.load(open('docs/data/parking-measurements.json'))
    for route in pending: route.fulfill(json=public_data)
    ready(page)
    page.unroute('**/data/parking-measurements.json')
    for bad in ['missing','malformed']:
        page.route('**/data/parking-measurements.json',lambda route:route.fulfill(status=404,body='Unavailable') if bad=='missing' else route.fulfill(json={'version':99}))
        page.goto(url)
        page.get_by_text('Measurements could not be loaded.',exact=True).wait_for()
        page.wait_for_function("() => document.querySelector('#preview-charts').textContent.includes('unavailable')")
        assert page.locator('.preview-bar').count()==0
        assert page.locator('#retry-load').is_visible()
        page.unroute('**/data/parking-measurements.json')
    page.locator('#retry-load').click()
    ready(page)
    assert page.locator('.comparison-card').count()==3
    assert not any('docs.google.com/spreadsheets' in r or 'sheets.googleapis.com' in r for r in requests)
    assert not page.locator('a[href*="docs.google.com/spreadsheets"]').count()
    assert not errors, errors
    print('Unavailable/malformed data: truthful no-bar state and retry recovery passed. No private-sheet requests, no permission grants, and zero JavaScript page errors.')
    browser.close()
server.shutdown()
`;
const result = spawnSync('python3', ['-c', python], { cwd: root, encoding: 'utf8', timeout: 180000 });
if (result.stdout) process.stdout.write(result.stdout);
if (result.stderr) process.stderr.write(result.stderr);
if (result.error) throw result.error;
assert.equal(result.status, 0, 'Chrome preview acceptance failed');
console.log('Parking preview acceptance passed.');
