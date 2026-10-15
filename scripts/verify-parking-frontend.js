#!/usr/bin/env node
'use strict';
// Isolated contract fixtures only. No illustrative rows are shipped in the dataset.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ui = require('../docs/assets/parking.js');
const root = path.resolve(__dirname, '..');
const base = { id: 'test-only', brand: 'Test brand', model: 'Test fixture', category: 'buffered-event', state: 'monitoring', test_status: 'production', superseded: false, power_w: 1, wake_seconds: null };
const variants = [base, { ...base, id: 'unknown', power_w: null }, { ...base, id: 'zero', power_w: 0, wake_seconds: 0 }, { ...base, id: 'event', state: 'event-recording' }, { ...base, id: 'prototype', test_status: 'prototype' }, { ...base, id: 'old', superseded: true }, { ...base, id: 'review', review_status: 'needs-review' }, { ...base, id: 'caveat', notes: 'DOUBLECHECK VIDEO' }];
const { state } = ui.readState('');
assert.deepEqual(ui.filterRows(variants, state).map(row => row.id), ['test-only', 'unknown', 'zero', 'prototype']);
assert.deepEqual(ui.sortRows(variants.slice(0, 3), 'watts').map(row => row.id), ['zero', 'test-only', 'unknown']);
assert.deepEqual(ui.sortRows(variants.slice(0, 3), 'wake').map(row => row.id), ['zero', 'test-only', 'unknown']);
assert.equal(ui.filterRows(variants, { ...state, state: 'event-recording' })[0].id, 'event');
assert.equal(ui.filterRows(variants, { ...state, provisional: true }).length, 6);
assert.equal(ui.filterRows(variants, { ...state, prototype: false }).length, 3);
assert.equal(ui.filterRows(variants, { ...state, superseded: true }).length, 5);
assert.equal(ui.filterRows(variants, { ...state, q: 'NO MATCH' }).length, 0);
assert.equal(ui.filterRows(variants, { ...state, category: 'impact-sleep' }).length, 0);
assert.equal(ui.rangeValue({current_ma:null,current_ma_min:343,current_ma_max:355},'current_ma','mA'),'343–355 mA (range)');
assert.equal(ui.rangeValue({power_w:0},'power_w','W'),'0 W');
assert.equal(ui.rangeValue({power_w:null},'power_w','W'),'Not reported');
assert.equal(ui.wake({wake_seconds:null,wake_seconds_min:3,wake_seconds_max:5,wake_camera:'rear camera'}),'3–5 s (range) · rear camera');
assert.equal(ui.wake({wake_seconds:0,wake_camera:'front camera'}),'0 s · front camera');
assert.equal(ui.wake({reported_startup_seconds:8}),'Not reported');
assert.equal(ui.watts({power_w:1.23456,power_is_derived:true}),'Approximately 1.23 W');
assert.equal(ui.watts({power_w:1.23456}),'1.23456 W');
assert.equal(ui.watts({power_w:null,power_w_min:1.23456,power_w_max:2.34567,power_is_derived:true}),'Approximately 1.23–2.35 W (range)');
const ranged = { ...base, id: 'range', power_w: null, power_w_min: 0.1, power_w_max: 0.2, wake_seconds_min: 0.1, wake_seconds_max: 0.2 };
for (const sort of ['watts','wake']) assert.equal(ui.sortRows([ranged,{...base,wake_seconds:9}],sort)[0].id,base.id);
for (const category of ['bad','toString','__proto__']) assert.equal(ui.readState(`category=${category}`).state.category,'');
const custom = { ...state, q: 'A & B', prototype: false, provisional: true, state: 'event-recording' };
assert.deepEqual(ui.readState(ui.query(custom, ['id:1', 'id,2'])), { state: custom, selected: ['id:1', 'id,2'] });
assert.equal(ui.readState('compare=a&compare=a&compare=b&compare=c&compare=d&compare=e').selected.length, 4);
assert.equal(ui.readState('sort=bad&state=bad').state.sort, 'watts');
for (const value of ['=HYPERLINK("x")', ' +cmd', '-cmd', '@SUM(1)', '\tformula', '\rformula']) assert.ok(ui.csvCell(value).startsWith('"\''));
assert.equal(ui.csvCell('a,"b"'), '"a,""b"""');
assert.equal(ui.safeURL('javascript:alert(1)'), '');
assert.equal(ui.safeURL('https://example.com/source'), 'https://example.com/source');
const csv = ui.toCSV([{ ...base, extra_metadata: 'preserved', active_channels: ['front', 'rear'] }]);
assert.ok(csv.includes('extra_metadata') && csv.includes('preserved') && csv.includes('active_channels'));
const rawCSV = ui.toCSV([{ ...ranged, power_w:1.23456, power_is_derived:true, wake_camera:'rear camera', connectivity:'No LTE module', prebuffer_impact_s:5, prebuffer_motion_s:10 }]);
for (const text of ['1.23456','power_w_min','wake_seconds_min','wake_camera','power_is_derived','connectivity','prebuffer_impact_s','prebuffer_motion_s']) assert.ok(rawCSV.includes(text));
const html = fs.readFileSync(path.join(root, 'docs/parking-mode.html'), 'utf8');
for (const asset of ['assets/parking.js', 'assets/parking.css', 'assets/styles.css']) assert.ok(html.includes(asset) && fs.existsSync(path.join(root, 'docs', asset)));
assert.ok(html.includes('name="viewport"') && html.includes('href="./"'));
const dataPath = path.join(root, 'docs/data/parking-measurements.json');
if (fs.existsSync(dataPath)) {
  const data = JSON.parse(fs.readFileSync(dataPath, 'utf8'));
  assert.equal(data.version, 1);
  assert.equal(data.measurements.length, 588);
  const groups = ui.groupModels(data.measurements);
  assert.equal(groups.flatMap(group => group.rows).length, 588);
  assert.equal(new Set(groups.map(group => group.label)).size, groups.length);
  for (const query of ['S1-QHD Infinite', 'S1-4K', 'N5', 'Nexus 5', 'S1 Pro', 'X800', '4K Omni', 'ARC800', 'ARC 800']) assert.equal(ui.groupModels(ui.filterRows(data.measurements, {...state, q: query})).length, 1);
  for (const [brand,source,display] of [['Vantrue','Nexus 5 (N5)','N5'],['Vantrue','Sonnet 1 (S1) Pro','S1 Pro'],['Vantrue','Sonnet 1 (S1)','S1'],['70mai','4K Omni [X800]','4K Omni'],['Thinkware','ARC800 LTE','ARC 800']]) assert.equal(ui.modelName({brand,model:source}),display);
  assert.equal(ui.modelName({brand:'Thinkware',model:'ARC'}),'ARC');
  assert.ok(ui.setup(data.measurements.find(row=>row.model==='ARC800 LTE')).includes('With LTE module'));
  assert.ok(ui.setup(data.measurements.find(row=>row.model==='ARC800')).includes('Without LTE module'));
  for (const model of ['Elite 9', 'Elite 10']) {
    const group = groups.find(group => group.label === `BlackVue ${model}`);
    assert.equal(group.rows.length, 10);
    assert.deepEqual(new Set(group.rows.map(row => row.connectivity)), new Set(['No LTE module', 'CM100G LTE connected']));
    assert.ok(group.rows.every(row => !ui.cabinIR(row)));
  }
  for (const row of data.measurements) {
    assert.ok(!/\b(PM|SM|AED|LBR|LFR|LPID|TLR|CD|MD)\b|H\.26|WiFi|\dCH|\bmonitoring\b|\bwaiting\b|\[|\]/i.test(ui.modeLabel(row)), ui.modeLabel(row));
    if (row.installed_channels === 1 || (row.active_channels || []).every(view => ['front','rear'].includes(view))) assert.equal(ui.cabinIR(row), '');
  }
  assert.equal(ui.modeLabel({mode_name:'PM Collision Detection PS [monitoring]'}), 'Collision detection · Power Saving');
  assert.equal(ui.modeLabel({mode_name:'PM Collision Detection QS [recording]'}), 'Collision detection · Quick Start');
  assert.equal(ui.modeLabel({mode_name:'PM UNRESOLVED'}), 'Mode awaiting review');
  assert.ok(Array.isArray(data.measurements));
  assert.equal(new Set(data.measurements.map(row => row.id)).size, data.measurements.length, 'Stable measurement IDs must be unique');
  const visible = ui.filterRows(data.measurements, state);
  assert.ok(visible.every(row => !row.superseded && !ui.provisional(row) && row.state !== 'event-recording'));
  console.log(`Actual dataset checked: ${data.measurements.length} rows, ${visible.length} default-visible.`);
} else console.log('Actual dataset not yet present; missing-data browser path must be checked separately.');
if (process.argv.includes('--browser')) {
  const { spawnSync } = require('node:child_process');
  const browserTest = String.raw`
import csv, functools, http.server, json, threading
from playwright.sync_api import sync_playwright
handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory='docs')
server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
threading.Thread(target=server.serve_forever, daemon=True).start()
url = 'http://127.0.0.1:%s/parking-mode.html' % server.server_port
base = {'id':'fixture-only', 'brand':'Test brand', 'model':'Contract fixture', 'installed_channels':2, 'active_channels':['front','rear'], 'firmware':'test', 'mode_name':'Test buffered', 'category':'buffered-event', 'state':'monitoring', 'power_w':1.25, 'current_ma':100, 'voltage_v':12.5, 'wake_seconds':None, 'prebuffer_s':10, 'tester':'Test only', 'source_url':'https://example.com/source', 'notes':'Isolated browser fixture, never production data.', 'test_status':'production', 'ir':'off', 'power_path':'Test fixture', 'superseded':False}
fixtures = [dict(base, id='fixture-%s'%i, model='Contract fixture %s'%i, power_w=i / 2) for i in range(6)]
fixtures += [dict(base,id='fixture-unknown',power_w=None),dict(base,id='fixture-review',review_status='needs-review'),dict(base,id='fixture-event',state='event-recording'),dict(base,id='fixture-old',superseded=True),dict(base,id='fixture-prototype',test_status='prototype')]
fixtures[0].update(connectivity='CM100G LTE connected', power_path='Battery-side hardwire input', wake_seconds_min=3, wake_seconds_max=5, wake_camera='rear camera', prebuffer_impact_s=5, prebuffer_motion_s=10, notes='Full tested variant note: CM100G LTE connected; front and rear recording; IR off. ' + 'Additional tested conditions. '*20 + 'END OF SOURCE NOTE')
fixtures[1].update(power_w=1.23456, power_is_derived=True)
fixtures[2].update(power_w=1.23456)
fixtures[3].update(wake_seconds=9,wake_camera='front camera')
fixtures[6].update(power_w_min=1.23456,power_w_max=2.34567,current_ma=None,current_ma_min=100,current_ma_max=120)
data = {'version':1,'updated':'test-only','measurements':fixtures,'sources':[{'id':'source-only','title':'Source without measurements','url':'https://example.com/no-rows','measurement_count':0,'images':['https://example.com/image.png'],'status':'needs-review','notes':'Test fixture source index'}], 'coverage':{'scope_note':'Isolated browser fixture, not a production dataset','posts_indexed':1}}
with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome',headless=True)
    context = browser.new_context(permissions=['clipboard-read','clipboard-write'])
    page = context.new_page()
    errors=[]
    page.on('pageerror', lambda error: errors.append(str(error)))
    # Serve actual files first. This intentionally accepts missing data before publication.
    page.goto(url)
    page.wait_for_function("() => document.querySelector('#parking-results').getAttribute('aria-busy') === 'false'")
    print('Actual served data state:', page.locator('#result-count').inner_text())
    for width in [320,375,768,1440]:
        page.set_viewport_size({'width':width,'height':900})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Actual page overflow at %s'%width
    actual = json.load(open('docs/data/parking-measurements.json'))['measurements']
    assert len(actual) == 588
    assert page.locator('a[href*="docs.google.com/spreadsheets"]').count() == 0
    assert not page.locator('#coverage-notes').is_visible()
    assert page.locator('#sources-title').inner_text() == 'Original testing data'
    assert page.locator('#vortex-radar-testing').inner_text().find("isn't public") >= 0
    for query in ['S1-QHD Infinite','S1-4K','S1-4K Infinite','Elite 9','Elite 10','N5','Nexus 5','S1 Pro','X800','4K Omni','ARC800','ARC 800']:
        page.locator('#filter-q').fill(query)
        assert page.locator('.parking-model-entry').count() == 1, query
        entry = page.locator('.parking-model-entry')
        entry.locator('.parking-model-tests > summary').click()
        text = entry.inner_text()
        assert 'Hardware status unknown' not in text
        assert 'IR: unknown' not in text
        assert 'monitoring' not in text.lower()
        assert not page.locator('#filter-tester').is_visible()
        if query.startswith('Elite'):
            assert 'No LTE module' in text and 'CM100G LTE connected' in text
        names = page.locator('.parking-mode-name').all_text_contents()
        assert all(not any(token in name for token in ['PM ', 'SM ', '[', 'WiFi', 'H.264', 'H.265']) for name in names)
    page.goto(url+'?state=all&superseded=1&provisional=1')
    page.wait_for_selector('.parking-model-entry')
    assert page.locator('.parking-measurement').count() == 588
    assert page.locator('.parking-model-entry').count() == 47
    page.locator('.parking-model-tests').evaluate_all('(items) => items.forEach(item => item.open = true)')
    for width in [320,375,768,1440]:
        page.set_viewport_size({'width':width,'height':900})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Expanded actual setup overflow at %s'%width
    picked = next(row for row in actual if row['model']=='S1-QHD Infinite')
    page.goto(url+'?q=NO+MATCH&compare='+picked['id'])
    page.wait_for_selector('.comparison-card')
    assert picked['id'] in page.url
    assert 'Outside current filters' in page.locator('.comparison-card').inner_text()
    page.reload()
    page.wait_for_selector('.comparison-card')
    assert 'Vueroid S1-QHD Infinite' in page.locator('.comparison-card').inner_text()
    page.goto(url)
    page.wait_for_selector('.parking-model-entry')
    # Force missing-data and malformed-data paths regardless of deployment state.
    page.route('**/data/parking-measurements.json', lambda route: route.fulfill(status=404,body='Not found'))
    page.reload()
    page.get_by_text('Measurements could not be loaded.',exact=True).wait_for()
    assert page.locator('#retry-load').is_visible()
    page.unroute('**/data/parking-measurements.json')
    page.route('**/data/parking-measurements.json', lambda route: route.fulfill(json={'version':99}))
    page.reload()
    page.get_by_text('Measurements could not be loaded.',exact=True).wait_for()
    page.unroute('**/data/parking-measurements.json')
    # Network-isolated contract fixtures exercise behavior without modifying data files.
    page.route('**/data/parking-measurements.json', lambda route: route.fulfill(json=data))
    for invalid_category in ['bad','toString','__proto__']:
        page.goto(url+'?category='+invalid_category+'&state=invalid&sort=invalid')
        page.wait_for_selector('[data-id="fixture-0"]', state='attached')
        assert page.locator('#filter-category').input_value()==''
        assert page.locator('#filter-state').input_value()=='parked'
        assert page.locator('#filter-sort').input_value()=='watts'
        assert 'category=' not in page.url
    page.goto(url+'?brand=RetiredBrand&channels=99&tester=RetiredTester&compare=stale-id')
    page.get_by_text('Measurement unavailable',exact=True).wait_for()
    assert page.locator('.parking-measurement').count()==0
    assert page.locator('#filter-brand').input_value()=='RetiredBrand'
    assert page.locator('#filter-channels').input_value()=='99'
    assert page.locator('#filter-tester').input_value()=='RetiredTester'
    assert 'RetiredTester' in page.locator('#legacy-tester-note').inner_text()
    assert not page.locator('#filter-tester').is_visible()
    page.reload()
    page.get_by_text('Measurement unavailable',exact=True).wait_for()
    page.locator('[data-remove="stale-id"]').click()
    assert page.locator('.comparison-card').count()==0
    page.goto(url)
    page.wait_for_selector('[data-id="fixture-0"]', state='attached')
    assert page.locator('.parking-measurement').count()==8
    page.locator('.parking-model-tests').evaluate_all('(items) => items.forEach(item => item.open = true)')
    assert not page.locator('[data-id="fixture-review"]').count()
    assert page.locator('.parking-track.unknown').count()==1
    assert page.locator('[data-id="fixture-unknown"] .parking-track span').count()==0
    assert '1.23456–2.34567 W (range)' in page.locator('[data-id="fixture-unknown"] .parking-watts').inner_text()
    assert '100–120 mA (range)' in page.locator('[data-id="fixture-unknown"] .parking-row').inner_text()
    assert page.locator('[data-id="fixture-1"] .parking-watts').inner_text()=='Approximately 1.23 W'
    assert page.locator('[data-id="fixture-2"] .parking-watts').inner_text()=='1.23456 W'
    assert page.locator('.parking-model-entry').filter(has=page.locator('[data-id="fixture-unknown"]')).locator('.parking-measurement').last.get_attribute('data-id')=='fixture-unknown'
    page.locator('#filter-sort').select_option('wake')
    assert page.locator('.parking-measurement').first.get_attribute('data-id')=='fixture-3'
    page.locator('#filter-sort').select_option('watts')
    page.locator('.parking-model-tests').evaluate_all('(items) => items.forEach(item => item.open = true)')
    summary = page.locator('[data-id="fixture-0"] .parking-row').inner_text()
    for text in ['CM100G LTE connected','Battery-side hardwire input','3–5 s (range) · rear camera']:
        assert text in summary, text
    assert page.locator('#source-index').inner_text().find('no transcribed measurements')>=0
    assert page.locator('#source-index img').count()==0
    for width in [320,375,768,1440]:
        page.set_viewport_size({'width':width,'height':900})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Populated page overflow at %s'%width
    for i in range(4): page.locator('[data-select="fixture-%s"]'%i).check()
    page.locator('[data-select="fixture-4"]').click()
    assert not page.locator('[data-select="fixture-4"]').is_checked()
    assert page.locator('.comparison-card').count()==4
    assert 'compare=fixture-0' in page.url
    card = page.locator('.comparison-card').first
    assert card.locator('details').count()==1
    card.locator('summary').click()
    for label, value in [('Channels','2 channels'),('Active views','front, rear'),('Firmware','test'),('LTE module','CM100G LTE connected'),('Current at stated voltage','100 mA / 12.5 V'),('Power adapter','Battery-side hardwire input'),('Impact to first frame / camera scope','3–5 s (range) · rear camera'),('Impact pre-event buffer','5 s'),('Motion pre-event buffer','10 s'),('Tester','Test only')]:
        fact = card.locator('.parking-facts > div').filter(has=page.get_by_text(label,exact=True))
        assert fact.locator('dd').is_visible() and fact.locator('dd').inner_text()==value, label
    assert 'END OF SOURCE NOTE' in card.inner_text()
    assert card.get_by_text('Pre-event buffer (source unqualified)',exact=True).count()==0
    generic = page.locator('.comparison-card').nth(1).locator('.parking-facts > div').filter(has=page.get_by_text('Pre-event buffer (source unqualified)',exact=True))
    page.locator('.comparison-card').nth(1).locator('summary').click()
    assert generic.locator('dd').inner_text()=='10 s'
    page.locator('#filter-q').fill('NO MATCH')
    assert page.locator('.parking-measurement').count()==0
    assert page.get_by_text('Outside current filters',exact=True).count()==4
    page.reload()
    page.wait_for_function("() => document.querySelectorAll('.comparison-card').length === 4")
    assert page.locator('#filter-q').input_value()=='NO MATCH'
    page.get_by_role('button',name='Reset filters',exact=True).click()
    assert page.locator('.comparison-card').count()==4
    page.locator('#filter-provisional').check()
    assert page.locator('[data-id="fixture-review"]').count()==1
    page.locator('.parking-model-tests').evaluate_all('(items) => items.forEach(item => item.open = true)')
    assert 'Provisional' in page.locator('[data-id="fixture-review"]').inner_text()
    page.locator('#filter-state').select_option('event-recording')
    assert page.locator('.parking-measurement').count()==1
    page.get_by_role('button',name='Reset filters',exact=True).click()
    page.locator('#copy-link').click()
    page.wait_for_function("() => document.querySelector('#action-status').textContent.includes('copied')")
    assert page.evaluate('navigator.clipboard.readText()')==page.url
    with page.expect_download() as download:
        page.locator('#download-csv').click()
    assert download.value.suggested_filename=='parking-measurements-filtered.csv'
    assert 'source_url' in open(download.value.path(),encoding='utf-8-sig').read()
    with open(download.value.path(),encoding='utf-8-sig',newline='') as downloaded:
        exported = {row['id']:row for row in csv.DictReader(downloaded)}
    assert exported['fixture-1']['power_w']=='1.23456'
    assert exported['fixture-1']['power_is_derived']=='true'
    assert exported['fixture-unknown']['power_w']==''
    assert exported['fixture-unknown']['power_w_min']=='1.23456'
    assert exported['fixture-0']['wake_seconds']==''
    assert exported['fixture-0']['wake_seconds_min']=='3'
    page.set_viewport_size({'width':375,'height':900})
    page.locator('.parking-model-tests').evaluate_all('(items) => items.forEach(item => item.open = true)')
    page.locator('.parking-measurement details').first.locator('summary').click()
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Expanded details overflow'
    for width in [320,375,768,1440]:
        page.set_viewport_size({'width':width,'height':900})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Comparison metadata overflow at %s'%width
    page.locator('#filter-q').focus()
    page.keyboard.press('Tab')
    assert page.evaluate('document.activeElement.id')=='filter-brand'
    assert not errors, errors
    print('Chrome browser checks passed: actual page, missing/malformed data, invalid/stale URLs, visible comparison metadata/full notes, scoped wake/current/power ranges, derived-only rounding, 320/375/768/1440px, selection cap, hidden-selection labels, URL reload, provisional gate, clipboard, CSV download, details, keyboard, and zero page errors.')
    browser.close()
server.shutdown()
`;
  const result = spawnSync('python3', ['-c', browserTest], { cwd: root, encoding: 'utf8', timeout: 120000 });
  if (result.stdout) process.stdout.write(result.stdout);
  if (result.stderr) process.stderr.write(result.stderr);
  if (result.error) throw result.error;
  assert.equal(result.status, 0, 'Playwright browser acceptance failed');
}
console.log('Parking frontend contract checks passed: filters, unknown/zero sort, review gates, URL round-trip, CSV metadata/injection safety, and asset links.');
