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
assert.equal(rows.length, 588);
assert.equal(UI.groupModels(rows).length, 47);
assert.equal(new Set(rows.map(r => r.id)).size, 588);
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
seed=['vortex-sheet-row-'+str(n) for n in [4,6,9,11,12,15,17,21]]
current={'vortex-sheet-row-'+str(n):v for n,v in [(6,36),(4,35),(12,17),(21,15),(11,11),(15,5),(9,1),(17,1)]}
delay={'vortex-sheet-row-'+str(n):v for n,v in [(21,'13.83'),(4,'2.10'),(6,'2.00'),(15,'1.80'),(11,'1.30'),(9,'1.00'),(17,'0.83')]}
def ready(page):
    page.wait_for_function("() => document.querySelectorAll('#chart-picker input[data-id]').length > 0")
    page.wait_for_function("() => document.querySelector('#chart-canvas').getAttribute('aria-busy') === 'false'")
def params(ids,metric='watts',**kw):
    p=[('selection','1'),('metric',metric)]+[('id',id) for id in ids]+list(kw.items())
    return urllib.parse.urlencode(p)
def row(page,id): return page.locator('#chart-canvas [data-measurement="%s"]'%id)
def fit_svg(page):
    assert page.locator('#chart-canvas svg').evaluate('''s => [...s.querySelectorAll('text')].every(t=>{const b=t.getBBox();return b.x>=0 && b.y>=0 && b.x+b.width<=s.viewBox.baseVal.width+1 && b.y+b.height<=s.viewBox.baseVal.height+1})'''), 'SVG text clipping'
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
    assert page.locator('#chart-picker input[data-id]').count()==588
    assert page.locator('.chart-model').count()==47
    assert page.locator('#chart-canvas [data-measurement]').count()==8
    assert '12.4 V' in page.locator('#chart-canvas').text_content()
    for id,value in current.items():
        assert row(page,id).locator('[data-kind=value]').text_content()==str(value)+' mA'
        assert float(row(page,id).get_attribute('data-max'))==value
    assert [float(v) for v in page.locator('#chart-canvas [data-measurement]').evaluate_all('es=>es.map(e=>e.dataset.max)')]==[36,35,17,15,11,5,1,1]
    # Exact linear widths, including 1 mA. No artificial minimum bar width.
    w36=float(row(page,'vortex-sheet-row-6').locator('rect').get_attribute('width'))
    w1=float(row(page,'vortex-sheet-row-9').locator('rect').get_attribute('width'))
    assert abs(w36/w1-36)<1e-8
    assert row(page,'vortex-sheet-row-6').get_attribute('data-highlight')=='true'
    assert row(page,'vortex-sheet-row-6').locator('rect').get_attribute('fill')=='#ef8a2c'
    fit_svg(page)
    for width in [320,375,768,1440]:
        page.set_viewport_size({'width':width,'height':1000})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Page overflow '+str(width)
        assert page.locator('#chart-settings input:not([type=checkbox]), #chart-settings select, .charts-actions button, #chart-settings .chart-check').evaluate_all('es => es.every(e=>{const r=e.getBoundingClientRect();return r.left>=0 && r.right<=innerWidth+1 && r.height>=40})')
        fit_svg(page)
        page.screenshot(path=str(out/('page-'+str(width)+'.png')),full_page=True)
    # Real downloadable initial artifacts, not screenshot substitutes.
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
    shared=page.url; page.locator('#chart-share').click()
    page.wait_for_function("() => document.querySelector('#chart-action-status').textContent.length>0")
    page.reload();ready(page)
    assert page.url==shared and page.locator('#chart-sort').input_value()=='asc'
    assert page.locator('#chart-highlight').input_value()=='Thinkware U3000'
    assert page.locator('#chart-title').input_value()=='My exact comparison & configurations'
    assert row(page,'vortex-sheet-row-11').get_attribute('data-highlight')=='true'
    assert row(page,'vortex-sheet-row-12').get_attribute('data-highlight')=='true'
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
    assert '7 selected measurements' in page.locator('#chart-notice').text_content()
    assert page.locator('#chart-svg').is_disabled()
    page.locator('#preset-current').click()
    assert page.locator('#chart-canvas [data-measurement]').count()==8
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
    assert row(page,chosen).count()==1 or 'unavailable' in page.locator('#chart-notice').text_content()
    # Selection remains when searching and clearing only removes selected measurements.
    page.locator('#chart-search').fill('NO SUCH CAMERA'); assert page.locator('.chart-model').count()==0
    assert chosen in urllib.parse.parse_qs(urllib.parse.urlparse(page.url).query)['id']
    page.locator('#chart-search').fill('')
    # Forty actual, separately plotted configurations, not a four-measurement cap.
    ids=[r['id'] for r in rows if isinstance(r.get('power_w'),(int,float)) and not r.get('power_w_min')][:40]
    page.goto(url+'?'+params(ids));ready(page)
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
    assert row(page,b).count()==0 and '1 selected measurements' in page.locator('#chart-notice').text_content()
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
    # Final page restored to the genuine eight-row initial dataset for review.
    page.goto(url);ready(page)
    page.screenshot(path=str(out/'review-initial-page.png'),full_page=True)
    assert not errors,errors
    assert not any('docs.google.com' in r or 'sheets.googleapis.com' in r for r in requests)
    (out/'verification.json').write_text(json.dumps({'measurements':588,'models':47,'viewports':[320,375,768,1440],'current_values':current,'delay_values':delay,'decoded_png':image,'page_errors':errors,'checks':['source-presets','same-voltage-block','method-separation','share-reload','aliases','40-configurations','true-zero-scale','range-endpoints','null-zero','escaped-svg','csv-injection','2x-png-white-canvas','text-bounds']},indent=2))
    browser.close()
server.shutdown()
print('PASS: Node contracts and real Chrome acceptance at 320, 375, 768, and 1440 px')
print('Review artifacts: '+str(out))
`;
const result = spawnSync(process.env.PYTHON || 'python3', ['-c', python], { cwd: path.resolve(__dirname, '..'), encoding: 'utf8', env: process.env, timeout: 240000 });
process.stdout.write(result.stdout || ''); process.stderr.write(result.stderr || '');
if (result.error) throw result.error;
process.exitCode = result.status === null ? 1 : result.status;
