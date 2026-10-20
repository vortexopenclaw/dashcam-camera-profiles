#!/usr/bin/env node
'use strict';
// Unit contracts plus real Chrome acceptance. Artifacts stay outside the repository.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const chart = require('../docs/assets/parking-charts.js');
const UI = require('../docs/assets/parking.js');
const rows = require('../docs/data/parking-measurements.json').measurements;
assert.equal(rows.length, 599);
assert.equal(UI.groupModels(rows).length, 48);
const e1s=rows.filter(r=>r.brand==='Vantrue'&&r.model==='E1 Pro S');
assert.equal(e1s.length,11);
assert.ok(e1s.every(r=>r.test_status==='prototype'&&r.voltage_v===12.6&&r.installed_channels===1));
const e1sIdle=e1s.find(r=>r.id==='rcg530-675957-5');
assert.equal(e1sIdle.power_w,0.09);assert.equal(e1sIdle.current_ma,7);
assert.equal(new Map(chart.testFields(e1sIdle)).get('Reported recording-start delay'),'1.37–1.42 s');
assert.equal(chart.interval(e1sIdle,'wake'),null);
assert.notEqual(new Map(chart.testFields(e1s.find(r=>r.id==='rcg530-675957-3'))).get('Settings'),new Map(chart.testFields(e1s.find(r=>r.id==='rcg530-675957-4'))).get('Settings'));
assert.equal(new Set(rows.map(r => r.id)).size, 599);
assert.equal(chart.readState('?metric=watts&title=Parking+Mode+Power+Draw',rows).title,'Parking Mode Power Draw Comparison');
assert.equal(chart.readState('?metric=watts&title=My+custom+title',rows).title,'My custom title');
const e1=rows.filter(r=>r.brand==='Vantrue'&&r.model==='E1 Pro'&&r.state==='monitoring'&&r.category==='impact-sleep');
assert.equal(chart.representative(e1,[],'low-power').id,'rcg530-660569-2');
assert.equal(chart.tester({tester:'Robert'}),'Retro CarGuy530 (rcg530)');
assert.equal(chart.tester({tester:'VIOFO-Support'}),'VIOFO-Support');
assert.equal(new Map(chart.testFields(e1[0])).has('Interior IR'),false);
assert.deepEqual(chart.differences(e1),['Mode']);
assert.equal(new Map(chart.testFields({notes:'1st 5-minutes.',mode_name:'Motion Detection'})).get('Test window'),'1st 5-minute interval');
assert.match(chart.sourceName({brand:'Viofo',model:'A329S',tester:'VIOFO-Support',source_url:'https://viofo.com/'}),/testing data$/);
const interiorOff=rows.find(r=>/Interior camera disabled in parking but still plugged in/.test(r.notes || '') && r.ir==='on');
assert.ok(interiorOff);
assert.equal(new Map(chart.testFields(interiorOff)).get('Interior camera'),'Off while parked, still connected');
assert.equal(new Map(chart.testFields(interiorOff)).get('Interior IR'),'on');
assert.equal(new Map(chart.testFields(interiorOff)).get('Lighting'),'Night');
const duplicates=[{...e1[0],id:'b'},{...e1[0],id:'a'}];
assert.match(chart.variantLabel(duplicates[0],duplicates,'watts'),/Test 2$/);
for(const group of UI.groupModels(rows)) {
  for(const channels of new Set(group.rows.map(row=>row.installed_channels))) {
    const variants=group.rows.filter(row=>row.installed_channels===channels);
    const labels=variants.map(row=>chart.variantLabel(row,variants,'watts'));
    assert.equal(new Set(labels).size,variants.length,group.label+' unique readable variant labels');
    assert.ok(labels.every(label=>!/vortex-sheet-row-|rcg530-\d/.test(label)));
  }
}
assert.equal(chart.representative(e1,['rcg530-660569-1'],'low-power').id,'rcg530-660569-1');
assert.match(UI.modeLabel(e1.find(r=>r.id==='rcg530-660569-1')),/Quick Start/);
assert.match(UI.modeLabel(e1.find(r=>r.id==='rcg530-660569-2')),/Power Saving/);
assert.equal(chart.representative(e1.map(r=>({...r,power_w:r.id.endsWith('-1')?0.001:9})),[],'low-power').id,'rcg530-660569-2');
assert.deepEqual(chart.interval({ power_w: 0 }, 'watts'), { min: 0, max: 0, range: false });
assert.deepEqual(chart.interval({ power_w: 2, power_w_min: 1, power_w_max: 3 }, 'watts'), { min: 1, max: 3, range: true });
for (const row of [{}, { power_w: null }, { power_w: -1 }, { power_w: '1' }, { power_w: Infinity }, { power_w_min: 3, power_w_max: 1 }, { power_w: 1, power_w_min: 1 }, { power_w: 1, disabled: true }]) assert.equal(chart.interval(row, 'watts'), null);
assert.equal(chart.interval({ reported_startup_seconds: 2 }, 'delay'), null);
assert.equal(chart.interval({ reported_startup_seconds: 2, reported_startup_method: 'unknown' }, 'wake'), null);
assert.equal(chart.prepare(rows, chart.preset('current')).blocked, false);
const ids40 = rows.filter(r => chart.interval(r, 'watts')).slice(0, 40).map(r => r.id);
assert.equal(chart.readState('?selection=1&'+ids40.map(id => 'id='+id).join('&'), rows).ids.length, 40);
assert.deepEqual(chart.readState('?selection=1&id=evil&id=vortex-sheet-row-4&id=vortex-sheet-row-4&metric=__proto__&highlight=javascript:alert(1)', rows).ids, ['vortex-sheet-row-4']);
assert.equal(chart.readState('?selection=1&metric=__proto__', rows).metric, 'current');
for (const file of ['docs/parking-charts.html', 'docs/assets/parking-charts.js', 'docs/assets/parking-charts.css']) {
  const content = fs.readFileSync(path.resolve(__dirname, '..', file), 'utf8');
  assert.ok(!/docs\.google\.com\/spreadsheets|sheets\.googleapis\.com|BEGIN PRIVATE KEY|client_email/.test(content), file);
}
assert.equal(chart.preset('current').highlight, '');
for (const group of Object.keys(chart.families).filter(group => group !== 'all')) {
  assert.equal(chart.matchesFamily({category:'unknown',mode_name:'Energy Saving M&I AED',prebuffer_motion_s:8},group),false);
}
assert.equal(chart.matchesFamily({category:'unknown',mode_name:'M&I'},'buffered-motion'),false);
assert.equal(chart.matchesFamily({category:'unbuffered-event',mode_name:'M&I'},'buffered-motion'),false);
assert.equal(chart.matchesFamily({category:'buffered-event',mode_name:'Energy Saving Parking Mode'},'low-power'),false);
assert.equal(chart.matchesFamily({category:'buffered-event',mode_name:'Energy Saving Parking Mode'},'buffered-motion'),false);
assert.equal(chart.matchesFamily({category:'buffered-event',mode_name:'PM M&I without Motion or Impact'},'buffered-motion'),true);
assert.equal(chart.matchesFamily({category:'buffered-event',mode_name:'PM AED'},'buffered-motion'),true);
assert.equal(chart.matchesFamily({category:'buffered-event',mode_name:'15 FPS'},'buffered-motion'),false);
assert.equal(chart.matchesFamily({category:'hybrid',state:'monitoring',mode_name:'Extreme Low Power + Impact & Motion',notes:'Sleeps after 75s. Elevated operation.'},'low-power'),false);
const familyCounts = Object.fromEntries(Object.keys(chart.families).map(group => [group, {all:rows.filter(row=>chart.matchesFamily(row,group)).length,waiting:rows.filter(row=>chart.matchesFamily(row,group)&&row.state===chart.defaultCondition(group)).length}]));
console.log('Functional family counts: '+JSON.stringify(familyCounts));
const modelCounts = Object.fromEntries(Object.keys(chart.families).map(group=>[group,UI.groupModels(rows.filter(row=>chart.matchesFamily(row,group)&&row.state===chart.defaultCondition(group))).length]));
console.log('Primary model counts: '+JSON.stringify(modelCounts));
for (const group of Object.keys(chart.families)) {
  for (const model of UI.groupModels(rows.filter(row=>chart.matchesFamily(row,group)&&row.state===chart.defaultCondition(group)))) {
    const chosen=chart.representative(model.rows,[],group);
    const highest=Math.max(...model.rows.map(row=>row.installed_channels || 0));
    if(highest>0)assert.equal(chosen.installed_channels,highest);
    assert.equal(chart.representative(model.rows,[chosen.id],group).id,chosen.id);
  }
}
const candidates=[{id:'a',installed_channels:3,power_w:8,date:'2025-01-01'},{id:'b',installed_channels:2,power_w:0.01,date:'2026-01-01'},{id:'c',installed_channels:3,power_w:2,date:'2026-01-01',superseded:true}];
assert.equal(chart.representative(candidates).id,'a');
assert.equal(chart.representative(candidates,['b']).id,'b');
assert.equal(chart.representative(candidates,[],'all',2).id,'b');
assert.deepEqual(chart.readState('?'+chart.query({...chart.preset('current'),group:'buffered-motion',family:'low-power',condition:'monitoring'}),rows),{...chart.preset('current'),group:'buffered-motion',family:'low-power',condition:'monitoring'});
for(const token of ['__proto__','toString','not-a-family']) assert.equal(chart.readState('?group='+token+'&family='+token,rows).group,'low-power');
if (!process.argv.includes('--browser')) {
  console.log('Parking chart numeric, selection, voltage, timing-method, and public-asset contracts passed.');
  process.exit(0);
}
const python = String.raw`
import base64, functools, http.server, json, os, pathlib, tempfile, threading, urllib.parse, xml.etree.ElementTree as ET
from playwright.sync_api import sync_playwright
class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args): pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory='docs'))
threading.Thread(target=server.serve_forever,daemon=True).start()
url='http://127.0.0.1:%s/parking-charts.html'%server.server_port
scratch=pathlib.Path.home()/'.hermes/cache/scratch'
scratch.mkdir(parents=True,exist_ok=True)
out=pathlib.Path(os.environ.get('PARKING_CHART_ARTIFACTS') or tempfile.mkdtemp(prefix='parking-charts-',dir=str(scratch)))
out.mkdir(parents=True,exist_ok=True)
data=json.load(open('docs/data/parking-measurements.json'))
rows=data['measurements']; byid={r['id']:r for r in rows}
seed=['vortex-sheet-row-'+str(n) for n in [4,6,9,11,15,17,21]]
current={'vortex-sheet-row-'+str(n):v for n,v in [(6,36),(4,35),(21,15),(11,11),(15,5),(9,1),(17,1)]}
delay={'vortex-sheet-row-'+str(n):v for n,v in [(21,'13.83'),(4,'2.10'),(6,'2.00'),(15,'1.80'),(11,'1.30'),(9,'1.00'),(17,'0.83')]}
def ready(page):
    page.wait_for_function("() => document.querySelectorAll('#chart-picker input[data-id]').length > 0")
    page.wait_for_function("() => document.querySelector('#chart-canvas').getAttribute('aria-busy') === 'false'")
def params(ids,metric='watts',**kw):
    p=[('selection','1'),('metric',metric)]+[('id',id) for id in ids]+list(kw.items())
    return urllib.parse.urlencode(p)
def row(page,id): return page.locator('#chart-canvas [data-measurement="%s"]'%id)
def fit_svg(page):
    assert page.locator('#chart-canvas svg [data-role="chart-heading"]').evaluate_all("es=>es.length>=2&&es.every(e=>e.getAttribute('text-anchor')==='middle'&&Number(e.getAttribute('x'))===e.ownerSVGElement.viewBox.baseVal.width/2)"), 'Centered chart headings'
    assert 'Zero baseline' not in page.locator('#chart-canvas svg > g').text_content()
    assert '(Lower is Better)' in page.locator('#chart-canvas svg [data-role="chart-heading"]').last.text_content()
    axis=page.locator('#chart-canvas svg [data-role="chart-axis"]')
    assert axis.count()==1
    assert axis.evaluate("e=>e.getBBox().y>Math.max(...[...e.ownerSVGElement.querySelectorAll('[data-measurement]')].map(g=>g.getBBox().y+g.getBBox().height))"), 'Axis label below chart'
    if page.locator('#chart-metric').input_value()=='watts':assert axis.text_content()=='Power Draw (Watts)'
    assert page.locator('#chart-canvas svg').evaluate('''s => [...s.querySelectorAll('text')].every(t=>{const b=t.getBoundingClientRect(),r=s.getBoundingClientRect();return b.left>=r.left-1 && b.top>=r.top-1 && b.right<=r.right+1 && b.bottom<=r.bottom+1})'''), 'SVG text clipping'
def download(page,button,name):
    with page.expect_download() as d: page.locator(button).click()
    dest=out/name; d.value.save_as(dest); return dest
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    context=browser.new_context(accept_downloads=True)
    page=context.new_page(); errors=[]; requests=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('request',lambda r:requests.append(r.url))
    page.goto(url); ready(page)
    assert page.locator('#chart-group').input_value()=='low-power'
    assert page.locator('#chart-condition').input_value()=='monitoring'
    assert page.locator('#chart-highlight').input_value()==''
    assert page.locator('#chart-data-status').text_content()=='599 measurements · 48 models'
    assert page.locator('#chart-canvas [data-measurement]').count()==7
    assert '12.4 V' in page.locator('#chart-canvas').text_content()
    for id,value in current.items():
        assert row(page,id).locator('[data-kind=value]').text_content()==str(value)+' mA'
        assert float(row(page,id).get_attribute('data-max'))==value
    assert [float(v) for v in page.locator('#chart-canvas [data-measurement]').evaluate_all('es=>es.map(e=>e.dataset.max)')]==[36,35,15,11,5,1,1]
    # Exact linear widths, including 1 mA. No artificial minimum bar width.
    w36=float(row(page,'vortex-sheet-row-6').locator('rect').get_attribute('width'))
    w1=float(row(page,'vortex-sheet-row-9').locator('rect').get_attribute('width'))
    assert abs(w36/w1-36)<1e-8
    assert page.locator('#chart-canvas [data-highlight=true]').count()==0
    assert row(page,'vortex-sheet-row-6').locator('rect').get_attribute('fill')=='#559bd4'
    assert 'Power Draw at Idle' in page.locator('#chart-canvas svg > g').text_content()
    assert 'Orange highlights' not in page.locator('#chart-canvas svg > g').text_content()
    assert row(page,'vortex-sheet-row-6').locator('text').count()==2
    assert row(page,'vortex-sheet-row-12').count()==0
    assert 'Energy saving' not in row(page,'vortex-sheet-row-11').text_content()
    fit_svg(page)
    for width in [320,375,768,1440]:
        page.set_viewport_size({'width':width,'height':1000})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Page overflow '+str(width)
        assert page.locator('#chart-settings input:not([type=checkbox]), #chart-settings select, .charts-actions button, #chart-settings .chart-check').evaluate_all('es => es.every(e=>{const r=e.getBoundingClientRect();return r.left>=0 && r.right<=innerWidth+1 && r.height>=40})')
        fit_svg(page)
        assert page.locator('.charts-page select').evaluate_all("es=>es.every(e=>{const s=getComputedStyle(e);return s.appearance==='none' && s.paddingRight==='44px' && s.backgroundPosition.includes('14px') && s.backgroundSize==='16px 16px'})"), 'Dropdown chevron inset'
        page.screenshot(path=str(out/('page-'+str(width)+'.png')),full_page=True)
    page.emulate_media(forced_colors='active')
    assert page.locator('#chart-metric').evaluate("e=>getComputedStyle(e).appearance==='auto' && getComputedStyle(e).backgroundImage==='none'")
    page.emulate_media(forced_colors='none')
    page.locator('#chart-sort').focus()
    # macOS native select keyboard typeahead, then commit with Tab.
    page.keyboard.press('l')
    page.keyboard.press('Tab')
    assert page.locator('#chart-sort').input_value()=='asc'
    page.locator('#preset-current').click()
    # Real downloadable initial artifacts, not screenshot substitutes.
    download(page,'#chart-svg','default-no-highlight.svg')
    download(page,'#chart-png','default-no-highlight-2x.png')
    page.locator('#chart-highlight').select_option('Viofo T340')
    assert row(page,'vortex-sheet-row-6').get_attribute('data-highlight')=='true'
    assert row(page,'vortex-sheet-row-6').locator('rect').get_attribute('fill')=='#ef8a2c'
    sv=download(page,'#chart-svg','idle-current.svg')
    png=download(page,'#chart-png','idle-current-2x.png')
    root=ET.parse(sv).getroot(); w=int(root.attrib['width']); h=int(root.attrib['height'])
    text=' '.join(root.itertext())
    assert '1 mA' in text and '36 mA' in text and '12.4 V' in text
    assert 'source' in text.lower() and 'Vortex Radar' in text
    assert '<foreignObject' not in sv.read_text() and '<script' not in sv.read_text()
    assert 'docs.google.com' not in text
    raw=png.read_bytes(); assert raw[:8]==b'\x89PNG\r\n\x1a\n'
    assert int.from_bytes(raw[16:20],'big')==w*2 and int.from_bytes(raw[20:24],'big')==h*2
    encoded=base64.b64encode(raw).decode()
    image=page.evaluate('''async data=>{const i=new Image();i.src='data:image/png;base64,'+data;await i.decode();const c=document.createElement('canvas');c.width=i.width;c.height=i.height;const x=c.getContext('2d');x.drawImage(i,0,0);const p=x.getImageData(0,0,c.width,c.height).data;let ink=0,blue=0,orange=0;for(let k=0;k<p.length;k+=4){if(p[k]<180||p[k+1]<180||p[k+2]<180)ink++;if(p[k+2]>p[k]+30&&p[k+2]>120)blue++;if(p[k]>200&&p[k+1]>80&&p[k+1]<190&&p[k+2]<90)orange++;}return {width:i.width,height:i.height,corner:[...p.slice(0,4)],ink,blue,orange}}''',encoded)
    assert image['corner']==[255,255,255,255] and image['ink']>15000 and image['blue']>1000 and image['orange']>1000, image
    assert page.locator('#chart-canvas [data-kind=value]').evaluate_all('es=>es.every(e=>e.getAttribute("font-size")==="16")')
    assert page.locator('#chart-canvas svg metadata').count()==1
    assert not page.locator('#chart-canvas svg text').filter(has_text='Sources and configurations').count()
    compact_height=int(page.locator('#chart-canvas svg').get_attribute('height'))
    page.locator('#chart-details').check()
    assert int(page.locator('#chart-canvas svg').get_attribute('height'))>compact_height
    assert page.locator('#chart-canvas svg text').filter(has_text='Sources and configurations').count()==1
    page.reload();ready(page)
    assert page.locator('#chart-details').is_checked()
    fit_svg(page)
    download(page,'#chart-svg','detailed-sources.svg')
    page.locator('#chart-details').uncheck()
    # Sort, model highlight, title, and every selected ID survive share/reload.
    page.locator('#chart-sort').select_option('asc')
    page.locator('#chart-highlight').select_option('Thinkware U3000')
    page.locator('#chart-title').fill('My exact comparison & configurations')
    page.wait_for_function("() => new URLSearchParams(location.search).get('title')==='My exact comparison & configurations'")
    shared=page.url; page.locator('#chart-share').click()
    page.wait_for_function("() => document.querySelector('#chart-action-status').textContent.length>0")
    page.reload();ready(page)
    assert page.url==shared and page.locator('#chart-sort').input_value()=='asc', (page.url,shared,page.locator('#chart-sort').input_value())
    assert page.locator('#chart-highlight').input_value()=='Thinkware U3000'
    assert page.locator('#chart-title').input_value()=='My exact comparison & configurations'
    assert row(page,'vortex-sheet-row-11').get_attribute('data-highlight')=='true'
    assert row(page,'vortex-sheet-row-12').count()==0
    assert float(page.locator('#chart-canvas [data-measurement]').first.get_attribute('data-max'))==1
    # Seven separate, method-qualified recording delays.
    page.locator('#preset-delay').click()
    assert page.locator('#chart-canvas [data-measurement]').count()==7
    for id,value in delay.items(): assert row(page,id).locator('[data-kind=value]').text_content()==value+' s'
    assert row(page,'vortex-sheet-row-12').count()==0
    download(page,'#chart-svg','recording-delay.svg');download(page,'#chart-png','recording-delay-2x.png')
    fit_svg(page)
    page.locator('#chart-metric').select_option('wake')
    assert page.locator('#chart-canvas svg').count()==0
    assert 'No impact to first frame data for:' in page.locator('#chart-notice').text_content()
    assert 'Viofo T340' in page.locator('#chart-notice').text_content()
    assert page.locator('#chart-svg').is_disabled()
    page.locator('#preset-current').click()
    assert page.locator('#chart-canvas [data-measurement]').count()==7
    page.locator('#chart-group').select_option('all')
    page.locator('#chart-advanced > summary').click()
    page.locator('#chart-condition').select_option('')
    assert page.locator('#chart-picker input[data-id]').count()==599
    # Aliases match their one canonical group, and exact model variants remain distinct.
    for search,label in [('Nexus 5','Vantrue N5'),('N5','Vantrue N5'),('Sonnet 1 (S1) Pro','Vantrue S1 Pro'),('4K Omni [X800]','70mai 4K Omni'),('ARC800','Thinkware ARC 800'),('S1-QHD Infinite','Vueroid S1-QHD Infinite')]:
        page.locator('#chart-search').fill(search)
        assert page.locator('.chart-model[data-model="%s"]'%label).count()==1,(search,label)
    before_details=page.url
    page.locator('.chart-test-details > summary').first.click()
    assert page.url==before_details,'Test details must not toggle the selection'
    page.locator('#chart-search').fill('S1 Pro')
    choose=page.locator('#chart-picker input[data-id]').first
    chosen=choose.get_attribute('data-id'); choose.check()
    assert chosen in urllib.parse.parse_qs(urllib.parse.urlparse(page.url).query)['id']
    page.locator('#chart-metric').select_option('watts')
    assert row(page,chosen).count()==1 or 'not shown' in page.locator('#chart-notice').text_content()
    # Selection remains when searching and clearing only removes selected measurements.
    page.locator('#chart-search').fill('NO SUCH CAMERA'); assert page.locator('.chart-model').count()==0
    assert chosen in urllib.parse.parse_qs(urllib.parse.urlparse(page.url).query)['id']
    page.locator('#chart-search').fill('')
    # Forty actual, separately plotted configurations, not a four-measurement cap.
    ids=[r['id'] for r in rows if isinstance(r.get('power_w'),(int,float)) and not r.get('power_w_min')][:40]
    page.goto(url+'?'+params(ids,group='all',condition=''));ready(page)
    assert page.locator('#chart-canvas [data-measurement]').count()==40
    assert page.locator('#chart-picker input:checked').count()==40
    page.reload();ready(page); assert page.locator('#chart-canvas [data-measurement]').count()==40
    fit_svg(page);download(page,'#chart-svg','forty-configurations.svg')
    forty_png=download(page,'#chart-png','forty-configurations-2x.png').read_bytes()
    assert forty_png[:8]==b'\x89PNG\r\n\x1a\n' and len(forty_png)>10000
    assert int.from_bytes(forty_png[16:20],'big')==int(page.locator('#chart-canvas svg').get_attribute('width'))*2
    # Watts stay source-exact. Never infer 0.0124 W from a 1 mA source row.
    page.goto(url+'?'+params(seed));ready(page)
    assert row(page,'vortex-sheet-row-9').locator('[data-kind=value]').text_content()=='0.01 W'
    # Mixed known voltages, then unknown voltage, must block measured mA.
    different=next(r['id'] for r in rows if r.get('voltage_v')==12.6 and r.get('current_ma') is not None)
    unknown=next(r['id'] for r in rows if r.get('voltage_v') is None and r.get('current_ma') is not None)
    for id in [different,unknown]:
        page.goto(url+'?'+params([seed[0],id],'current'));ready(page)
        assert 'blocked' in page.locator('#chart-notice').text_content()
        assert page.locator('#chart-canvas svg').count()==0
        assert page.locator('#chart-png').is_disabled()
        page.locator('#chart-switch-watts').click()
        assert page.locator('#chart-metric').input_value()=='watts'
        assert page.locator('#chart-canvas svg').count()==1
    # Actual source range, with endpoint markers and no scalar rectangle.
    ranged=next(r for r in rows if r.get('power_w_min') is not None)
    page.goto(url+'?'+params([ranged['id']]));ready(page)
    assert row(page,ranged['id']).locator('[data-kind=range]').count()==1
    assert row(page,ranged['id']).locator('rect').count()==0
    assert float(row(page,ranged['id']).get_attribute('data-min'))==ranged['power_w_min']
    assert float(row(page,ranged['id']).get_attribute('data-max'))==ranged['power_w_max']
    download(page,'#chart-svg','source-range.svg')
    # Established first-frame range remains separate from reported recording delay.
    wake=next(r for r in rows if r.get('wake_seconds_min') is not None)
    page.goto(url+'?'+params([wake['id']],'wake'));ready(page)
    assert row(page,wake['id']).locator('[data-kind=range]').count()==1
    # Malicious share URL cannot insert tags, handlers, arbitrary measurements, or CSS.
    evil='<script>window.pwned=1</script><svg onload="window.pwned=2">&'
    page.goto(url+'?'+params([seed[0],'made-up-id'],'watts',title=evil,highlight='javascript:alert(1)'));ready(page)
    assert page.evaluate('window.pwned') is None
    assert page.locator('#chart-canvas script,#chart-canvas foreignObject,#chart-canvas [onload]').count()==0
    assert page.locator('#chart-canvas [data-measurement]').count()==1
    bad=download(page,'#chart-svg','escaped-title.svg'); ET.parse(bad)
    assert '&lt;script&gt;' in bad.read_text() and '<script>' not in bad.read_text()
    fit_svg(page)
    # Isolated adversarial dataset fixture. No disk or real source measurements are changed.
    fixture=json.loads(json.dumps(data));f={r['id']:r for r in fixture['measurements']}
    a,b,c=seed[:3]
    f[a].update(power_w=0,power_w_min=None,power_w_max=None,brand='=SUM(1,1)',source_url='javascript:window.pwned=3',source_is_private=False)
    f[b].update(power_w=None,power_w_min=None,power_w_max=None)
    f[c].update(power_w=2,power_w_min=1,power_w_max=3)
    page.route('**/data/parking-measurements.json',lambda route:route.fulfill(json=fixture))
    page.goto(url+'?'+params([a,b,c]));ready(page)
    assert row(page,a).locator('[data-kind=zero]').count()==1
    assert row(page,a).locator('[data-kind=value]').text_content()=='0 W'
    assert row(page,b).count()==0 and 'No measured power data for: Viofo T340. That selection is not shown.' == page.locator('#chart-notice').text_content()
    assert 'not shown' not in page.locator('#chart-canvas svg > g').text_content()
    assert 'unavailable' not in page.locator('#chart-canvas svg > g').text_content()
    assert row(page,c).locator('[data-kind=range]').count()==1 and row(page,c).locator('rect').count()==0
    assert row(page,c).locator('[data-kind=value]').text_content()=='1–3 W'
    fit_svg(page)
    safe=download(page,'#chart-svg','fixture-zero-range.svg')
    assert 'javascript:' not in safe.read_text()
    csv=download(page,'#chart-csv','fixture-safe.csv').read_text(encoding='utf-8-sig')
    assert "'=SUM(1,1)" in csv and 'javascript:' not in csv
    f[a].update(disabled=True,power_w=1)
    f[b].update(reported_startup_seconds=99,reported_startup_method='unknown',wake_seconds=None)
    page.goto(url+'?'+params([a,b]));ready(page)
    assert page.locator('#chart-canvas svg').count()==0
    page.locator('#chart-metric').select_option('delay')
    assert page.locator('#chart-canvas svg').count()==0
    page.locator('#chart-metric').select_option('wake')
    assert page.locator('#chart-canvas svg').count()==0
    page.unroute('**/data/parking-measurements.json')
    # One visible checkbox per model. Channel overrides choose real source IDs.
    page.goto(url);ready(page)
    assert not page.locator('#chart-advanced').evaluate('e=>e.open')
    assert page.locator('#chart-condition').is_hidden()
    assert page.locator('#picker-title').text_content()=='Choose your dashcams and parking modes'
    for selector in ['#chart-highlight option:not([value=""])','.chart-model-choice','.chart-model']:
        assert page.locator(selector).evaluate_all("es=>{const names=es.map(e=>e.dataset.model||e.textContent);return names.every((name,i)=>i===0||names[i-1].localeCompare(name,undefined,{numeric:true,sensitivity:'base'})<=0)}"), 'Natural model-name ordering'
    elite=[name for name in page.locator('#chart-highlight option').all_text_contents() if name.startswith('Blackvue Elite ')]
    assert elite==['Blackvue Elite 8','Blackvue Elite 9','Blackvue Elite 10'], elite
    assert page.locator('#chart-model-picker input[type=checkbox]').evaluate_all('es=>es.every(e=>e.getBoundingClientRect().height>0)')
    omni=page.locator('.chart-model-choice[data-model="70mai 4K Omni"]')
    assert omni.count()==1 and omni.locator('input[type=checkbox]').count()==1
    assert not omni.locator('.chart-model-setup').evaluate('e=>e.open')
    omni_rows=[r for r in rows if r['brand']=='70mai' and 'Omni' in r['model'] and r['category'] in ['impact-sleep','radar'] and r['state']=='monitoring']
    high=max(r['installed_channels'] for r in omni_rows if isinstance(r.get('installed_channels'),int))
    assert omni.locator('select[data-channels]').input_value()==str(high)
    omni.locator('input[type=checkbox]').focus()
    page.keyboard.press('Space')
    assert omni.locator('input[type=checkbox]').is_checked()
    assert page.locator('#chart-metric').input_value()=='watts'
    assert 'Switched to W' in page.locator('#chart-action-status').text_content()
    assert page.locator('#chart-canvas svg').count()==1
    assert omni.locator('input[type=checkbox]').evaluate('e=>e===document.activeElement')
    selected=urllib.parse.parse_qs(urllib.parse.urlparse(page.url).query)['id']
    omni_ids=[id for id in selected if byid[id] in omni_rows]
    assert len(omni_ids)==1 and byid[omni_ids[0]]['installed_channels']==high
    omni.locator('.chart-model-setup > summary').click()
    lower=min(r['installed_channels'] for r in omni_rows if isinstance(r.get('installed_channels'),int))
    assert lower<high
    omni.locator('select[data-channels]').select_option(str(lower))
    changed=urllib.parse.parse_qs(urllib.parse.urlparse(page.url).query)['id']
    omni_changed=[id for id in changed if byid[id] in omni_rows]
    assert len(omni_changed)==1 and byid[omni_changed[0]]['installed_channels']==lower and omni_changed!=omni_ids
    assert float(row(page,omni_changed[0]).get_attribute('data-max'))==byid[omni_changed[0]]['power_w']
    page.reload();ready(page)
    assert omni.locator('select[data-channels]').input_value()==str(lower)
    page.locator('#chart-group').select_option('buffered')
    box=page.locator('.chart-model-choice[data-model="Blackvue DR970X BOX-2CH Plus"]')
    assert box.count()==1 and box.locator('input[type=checkbox]').count()==1
    assert not box.locator('.chart-model-setup').evaluate('e=>e.open')
    box.locator('input[type=checkbox]').check()
    box_selected=urllib.parse.parse_qs(urllib.parse.urlparse(page.url).query)['id']
    assert len([id for id in box_selected if 'BOX' in byid[id]['model'] and 'DR970' in byid[id]['model']])==1
    for family,condition in [('time-lapse','time-lapse'),('low-bitrate','continuous')]:
        page.locator('#chart-group').select_option(family)
        assert page.locator('#chart-model-picker input[type=checkbox]').count()>0
        assert page.locator('#chart-condition').input_value()==condition
    # Old explicit links retain multiple measurements until that model is edited.
    legacy=['vortex-sheet-row-11','vortex-sheet-row-12']
    page.goto(url+'?'+params(legacy,'current',group='low-power'));ready(page)
    assert set(urllib.parse.parse_qs(urllib.parse.urlparse(page.url).query)['id'])==set(legacy)
    assert page.locator('#chart-canvas [data-measurement]').count()==2
    assert 'Radar impact detection' in row(page,'vortex-sheet-row-12').text_content()
    assert 'Energy saving' in row(page,'vortex-sheet-row-11').text_content()
    page.reload();ready(page)
    assert page.locator('#chart-canvas [data-measurement]').count()==2
    u=page.locator('.chart-model-choice[data-model="Thinkware U3000"]')
    u.locator('input[type=checkbox]').uncheck()
    assert 'id' not in urllib.parse.parse_qs(urllib.parse.urlparse(page.url).query)
    # Functional quick groups are explicit, complete and waiting-state comparisons.
    page.goto(url);ready(page)
    before=page.locator('#chart-canvas [data-measurement]').evaluate_all('es=>es.map(e=>e.dataset.measurement)')
    page.locator('#chart-group').select_option('buffered-motion')
    assert page.locator('#chart-condition').input_value()=='monitoring'
    assert page.locator('#chart-canvas [data-measurement]').evaluate_all('es=>es.map(e=>e.dataset.measurement)')==before
    models=page.locator('#chart-model-picker input[type=checkbox]').evaluate_all('es=>es.map(e=>e.dataset.model)')
    assert len(models)>7 and len(models)==len(set(models))
    assert 'Compare shown models · '+str(len(models)) == page.locator('#chart-apply-group').text_content()
    page.reload();ready(page)
    assert page.locator('#chart-group').input_value()=='buffered-motion'
    assert page.locator('#chart-canvas [data-measurement]').evaluate_all('es=>es.map(e=>e.dataset.measurement)')==before
    page.locator('#chart-apply-group').click()
    assert page.locator('#chart-metric').input_value()=='watts'
    assert 'Switched to W' in page.locator('#chart-action-status').text_content()
    matching=urllib.parse.parse_qs(urllib.parse.urlparse(page.url).query)['id']
    assert len(matching)==len(models)
    assert all(byid[id]['state']=='monitoring' for id in matching)
    assert len({(byid[id]['brand'],byid[id]['model']) for id in matching})==len(matching)
    assert page.locator('#chart-model-picker input:checked').count()==len(models)
    plotted=page.locator('#chart-canvas [data-measurement]').evaluate_all('es=>es.map(e=>e.dataset.measurement)')
    expected=[id for id in matching if isinstance(byid[id].get('power_w'),(int,float)) or byid[id].get('power_w_min') is not None]
    assert set(plotted)==set(expected)
    assert 'Power Draw at Idle' in page.locator('#chart-canvas svg > g').text_content()
    fit_svg(page)
    download(page,'#chart-svg','buffered-motion.svg');download(page,'#chart-png','buffered-motion-2x.png')
    download(page,'#chart-csv','buffered-motion.csv')
    (out/'buffered-motion-selection.json').write_text(json.dumps({'selected_ids':matching,'plotted_ids':plotted,'share_query':urllib.parse.urlparse(page.url).query},indent=2))
    page.reload();ready(page)
    assert page.locator('#chart-group').input_value()=='buffered-motion'
    assert page.locator('#chart-metric').input_value()=='watts'
    assert set(page.locator('#chart-canvas [data-measurement]').evaluate_all('es=>es.map(e=>e.dataset.measurement)'))==set(plotted)
    # Readable variants, named provenance, real expanded setup screenshots.
    n4=[r['id'] for r in rows if r['model']=='N4 Pro S' and r['category']=='impact-sleep' and r['state']=='monitoring']
    e1=['rcg530-660569-1','rcg530-660569-2']
    for model,ids,slug in [('Vantrue N4 Pro S',n4,'n4-pro-s'),('Vantrue E1 Pro',e1,'e1-pro')]:
        page.goto(url+'?'+params(ids,'watts',details='1'));ready(page)
        page.locator('#chart-search').fill(model.replace('Vantrue ',''))
        card=page.locator('.chart-model-choice[data-model="%s"]'%model)
        card.locator('.chart-model-setup > summary').click()
        options=card.locator('select[data-test] option').all_text_contents()
        assert len(options)==len(set(options)),options
        assert all(not any(id in option for id in byid) for option in options)
        assert 'Firmware' in card.text_content() and 'Tested by' in card.text_content()
        assert 'Available tests differ by' in card.text_content()
        if slug=='e1-pro':
            assert any('Quick Start' in text for text in options) and any('Power Saving' in text for text in options)
            assert 'Interior IR' not in card.text_content()
            assert 'Retro CarGuy530 (rcg530)' in card.text_content()
            assert card.locator('a').first.get_attribute('href')==byid[e1[0]]['source_url']
        else:
            assert 'firmware' in card.locator('.chart-variant-summary').text_content()
        assert not page.locator('#chart-canvas svg text').evaluate_all('es=>es.some(e=>/vortex-sheet-row-|rcg530-\\d/.test(e.textContent))')
        assert set(page.locator('#chart-canvas [data-measurement]').evaluate_all('es=>es.map(e=>e.dataset.measurement)'))==set(ids)
        download(page,'#chart-svg',slug+'-detailed-sources.svg')
        page.locator('.site-header').evaluate("e=>e.style.visibility='hidden'")
        page.locator('#chart-canvas svg').screenshot(path=str(out/(slug+'-detailed-sources.png')))
        page.locator('.site-header').evaluate("e=>e.style.visibility=''")
        fit_svg(page)
        if slug=='n4-pro-s':
            card.locator('select[data-test]').select_option('vortex-sheet-row-21')
            assert card.locator('a',has_text='Vortex Radar testing notes').count()==1
        for width in [1440,375]:
            page.set_viewport_size({'width':width,'height':1100})
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            card.scroll_into_view_if_needed()
            page.screenshot(path=str(out/(slug+'-setup-'+str(width)+'.png')))
            card.screenshot(path=str(out/(slug+'-setup-card-'+str(width)+'.png')))
        if slug=='e1-pro':
            card.locator('select[data-test]').select_option(e1[1])
            assert '0.21 W' in card.text_content()
            assert card.locator('select[data-test]').input_value()==e1[1]
    # Final page restored to the genuine seven-camera initial dataset for review.
    page.goto(url);ready(page)
    pro_s=page.locator('.chart-model-choice[data-model="Vantrue E1 Pro S"]')
    assert pro_s.count()==1
    pro_s.locator('input[type=checkbox]').check()
    page.wait_for_function("()=>document.querySelector('#chart-canvas [data-measurement=\"rcg530-675957-5\"] [data-kind=value]')?.textContent==='0.09 W'")
    assert 'Prototype' in row(page,'rcg530-675957-5').text_content()
    pro_s.locator('.chart-model-setup > summary').click()
    assert '1.37–1.42 s' in pro_s.locator('.chart-test-fields').text_content()
    for family,id,value in [('buffered-motion','rcg530-675957-7','2.85 W'),('hybrid','rcg530-675957-1','0.87 W')]:
        page.locator('#chart-group').select_option(family)
        pro_s.locator('input[type=checkbox]').check()
        page.wait_for_function("([id,value])=>document.querySelector('[data-measurement=\"'+id+'\"] [data-kind=value]')?.textContent===value",arg=[id,value])
    page.locator('#chart-group').select_option('time-lapse')
    opts=pro_s.locator('select[data-test] option').all_text_contents()
    assert any('1 Second Per Frame' in text for text in opts) and any('2 Seconds Per Frame' in text for text in opts)
    page.goto(url);ready(page)
    page.screenshot(path=str(out/'review-initial-page.png'),full_page=True)
    page.locator('#picker-title').evaluate('e=>window.scrollTo(0,e.getBoundingClientRect().top+scrollY-100)')
    page.screenshot(path=str(out/'primary-model-picker.png'))
    assert not errors,errors
    assert not any('docs.google.com' in r or 'sheets.googleapis.com' in r for r in requests)
    (out/'verification.json').write_text(json.dumps({'measurements':599,'models':48,'viewports':[320,375,768,1440],'current_values':current,'delay_values':delay,'decoded_png':image,'page_errors':errors,'selected_buffered_models':len(matching),'selected_buffered_ids':matching,'checks':['primary-one-checkbox','70mai-highest-channel-default','channel-override-exact-value','Blackvue-single-model-choice','functional-family-evidence','explicit-model-bulk','legacy-multiple-ID-preservation','native-keyboard-typeahead','forced-colors-native-select','source-presets','same-voltage-block','method-separation','share-reload','aliases','40-configurations','true-zero-scale','range-endpoints','null-zero','escaped-svg','csv-injection','2x-png-white-canvas','text-bounds']},indent=2))
    browser.close()
server.shutdown()
print('PASS: Node contracts and real Chrome acceptance at 320, 375, 768, and 1440 px')
print('Review artifacts: '+str(out))
`;
const result = spawnSync(process.env.PYTHON || 'python3', ['-c', python], { cwd: path.resolve(__dirname, '..'), encoding: 'utf8', env: process.env, timeout: 240000 });
process.stdout.write(result.stdout || ''); process.stderr.write(result.stderr || '');
if (result.error) throw result.error;
process.exitCode = result.status === null ? 1 : result.status;
